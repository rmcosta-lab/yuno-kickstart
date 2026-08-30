from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest
from app.config import Settings
from app.contract_service import ContractServiceError
from app.schemas.errors import ApiErrorCode
from app.volta_text_service import (
    VoltaTextContractService,
    create_volta_text_contract_service,
)
from yuno_backend.volta.idempotency import IdempotencyResultMissing
from yuno_backend.volta.mandates.errors import (
    DraftNotApprovable,
    DraftNotFound,
    MandateConflict,
    OperationAlreadyApproved,
    StaleDraftVersion,
)
from yuno_backend.volta.negotiations.errors import (
    CallSessionNotFound,
    CarrierSessionMismatch,
    IdempotencyConflict,
    InvalidNegotiationTransition,
    NegotiationAlreadyStarted,
    OperationNotFound,
    StaleMandateVersion,
    StaleOperationVersion,
)
from yuno_backend.volta.persistence.errors import PersistenceConflict, PersistenceUnavailable
from yuno_backend.volta.text_slice import (
    AuditProjection,
    AuditQuoteProjection,
    CommitmentEvidenceNotFound,
    CommitmentProjection,
    DraftProjection,
    EscalationResolutionState,
    EvidenceArtifactUnavailable,
    EvidenceReservation,
    EvidenceReservationMismatch,
    EvidenceReservationNotFound,
    MutationOutcome,
    NegotiationProjection,
    NegotiationSummaryProjection,
    OperationProjection,
    PreContactEscalationProjection,
    SessionProjection,
)

NOW = datetime(2026, 8, 29, 12, tzinfo=UTC)
IDS = {
    name: UUID(int=index)
    for index, name in enumerate(
        (
            "draft",
            "operation",
            "mandate",
            "negotiation",
            "call",
            "carrier",
            "quote",
            "event",
            "correlation",
            "escalation",
            "commitment",
            "evidence",
            "prior_commitment",
            "prior_evidence",
            "prior_quote",
        ),
        1,
    )
}


def value(name: str) -> SimpleNamespace:
    return SimpleNamespace(value=name)


def pickup_window() -> SimpleNamespace:
    return SimpleNamespace(start_date=date(2026, 9, 3), end_date=date(2026, 9, 3))


def terms(amount: str = "8750") -> SimpleNamespace:
    return SimpleNamespace(
        amount=Decimal(amount),
        currency="MXN",
        pickup_window_start=date(2026, 9, 3),
        pickup_window_end=date(2026, 9, 3),
        conditions=("40ft dry container",),
    )


def draft_projection() -> DraftProjection:
    mandate = SimpleNamespace(
        maximum_amount=SimpleNamespace(amount=Decimal("9000"), currency="MXN"),
        pickup_window=pickup_window(),
        allowed_conditions=("40ft dry container",),
        escalation_conditions=("No carrier available within budget",),
    )
    proposal = SimpleNamespace(
        route=SimpleNamespace(origin="Puerto de Manzanillo", destination="Guadalajara"),
        pickup_date=date(2026, 9, 3),
        mandate=mandate,
    )
    draft = SimpleNamespace(
        id=IDS["draft"],
        source_prompt="Move a 40ft container from Manzanillo to Guadalajara.",
        requested_language="EN_US",
        extraction_policy_version="intake-v1",
        proposal=proposal,
        validation_issues=(),
        approval_eligible=True,
        version=1,
        created_at=NOW,
        updated_at=NOW,
    )
    return DraftProjection(draft)


def session() -> SessionProjection:
    domain_session = SimpleNamespace(
        call_id=IDS["call"],
        carrier_id=IDS["carrier"],
        carrier_display_label="Puerto Azul Drayage",
        available_snapshot=True,
        selection_rank=1,
        channel=value("BROWSER_TEXT"),
        state=value("SELECTED"),
        created_at=NOW,
    )
    return SessionProjection(
        domain_session,
        ("route_covered", "available", "fixed_priority_1", "selection_rank_1"),
    )


