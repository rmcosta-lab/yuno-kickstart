"""FastAPI-to-core adapter for the PostgreSQL-backed Volta text slice."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import httpx
from yuno_backend.database import DatabaseConfig, create_database_engine, create_session_factory
from yuno_backend.integrations.openai import OpenAIExtractionConfig, OpenAIIntakeExtractor
from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.evidence import (
    CallBrief,
    EvidenceAudio,
    EvidenceAudioNotFound,
    EvidenceAudioTooLarge,
    Recap,
    RetrieveEvidenceAudioService,
)
from yuno_backend.volta.idempotency import IdempotencyConflict, IdempotencyResultMissing
from yuno_backend.volta.intake import IntakeExtractor
from yuno_backend.volta.mandates.errors import (
    DraftNotApprovable,
    DraftNotFound,
    MandateConflict,
    OperationAlreadyApproved,
    StaleDraftVersion,
)
from yuno_backend.volta.mandates.models import (
    Mandate,
    Money,
)
from yuno_backend.volta.mandates.models import (
    PickupWindow as MandatePickupWindow,
)
from yuno_backend.volta.negotiations.errors import (
    CallSessionNotFound,
    CarrierSessionMismatch,
    InvalidNegotiationTransition,
    NegotiationAlreadyStarted,
    OperationNotFound,
    QuoteExpired,
    QuoteNotBestCandidate,
    QuoteNotEligible,
    QuoteNotFound,
    StaleMandateVersion,
    StaleOperationVersion,
)
from yuno_backend.volta.negotiations.models import Quote
from yuno_backend.volta.persistence.errors import PersistenceConflict, PersistenceUnavailable
from yuno_backend.volta.persistence.unit_of_work import SqlAlchemyOperationUnitOfWork
from yuno_backend.volta.recovery import (
    CommitmentNotFound,
    EscalationAlreadyResolved,
    EscalationContextConflict,
    EscalationNotFound,
    EvidenceAlreadyRecorded,
    InvalidCommitmentDisposition,
    MandateVersionNotAdvanced,
    Notification,
    NotificationAlreadyAcknowledged,
    NotificationNotFound,
    OperationBlockedByEscalation,
    PostContactEscalation,
    RecoveryDecisionState,
    RecoveryEvidenceRequired,
    RecoveryScenario,
    RecoveryScenarioMismatch,
)
from yuno_backend.volta.text_slice import (
    AcknowledgeNotificationInput,
    ApproveOperationInput,
    AttachCommitmentEvidenceInput,
    AuditProjection,
    AuditQuery,
    AuditQuoteProjection,
    BrowserChannel,
    CommitmentEvidenceNotFound,
    CommitmentProjection,
    CreateCallBriefInput,
    CreateCommitmentInput,
    CreateEscalationInput,
    CreateOperationDraftInput,
    CreateSimulatedRecapInput,
    DraftProjection,
    EvidenceArtifactUnavailable,
    EvidenceReservation,
    EvidenceReservationMismatch,
    EvidenceReservationNotFound,
    MutationOutcome,
    NegotiationProjection,
    OperationProjection,
    PreContactEscalationProjection,
    QuoteTerms,
    RecordQuoteInput,
    RecoveryProjection,
    ReplaceMandateInput,
    SessionProjection,
    StartInboundRecoveryInput,
    StartNegotiationInput,
    TextNegotiationApplication,
    create_demo_carrier_catalog,
    create_demo_evidence_storage,
    create_demo_text_extractor,
)

from app.config import Settings
from app.contract_service import (
    ContractResult,
    ContractServiceError,
    JsonValue,
    UnimplementedContractService,
)
from app.schemas.common import ResponseModel
from app.schemas.contracts import (
    AuditEventResponse,
    AuditTimelineResponse,
    CallBriefResponse,
    CarrierResponse,
    CarrierSessionResponse,
    CommitmentEvidenceResponse,
    CommitmentResponse,
    CoordinatorNotificationResponse,
    EscalationResponse,
    MandateResponse,
    NegotiationResponse,
    NegotiationSummary,
    OperationDraftResponse,
    OperationResponse,
    PickupWindow,
    ProposedMandate,
    QuoteComparisonRow,
    QuoteResponse,
    RecoveryDecisionResponse,
    RecoverySimulationResponse,
    ValidationIssue,
    WrittenRecapResponse,
)
from app.schemas.contracts import (
    RecoveryDecisionState as RecoveryDecisionStateResponse,
)
from app.schemas.errors import ApiErrorCode

_INTEGRATED_OPERATIONS = frozenset(
    {
        "create_operation_draft",
        "approve_operation",
        "get_operation",
        "start_negotiation",
        "record_quote",
        "attach_commitment_evidence",
        "create_candidate_commitment",
        "create_simulated_recap",
        "create_call_brief",
        "start_inbound_simulation",
        "replace_mandate",
        "create_escalation",
        "acknowledge_notification",
        "get_operation_audit",
    }
)


class _UtcClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class _UuidGenerator:
    def new_id(self) -> UUID:
        return uuid4()


class VoltaTextContractService:
    """Translate validated JSON values to the provider-neutral application facade."""

    def __init__(
        self,
        application: TextNegotiationApplication | None = None,
        *,
        application_factory: Callable[[], TextNegotiationApplication] | None = None,
        audio_service: RetrieveEvidenceAudioService | None = None,
        audio_service_factory: Callable[[], RetrieveEvidenceAudioService] | None = None,
        correlation_id_factory: Callable[[], UUID] = uuid4,
        close: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        if (application is None) == (application_factory is None):
            raise ValueError("provide exactly one text application source")
        self._application = application
        self._application_factory = application_factory
        self._audio_service = audio_service
        self._audio_service_factory = audio_service_factory
        self._correlation_ids = correlation_id_factory
        self._close = close
        self._unimplemented = UnimplementedContractService()

    async def aclose(self) -> None:
        if self._close is not None:
            close, self._close = self._close, None
            await close()

    def _get_application(self) -> TextNegotiationApplication:
        if self._application is None:
            assert self._application_factory is not None
            self._application = self._application_factory()
        return self._application

    def _get_audio_service(self) -> RetrieveEvidenceAudioService:
        if self._audio_service is None:
            if self._audio_service_factory is None:
                raise PersistenceUnavailable("configuration_missing", "evidence_audio")
            self._audio_service = self._audio_service_factory()
        return self._audio_service

    async def get_evidence_audio(self, evidence_id: UUID) -> EvidenceAudio:
        try:
            return await self._get_audio_service().retrieve(evidence_id)
        except EvidenceAudioNotFound:
            raise ContractServiceError(
                status_code=404,
                code=ApiErrorCode.RESOURCE_NOT_FOUND,
                message="Evidence audio is unavailable.",
            ) from None
        except EvidenceAudioTooLarge:
            raise ContractServiceError(
                status_code=413,
                code=ApiErrorCode.EVIDENCE_AUDIO_TOO_LARGE,
                message="Evidence audio exceeds the demo playback limit.",
            ) from None
        except ContractServiceError:
            raise
        except Exception as error:
            raise _translate_error(error) from None

    async def execute(
        self,
        operation_id: str,
        payload: dict[str, JsonValue],
        idempotency_key: str | None,
    ) -> ContractResult:
        if operation_id not in _INTEGRATED_OPERATIONS:
            return await self._unimplemented.execute(operation_id, payload, idempotency_key)
        try:
            return await self._execute_integrated(operation_id, payload, idempotency_key)
        except ContractServiceError:
            raise
        except Exception as error:
            raise _translate_error(error) from None

    async def _execute_integrated(
        self,
        operation_id: str,
        payload: dict[str, JsonValue],
        idempotency_key: str | None,
    ) -> ContractResult:
        application = self._get_application()
        if operation_id == "create_operation_draft":
            body = _body(payload)
            outcome = await application.create_operation_draft(
                CreateOperationDraftInput(
                    source_prompt=_string(body, "source_prompt"),
                    requested_language=_string(body, "requested_language"),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                )
            )
            return _mutation_result(_draft_response(outcome.value), outcome)
        if operation_id == "approve_operation":
            body = _body(payload)
            outcome = await application.approve_operation(
                ApproveOperationInput(
                    draft_id=_uuid(body, "draft_id"),
                    expected_draft_version=_integer(body, "expected_draft_version"),
                    approval_actor=_string(body, "approval_actor"),
                    correlation_id=self._correlation_ids(),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                )
            )
            return _mutation_result(_operation_response(outcome.value), outcome)
        if operation_id == "get_operation":
            projection = await application.get_operation(_path_uuid(payload, "operation_id"))
            return _query_result(_operation_response(projection))
        if operation_id == "start_negotiation":
            body = _body(payload)
            outcome = await application.start_negotiation(
                StartNegotiationInput(
                    operation_id=_path_uuid(payload, "operation_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    channel=BrowserChannel(_string(body, "channel")),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_negotiation_response(outcome.value), outcome)
        if operation_id == "record_quote":
            body = _body(payload)
            terms = _mapping(body, "terms")
            pickup_window = _mapping(terms, "pickup_window")
            outcome = await application.record_quote(
                RecordQuoteInput(
                    call_id=_path_uuid(payload, "call_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    carrier_id=_uuid(body, "carrier_id"),
                    mandate_version=_integer(body, "mandate_version"),
                    terms=QuoteTerms(
                        amount=Decimal(_integer(terms, "amount_minor")) / Decimal(100),
                        currency=_string(terms, "currency"),
                        pickup_window_start=_date(pickup_window, "start_date"),
                        pickup_window_end=_date(pickup_window, "end_date"),
                        conditions=tuple(_strings(terms, "conditions")),
                    ),
                    valid_until=_datetime(body, "valid_until"),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_quote_response(outcome.value), outcome)
        if operation_id == "attach_commitment_evidence":
            body = _body(payload)
            outcome = await application.attach_commitment_evidence(
                AttachCommitmentEvidenceInput(
                    call_id=_path_uuid(payload, "call_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    recording_reference=_string(body, "recording_reference"),
                    audio_start_ms=_integer(body, "audio_start_ms"),
                    item_id=_string(body, "item_id"),
                    event_id=_string(body, "event_id"),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_evidence_response(outcome.value), outcome)
        if operation_id == "create_candidate_commitment":
            body = _body(payload)
            outcome = await application.create_candidate_commitment(
                CreateCommitmentInput(
                    call_id=_path_uuid(payload, "call_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    quote_id=_uuid(body, "quote_id"),
                    mandate_version=_integer(body, "mandate_version"),
                    evidence_id=_uuid(body, "evidence_id"),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_commitment_response(outcome.value), outcome)
        if operation_id == "create_simulated_recap":
            body = _body(payload)
            outcome = await application.create_simulated_recap(
                CreateSimulatedRecapInput(
                    call_id=_path_uuid(payload, "call_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    commitment_id=_uuid(body, "commitment_id"),
                    rendered_content=_string(body, "rendered_content"),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_recap_response(outcome.value), outcome)
        if operation_id == "create_call_brief":
            body = _body(payload)
            outcome = await application.create_call_brief(
                CreateCallBriefInput(
                    call_id=_path_uuid(payload, "call_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    facts=tuple(_strings(body, "facts")),
                    objections=tuple(_strings(body, "objections")),
                    changes=tuple(_strings(body, "changes")),
                    unresolved_items=tuple(_strings(body, "unresolved_items")),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_brief_response(outcome.value), outcome)
        if operation_id == "start_inbound_simulation":
            body = _body(payload)
            outcome = await application.start_inbound_simulation(
                StartInboundRecoveryInput(
                    operation_id=_path_uuid(payload, "operation_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    scenario=RecoveryScenario(_string(body, "scenario")),
                    active_commitment_id=_uuid(body, "active_commitment_id"),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_recovery_response(outcome.value), outcome)
        if operation_id == "replace_mandate":
            body = _body(payload)
            pickup_window = _mapping(body, "pickup_window")
            outcome = await application.replace_mandate(
                ReplaceMandateInput(
                    operation_id=_path_uuid(payload, "operation_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    resolved_escalation_id=_uuid(body, "resolved_escalation_id"),
                    maximum_amount=Money(
                        Decimal(_integer(body, "maximum_amount_minor")) / Decimal(100),
                        _string(body, "currency"),
                    ),
                    pickup_window=MandatePickupWindow(
                        _date(pickup_window, "start_date"),
                        _date(pickup_window, "end_date"),
                    ),
                    allowed_conditions=tuple(_strings(body, "allowed_conditions")),
                    escalation_conditions=tuple(
                        _strings(body, "escalation_conditions")
                    ),
                    approval_actor=_string(body, "approval_actor"),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_operation_response(outcome.value), outcome)
        if operation_id == "create_escalation":
            body = _body(payload)
            outcome = await application.create_escalation(
                CreateEscalationInput(
                    call_id=_path_uuid(payload, "call_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    conflict=_string(body, "conflict"),
                    attempted_alternatives=tuple(
                        _strings(body, "attempted_alternatives")
                    ),
                    recommended_action=_string(body, "recommended_action"),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_post_contact_escalation_response(outcome.value), outcome)
        if operation_id == "acknowledge_notification":
            body = _body(payload)
            outcome = await application.acknowledge_notification(
                AcknowledgeNotificationInput(
                    notification_id=_path_uuid(payload, "notification_id"),
                    expected_operation_version=_integer(body, "expected_operation_version"),
                    acknowledged_by=_string(body, "acknowledged_by"),
                    idempotency_key=_required_idempotency_key(idempotency_key),
                    correlation_id=self._correlation_ids(),
                )
            )
            return _mutation_result(_notification_response(outcome.value), outcome)
        projection = await application.get_operation_audit(
            AuditQuery(
                operation_id=_path_uuid(payload, "operation_id"),
                cursor=_optional_string(payload, "cursor"),
                limit=_integer(payload, "limit"),
            )
        )
        return _query_result(_audit_response(projection))


def create_volta_text_contract_service(
    settings: Settings,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> VoltaTextContractService:
    """Build the live adapter without opening a database connection at import time."""

    engine = None
    session_factory = None
    evidence_storage = None

    def runtime_dependencies():
        nonlocal engine, session_factory, evidence_storage
        if session_factory is None:
            database_url = settings.database_url.get_secret_value()
            if not database_url:
                raise PersistenceUnavailable("configuration_missing", "database")
            engine = create_database_engine(DatabaseConfig(url=database_url))
            session_factory = create_session_factory(engine)
            evidence_storage = create_demo_evidence_storage(settings.volta_evidence_storage_path)
        return session_factory, evidence_storage

    def application_factory() -> TextNegotiationApplication:
        session_factory, evidence_storage = runtime_dependencies()
        extractor = _create_intake_extractor(settings, http_client)
        return TextNegotiationApplication(
            unit_of_work_factory=lambda: SqlAlchemyOperationUnitOfWork(session_factory),
            extractor=extractor,
            carrier_catalog=create_demo_carrier_catalog(),
            clock=_UtcClock(),
            id_generator=_UuidGenerator(),
            evidence_storage=evidence_storage,
            extraction_policy_version=settings.volta_extraction_policy_version,
        )

    def audio_service_factory() -> RetrieveEvidenceAudioService:
        session_factory, evidence_storage = runtime_dependencies()
        return RetrieveEvidenceAudioService(
            unit_of_work_factory=lambda: SqlAlchemyOperationUnitOfWork(session_factory),
            evidence_storage=evidence_storage,
        )

    async def close() -> None:
        if engine is not None:
            await engine.dispose()

    return VoltaTextContractService(
        application_factory=application_factory,
        audio_service_factory=audio_service_factory,
        close=close,
    )


def _create_intake_extractor(
    settings: Settings,
    http_client: httpx.AsyncClient | None,
) -> IntakeExtractor:
    if settings.volta_extraction_mode == "deterministic":
        return create_demo_text_extractor()
    if http_client is None:
        raise ValueError("caller-owned OpenAI HTTP client is required")
    return OpenAIIntakeExtractor(
        http_client,
        OpenAIExtractionConfig(
            api_key=settings.openai_api_key.get_secret_value(),
            base_url=settings.openai_base_url,
            model=settings.openai_extraction_model,
            policy_version=settings.volta_extraction_policy_version,
        ),
    )


def _translate_error(error: Exception) -> ContractServiceError:
    if isinstance(error, DraftNotFound):
        return _public_error(404, ApiErrorCode.RESOURCE_NOT_FOUND, error.draft_id)
    if isinstance(error, OperationNotFound):
        return _public_error(404, ApiErrorCode.RESOURCE_NOT_FOUND, error.operation_id)
    if isinstance(error, CallSessionNotFound):
        return _public_error(404, ApiErrorCode.RESOURCE_NOT_FOUND, error.call_id)
    if isinstance(error, CommitmentNotFound):
        return _public_error(404, ApiErrorCode.RESOURCE_NOT_FOUND, error.commitment_id)
    if isinstance(error, EscalationNotFound):
        return _public_error(404, ApiErrorCode.RESOURCE_NOT_FOUND, error.escalation_id)
    if isinstance(error, NotificationNotFound):
        return _public_error(404, ApiErrorCode.RESOURCE_NOT_FOUND, error.notification_id)
    if isinstance(error, EvidenceArtifactUnavailable):
        return _public_error(404, ApiErrorCode.RESOURCE_NOT_FOUND, None)
    if isinstance(error, EvidenceReservationNotFound):
        return _public_error(404, ApiErrorCode.RESOURCE_NOT_FOUND, error.evidence_id)
    if isinstance(error, StaleDraftVersion):
        return ContractServiceError(
            status_code=409,
            code=ApiErrorCode.STALE_DRAFT_VERSION,
            message="The submitted draft version is stale.",
            resource_id=str(error.draft_id),
            current_draft_version=error.current_version,
        )
    if isinstance(error, StaleOperationVersion):
        return ContractServiceError(
            status_code=409,
            code=ApiErrorCode.STALE_OPERATION_VERSION,
            message="The submitted operation version is stale.",
            resource_id=str(error.operation_id),
            current_operation_version=error.current_version,
        )
    if isinstance(error, (StaleMandateVersion, MandateConflict)):
        resource_id = error.operation_id
        return _public_error(409, ApiErrorCode.MANDATE_CONFLICT, resource_id)
    if isinstance(error, IdempotencyConflict):
        return _public_error(409, ApiErrorCode.IDEMPOTENCY_KEY_REUSED, error.operation_id)
    if isinstance(error, InvalidDomainValue):
        return ContractServiceError(
            status_code=422,
            code=ApiErrorCode.VALIDATION_ERROR,
            message="The request does not satisfy the public contract.",
        )
    if isinstance(
        error,
        (
            OperationAlreadyApproved,
            DraftNotApprovable,
            NegotiationAlreadyStarted,
            CarrierSessionMismatch,
            CommitmentEvidenceNotFound,
            EvidenceReservationMismatch,
            EscalationAlreadyResolved,
            EscalationContextConflict,
            EvidenceAlreadyRecorded,
            IdempotencyResultMissing,
            InvalidCommitmentDisposition,
            InvalidNegotiationTransition,
            MandateVersionNotAdvanced,
            NotificationAlreadyAcknowledged,
            OperationBlockedByEscalation,
            QuoteNotFound,
            QuoteNotEligible,
            QuoteExpired,
            QuoteNotBestCandidate,
            RecoveryEvidenceRequired,
            RecoveryScenarioMismatch,
            PersistenceConflict,
        ),
    ):
        resource_id = _safe_resource_id(error)
        return _public_error(409, ApiErrorCode.STATE_CONFLICT, resource_id)
    return ContractServiceError(
        status_code=500,
        code=ApiErrorCode.INTERNAL_ERROR,
        message="The request could not be completed.",
    )


def _public_error(
    status_code: int,
    code: ApiErrorCode,
    resource_id: UUID | None,
) -> ContractServiceError:
    messages = {
        ApiErrorCode.RESOURCE_NOT_FOUND: "The referenced resource was not found.",
        ApiErrorCode.MANDATE_CONFLICT: "The request conflicts with the active mandate.",
        ApiErrorCode.IDEMPOTENCY_KEY_REUSED: (
            "The idempotency key belongs to a different request."
        ),
        ApiErrorCode.STATE_CONFLICT: "The requested action conflicts with current state.",
    }
    return ContractServiceError(
        status_code=status_code,
        code=code,
        message=messages[code],
        resource_id=None if resource_id is None else str(resource_id),
    )


def _safe_resource_id(error: Exception) -> UUID | None:
    for name in (
        "operation_id",
        "draft_id",
        "call_id",
        "quote_id",
        "commitment_id",
        "evidence_id",
        "escalation_id",
        "notification_id",
        "resource_id",
    ):
        value = getattr(error, name, None)
        if isinstance(value, UUID):
            return value
    return None


def _mutation_result[T](response: ResponseModel, outcome: MutationOutcome[T]) -> ContractResult:
    return ContractResult(
        cast(JsonValue, response.model_dump(mode="json")),
        idempotency_replayed=outcome.idempotency_replayed,
    )


def _query_result(response: ResponseModel) -> ContractResult:
    return ContractResult(cast(JsonValue, response.model_dump(mode="json")))


def _draft_response(projection: DraftProjection) -> OperationDraftResponse:
    draft = projection.draft
    proposal = draft.proposal
    mandate = proposal.mandate
    return OperationDraftResponse(
        draft_id=draft.id,
        source_prompt=draft.source_prompt,
        requested_language=draft.requested_language,
        extraction_policy_version=draft.extraction_policy_version,
        proposed_route={"origin": proposal.route.origin, "destination": proposal.route.destination},
        proposed_pickup_date=proposal.pickup_date,
        proposed_mandate=ProposedMandate(
            maximum_amount_minor=_minor_amount(mandate.maximum_amount.amount),
            currency=mandate.maximum_amount.currency,
            pickup_window=PickupWindow(
                start_date=mandate.pickup_window.start_date,
                end_date=mandate.pickup_window.end_date,
            ),
            allowed_conditions=list(mandate.allowed_conditions),
            escalation_conditions=list(mandate.escalation_conditions),
        ),
        validation_issues=[
            ValidationIssue(field=issue.field, message=issue.reason_code)
            for issue in draft.validation_issues
        ],
        approval_eligible=draft.approval_eligible,
        draft_version=draft.version,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _operation_response(projection: OperationProjection) -> OperationResponse:
    operation = projection.operation
    negotiation = projection.negotiation
    sessions = (
        [] if negotiation is None else [_session_response(item) for item in negotiation.sessions]
    )
    quotes = [_quote_response(item) for item in projection.quotes]
    escalation = (
        None
        if projection.open_escalation is None
        else _post_contact_escalation_response(projection.open_escalation)
    )
    if (
        escalation is None
        and negotiation is not None
        and negotiation.pre_contact_escalation is not None
    ):
        escalation = _escalation_response(negotiation.pre_contact_escalation)
    summary_projection = projection.negotiation_summary
    summary = None
    if summary_projection is not None:
        summary = NegotiationSummary(
            negotiation_id=summary_projection.negotiation_id,
            selected_carrier_count=summary_projection.selected_carrier_count,
            active_session_count=summary_projection.active_session_count,
            valid_quote_count=summary_projection.valid_quote_count,
        )
    return OperationResponse(
        operation_id=operation.id,
        route={"origin": operation.route.origin, "destination": operation.route.destination},
        cargo_label=operation.cargo_label,
        status=operation.status.value,
        operation_version=operation.version,
        active_mandate=_mandate_response(operation.mandate),
        negotiation_summary=summary,
        sessions=sessions,
        quotes=quotes,
        active_commitment=(
            None
            if (
                projection.active_commitment is None
                or projection.active_commitment.evidence is None
            )
            else _commitment_response(projection.active_commitment)
        ),
        open_escalation=escalation,
        notifications=[_notification_response(item) for item in projection.notifications],
        created_at=operation.created_at,
        updated_at=projection.updated_at,
    )


def _mandate_response(mandate: Mandate) -> MandateResponse:
    maximum_amount = mandate.maximum_amount
    pickup_window = mandate.pickup_window
    return MandateResponse(
        mandate_id=mandate.id,
        version=mandate.version,
        maximum_amount_minor=_minor_amount(maximum_amount.amount),
        currency=maximum_amount.currency,
        pickup_window=PickupWindow(
            start_date=pickup_window.start_date,
            end_date=pickup_window.end_date,
        ),
        allowed_conditions=list(mandate.allowed_conditions),
        escalation_conditions=list(mandate.escalation_conditions),
        approval_actor=mandate.approval_actor,
        approved_at=mandate.approved_at,
    )


def _negotiation_response(projection: NegotiationProjection) -> NegotiationResponse:
    negotiation = projection.negotiation
    escalation = projection.pre_contact_escalation
    return NegotiationResponse(
        negotiation_id=negotiation.id,
        operation_id=negotiation.operation_id,
        operation_version=negotiation.operation_version,
        sessions=[_session_response(item) for item in projection.sessions],
        pre_contact_escalation=(None if escalation is None else _escalation_response(escalation)),
        started_at=negotiation.started_at,
    )


def _session_response(projection: SessionProjection) -> CarrierSessionResponse:
    session = projection.session
    state = session.state.value
    created_at = session.created_at
    return CarrierSessionResponse(
        call_id=session.call_id,
        carrier=CarrierResponse(
            carrier_id=session.carrier_id,
            display_name=session.carrier_display_label,
            eligible=session.available_snapshot,
            deterministic_rank=session.selection_rank,
            ranking_evidence=list(projection.ranking_evidence),
        ),
        channel=session.channel.value,
        direction="OUTBOUND_SIMULATION",
        state=state,
        started_at=None if state == "SELECTED" else created_at,
        ended_at=None,
    )


def _quote_response(quote: Quote) -> QuoteResponse:
    terms = quote.terms
    return QuoteResponse(
        quote_id=quote.id,
        operation_id=quote.operation_id,
        call_id=quote.call_id,
        carrier_id=quote.carrier_id,
        terms={
            "amount_minor": _minor_amount(terms.amount),
            "currency": terms.currency,
            "pickup_window": {
                "start_date": terms.pickup_window_start,
                "end_date": terms.pickup_window_end,
            },
            "conditions": list(terms.conditions),
        },
        valid_until=quote.valid_until,
        mandate_version=quote.mandate_version,
        eligibility=quote.eligibility.value,
        rejection_reasons=list(quote.rejection_reasons),
        created_at=quote.created_at,
    )


def _commitment_response(projection: CommitmentProjection) -> CommitmentResponse:
    commitment = projection.commitment
    evidence = projection.evidence
    if evidence is None:
        raise ValueError("commitment evidence is pending")
    return CommitmentResponse(
        commitment_id=commitment.id,
        operation_id=commitment.operation_id,
        call_id=commitment.call_id,
        quote_id=commitment.quote_id,
        carrier_id=commitment.carrier_id,
        agreed_terms={
            "amount_minor": _minor_amount(commitment.agreed_terms.amount),
            "currency": commitment.agreed_terms.currency,
            "pickup_window": {
                "start_date": commitment.agreed_terms.pickup_window_start,
                "end_date": commitment.agreed_terms.pickup_window_end,
            },
            "conditions": list(commitment.agreed_terms.conditions),
        },
        mandate_version=commitment.mandate_version,
        evidence={
            "evidence_id": evidence.id,
            "call_id": commitment.call_id,
            "audio_start_ms": evidence.audio_start_ms,
            "item_id": evidence.item_id,
            "event_id": evidence.event_id,
            "lifecycle": commitment.lifecycle.value,
            "created_at": evidence.created_at,
        },
        lifecycle=commitment.lifecycle.value,
        disposition=commitment.disposition.value,
        replaces_commitment_id=commitment.replaces_commitment_id,
        created_at=commitment.created_at,
        superseded_at=commitment.superseded_at,
    )


def _evidence_response(reservation: EvidenceReservation) -> CommitmentEvidenceResponse:
    return CommitmentEvidenceResponse(
        evidence_id=reservation.id,
        call_id=reservation.call_id,
        audio_start_ms=reservation.audio_start_ms,
        item_id=reservation.item_id,
        event_id=reservation.event_id,
        lifecycle="CANDIDATE",
        created_at=reservation.created_at,
    )


def _recap_response(recap: Recap) -> WrittenRecapResponse:
    return WrittenRecapResponse(
        recap_id=recap.id,
        operation_id=recap.operation_id,
        call_id=recap.call_id,
        commitment_id=recap.commitment_id,
        channel=recap.disclosure_state.value,
        content_hash=recap.content_hash,
        rendered_content=recap.rendered_content,
        created_at=recap.generated_at,
    )


def _brief_response(brief: CallBrief) -> CallBriefResponse:
    return CallBriefResponse(
        brief_id=brief.id,
        operation_id=brief.operation_id,
        call_id=brief.call_id,
        commitment_id=brief.commitment_id,
        facts=list(brief.facts),
        objections=list(brief.objections),
        changes=list(brief.changes),
        unresolved_items=list(brief.unresolved_items),
        created_at=brief.generated_at,
    )


def _recovery_response(projection: RecoveryProjection) -> RecoverySimulationResponse:
    attempt = projection.attempt
    active_commitment = projection.active_commitment
    return RecoverySimulationResponse(
        recovery_id=attempt.id,
        operation_id=attempt.operation_id,
        scenario=attempt.scenario.value,
        before_operation_version=attempt.before_operation_version,
        after_operation_version=attempt.after_operation_version,
        decision_reason=attempt.decision_reason,
        active_commitment=(
            None
            if active_commitment is None or active_commitment.evidence is None
            else _commitment_response(active_commitment)
        ),
        escalation=(
            None
            if projection.escalation is None
            else _post_contact_escalation_response(projection.escalation)
        ),
        correlation_id=attempt.correlation_id,
        created_at=attempt.created_at,
    )


def _post_contact_escalation_response(
    escalation: PostContactEscalation,
) -> EscalationResponse:
    context = escalation.context
    return EscalationResponse(
        escalation_id=escalation.id,
        operation_id=escalation.operation_id,
        call_id=escalation.call_id,
        conflict=escalation.reason_code if context is None else context.conflict,
        attempted_alternatives=(
            [] if context is None else list(context.attempted_alternatives)
        ),
        recommended_action=(
            "Coordinator review required"
            if context is None
            else context.recommended_action
        ),
        resolution_state="RESOLVED" if escalation.resolved else "OPEN",
        correlation_id=escalation.correlation_id,
        created_at=escalation.created_at,
        resolved_at=escalation.resolved_at,
    )


def _notification_response(notification: Notification) -> CoordinatorNotificationResponse:
    if (
        notification.operation_version is None
        or notification.recovery_decision is None
        or notification.message is None
        or notification.correlation_id is None
    ):
        raise ValueError("notification recovery projection is incomplete")
    decision = notification.recovery_decision
    return CoordinatorNotificationResponse(
        notification_id=notification.id,
        operation_id=notification.operation_id,
        operation_version=notification.operation_version,
        recovery_decision=RecoveryDecisionResponse(
            before=_recovery_decision_state_response(decision.before),
            after=_recovery_decision_state_response(decision.after),
            reason=decision.reason,
        ),
        message=notification.message,
        acknowledged=notification.acknowledged,
        acknowledged_by=notification.acknowledged_by,
        acknowledged_at=notification.acknowledged_at,
        correlation_id=notification.correlation_id,
        created_at=notification.created_at,
    )


def _recovery_decision_state_response(
    state: RecoveryDecisionState,
) -> RecoveryDecisionStateResponse:
    terms = state.agreed_terms
    return RecoveryDecisionStateResponse(
        operation_version=state.operation_version,
        operation_status=state.operation_status.value,
        active_commitment_id=state.active_commitment_id,
        carrier_id=state.carrier_id,
        agreed_terms=(
            None
            if terms is None
            else {
                "amount_minor": _minor_amount(terms.amount),
                "currency": terms.currency,
                "pickup_window": {
                    "start_date": terms.pickup_window_start,
                    "end_date": terms.pickup_window_end,
                },
                "conditions": list(terms.conditions),
            }
        ),
    )


def _escalation_response(projection: PreContactEscalationProjection) -> EscalationResponse:
    escalation = projection.escalation
    return EscalationResponse(
        escalation_id=escalation.id,
        operation_id=escalation.operation_id,
        call_id=None,
        conflict=projection.conflict,
        attempted_alternatives=list(projection.attempted_alternatives),
        recommended_action=projection.recommended_action,
        resolution_state=projection.resolution_state.value,
        correlation_id=escalation.correlation_id,
        created_at=escalation.created_at,
        resolved_at=None,
    )


def _audit_response(projection: AuditProjection) -> AuditTimelineResponse:
    escalations = [
        _post_contact_escalation_response(item) for item in projection.escalations
    ]
    if projection.negotiation is not None:
        escalation = projection.negotiation.pre_contact_escalation
        if escalation is not None:
            escalations.append(_escalation_response(escalation))
    return AuditTimelineResponse(
        operation_id=projection.operation_id,
        events=[
            AuditEventResponse(
                event_id=event.event_id,
                operation_version=event.operation_version,
                actor_kind=event.actor_kind.value,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                correlation_id=event.correlation_id,
                metadata=dict(event.metadata),
            )
            for event in projection.events
        ],
        quote_comparison=[_comparison_response(row) for row in projection.quote_comparison],
        commitment_history=[
            _commitment_response(item)
            for item in projection.commitment_history
            if item.evidence is not None
        ],
        recaps=[_recap_response(item) for item in projection.recaps],
        briefs=[_brief_response(item) for item in projection.briefs],
        recoveries=[_recovery_response(item) for item in projection.recoveries],
        escalations=escalations,
        notifications=[_notification_response(item) for item in projection.notifications],
        next_cursor=projection.next_cursor,
    )


def _comparison_response(row: AuditQuoteProjection) -> QuoteComparisonRow:
    quote = row.quote
    terms = quote.terms
    return QuoteComparisonRow(
        quote_id=quote.id,
        call_id=quote.call_id,
        carrier_id=quote.carrier_id,
        carrier_display_name=row.carrier_display_name,
        terms={
            "amount_minor": _minor_amount(terms.amount),
            "currency": terms.currency,
            "pickup_window": {
                "start_date": terms.pickup_window_start,
                "end_date": terms.pickup_window_end,
            },
            "conditions": list(terms.conditions),
        },
        valid_until=quote.valid_until,
        mandate_version=quote.mandate_version,
        eligibility=quote.eligibility.value,
        selected=row.selected,
        rejection_reasons=list(quote.rejection_reasons),
        created_at=quote.created_at,
    )


def _minor_amount(amount: Decimal) -> int:
    scaled = amount * Decimal(100)
    integral = scaled.to_integral_value()
    if scaled != integral:
        raise ValueError("domain amount cannot be represented in minor units")
    return int(integral)


def _required_idempotency_key(value: str | None) -> str:
    if value is None:
        raise ValueError("mutation requires idempotency key")
    return value


def _body(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    value = payload.get("body")
    if not isinstance(value, dict):
        raise ValueError("validated request body is missing")
    return value


def _mapping(values: dict[str, JsonValue], key: str) -> dict[str, JsonValue]:
    value = values.get(key)
    if not isinstance(value, dict):
        raise ValueError("validated mapping value is missing")
    return value


def _string(values: dict[str, JsonValue], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str):
        raise ValueError("validated string value is missing")
    return value


def _optional_string(values: dict[str, JsonValue], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("validated optional string value is invalid")
    return value


def _strings(values: dict[str, JsonValue], key: str) -> list[str]:
    value = values.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("validated string list is missing")
    return cast(list[str], value)


def _integer(values: dict[str, JsonValue], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("validated integer value is missing")
    return value


def _uuid(values: dict[str, JsonValue], key: str) -> UUID:
    return UUID(_string(values, key))


def _path_uuid(payload: dict[str, JsonValue], key: str) -> UUID:
    return _uuid(payload, key)


def _date(values: dict[str, JsonValue], key: str) -> date:
    return date.fromisoformat(_string(values, key))


def _datetime(values: dict[str, JsonValue], key: str) -> datetime:
    value = datetime.fromisoformat(_string(values, key).replace("Z", "+00:00"))
    if value.utcoffset() is None:
        raise ValueError("validated datetime must include an offset")
    return value
