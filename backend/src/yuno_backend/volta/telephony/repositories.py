"""Atomic persistence port for durable outbound call attempts."""

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from yuno_backend.volta.telephony.models import (
    HumanHandoff,
    HumanHandoffCommand,
    HumanHandoffReadiness,
    HumanHandoffReservation,
    HumanHandoffStatus,
    HumanHandoffStatusEvent,
    OutboundCall,
    OutboundCallAttempt,
    OutboundCallAttemptReservation,
    OutboundCallFailure,
    OutboundCallUncertainState,
)

__all__ = [
    "AIAuthorityFence",
    "HumanHandoffAudit",
    "HumanHandoffRepository",
    "OutboundCallAttemptStore",
]


@runtime_checkable
class AIAuthorityFence(Protocol):
    """Fence enlisted in the same atomic reservation as the handoff."""

    async def fence(
        self, call_id: UUID, handoff_id: UUID, *, fenced_at: datetime
    ) -> None: ...

    async def ensure_speech_allowed(self, call_id: UUID) -> None: ...

    async def ensure_commitment_allowed(self, call_id: UUID) -> None: ...


@runtime_checkable
class HumanHandoffAudit(Protocol):
    """Safe audit boundary enlisted by the repository transaction."""

    async def handoff_requested(
        self, handoff: HumanHandoff, command: HumanHandoffCommand
    ) -> None: ...

    async def handoff_outcome(self, handoff: HumanHandoff) -> None: ...


@runtime_checkable
class HumanHandoffRepository(Protocol):
    """Atomic persistence boundary; implementations own transaction lifetime."""

    async def reserve(
        self,
        command: HumanHandoffCommand,
        proposed: HumanHandoff,
        authority_fence: AIAuthorityFence,
        audit: HumanHandoffAudit,
    ) -> HumanHandoffReservation: ...

    async def get(self, call_id: UUID, handoff_id: UUID) -> HumanHandoff | None: ...

    async def get_readiness(self, call_id: UUID) -> HumanHandoffReadiness | None: ...

    async def observe(
        self, event: HumanHandoffStatusEvent, audit: HumanHandoffAudit
    ) -> HumanHandoff | None: ...

    async def fail_provider_attempt(
        self,
        handoff_id: UUID,
        status: HumanHandoffStatus,
        occurred_at: datetime,
        audit: HumanHandoffAudit,
    ) -> HumanHandoff: ...


@runtime_checkable
class OutboundCallAttemptStore(Protocol):
    async def reserve(
        self, attempt: OutboundCallAttempt
    ) -> OutboundCallAttemptReservation: ...

    async def complete(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        result: OutboundCall,
        completed_at: datetime,
    ) -> OutboundCallAttempt: ...

    async def mark_uncertain(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        uncertainty: OutboundCallUncertainState,
    ) -> OutboundCallAttempt: ...

    async def fail(
        self,
        idempotency_key: str,
        request_fingerprint: str,
        failure: OutboundCallFailure,
    ) -> OutboundCallAttempt: ...