def negotiation(*, escalated: bool = False) -> NegotiationProjection:
    escalation = None
    sessions = (session(),)
    if escalated:
        sessions = ()
        escalation = PreContactEscalationProjection(
            SimpleNamespace(
                id=IDS["escalation"],
                operation_id=IDS["operation"],
                reason_code="no_eligible_carrier",
                correlation_id=IDS["correlation"],
                created_at=NOW,
            ),
            "no_eligible_carrier",
            (),
            "Coordinator review required",
            EscalationResolutionState.OPEN,
        )
    domain_negotiation = SimpleNamespace(
        id=IDS["negotiation"],
        operation_id=IDS["operation"],
        operation_version=2,
        sessions=tuple(item.session for item in sessions),
        pre_contact_escalation=None if escalation is None else escalation.escalation,
        started_at=NOW,
    )
    return NegotiationProjection(domain_negotiation, sessions, escalation)


def quote() -> SimpleNamespace:
    return SimpleNamespace(
        id=IDS["quote"],
        operation_id=IDS["operation"],
        call_id=IDS["call"],
        carrier_id=IDS["carrier"],
        terms=terms(),
        valid_until=datetime(2026, 8, 29, 13, tzinfo=UTC),
        mandate_version=1,
        eligibility=value("ELIGIBLE"),
        rejection_reasons=(),
        created_at=NOW,
    )


def evidence_reservation() -> EvidenceReservation:
    return EvidenceReservation(
        id=IDS["evidence"],
        operation_id=IDS["operation"],
        call_id=IDS["call"],
        quote_id=IDS["quote"],
        recording_reference="private/current-recording.wav",
        audio_start_ms=4200,
        item_id="synthetic-item-001",
        event_id="synthetic-event-001",
        created_at=NOW,
    )


def commitment_projection(*, superseded: bool = False) -> CommitmentProjection:
    commitment_id = IDS["prior_commitment"] if superseded else IDS["commitment"]
    evidence_id = IDS["prior_quote"] if superseded else IDS["quote"]
    quote_id = IDS["prior_quote"] if superseded else IDS["quote"]
    commitment = SimpleNamespace(
        id=commitment_id,
        operation_id=IDS["operation"],
        call_id=IDS["call"],
        quote_id=quote_id,
        carrier_id=IDS["carrier"],
        agreed_terms=terms(),
        mandate_version=1,
        lifecycle=value("CANDIDATE"),
        disposition=value("SUPERSEDED" if superseded else "ACTIVE"),
        replaces_commitment_id=None,
        created_at=NOW,
        superseded_at=NOW if superseded else None,
        evidence_id=evidence_id,
    )
    evidence = SimpleNamespace(
        id=evidence_id,
        commitment_id=commitment_id,
        recording_reference=(
            "private/prior-recording.wav" if superseded else "private/current-recording.wav"
        ),
        audio_start_ms=4200,
        item_id="synthetic-item-001",
        event_id="synthetic-event-001",
        created_at=NOW,
    )
    return CommitmentProjection(commitment, evidence)


def operation_projection() -> OperationProjection:
    mandate = SimpleNamespace(
        id=IDS["mandate"],
        version=1,
        maximum_amount=SimpleNamespace(amount=Decimal("9000"), currency="MXN"),
        pickup_window=pickup_window(),
        allowed_conditions=("40ft dry container",),
        escalation_conditions=("No carrier available within budget",),
        approval_actor="demo-coordinator",
        approved_at=NOW,
    )
    operation = SimpleNamespace(
        id=IDS["operation"],
        route=SimpleNamespace(origin="Puerto de Manzanillo", destination="Guadalajara"),
        cargo_label="40ft dry container",
        status=value("COMMITTED"),
        version=3,
        mandate=mandate,
        created_at=NOW,
    )
    return OperationProjection(
        operation,
        negotiation(),
        NegotiationSummaryProjection(IDS["negotiation"], 1, 0, 0),
        (quote(),),
        None,
        commitment_projection(),
        (),
        NOW,
    )


def audit_projection() -> AuditProjection:
    event = SimpleNamespace(
        event_id=IDS["event"],
        operation_version=2,
        actor_kind=value("SYSTEM"),
        event_type="QUOTE_RECORDED",
        occurred_at=NOW,
        correlation_id=IDS["correlation"],
        metadata={},
    )
    return AuditProjection(
        IDS["operation"],
        (event,),
        negotiation(),
        (AuditQuoteProjection(quote(), "Puerto Azul Drayage", True),),
        (commitment_projection(superseded=True), commitment_projection()),
    )


