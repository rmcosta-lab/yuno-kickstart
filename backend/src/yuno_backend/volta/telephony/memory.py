"""Deterministic in-process handoff ports for tests and local fallback."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime
from uuid import UUID

from yuno_backend.volta.telephony.errors import (
    HumanHandoffActiveConflict,
    HumanHandoffAuthorityError,
    HumanHandoffDestinationError,
    HumanHandoffIdempotencyConflict,
)
from yuno_backend.volta.telephony.models import (
    HumanHandoff,
    HumanHandoffCommand,
    HumanHandoffContext,
    HumanHandoffReadiness,
    HumanHandoffReservation,
    HumanHandoffStatus,
    HumanHandoffStatusEvent,
)
from yuno_backend.volta.telephony.repositories import (
    AIAuthorityFence,
    HumanHandoffAudit,
)
from yuno_backend.volta.telephony.services import apply_handoff_status_event

__all__ = ["InMemoryAIAuthorityFence", "InMemoryHumanHandoffRepository"]

type ContextResolver = Callable[
    [UUID, datetime], Awaitable[HumanHandoffContext]
]
type ReadinessResolver = Callable[
    [UUID], Awaitable[HumanHandoffReadiness | None]
]


class InMemoryAIAuthorityFence:
    """Race-safe demo fence; production persistence belongs in PostgreSQL."""

    def __init__(
        self, clear_pending_audio: Callable[[UUID], Awaitable[None]] | None = None
    ) -> None:
        self._fenced: dict[UUID, UUID] = {}
        self._lock = asyncio.Lock()
        self._clear_pending_audio = clear_pending_audio

    async def fence(
        self, call_id: UUID, handoff_id: UUID, *, fenced_at: datetime
    ) -> None:
        del fenced_at
        async with self._lock:
            current = self._fenced.get(call_id)
            if current is not None and current != handoff_id:
                raise HumanHandoffAuthorityError(call_id=call_id)
            self._fenced[call_id] = handoff_id
            if self._clear_pending_audio is not None:
                await self._clear_pending_audio(call_id)

    async def ensure_speech_allowed(self, call_id: UUID) -> None:
        if call_id in self._fenced:
            raise HumanHandoffAuthorityError(call_id=call_id)

    async def ensure_commitment_allowed(self, call_id: UUID) -> None:
        if call_id in self._fenced:
            raise HumanHandoffAuthorityError(call_id=call_id)


class InMemoryHumanHandoffRepository:
    """Atomic reference repository used by deterministic application tests."""

    def __init__(
        self,
        context_resolver: ContextResolver,
        *,
        allowed_destination_labels: frozenset[str],
        readiness_resolver: ReadinessResolver | None = None,
    ) -> None:
        self._context_resolver = context_resolver
        self._allowed_destination_labels = allowed_destination_labels
        self._readiness_resolver = readiness_resolver
        self._by_id: dict[UUID, HumanHandoff] = {}
        self._by_key: dict[str, UUID] = {}
        self._active_by_call: dict[UUID, UUID] = {}
        self._lock = asyncio.Lock()

    async def reserve(
        self,
        command: HumanHandoffCommand,
        proposed: HumanHandoff,
        authority_fence: AIAuthorityFence,
        audit: HumanHandoffAudit,
    ) -> HumanHandoffReservation:
        async with self._lock:
            existing_id = self._by_key.get(command.idempotency_key)
            if existing_id is not None:
                existing = self._by_id[existing_id]
                if existing.request_fingerprint != proposed.request_fingerprint:
                    raise HumanHandoffIdempotencyConflict(call_id=command.call_id)
                return HumanHandoffReservation(existing, False)
            if command.coordinator_destination_label not in self._allowed_destination_labels:
                raise HumanHandoffDestinationError(call_id=command.call_id)
            active_id = self._active_by_call.get(command.call_id)
            if active_id is not None:
                active = self._by_id[active_id]
                if not active.status.is_terminal:
                    raise HumanHandoffActiveConflict(call_id=command.call_id)
            context = await self._context_resolver(
                command.call_id, command.expected_call_status_updated_at
            )
            handoff = replace(proposed, context=context)
            # Durable implementations enlist both ports in this same transaction.
            await authority_fence.fence(
                handoff.call_id, handoff.handoff_id, fenced_at=handoff.requested_at
            )
            await audit.handoff_requested(handoff, command)
            self._by_id[handoff.handoff_id] = handoff
            self._by_key[handoff.idempotency_key] = handoff.handoff_id
            self._active_by_call[handoff.call_id] = handoff.handoff_id
            return HumanHandoffReservation(handoff, True)

    async def get(self, call_id: UUID, handoff_id: UUID) -> HumanHandoff | None:
        handoff = self._by_id.get(handoff_id)
        return handoff if handoff is not None and handoff.call_id == call_id else None

    async def get_readiness(self, call_id: UUID) -> HumanHandoffReadiness | None:
        if self._readiness_resolver is None:
            return None
        return await self._readiness_resolver(call_id)

    async def observe(
        self, event: HumanHandoffStatusEvent, audit: HumanHandoffAudit
    ) -> HumanHandoff | None:
        async with self._lock:
            current = self._by_id.get(event.handoff_id)
            if current is None or current.call_id != event.call_id:
                return None
            updated = apply_handoff_status_event(current, event)
            if updated is current:
                return current
            if updated.status.is_terminal and updated.status is not current.status:
                await audit.handoff_outcome(updated)
            self._by_id[updated.handoff_id] = updated
            return updated

    async def fail_provider_attempt(
        self,
        handoff_id: UUID,
        status: HumanHandoffStatus,
        occurred_at: datetime,
        audit: HumanHandoffAudit,
    ) -> HumanHandoff:
        if status not in {
            HumanHandoffStatus.FAILED_SAFE,
            HumanHandoffStatus.TIMED_OUT_SAFE,
        }:
            raise ValueError("provider attempt must end in a safe failure state")
        async with self._lock:
            current = self._by_id[handoff_id]
            if current.status.is_terminal:
                return current
            updated = replace(
                current,
                status=status,
                status_updated_at=max(current.status_updated_at, occurred_at),
            )
            await audit.handoff_outcome(updated)
            self._by_id[handoff_id] = updated
            return updated
