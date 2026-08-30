"""Durable PostgreSQL repository for live human handoffs."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from yuno_backend.volta.persistence.errors import PersistenceConflict, PersistenceUnavailable
from yuno_backend.volta.persistence.repositories import _mapping
from yuno_backend.volta.persistence.tables import (
    _ai_authority_fences,
    _audit_events,
    _call_briefs,
    _human_handoffs,
    _mandates,
    _operations,
    _outbound_call_attempts,
    _quotes,
)
from yuno_backend.volta.telephony.errors import (
    HumanHandoffActiveConflict,
    HumanHandoffAuthorityError,
    HumanHandoffCallNotLiveError,
    HumanHandoffDestinationError,
    HumanHandoffIdempotencyConflict,
    HumanHandoffMissingContextError,
    HumanHandoffNotFoundError,
    HumanHandoffStaleCallError,
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
from yuno_backend.volta.telephony.repositories import AIAuthorityFence, HumanHandoffAudit
from yuno_backend.volta.telephony.services import apply_handoff_status_event

__all__ = ["SqlAlchemyHumanHandoffRepository"]


class SqlAlchemyHumanHandoffRepository:
    """Own one short transaction per reservation or callback observation."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        allowed_destination_labels: frozenset[str],
    ) -> None:
        self._session_factory = session_factory
        self._allowed_destination_labels = allowed_destination_labels

    async def reserve(
        self,
        command: HumanHandoffCommand,
        proposed: HumanHandoff,
        authority_fence: AIAuthorityFence,
        audit: HumanHandoffAudit,
    ) -> HumanHandoffReservation:
        try:
            async with self._session_factory.begin() as session:
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                    {"scope": f"human_handoff:{command.call_id}"},
                )
                existing = await self._by_key(session, command.idempotency_key)
                if existing is not None:
                    handoff, _operation_id, _version, _correlation_id = existing
                    if handoff.request_fingerprint != proposed.request_fingerprint:
                        raise HumanHandoffIdempotencyConflict(call_id=command.call_id)
                    return HumanHandoffReservation(handoff, False)
                if command.coordinator_destination_label not in self._allowed_destination_labels:
                    raise HumanHandoffDestinationError(call_id=command.call_id)
                active = (
                    await session.execute(
                        select(_human_handoffs.c.handoff_id).where(
                            _human_handoffs.c.call_id == command.call_id,
                            _human_handoffs.c.status == HumanHandoffStatus.CONNECTING.value,
                        )
                    )
                ).scalar_one_or_none()
                if active is not None:
                    raise HumanHandoffActiveConflict(call_id=command.call_id)
                context, operation_id, operation_version = await self._context(
                    session, command
                )
                handoff = replace(proposed, context=context)
                await session.execute(
                    insert(_human_handoffs).values(
                        **_handoff_values(
                            handoff,
                            operation_id=operation_id,
                            operation_version=operation_version,
                            correlation_id=command.correlation_id,
                        )
                    )
                )
                await session.execute(
                    insert(_ai_authority_fences).values(
                        call_id=handoff.call_id,
                        handoff_id=handoff.handoff_id,
                        fenced_at=handoff.requested_at,
                    )
                )
                await self._audit(
                    session,
                    handoff,
                    operation_id,
                    operation_version,
                    command.correlation_id,
                    "HANDOFF_REQUESTED",
                    event_id=handoff.handoff_id,
                )
                if authority_fence is not self:
                    await authority_fence.fence(
                        handoff.call_id,
                        handoff.handoff_id,
                        fenced_at=handoff.requested_at,
                    )
                if audit is not self:
                    await audit.handoff_requested(handoff, command)
                return HumanHandoffReservation(handoff, True)
        except (
            HumanHandoffActiveConflict,
            HumanHandoffCallNotLiveError,
            HumanHandoffDestinationError,
            HumanHandoffIdempotencyConflict,
            HumanHandoffMissingContextError,
            HumanHandoffNotFoundError,
            HumanHandoffStaleCallError,
        ):
            raise
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "human_handoff") from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "human_handoff") from None

    async def get(self, call_id: UUID, handoff_id: UUID) -> HumanHandoff | None:
        try:
            async with self._session_factory() as session:
                row = (
                    await session.execute(
                        select(_human_handoffs).where(
                            _human_handoffs.c.call_id == call_id,
                            _human_handoffs.c.handoff_id == handoff_id,
                        )
                    )
                ).first()
                return None if row is None else _handoff_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "human_handoff", handoff_id) from None

    async def get_readiness(self, call_id: UUID) -> HumanHandoffReadiness | None:
        try:
            async with self._session_factory() as session:
                readiness, _operation_id, _operation_version = (
                    await self._readiness_context(session, call_id)
                )
                return readiness
        except (HumanHandoffCallNotLiveError, HumanHandoffMissingContextError):
            raise
        except HumanHandoffNotFoundError:
            return None
        except DBAPIError:
            raise PersistenceUnavailable(
                "read_failed", "human_handoff_readiness", call_id
            ) from None

    async def observe(
        self, event: HumanHandoffStatusEvent, audit: HumanHandoffAudit
    ) -> HumanHandoff | None:
        try:
            async with self._session_factory.begin() as session:
                row = (
                    await session.execute(
                        select(_human_handoffs)
                        .where(_human_handoffs.c.handoff_id == event.handoff_id)
                        .with_for_update()
                    )
                ).first()
                if row is None:
                    return None
                values = _mapping(row)
                current = _handoff_from_row(values)
                if current.call_id != event.call_id:
                    return None
                updated = apply_handoff_status_event(current, event)
                if updated == current:
                    return current
                await session.execute(
                    update(_human_handoffs)
                    .where(_human_handoffs.c.handoff_id == updated.handoff_id)
                    .values(**_handoff_update_values(updated))
                )
                if updated.status.is_terminal and updated.status is not current.status:
                    await self._outcome_audit(
                        session, values, updated, event.provider_event_id
                    )
                    if audit is not self:
                        await audit.handoff_outcome(updated)
                return updated
        except DBAPIError:
            raise PersistenceUnavailable(
                "write_failed", "human_handoff", event.handoff_id
            ) from None

    async def fail_provider_attempt(
        self,
        handoff_id: UUID,
        status: HumanHandoffStatus,
        occurred_at: datetime,
        audit: HumanHandoffAudit,
    ) -> HumanHandoff:
        try:
            async with self._session_factory.begin() as session:
                row = (
                    await session.execute(
                        select(_human_handoffs)
                        .where(_human_handoffs.c.handoff_id == handoff_id)
                        .with_for_update()
                    )
                ).one()
                values = _mapping(row)
                current = _handoff_from_row(values)
                if current.status.is_terminal:
                    return current
                updated = replace(
                    current,
                    status=status,
                    status_updated_at=max(current.status_updated_at, occurred_at),
                )
                await session.execute(
                    update(_human_handoffs)
                    .where(_human_handoffs.c.handoff_id == handoff_id)
                    .values(**_handoff_update_values(updated))
                )
                await self._outcome_audit(session, values, updated, status.value)
                if audit is not self:
                    await audit.handoff_outcome(updated)
                return updated
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "human_handoff", handoff_id) from None

    async def fence(
        self, call_id: UUID, handoff_id: UUID, *, fenced_at: datetime
    ) -> None:
        try:
            async with self._session_factory.begin() as session:
                await session.execute(
                    insert(_ai_authority_fences).values(
                        call_id=call_id, handoff_id=handoff_id, fenced_at=fenced_at
                    )
                )
        except IntegrityError:
            raise HumanHandoffAuthorityError(call_id=call_id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "ai_authority_fence", call_id) from None

    async def ensure_speech_allowed(self, call_id: UUID) -> None:
        await self._ensure_allowed(call_id)

    async def ensure_commitment_allowed(self, call_id: UUID) -> None:
        await self._ensure_allowed(call_id)

    async def handoff_requested(
        self, handoff: HumanHandoff, command: HumanHandoffCommand
    ) -> None:
        del handoff, command

    async def handoff_outcome(self, handoff: HumanHandoff) -> None:
        del handoff

    async def _ensure_allowed(self, call_id: UUID) -> None:
        try:
            async with self._session_factory() as session:
                fenced = (
                    await session.execute(
                        select(_ai_authority_fences.c.call_id).where(
                            _ai_authority_fences.c.call_id == call_id
                        )
                    )
                ).scalar_one_or_none()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "ai_authority_fence", call_id) from None
        if fenced is not None:
            raise HumanHandoffAuthorityError(call_id=call_id)

    async def _by_key(self, session: AsyncSession, key: str):
        row = (
            await session.execute(
                select(_human_handoffs).where(_human_handoffs.c.idempotency_key == key)
            )
        ).first()
        if row is None:
            return None
        values = _mapping(row)
        return (
            _handoff_from_row(values),
            values["operation_id"],
            values["operation_version"],
            values["correlation_id"],
        )

    async def _context(
        self, session: AsyncSession, command: HumanHandoffCommand
    ) -> tuple[HumanHandoffContext, UUID, int]:
        readiness, operation_id, operation_version = await self._readiness_context(
            session, command.call_id
        )
        if (
            readiness.call_status_updated_at
            != command.expected_call_status_updated_at
        ):
            raise HumanHandoffStaleCallError(call_id=command.call_id)
        return readiness.context, operation_id, operation_version

    async def _readiness_context(
        self, session: AsyncSession, call_id: UUID
    ) -> tuple[HumanHandoffReadiness, UUID, int]:
        call = (
            await session.execute(
                select(_outbound_call_attempts).where(
                    _outbound_call_attempts.c.call_session_id == call_id
                )
                .order_by(_outbound_call_attempts.c.updated_at.desc())
                .limit(1)
            )
        ).first()
        if call is None:
            raise HumanHandoffNotFoundError(call_id=call_id)
        call_values = _mapping(call)
        if call_values["call_status"] != "IN_PROGRESS":
            raise HumanHandoffCallNotLiveError(call_id=call_id)
        operation_id = call_values["operation_id"]
        operation_row = (
            await session.execute(
                _readiness_operation_statement(operation_id)
            )
        ).first()
        brief_row = (
            await session.execute(
                select(_call_briefs)
                .where(_call_briefs.c.call_id == call_id)
                .order_by(_call_briefs.c.generated_at.desc())
                .limit(1)
            )
        ).first()
        if operation_row is None or brief_row is None:
            raise HumanHandoffMissingContextError(call_id=call_id)
        operation = _mapping(operation_row)
        brief = _mapping(brief_row)
        quote_rows = (
            await session.execute(
                select(_quotes)
                .where(
                    _quotes.c.operation_id == operation_id,
                    _quotes.c.eligibility == "ELIGIBLE",
                )
                .order_by(_quotes.c.carrier_priority, _quotes.c.created_at)
                .limit(3)
            )
        ).all()
        return self._project_readiness(
            call_id,
            call_values,
            operation,
            brief,
            tuple(_mapping(row) for row in quote_rows),
        )

    @staticmethod
    def _project_readiness(
        call_id: UUID,
        call_values,
        operation,
        brief,
        quote_rows,
    ) -> tuple[HumanHandoffReadiness, UUID, int]:
        """Project explicitly labeled operation and mandate versions."""

        operation_id = operation["operation_id"]
        facts = (
            f"Route: {operation['route_origin']} to {operation['route_destination']}",
            f"Cargo: {operation['cargo_label']}",
            f"Maximum: {_amount(operation['maximum_amount'])} {operation['currency']}",
            "Pickup window: "
            f"{operation['pickup_window_start_date']} to "
            f"{operation['pickup_window_end_date']}",
        )
        summaries = tuple(
            f"Priority {row['carrier_priority']}: "
            f"{_amount(row['amount'])} {row['currency']}"
            for row in quote_rows
        )
        structured = tuple(
            (
                *brief["facts"],
                *brief["objections"],
                *brief["changes"],
                *brief["unresolved_items"],
            )[:20]
        )
        return (
            HumanHandoffReadiness(
                call_id=call_id,
                call_status_updated_at=call_values["status_updated_at"],
                context=HumanHandoffContext(
                    mandate_version=operation["mandate_version"],
                    mandate_facts=facts,
                    eligible_quote_summaries=summaries,
                    structured_call_brief=structured,
                    call_status=call_values["call_status"],
                ),
            ),
            operation_id,
            operation["operation_version"],
        )

    async def _outcome_audit(
        self, session: AsyncSession, row, handoff: HumanHandoff, event_key: str
    ) -> None:
        await self._audit(
            session,
            handoff,
            row["operation_id"],
            row["operation_version"],
            row["correlation_id"],
            f"HANDOFF_{handoff.status.value}",
            event_id=uuid5(NAMESPACE_URL, f"human-handoff:{handoff.handoff_id}:{event_key}"),
        )

    @staticmethod
    async def _audit(
        session: AsyncSession,
        handoff: HumanHandoff,
        operation_id: UUID,
        operation_version: int,
        correlation_id: UUID,
        event_type: str,
        *,
        event_id: UUID,
    ) -> None:
        await session.execute(
            insert(_audit_events).values(
                event_id=event_id,
                operation_id=operation_id,
                operation_version=operation_version,
                actor_kind="SYSTEM",
                event_type=event_type,
                occurred_at=handoff.status_updated_at,
                correlation_id=correlation_id,
                metadata={},
            )
        )