class FakeTextApplication:
    def __init__(self) -> None:
        self.commands: list[object] = []
        self.error: Exception | None = None
        self.operation_result = operation_projection()
        self.audit_result = audit_projection()

    def check(self, command: object) -> None:
        self.commands.append(command)
        if self.error is not None:
            raise self.error

    async def create_operation_draft(self, command: object):
        self.check(command)
        return MutationOutcome(draft_projection(), True)

    async def approve_operation(self, command: object):
        self.check(command)
        return MutationOutcome(operation_projection(), False)

    async def get_operation(self, operation_id: UUID):
        self.check(operation_id)
        return self.operation_result

    async def start_negotiation(self, command: object):
        self.check(command)
        return MutationOutcome(negotiation(), False)

    async def record_quote(self, command: object):
        self.check(command)
        return MutationOutcome(quote(), True)

    async def attach_commitment_evidence(self, command: object):
        self.check(command)
        return MutationOutcome(evidence_reservation(), True)

    async def create_candidate_commitment(self, command: object):
        self.check(command)
        return MutationOutcome(commitment_projection(), True)

    async def get_operation_audit(self, operation_id: UUID):
        self.check(operation_id)
        return self.audit_result


def service(
    application: FakeTextApplication | None = None,
) -> tuple[VoltaTextContractService, FakeTextApplication]:
    fake = application or FakeTextApplication()
    return VoltaTextContractService(fake, correlation_id_factory=lambda: IDS["correlation"]), fake  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_adapter_converts_draft_and_propagates_truthful_replay() -> None:
    adapter, application = service()
    result = await adapter.execute(
        "create_operation_draft",
        {"body": {"source_prompt": "Move a 40ft container.", "requested_language": "EN_US"}},
        "draft-key-001",
    )

    command = application.commands[0]
    assert command.source_prompt == "Move a 40ft container."  # type: ignore[attr-defined]
    assert command.idempotency_key == "draft-key-001"  # type: ignore[attr-defined]
    assert result.idempotency_replayed is True
    assert result.payload["proposed_mandate"]["maximum_amount_minor"] == 900000  # type: ignore[index]


@pytest.mark.asyncio
async def test_adapter_converts_quote_minor_units_and_serializes_result() -> None:
    adapter, application = service()
    result = await adapter.execute(
        "record_quote",
        {
            "call_id": str(IDS["call"]),
            "body": {
                "expected_operation_version": 2,
                "carrier_id": str(IDS["carrier"]),
                "mandate_version": 1,
                "terms": {
                    "amount_minor": 875000,
                    "currency": "MXN",
                    "pickup_window": {"start_date": "2026-09-03", "end_date": "2026-09-03"},
                    "conditions": ["40ft dry container"],
                },
                "valid_until": "2026-08-29T13:00:00Z",
            },
        },
        "quote-key-001",
    )

    command = application.commands[0]
    assert command.terms.amount == Decimal("8750")  # type: ignore[attr-defined]
    assert command.correlation_id == IDS["correlation"]  # type: ignore[attr-defined]
    assert result.payload["terms"]["amount_minor"] == 875000  # type: ignore[index]
    assert result.idempotency_replayed is True


@pytest.mark.asyncio
async def test_adapter_converts_approval_and_serializes_durable_cargo() -> None:
    adapter, application = service()
    result = await adapter.execute(
        "approve_operation",
        {
            "body": {
                "draft_id": str(IDS["draft"]),
                "expected_draft_version": 1,
                "approval_actor": "demo-coordinator",
            }
        },
        "approve-key-001",
    )

    command = application.commands[0]
    assert command.draft_id == IDS["draft"]  # type: ignore[attr-defined]
    assert command.correlation_id == IDS["correlation"]  # type: ignore[attr-defined]
    assert result.payload["cargo_label"] == "40ft dry container"  # type: ignore[index]


@pytest.mark.asyncio
async def test_adapter_converts_commitment_and_serializes_real_evidence_with_replay() -> None:
    adapter, application = service()
    result = await adapter.execute(
        "create_candidate_commitment",
        {
            "call_id": str(IDS["call"]),
            "body": {
                "expected_operation_version": 2,
                "quote_id": str(IDS["quote"]),
                "mandate_version": 1,
                "evidence_id": str(IDS["quote"]),
            },
        },
        "commitment-key-001",
    )

    command = application.commands[0]
    assert command.evidence_id == IDS["quote"]  # type: ignore[attr-defined]
    assert command.correlation_id == IDS["correlation"]  # type: ignore[attr-defined]
    assert result.idempotency_replayed is True
    assert result.payload["evidence"]["recording_reference"] == (  # type: ignore[index]
        "private/current-recording.wav"
    )
    assert result.payload["evidence"]["lifecycle"] == "CANDIDATE"  # type: ignore[index]


