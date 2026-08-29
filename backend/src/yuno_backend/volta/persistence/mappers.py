"""Explicit mappings between frozen Volta domain values and private SQL rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from yuno_backend.volta.audit.models import AuditActorKind, AuditEvent
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
