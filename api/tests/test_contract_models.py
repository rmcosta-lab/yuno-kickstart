from datetime import datetime
from typing import Any

import pytest
from app.schemas.common import (
    JS_SAFE_MAX,
    MinorAmount,
    NonNegativeCount,
    NonNegativeMilliseconds,
    PositiveVersion,
    SafeMetadataInteger,
    ThreeItemCount,
    ThreeItemRank,
)
from app.schemas.contracts import (
    AcknowledgeNotificationRequest,
    ApproveOperationRequest,
    AuditTimelineResponse,
    CallBriefResponse,
    CommitmentEvidenceResponse,
    CommitmentResponse,
    CoordinatorNotificationResponse,
    CreateCallBriefRequest,
    CreateCommitmentEvidenceRequest,
    CreateCommitmentRequest,
    CreateEscalationRequest,
    CreateOperationDraftRequest,
    CreateQuoteRequest,
    CreateSimulatedRecapRequest,
    EscalationResponse,
    NegotiationResponse,
    OperationDraftResponse,
    OperationResponse,
    QuoteResponse,
    RecoverySimulationResponse,
    ReplaceMandateRequest,
    StartInboundSimulationRequest,
    StartNegotiationRequest,
    WrittenRecapResponse,
)
from contract_fixtures import request_for, response_for
from pydantic import TypeAdapter, ValidationError

REQUEST_MODELS = {
    "create_operation_draft": CreateOperationDraftRequest,
    "approve_operation": ApproveOperationRequest,
    "start_negotiation": StartNegotiationRequest,
    "record_quote": CreateQuoteRequest,
    "attach_commitment_evidence": CreateCommitmentEvidenceRequest,
    "create_candidate_commitment": CreateCommitmentRequest,
    "create_simulated_recap": CreateSimulatedRecapRequest,
    "create_call_brief": CreateCallBriefRequest,
    "start_inbound_simulation": StartInboundSimulationRequest,
    "replace_mandate": ReplaceMandateRequest,
    "create_escalation": CreateEscalationRequest,
    "acknowledge_notification": AcknowledgeNotificationRequest,
}

RESPONSE_MODELS = {
    "create_operation_draft": OperationDraftResponse,
    "approve_operation": OperationResponse,
    "get_operation": OperationResponse,
    "start_negotiation": NegotiationResponse,
    "record_quote": QuoteResponse,
    "attach_commitment_evidence": CommitmentEvidenceResponse,
    "create_candidate_commitment": CommitmentResponse,
    "create_simulated_recap": WrittenRecapResponse,
    "create_call_brief": CallBriefResponse,
    "start_inbound_simulation": RecoverySimulationResponse,
    "replace_mandate": OperationResponse,
    "create_escalation": EscalationResponse,
    "acknowledge_notification": CoordinatorNotificationResponse,
    "get_operation_audit": AuditTimelineResponse,
}


@pytest.mark.parametrize(("operation_id", "model"), REQUEST_MODELS.items())
def test_request_models_accept_canonical_fixture_and_reject_unknown_fields(
    operation_id: str,
    model: Any,
) -> None:
    fixture = request_for(operation_id)
    assert fixture is not None
    model.model_validate(fixture)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        model.model_validate({**fixture, "server_owned_state": "ACTIVE"})


@pytest.mark.parametrize(("operation_id", "model"), RESPONSE_MODELS.items())
def test_response_models_accept_each_contract_family(operation_id: str, model: Any) -> None:
    model.model_validate(response_for(operation_id))


def test_create_requests_do_not_publish_server_owned_state_fields() -> None:
    forbidden = {
        "operation_version",
        "draft_version",
        "lifecycle",
        "disposition",
        "eligibility",
        "created_at",
        "updated_at",
        "resolution_state",
        "acknowledged",
    }

    for model in REQUEST_MODELS.values():
        assert forbidden.isdisjoint(model.model_fields)


def test_recap_response_only_accepts_simulated_channel() -> None:
    fixture = response_for("create_simulated_recap")
    fixture["channel"] = "VERIFIED"

    with pytest.raises(ValidationError):
        WrittenRecapResponse.model_validate(fixture)


def test_response_timestamps_require_utc() -> None:
    fixture = response_for("create_operation_draft")
    fixture["created_at"] = datetime.fromisoformat("2026-08-29T12:00:00+01:00")

    with pytest.raises(ValidationError, match="timestamps must use UTC"):
        OperationDraftResponse.model_validate(fixture)


def test_extraction_policy_is_server_selected_and_returned_for_audit() -> None:
    request = request_for("create_operation_draft")
    assert request is not None
    assert "extraction_policy_version" not in CreateOperationDraftRequest.model_fields
    CreateOperationDraftRequest.model_validate(request)

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        CreateOperationDraftRequest.model_validate(
            {**request, "extraction_policy_version": "browser-selected-policy"}
        )

    response = OperationDraftResponse.model_validate(response_for("create_operation_draft"))
    assert response.extraction_policy_version == "intake-v1"


def test_draft_response_retains_missing_route_endpoints_for_correction() -> None:
    fixture = response_for("create_operation_draft")
    fixture["proposed_route"] = {"origin": "", "destination": ""}
    fixture["validation_issues"] = [
        {"field": "route.origin", "message": "required"},
        {"field": "route.destination", "message": "required"},
    ]
    fixture["approval_eligible"] = False

    response = OperationDraftResponse.model_validate(fixture)

    assert response.proposed_route.origin == ""
    assert response.proposed_route.destination == ""

    operation = response_for("get_operation")
    operation["route"] = {"origin": "", "destination": ""}
    with pytest.raises(ValidationError):
        OperationResponse.model_validate(operation)


