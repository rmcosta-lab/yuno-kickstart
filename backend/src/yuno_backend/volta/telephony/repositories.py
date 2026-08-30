"""Atomic persistence port for durable outbound call attempts."""

from datetime import datetime
from typing import Protocol, runtime_checkable

from yuno_backend.volta.telephony.models import (
    OutboundCall,
    OutboundCallAttempt,
    OutboundCallAttemptReservation,
    OutboundCallFailure,
    OutboundCallUncertainState,
)

__all__ = ["OutboundCallAttemptStore"]


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