@pytest.mark.asyncio
async def test_adapter_serializes_operation_negotiation_and_post_f14_audit() -> None:
    adapter, _ = service()

    operation = await adapter.execute(
        "get_operation", {"operation_id": str(IDS["operation"])}, None
    )
    started = await adapter.execute(
        "start_negotiation",
        {
            "operation_id": str(IDS["operation"]),
            "body": {"expected_operation_version": 1, "channel": "BROWSER_TEXT"},
        },
        "start-key-001",
    )
    audit = await adapter.execute(
        "get_operation_audit",
        {"operation_id": str(IDS["operation"]), "cursor": None, "limit": 50},
        None,
    )

    assert operation.payload["cargo_label"] == "40ft dry container"  # type: ignore[index]
    assert operation.payload["negotiation_summary"]["valid_quote_count"] == 0  # type: ignore[index]
    assert operation.payload["active_commitment"]["commitment_id"] == str(  # type: ignore[index]
        IDS["commitment"]
    )
    assert started.payload["sessions"][0]["carrier"]["display_name"] == "Puerto Azul Drayage"  # type: ignore[index]
    assert audit.payload["quote_comparison"][0]["selected"] is True  # type: ignore[index]
    assert [item["disposition"] for item in audit.payload["commitment_history"]] == [  # type: ignore[index]
        "SUPERSEDED",
        "ACTIVE",
    ]
    for collection in ("recaps", "briefs", "recoveries", "notifications"):
        assert audit.payload[collection] == []  # type: ignore[index]


@pytest.mark.asyncio
async def test_pending_recovery_evidence_does_not_make_queries_fail() -> None:
    application = FakeTextApplication()
    pending = CommitmentProjection(commitment_projection().commitment, None)
    application.operation_result = replace(
        operation_projection(),
        active_commitment=pending,
    )
    application.audit_result = replace(
        audit_projection(),
        commitment_history=(pending, commitment_projection()),
    )
    adapter, _ = service(application)

    operation = await adapter.execute(
        "get_operation", {"operation_id": str(IDS["operation"])}, None
    )
    audit = await adapter.execute(
        "get_operation_audit",
        {"operation_id": str(IDS["operation"]), "cursor": None, "limit": 50},
        None,
    )

    assert operation.payload["active_commitment"] is None  # type: ignore[index]
    assert len(audit.payload["commitment_history"]) == 1  # type: ignore[arg-type,index]
    assert audit.payload["commitment_history"][0]["commitment_id"] == str(  # type: ignore[index]
        IDS["commitment"]
    )


@pytest.mark.asyncio
async def test_adapter_attaches_existing_f14_evidence_and_preserves_replay() -> None:
    adapter, application = service()
    result = await adapter.execute(
        "attach_commitment_evidence",
        {
            "call_id": str(IDS["call"]),
            "body": {
                "expected_operation_version": 2,
                "recording_reference": "private/current-recording.wav",
                "audio_start_ms": 4200,
                "item_id": "synthetic-item-001",
                "event_id": "synthetic-event-001",
            },
        },
        "evidence-key-001",
    )

    command = application.commands[0]
    assert command.call_id == IDS["call"]  # type: ignore[attr-defined]
    assert command.recording_reference == "private/current-recording.wav"  # type: ignore[attr-defined]
    assert command.correlation_id == IDS["correlation"]  # type: ignore[attr-defined]
    assert result.idempotency_replayed is True
    assert result.payload["evidence_id"] == str(IDS["evidence"])  # type: ignore[index]
    assert result.payload["lifecycle"] == "CANDIDATE"  # type: ignore[index]


