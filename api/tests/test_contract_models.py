from datetime import datetime
from typing import Any

import pytest
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
from pydantic import ValidationError

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