def _amount(value: Decimal) -> str:
    return format(value, "f")


def _readiness_operation_statement(operation_id: UUID):
    return (
        select(
            _operations.c.id.label("operation_id"),
            _operations.c.version.label("operation_version"),
            _operations.c.route_origin,
            _operations.c.route_destination,
            _operations.c.cargo_label,
            _mandates.c.version.label("mandate_version"),
            _mandates.c.maximum_amount,
            _mandates.c.currency,
            _mandates.c.pickup_window_start_date,
            _mandates.c.pickup_window_end_date,
        )
        .join(
            _mandates,
            (_mandates.c.operation_id == _operations.c.id)
            & (_mandates.c.id == _operations.c.active_mandate_id),
        )
        .where(_operations.c.id == operation_id)
    )


def _context_values(context: HumanHandoffContext) -> dict[str, object]:
    return {
        "mandate_version": context.mandate_version,
        "mandate_facts": list(context.mandate_facts),
        "eligible_quote_summaries": list(context.eligible_quote_summaries),
        "structured_call_brief": list(context.structured_call_brief),
        "call_status": context.call_status,
    }


def _handoff_values(
    handoff: HumanHandoff,
    *,
    operation_id: UUID,
    operation_version: int,
    correlation_id: UUID,
) -> dict[str, object]:
    return {
        "handoff_id": handoff.handoff_id,
        "call_id": handoff.call_id,
        "operation_id": operation_id,
        "operation_version": operation_version,
        "correlation_id": correlation_id,
        "coordinator_destination_label": handoff.coordinator_destination_label,
        "idempotency_key": handoff.idempotency_key,
        "request_fingerprint": handoff.request_fingerprint,
        **_handoff_update_values(handoff),
        "requested_at": handoff.requested_at,
        "context": _context_values(handoff.context),
    }


