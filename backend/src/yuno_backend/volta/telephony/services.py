"""Deterministic provider-neutral telephony application services."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid4

from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.idempotency import fingerprint
from yuno_backend.volta.telephony.errors import (
    HumanHandoffError,
    HumanHandoffNotFoundError,
    HumanHandoffOutcomeUncertain,
    HumanHandoffTimeoutError,
)
from yuno_backend.volta.telephony.gateway import HumanHandoffGateway
from yuno_backend.volta.telephony.models import (
    HumanHandoff,
    HumanHandoffCommand,
    HumanHandoffReadiness,
    HumanHandoffStatus,
    HumanHandoffStatusEvent,
    OutboundCall,
    OutboundCallRequest,
    OutboundCallStatus,
    OutboundCallStatusEvent,
)
from yuno_backend.volta.telephony.repositories import (
    AIAuthorityFence,
    HumanHandoffAudit,
    HumanHandoffRepository,
)

__all__ = [
    "HumanHandoffService",
    "apply_handoff_status_event",
    "human_handoff_request_fingerprint",
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


class _Clock(Protocol):
    def now(self) -> datetime: ...


class HumanHandoffService:
    """Reserve/fence/audit first, then perform provider I/O outside a transaction."""

    def __init__(
        self,
        repository: HumanHandoffRepository,
        gateway: HumanHandoffGateway,
        audit: HumanHandoffAudit,
        clock: _Clock,
        authority_fence: AIAuthorityFence,
        *,
        id_generator: Callable[[], UUID] = uuid4,
        authorization_max_age_seconds: int = 300,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._audit = audit
        self._clock = clock
        self._authority_fence = authority_fence
        self._id_generator = id_generator
        self._authorization_max_age_seconds = authorization_max_age_seconds

    async def request_handoff(self, command: HumanHandoffCommand) -> HumanHandoff:
        if not isinstance(command, HumanHandoffCommand):
            raise InvalidDomainValue("command", "human_handoff_command_required")
        now = self._clock.now()
        age = (now - command.authorized_at).total_seconds()
        if age < 0 or age > self._authorization_max_age_seconds:
            from yuno_backend.volta.telephony.errors import HumanHandoffAuthorityError

            raise HumanHandoffAuthorityError(call_id=command.call_id)
        request_fingerprint = human_handoff_request_fingerprint(command)
        proposed = HumanHandoff(
            handoff_id=self._id_generator(),
            call_id=command.call_id,
            coordinator_destination_label=command.coordinator_destination_label,
            idempotency_key=command.idempotency_key,
            request_fingerprint=request_fingerprint,
            status=HumanHandoffStatus.CONNECTING,
            requested_at=now,
            status_updated_at=now,
            context=_unresolved_context(),
        )
        reservation = await self._repository.reserve(
            command, proposed, self._authority_fence, self._audit
        )
        handoff = reservation.handoff
        if not reservation.created:
            return handoff
        try:
            await self._gateway.begin_handoff(handoff)
        except HumanHandoffTimeoutError:
            await self._repository.fail_provider_attempt(
                handoff.handoff_id,
                HumanHandoffStatus.TIMED_OUT_SAFE,
                self._clock.now(),
                self._audit,
            )
            raise
        except HumanHandoffError:
            await self._repository.fail_provider_attempt(
                handoff.handoff_id,
                HumanHandoffStatus.FAILED_SAFE,
                self._clock.now(),
                self._audit,
            )
            raise
        except Exception:
            await self._repository.fail_provider_attempt(
                handoff.handoff_id,
                HumanHandoffStatus.FAILED_SAFE,
                self._clock.now(),
                self._audit,
            )
            raise HumanHandoffOutcomeUncertain(call_id=handoff.call_id) from None
        return await self.get_handoff(handoff.call_id, handoff.handoff_id)

    async def get_handoff(self, call_id: UUID, handoff_id: UUID) -> HumanHandoff:
        handoff = await self._repository.get(call_id, handoff_id)
        if handoff is None:
            raise HumanHandoffNotFoundError(call_id=call_id)
        return handoff

    async def get_handoff_readiness(self, call_id: UUID) -> HumanHandoffReadiness:
        readiness = await self._repository.get_readiness(call_id)
        if readiness is None:
            raise HumanHandoffNotFoundError(call_id=call_id)
        return readiness

    async def observe_handoff(
        self, event: HumanHandoffStatusEvent
    ) -> HumanHandoff:
        if not isinstance(event, HumanHandoffStatusEvent):
            raise InvalidDomainValue("event", "human_handoff_status_event_required")
        handoff = await self._repository.observe(event, self._audit)
        if handoff is None:
            raise HumanHandoffNotFoundError(call_id=event.call_id)
        return handoff


def human_handoff_request_fingerprint(command: HumanHandoffCommand) -> str:
    if not isinstance(command, HumanHandoffCommand):
        raise InvalidDomainValue("command", "human_handoff_command_required")
    return fingerprint(command, exclude=("idempotency_key", "correlation_id"))


def apply_handoff_status_event(
    handoff: HumanHandoff, event: HumanHandoffStatusEvent
) -> HumanHandoff:
    """Apply callback evidence once without terminal or sequence regression."""

    if handoff.call_id != event.call_id or handoff.handoff_id != event.handoff_id:
        raise InvalidDomainValue("event", "must_match_handoff")
    if event.provider_event_id in handoff.processed_status_event_ids:
        return handoff
    if (
        handoff.last_status_sequence_number is not None
        and event.sequence_number <= handoff.last_status_sequence_number
    ):
        return handoff
    next_status = handoff.status if handoff.status.is_terminal else event.status
    return replace(
        handoff,
        status=next_status,
        status_updated_at=(
            max(handoff.status_updated_at, event.observed_at)
            if next_status is not handoff.status
            else handoff.status_updated_at
        ),
        last_status_event_id=event.provider_event_id,
        last_status_sequence_number=event.sequence_number,
        processed_status_event_ids=(
            *handoff.processed_status_event_ids,
            event.provider_event_id,
        ),
    )


def _unresolved_context():
    """Repository atomically replaces this sentinel with current bounded context."""

    from yuno_backend.volta.telephony.models import HumanHandoffContext

    return HumanHandoffContext(
        mandate_version=1,
        mandate_facts=(),
        eligible_quote_summaries=(),
        structured_call_brief=(),
        call_status="UNRESOLVED",
    )


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
