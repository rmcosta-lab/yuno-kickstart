"""Explicit mappings between frozen Volta domain values and private SQL rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from yuno_backend.volta.audit.models import AuditActorKind, AuditEvent
from yuno_backend.volta.evidence.models import (
    AgreementEvidence,
    CallBrief,
    Recap,
    RecapDisclosureState,
)
from yuno_backend.volta.idempotency import TextMutationIdempotency
from yuno_backend.volta.mandates.models import (
    DraftValidationIssue,
    IntakeDraft,
    Mandate,
    MandateAction,
    MandateProposal,
    Money,
    Operation,
    OperationProposal,
    OperationStatus,
    OperationStatusEntry,
    PickupWindow,
    Route,
)
from yuno_backend.volta.negotiations.models import (
    BrowserChannel,
    CallState,
    CarrierSession,
    Commitment,
    CommitmentDisposition,
    CommitmentLifecycle,
    MutationIdempotency,
    Negotiation,
    PreContactEscalation,
    Quote,
    QuoteEligibility,
    QuoteTerms,
)
from yuno_backend.volta.recovery.models import (
    EscalationContext,
    Notification,
    PostContactEscalation,
    RecoveryAttempt,
    RecoveryDecision,
    RecoveryDecisionState,
    RecoveryOutcome,
)

__all__: list[str] = []


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _draft_to_values(draft: IntakeDraft) -> dict[str, Any]:
    proposal = draft.proposal
    mandate = proposal.mandate
    return {
        "id": draft.id,
        "source_prompt": draft.source_prompt,
        "requested_language": draft.requested_language,
        "extraction_policy_version": draft.extraction_policy_version,
        "route_origin": proposal.route.origin,
        "route_destination": proposal.route.destination,
        "cargo_label": proposal.cargo_label,
        "pickup_date": proposal.pickup_date,
        "maximum_amount": mandate.maximum_amount.amount,
        "currency": mandate.maximum_amount.currency,
        "pickup_window_start_date": mandate.pickup_window.start_date,
        "pickup_window_end_date": mandate.pickup_window.end_date,
        "allowed_conditions": list(mandate.allowed_conditions),
        "escalation_conditions": list(mandate.escalation_conditions),
        "validation_issues": [
            {"field": issue.field, "reason_code": issue.reason_code}
            for issue in draft.validation_issues
        ],
        "approval_eligible": draft.approval_eligible,
        "version": draft.version,
        "created_at": draft.created_at,
        "updated_at": draft.updated_at,
    }


def _draft_from_row(row: Mapping[str, Any]) -> IntakeDraft:
    proposal = OperationProposal(
        route=Route(origin=row["route_origin"], destination=row["route_destination"]),
        pickup_date=row["pickup_date"],
        cargo_label=row["cargo_label"],
        mandate=MandateProposal(
            maximum_amount=Money(
                amount=Decimal(row["maximum_amount"]),
                currency=row["currency"],
            ),
            pickup_window=PickupWindow(
                start_date=row["pickup_window_start_date"],
                end_date=row["pickup_window_end_date"],
            ),
            allowed_conditions=tuple(row["allowed_conditions"]),
            escalation_conditions=tuple(row["escalation_conditions"]),
        ),
    )
    return IntakeDraft(
        id=row["id"],
        source_prompt=row["source_prompt"],
        requested_language=row["requested_language"],
        extraction_policy_version=row["extraction_policy_version"],
        proposal=proposal,
        validation_issues=tuple(
            DraftValidationIssue(field=item["field"], reason_code=item["reason_code"])
            for item in row["validation_issues"]
        ),
        approval_eligible=row["approval_eligible"],
        version=row["version"],
        created_at=_utc(row["created_at"]),
        updated_at=_utc(row["updated_at"]),
    )


def _operation_to_values(operation: Operation) -> dict[str, Any]:
    return {
        "id": operation.id,
        "version": operation.version,
        "source_draft_id": operation.source_draft_id,
        "source_draft_version": operation.source_draft_version,
        "route_origin": operation.route.origin,
        "route_destination": operation.route.destination,
        "cargo_label": operation.cargo_label,
        "pickup_date": operation.pickup_date,
        "active_mandate_id": operation.mandate.id,
        "created_at": operation.created_at,
    }


def _mandate_to_values(mandate: Mandate) -> dict[str, Any]:
    return {
        "id": mandate.id,
        "operation_id": mandate.operation_id,
        "version": mandate.version,
        "maximum_amount": mandate.maximum_amount.amount,
        "currency": mandate.maximum_amount.currency,
        "pickup_window_start_date": mandate.pickup_window.start_date,
        "pickup_window_end_date": mandate.pickup_window.end_date,
        "allowed_conditions": list(mandate.allowed_conditions),
        "escalation_conditions": list(mandate.escalation_conditions),
        "authorized_actions": [action.value for action in mandate.authorized_actions],
        "approval_actor": mandate.approval_actor,
        "approved_at": mandate.approved_at,
    }


def _status_to_values(entry: OperationStatusEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "operation_id": entry.operation_id,
        "operation_version": entry.operation_version,
        "status": entry.status.value,
        "occurred_at": entry.occurred_at,
    }


def _operation_from_rows(
    operation_row: Mapping[str, Any],
    mandate_row: Mapping[str, Any],
    status_rows: Iterable[Mapping[str, Any]],
) -> Operation:
    mandate = Mandate(
        id=mandate_row["id"],
        operation_id=mandate_row["operation_id"],
        version=mandate_row["version"],
        maximum_amount=Money(
            amount=Decimal(mandate_row["maximum_amount"]),
            currency=mandate_row["currency"],
        ),
        pickup_window=PickupWindow(
            start_date=mandate_row["pickup_window_start_date"],
            end_date=mandate_row["pickup_window_end_date"],
        ),
        allowed_conditions=tuple(mandate_row["allowed_conditions"]),
        escalation_conditions=tuple(mandate_row["escalation_conditions"]),
        authorized_actions=tuple(
            MandateAction(value) for value in mandate_row["authorized_actions"]
        ),
        approval_actor=mandate_row["approval_actor"],
        approved_at=_utc(mandate_row["approved_at"]),
    )
    history = tuple(
        OperationStatusEntry(
            id=row["id"],
            operation_id=row["operation_id"],
            operation_version=row["operation_version"],
            status=OperationStatus(row["status"]),
            occurred_at=_utc(row["occurred_at"]),
        )
        for row in status_rows
    )
    return Operation(
        id=operation_row["id"],
        version=operation_row["version"],
        source_draft_id=operation_row["source_draft_id"],
        source_draft_version=operation_row["source_draft_version"],
        route=Route(
            origin=operation_row["route_origin"],
            destination=operation_row["route_destination"],
        ),
        pickup_date=operation_row["pickup_date"],
        cargo_label=operation_row["cargo_label"],
        mandate=mandate,
        status=history[-1].status,
        status_history=history,
        created_at=_utc(operation_row["created_at"]),
    )


def _audit_to_values(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "operation_id": event.operation_id,
        "operation_version": event.operation_version,
        "actor_kind": event.actor_kind.value,
        "event_type": event.event_type,
        "occurred_at": event.occurred_at,
        "correlation_id": event.correlation_id,
        "metadata": dict(event.metadata),
    }


def _audit_from_row(row: Mapping[str, Any]) -> AuditEvent:
    return AuditEvent(
        event_id=row["event_id"],
        operation_id=row["operation_id"],
        operation_version=row["operation_version"],
        actor_kind=AuditActorKind(row["actor_kind"]),
        event_type=row["event_type"],
        occurred_at=_utc(row["occurred_at"]),
        correlation_id=row["correlation_id"],
        metadata=dict(row["metadata"]),
    )


def _session_to_values(value: CarrierSession) -> dict[str, Any]:
    return {
        "call_id": value.call_id,
        "negotiation_id": value.negotiation_id,
        "operation_id": value.operation_id,
        "carrier_id": value.carrier_id,
        "carrier_display_label": value.carrier_display_label,
        "route_origin": value.route.origin,
        "route_destination": value.route.destination,
        "available_snapshot": value.available_snapshot,
        "fixed_priority": value.fixed_priority,
        "selection_rank": value.selection_rank,
        "channel": value.channel.value,
        "state": value.state.value,
        "created_at": value.created_at,
    }


def _session_from_row(row: Mapping[str, Any]) -> CarrierSession:
    return CarrierSession(
        row["call_id"],
        row["negotiation_id"],
        row["operation_id"],
        row["carrier_id"],
        row["carrier_display_label"],
        Route(row["route_origin"], row["route_destination"]),
        row["available_snapshot"],
        row["fixed_priority"],
        row["selection_rank"],
        BrowserChannel(row["channel"]),
        CallState(row["state"]),
        _utc(row["created_at"]),
    )


def _escalation_to_values(value: PreContactEscalation) -> dict[str, Any]:
    return {
        "id": value.id,
        "negotiation_id": value.negotiation_id,
        "operation_id": value.operation_id,
        "reason_code": value.reason_code,
        "correlation_id": value.correlation_id,
        "created_at": value.created_at,
    }


def _escalation_from_row(row: Mapping[str, Any]) -> PreContactEscalation:
    return PreContactEscalation(
        row["id"],
        row["negotiation_id"],
        row["operation_id"],
        row["reason_code"],
        row["correlation_id"],
        _utc(row["created_at"]),
    )


def _negotiation_from_rows(
    row: Mapping[str, Any],
    sessions: Iterable[Mapping[str, Any]],
    escalation: Mapping[str, Any] | None,
) -> Negotiation:
    return Negotiation(
        row["id"],
        row["operation_id"],
        row["operation_version"],
        row["mandate_version"],
        tuple(_session_from_row(item) for item in sessions),
        None if escalation is None else _escalation_from_row(escalation),
        _utc(row["started_at"]),
    )


def _quote_to_values(value: Quote) -> dict[str, Any]:
    return {
        "id": value.id,
        "operation_id": value.operation_id,
        "call_id": value.call_id,
        "carrier_id": value.carrier_id,
        "carrier_priority": value.carrier_priority,
        "amount": value.terms.amount,
        "currency": value.terms.currency,
        "pickup_window_start": value.terms.pickup_window_start,
        "pickup_window_end": value.terms.pickup_window_end,
        "conditions": list(value.terms.conditions),
        "valid_until": value.valid_until,
        "mandate_version": value.mandate_version,
        "eligibility": value.eligibility.value,
        "rejection_reasons": list(value.rejection_reasons),
        "created_at": value.created_at,
    }


def _quote_from_row(row: Mapping[str, Any]) -> Quote:
    return Quote(
        row["id"],
        row["operation_id"],
        row["call_id"],
        row["carrier_id"],
        row["carrier_priority"],
        QuoteTerms(
            Decimal(row["amount"]),
            row["currency"],
            row["pickup_window_start"],
            row["pickup_window_end"],
            tuple(row["conditions"]),
        ),
        _utc(row["valid_until"]),
        row["mandate_version"],
        QuoteEligibility(row["eligibility"]),
        tuple(row["rejection_reasons"]),
        _utc(row["created_at"]),
    )


def _commitment_to_values(value: Commitment) -> dict[str, Any]:
    return {
        "id": value.id,
        "operation_id": value.operation_id,
        "call_id": value.call_id,
        "quote_id": value.quote_id,
        "carrier_id": value.carrier_id,
        "amount": value.agreed_terms.amount,
        "currency": value.agreed_terms.currency,
        "pickup_window_start": value.agreed_terms.pickup_window_start,
        "pickup_window_end": value.agreed_terms.pickup_window_end,
        "conditions": list(value.agreed_terms.conditions),
        "mandate_version": value.mandate_version,
        "evidence_id": value.evidence_id,
        "lifecycle": value.lifecycle.value,
        "disposition": value.disposition.value,
        "replaces_commitment_id": value.replaces_commitment_id,
        "replaced_by_commitment_id": value.replaced_by_commitment_id,
        "created_at": value.created_at,
        "superseded_at": value.superseded_at,
    }


def _commitment_from_row(row: Mapping[str, Any]) -> Commitment:
    return Commitment(
        row["id"],
        row["operation_id"],
        row["call_id"],
        row["quote_id"],
        row["carrier_id"],
        QuoteTerms(
            Decimal(row["amount"]),
            row["currency"],
            row["pickup_window_start"],
            row["pickup_window_end"],
            tuple(row["conditions"]),
        ),
        row["mandate_version"],
        row["evidence_id"],
        CommitmentLifecycle(row["lifecycle"]),
        CommitmentDisposition(row["disposition"]),
        row["replaces_commitment_id"],
        row["replaced_by_commitment_id"],
        _utc(row["created_at"]),
        None if row["superseded_at"] is None else _utc(row["superseded_at"]),
    )


def _idempotency_to_values(value: MutationIdempotency) -> dict[str, Any]:
    result_column = {
        "start_negotiation": "negotiation_id",
        "record_quote": "quote_id",
        "create_commitment": "commitment_id",
        "attach_commitment_evidence": "evidence_reservation_id",
    }[value.operation_name]
    return {
        "operation_name": value.operation_name,
        "idempotency_key": value.key,
        "operation_id": value.operation_id,
        "fingerprint": value.fingerprint,
        "negotiation_id": value.result_id if result_column == "negotiation_id" else None,
        "quote_id": value.result_id if result_column == "quote_id" else None,
        "commitment_id": value.result_id if result_column == "commitment_id" else None,
        "evidence_reservation_id": (
            value.result_id if result_column == "evidence_reservation_id" else None
        ),
        "created_at": value.created_at,
    }


def _idempotency_from_row(row: Mapping[str, Any]) -> MutationIdempotency:
    result_id = (
        row["negotiation_id"]
        or row["quote_id"]
        or row["commitment_id"]
        or row["evidence_reservation_id"]
    )
    return MutationIdempotency(
        row["operation_id"],
        row["operation_name"],
        row["idempotency_key"],
        row["fingerprint"],
        result_id,
        _utc(row["created_at"]),
    )


def _evidence_to_values(value: AgreementEvidence) -> dict[str, Any]:
    return {
        "id": value.id,
        "commitment_id": value.commitment_id,
        "recording_reference": value.recording_reference,
        "audio_start_ms": value.audio_start_ms,
        "item_id": value.item_id,
        "event_id": value.event_id,
        "created_at": value.created_at,
    }


def _text_idempotency_to_values(value: TextMutationIdempotency) -> dict[str, Any]:
    return {
        "operation_name": value.operation_name,
        "idempotency_key": value.key,
        "fingerprint": value.fingerprint,
        "draft_id": value.result_id if value.operation_name == "create_operation_draft" else None,
        "operation_id": value.result_id if value.operation_name == "approve_operation" else None,
        "created_at": value.created_at,
    }


def _evidence_from_row(row: Mapping[str, Any]) -> AgreementEvidence:
    return AgreementEvidence(
        row["id"],
        row["commitment_id"],
        row["recording_reference"],
        row["audio_start_ms"],
        row["item_id"],
        row["event_id"],
        _utc(row["created_at"]),
    )


def _brief_to_values(value: CallBrief) -> dict[str, Any]:
    return {
        "id": value.id,
        "commitment_id": value.commitment_id,
        "operation_id": value.operation_id,
        "route_origin": value.route.origin,
        "route_destination": value.route.destination,
        "carrier_id": value.carrier_id,
        "agreed_terms_reference": value.agreed_terms_reference,
        "mandate_version": value.mandate_version,
        "generated_at": value.generated_at,
    }


def _brief_from_row(row: Mapping[str, Any]) -> CallBrief:
    return CallBrief(
        row["id"],
        row["commitment_id"],
        row["operation_id"],
        Route(row["route_origin"], row["route_destination"]),
        row["carrier_id"],
        row["agreed_terms_reference"],
        row["mandate_version"],
        _utc(row["generated_at"]),
    )


def _recap_to_values(value: Recap) -> dict[str, Any]:
    return {
        "id": value.id,
        "commitment_id": value.commitment_id,
        "operation_id": value.operation_id,
        "disclosure_state": value.disclosure_state.value,
        "generated_at": value.generated_at,
    }


def _recap_from_row(row: Mapping[str, Any]) -> Recap:
    return Recap(
        row["id"],
        row["commitment_id"],
        row["operation_id"],
        RecapDisclosureState(row["disclosure_state"]),
        _utc(row["generated_at"]),
    )


def _post_contact_escalation_to_values(value: PostContactEscalation) -> dict[str, Any]:
    return {
        "id": value.id,
        "operation_id": value.operation_id,
        "commitment_id": value.commitment_id,
        "call_id": value.call_id,
        "reason_code": value.reason_code,
        "operation_version": value.operation_version,
        "mandate_version": value.mandate_version,
        "resolved": value.resolved,
        "correlation_id": value.correlation_id,
        "created_at": value.created_at,
        "resolved_at": value.resolved_at,
        "conflict": None if value.context is None else value.context.conflict,
        "attempted_alternatives": (
            None if value.context is None else list(value.context.attempted_alternatives)
        ),
        "recommended_action": (
            None if value.context is None else value.context.recommended_action
        ),
    }


def _post_contact_escalation_from_row(row: Mapping[str, Any]) -> PostContactEscalation:
    context = (
        None
        if row["conflict"] is None
        else EscalationContext(
            row["conflict"],
            tuple(row["attempted_alternatives"]),
            row["recommended_action"],
        )
    )
    return PostContactEscalation(
        row["id"],
        row["operation_id"],
        row["commitment_id"],
        row["reason_code"],
        row["operation_version"],
        row["mandate_version"],
        row["resolved"],
        row["correlation_id"],
        _utc(row["created_at"]),
        None if row["resolved_at"] is None else _utc(row["resolved_at"]),
        row["call_id"],
        context,
    )


def _recovery_attempt_to_values(value: RecoveryAttempt) -> dict[str, Any]:
    return {
        "id": value.id,
        "operation_id": value.operation_id,
        "commitment_id": value.commitment_id,
        "outcome": value.outcome.value,
        "resulting_commitment_id": value.resulting_commitment_id,
        "escalation_id": value.escalation_id,
        "correlation_id": value.correlation_id,
        "created_at": value.created_at,
    }


def _recovery_attempt_from_row(row: Mapping[str, Any]) -> RecoveryAttempt:
    return RecoveryAttempt(
        row["id"],
        row["operation_id"],
        row["commitment_id"],
        RecoveryOutcome(row["outcome"]),
        row["resulting_commitment_id"],
        row["escalation_id"],
        row["correlation_id"],
        _utc(row["created_at"]),
    )


def _notification_to_values(value: Notification) -> dict[str, Any]:
    return {
        "id": value.id,
        "operation_id": value.operation_id,
        "commitment_id": value.commitment_id,
        "reason_code": value.reason_code,
        "created_at": value.created_at,
        "operation_version": value.operation_version,
        "recovery_before": (
            None
            if value.recovery_decision is None
            else _decision_state_to_json(value.recovery_decision.before)
        ),
        "recovery_after": (
            None
            if value.recovery_decision is None
            else _decision_state_to_json(value.recovery_decision.after)
        ),
        "decision_reason": (
            None if value.recovery_decision is None else value.recovery_decision.reason
        ),
        "message": value.message,
        "correlation_id": value.correlation_id,
        "acknowledged_by": value.acknowledged_by,
        "acknowledged_at": value.acknowledged_at,
    }


def _notification_from_row(row: Mapping[str, Any]) -> Notification:
    decision = (
        None
        if row["recovery_before"] is None
        else RecoveryDecision(
            _decision_state_from_json(row["recovery_before"]),
            _decision_state_from_json(row["recovery_after"]),
            row["decision_reason"],
        )
    )
    return Notification(
        row["id"],
        row["operation_id"],
        row["commitment_id"],
        row["reason_code"],
        _utc(row["created_at"]),
        row["operation_version"],
        decision,
        row["message"],
        row["correlation_id"],
        row["acknowledged_by"],
        None if row["acknowledged_at"] is None else _utc(row["acknowledged_at"]),
    )


def _decision_state_to_json(value: RecoveryDecisionState) -> dict[str, Any]:
    terms = value.agreed_terms
    return {
        "operation_version": value.operation_version,
        "operation_status": value.operation_status.value,
        "active_commitment_id": (
            None if value.active_commitment_id is None else str(value.active_commitment_id)
        ),
        "carrier_id": None if value.carrier_id is None else str(value.carrier_id),
        "agreed_terms": (
            None
            if terms is None
            else {
                "amount": str(terms.amount),
                "currency": terms.currency,
                "pickup_window_start": terms.pickup_window_start.isoformat(),
                "pickup_window_end": terms.pickup_window_end.isoformat(),
                "conditions": list(terms.conditions),
            }
        ),
    }


def _decision_state_from_json(value: Mapping[str, Any]) -> RecoveryDecisionState:
    terms = value["agreed_terms"]
    return RecoveryDecisionState(
        operation_version=value["operation_version"],
        operation_status=OperationStatus(value["operation_status"]),
        active_commitment_id=(
            None
            if value["active_commitment_id"] is None
            else UUID(value["active_commitment_id"])
        ),
        carrier_id=None if value["carrier_id"] is None else UUID(value["carrier_id"]),
        agreed_terms=(
            None
            if terms is None
            else QuoteTerms(
                Decimal(terms["amount"]),
                terms["currency"],
                date.fromisoformat(terms["pickup_window_start"]),
                date.fromisoformat(terms["pickup_window_end"]),
                tuple(terms["conditions"]),
            )
        ),
    )


def _text_idempotency_from_row(row: Mapping[str, Any]) -> TextMutationIdempotency:
    return TextMutationIdempotency(
        row["operation_name"],
        row["idempotency_key"],
        row["fingerprint"],
        row["draft_id"] or row["operation_id"],
        _utc(row["created_at"]),
    )