ERROR_CASES = [
    (DraftNotFound(IDS["draft"]), 404, ApiErrorCode.RESOURCE_NOT_FOUND),
    (OperationNotFound(IDS["operation"]), 404, ApiErrorCode.RESOURCE_NOT_FOUND),
    (CallSessionNotFound(IDS["call"]), 404, ApiErrorCode.RESOURCE_NOT_FOUND),
    (StaleDraftVersion(IDS["draft"], 1, 2), 409, ApiErrorCode.STALE_DRAFT_VERSION),
    (StaleOperationVersion(IDS["operation"], 1, 2), 409, ApiErrorCode.STALE_OPERATION_VERSION),
    (StaleMandateVersion(IDS["operation"], 1, 2), 409, ApiErrorCode.MANDATE_CONFLICT),
    (
        MandateConflict(IDS["operation"], 1, ("amount_exceeds_maximum",)),
        409,
        ApiErrorCode.MANDATE_CONFLICT,
    ),
    (
        IdempotencyConflict(IDS["operation"], "record_quote", "secret-key"),
        409,
        ApiErrorCode.IDEMPOTENCY_KEY_REUSED,
    ),
    (OperationAlreadyApproved(IDS["draft"], IDS["operation"]), 409, ApiErrorCode.STATE_CONFLICT),
    (DraftNotApprovable(IDS["draft"], ("cargo_required",)), 409, ApiErrorCode.STATE_CONFLICT),
    (
        NegotiationAlreadyStarted(IDS["operation"], IDS["negotiation"]),
        409,
        ApiErrorCode.STATE_CONFLICT,
    ),
    (CarrierSessionMismatch(IDS["call"], IDS["carrier"]), 409, ApiErrorCode.STATE_CONFLICT),
    (
        InvalidNegotiationTransition(IDS["operation"], "evidence_projection_unavailable"),
        409,
        ApiErrorCode.STATE_CONFLICT,
    ),
    (
        IdempotencyResultMissing(IDS["operation"], "record_quote"),
        409,
        ApiErrorCode.STATE_CONFLICT,
    ),
    (
        CommitmentEvidenceNotFound(IDS["commitment"], IDS["evidence"]),
        409,
        ApiErrorCode.STATE_CONFLICT,
    ),
    (
        EvidenceReservationMismatch(IDS["quote"], IDS["evidence"]),
        409,
        ApiErrorCode.STATE_CONFLICT,
    ),
    (EvidenceReservationNotFound(IDS["evidence"]), 409, ApiErrorCode.STATE_CONFLICT),
    (
        EvidenceArtifactUnavailable("private/missing-recording.wav"),
        409,
        ApiErrorCode.STATE_CONFLICT,
    ),
    (
        PersistenceConflict("unique_violation", "operation", IDS["operation"]),
        409,
        ApiErrorCode.STATE_CONFLICT,
    ),
    (PersistenceUnavailable("connection_failed", "database"), 500, ApiErrorCode.INTERNAL_ERROR),
    (RuntimeError("provider-secret-response"), 500, ApiErrorCode.INTERNAL_ERROR),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("error", "status_code", "code"), ERROR_CASES)
async def test_adapter_maps_allowlisted_errors_and_redacts_everything_else(
    error: Exception,
    status_code: int,
    code: ApiErrorCode,
) -> None:
    application = FakeTextApplication()
    application.error = error
    adapter, _ = service(application)

    with pytest.raises(ContractServiceError) as captured:
        await adapter.execute("get_operation", {"operation_id": str(IDS["operation"])}, None)

    assert captured.value.status_code == status_code
    assert captured.value.code is code
    assert "secret" not in captured.value.safe_message
    assert type(error).__name__ not in captured.value.safe_message


@pytest.mark.asyncio
async def test_default_wiring_is_lazy_and_missing_database_configuration_is_safe() -> None:
    adapter = create_volta_text_contract_service(Settings(app_env="test"))

    with pytest.raises(ContractServiceError) as captured:
        await adapter.execute(
            "create_operation_draft",
            {"body": {"source_prompt": "Synthetic prompt", "requested_language": "EN_US"}},
            "draft-key-001",
        )

    assert captured.value.status_code == 500
    assert captured.value.code is ApiErrorCode.INTERNAL_ERROR
    assert "DATABASE_URL" not in captured.value.safe_message


@pytest.mark.asyncio
async def test_adapter_closes_owned_resources_once() -> None:
    closed = 0

    async def close() -> None:
        nonlocal closed
        closed += 1

    application = FakeTextApplication()
    adapter = VoltaTextContractService(application, close=close)  # type: ignore[arg-type]

    await adapter.aclose()
    await adapter.aclose()

    assert closed == 1