def _handoff_update_values(handoff: HumanHandoff) -> dict[str, object]:
    return {
        "status": handoff.status.value,
        "status_updated_at": handoff.status_updated_at,
        "last_status_event_id": handoff.last_status_event_id,
        "last_status_sequence_number": handoff.last_status_sequence_number,
        "processed_status_event_ids": list(handoff.processed_status_event_ids),
    }


def _handoff_from_row(row) -> HumanHandoff:
    context = row["context"]
    return HumanHandoff(
        handoff_id=row["handoff_id"],
        call_id=row["call_id"],
        coordinator_destination_label=row["coordinator_destination_label"],
        idempotency_key=row["idempotency_key"],
        request_fingerprint=row["request_fingerprint"],
        status=HumanHandoffStatus(row["status"]),
        requested_at=row["requested_at"],
        status_updated_at=row["status_updated_at"],
        context=HumanHandoffContext(
            mandate_version=context["mandate_version"],
            mandate_facts=tuple(context["mandate_facts"]),
            eligible_quote_summaries=tuple(context["eligible_quote_summaries"]),
            structured_call_brief=tuple(context["structured_call_brief"]),
            call_status=context["call_status"],
        ),
        last_status_event_id=row["last_status_event_id"],
        last_status_sequence_number=row["last_status_sequence_number"],
        processed_status_event_ids=tuple(row["processed_status_event_ids"]),
    )
