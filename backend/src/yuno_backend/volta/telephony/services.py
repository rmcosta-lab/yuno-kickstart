"""Deterministic provider-neutral outbound call helpers."""

from dataclasses import replace

from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.idempotency import fingerprint
from yuno_backend.volta.telephony.models import (
    OutboundCall,
    OutboundCallRequest,
    OutboundCallStatus,
    OutboundCallStatusEvent,
)

__all__ = [
    "apply_status_event",
    "outbound_call_request_fingerprint",
    "transition_status",
]

_STATUS_ORDER = {
    OutboundCallStatus.QUEUED: 0,
    OutboundCallStatus.INITIATED: 1,
    OutboundCallStatus.RINGING: 2,
    OutboundCallStatus.IN_PROGRESS: 3,
    OutboundCallStatus.COMPLETED: 4,
    OutboundCallStatus.BUSY: 4,
    OutboundCallStatus.FAILED: 4,
    OutboundCallStatus.NO_ANSWER: 4,
    OutboundCallStatus.CANCELED: 4,
}


def outbound_call_request_fingerprint(request: OutboundCallRequest) -> str:
    """Hash the logical request without its caller-selected replay key."""

    if not isinstance(request, OutboundCallRequest):
        raise InvalidDomainValue("request", "outbound_call_request_required")
    return fingerprint(request, exclude=("idempotency_key",))


def transition_status(
    current: OutboundCallStatus, incoming: OutboundCallStatus
) -> OutboundCallStatus:
    """Apply the monotonic lifecycle rule without callback ordering metadata."""

    if not isinstance(current, OutboundCallStatus) or not isinstance(
        incoming, OutboundCallStatus
    ):
        raise InvalidDomainValue("status", "outbound_call_status_required")
    if current.is_terminal or _STATUS_ORDER[incoming] < _STATUS_ORDER[current]:
        return current
    return incoming


def apply_status_event(call: OutboundCall, event: OutboundCallStatusEvent) -> OutboundCall:
    """Apply a deduplicated, sequence-ordered callback without terminal regression."""

    if not isinstance(call, OutboundCall):
        raise InvalidDomainValue("call", "outbound_call_required")
    if not isinstance(event, OutboundCallStatusEvent):
        raise InvalidDomainValue("event", "outbound_call_status_event_required")
    if event.provider_call_id != call.provider_call_id:
        raise InvalidDomainValue("provider_call_id", "must_match_outbound_call")
    if event.provider_event_id in call.processed_status_event_ids:
        return call
    if (
        call.last_status_sequence_number is not None
        and event.sequence_number <= call.last_status_sequence_number
    ):
        return call

    next_status = transition_status(call.status, event.status)
    status_updated_at = call.status_updated_at
    if next_status is not call.status:
        status_updated_at = max(
            call.created_at,
            event.observed_at,
            *(value for value in (call.status_updated_at,) if value is not None),
        )
    return replace(
        call,
        status=next_status,
        status_updated_at=status_updated_at,
        last_status_event_id=event.provider_event_id,
        last_status_sequence_number=event.sequence_number,
        processed_status_event_ids=(*call.processed_status_event_ids, event.provider_event_id),
    )