def _replace_nested_value(
    fixture: dict[str, Any],
    path: tuple[str | int, ...],
    value: Any,
) -> None:
    target: Any = fixture
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


@pytest.mark.parametrize(
    ("operation_id", "model", "path"),
    [
        ("approve_operation", ApproveOperationRequest, ("expected_draft_version",)),
        ("record_quote", CreateQuoteRequest, ("terms", "amount_minor")),
        (
            "attach_commitment_evidence",
            CreateCommitmentEvidenceRequest,
            ("audio_start_ms",),
        ),
        (
            "get_operation",
            OperationResponse,
            ("negotiation_summary", "selected_carrier_count"),
        ),
        (
            "get_operation",
            OperationResponse,
            ("negotiation_summary", "active_session_count"),
        ),
        (
            "get_operation",
            OperationResponse,
            ("negotiation_summary", "valid_quote_count"),
        ),
        (
            "get_operation",
            OperationResponse,
            ("sessions", 0, "carrier", "deterministic_rank"),
        ),
    ],
)
@pytest.mark.parametrize("invalid_value", ["1", True, False, -1, JS_SAFE_MAX + 1])
def test_json_integer_fields_reject_coercion_negative_and_unsafe_values(
    operation_id: str,
    model: Any,
    path: tuple[str | int, ...],
    invalid_value: Any,
) -> None:
    fixture = (
        response_for(operation_id) if operation_id == "get_operation" else request_for(operation_id)
    )
    assert fixture is not None
    _replace_nested_value(fixture, path, invalid_value)

    with pytest.raises(ValidationError):
        model.model_validate(fixture)


@pytest.mark.parametrize(
    ("operation_id", "model", "path"),
    [
        ("approve_operation", ApproveOperationRequest, ("expected_draft_version",)),
        ("record_quote", CreateQuoteRequest, ("terms", "amount_minor")),
        (
            "attach_commitment_evidence",
            CreateCommitmentEvidenceRequest,
            ("audio_start_ms",),
        ),
        (
            "get_operation",
            OperationResponse,
            ("negotiation_summary", "valid_quote_count"),
        ),
    ],
)
def test_json_integer_fields_accept_the_javascript_safe_boundary(
    operation_id: str,
    model: Any,
    path: tuple[str | int, ...],
) -> None:
    fixture = (
        response_for(operation_id) if operation_id == "get_operation" else request_for(operation_id)
    )
    assert fixture is not None
    _replace_nested_value(fixture, path, JS_SAFE_MAX)

    model.model_validate(fixture)


@pytest.mark.parametrize(
    ("annotation", "minimum", "maximum"),
    [
        (PositiveVersion, 1, JS_SAFE_MAX),
        (MinorAmount, 0, JS_SAFE_MAX),
        (NonNegativeMilliseconds, 0, JS_SAFE_MAX),
        (NonNegativeCount, 0, JS_SAFE_MAX),
        (SafeMetadataInteger, 0, JS_SAFE_MAX),
        (ThreeItemCount, 0, 3),
        (ThreeItemRank, 1, 3),
    ],
)
def test_integer_aliases_document_their_transport_bounds(
    annotation: Any,
    minimum: int,
    maximum: int,
) -> None:
    schema = TypeAdapter(annotation).json_schema()

    assert schema["type"] == "integer"
    assert schema["minimum"] == minimum
    assert schema["maximum"] == maximum


def test_read_projections_reconstruct_complete_p0_control_tower_state() -> None:
    operation = OperationResponse.model_validate(response_for("get_operation"))
    assert {session.state for session in operation.sessions} == {"COMPLETED"}
    assert [quote.terms.amount_minor for quote in operation.quotes] == [130000, 125000]
    assert operation.quotes[-1].terms.conditions == ["sealed container"]
    assert operation.active_commitment is not None
    assert operation.active_commitment.evidence.audio_start_ms == 4200
    assert operation.open_escalation is not None
    assert operation.notifications[0].recovery_decision.before.operation_version == 3

    audit = AuditTimelineResponse.model_validate(response_for("get_operation_audit"))
    assert audit.quote_comparison[0].terms.pickup_window.start_date.isoformat() == ("2026-09-01")
    assert {item.disposition for item in audit.commitment_history} == {
        "ACTIVE",
        "SUPERSEDED",
    }
    superseded = next(item for item in audit.commitment_history if item.disposition == "SUPERSEDED")
    assert "recording_reference" not in type(superseded.evidence).model_fields
    assert audit.recaps[0].channel == "SIMULATED"
    assert audit.briefs[0].changes == ["Recovered with a mandate-safe alternative"]
    assert audit.recoveries[0].scenario == "MANDATE_SAFE"
    assert audit.notifications[0].operation_version == 4
    assert audit.escalations[0].resolution_state == "OPEN"


def test_notification_acknowledgement_preserves_structured_recovery_decision() -> None:
    notification = CoordinatorNotificationResponse.model_validate(
        response_for("acknowledge_notification")
    )

    assert notification.acknowledged is True
    assert notification.operation_version == 4
    assert notification.recovery_decision.before.active_commitment_id != (
        notification.recovery_decision.after.active_commitment_id
    )
    assert notification.recovery_decision.before.agreed_terms is not None
    assert notification.recovery_decision.after.agreed_terms is not None
    assert notification.recovery_decision.reason == (
        "The alternative reconfirmed terms inside the active mandate."
    )
