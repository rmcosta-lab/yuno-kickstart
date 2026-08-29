"""Async SQLAlchemy repositories returning only frozen provider-neutral values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yuno_backend.volta.audit.models import AuditEvent
from yuno_backend.volta.mandates.errors import InvalidDomainValue, OperationAlreadyApproved
from yuno_backend.volta.mandates.models import IntakeDraft, Operation
from yuno_backend.volta.negotiations.models import (
    Commitment,
    MutationIdempotency,
    Negotiation,
    Quote,
)
from yuno_backend.volta.persistence.errors import PersistenceConflict, PersistenceUnavailable
from yuno_backend.volta.persistence.mappers import (
    _audit_from_row,
    _audit_to_values,
    _commitment_from_row,
    _commitment_to_values,
    _draft_from_row,
    _draft_to_values,
    _escalation_to_values,
    _idempotency_from_row,
    _idempotency_to_values,
    _mandate_to_values,
    _negotiation_from_rows,
    _operation_from_rows,
    _operation_to_values,
    _quote_from_row,
    _quote_to_values,
    _session_to_values,
    _status_to_values,
)
from yuno_backend.volta.persistence.tables import (
    _audit_events,
    _carrier_sessions,
    _commitments,
    _intake_drafts,
    _mandates,
    _mutation_idempotency,
    _negotiations,
    _operation_status_history,
    _operations,
    _pre_contact_escalations,
    _quotes,
)

__all__ = [
    "SqlAlchemyAuditEventRepository",
    "SqlAlchemyIntakeDraftRepository",
    "SqlAlchemyOperationRepository",
    "SqlAlchemyCommitmentRepository",
    "SqlAlchemyIdempotencyRepository",
    "SqlAlchemyNegotiationRepository",
    "SqlAlchemyQuoteRepository",
]


def _mapping(row: Any) -> Mapping[str, Any]:
    return row._mapping  # noqa: SLF001 - SQLAlchemy's documented Row mapping view


class SqlAlchemyIntakeDraftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, draft_id: UUID) -> IntakeDraft | None:
        try:
            row = (
                await self._session.execute(
                    select(_intake_drafts).where(_intake_drafts.c.id == draft_id)
                )
            ).first()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "intake_draft", draft_id) from None
        if row is None:
            return None
        try:
            return _draft_from_row(_mapping(row))
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "intake_draft", draft_id) from None

    async def add(self, draft: IntakeDraft) -> None:
        try:
            await self._session.execute(insert(_intake_drafts).values(_draft_to_values(draft)))
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "intake_draft", draft.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "intake_draft", draft.id) from None


class SqlAlchemyOperationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_draft_id(self, draft_id: UUID) -> Operation | None:
        return await self._get_by(_operations.c.source_draft_id == draft_id)

    async def get(self, operation_id: UUID, *, for_update: bool = False) -> Operation | None:
        return await self._get_by(_operations.c.id == operation_id, for_update=for_update)

    async def _get_by(self, criterion: Any, *, for_update: bool = False) -> Operation | None:
        try:
            statement = select(_operations).where(criterion)
            if for_update:
                statement = statement.with_for_update()
            operation_row = (await self._session.execute(statement)).first()
            if operation_row is None:
                return None
            operation = _mapping(operation_row)
            mandate_row = (
                await self._session.execute(
                    select(_mandates).where(
                        _mandates.c.operation_id == operation["id"],
                        _mandates.c.id == operation["active_mandate_id"],
                    )
                )
            ).first()
            status_rows = (
                await self._session.execute(
                    select(_operation_status_history)
                    .where(_operation_status_history.c.operation_id == operation["id"])
                    .order_by(
                        _operation_status_history.c.occurred_at,
                        _operation_status_history.c.id,
                    )
                )
            ).all()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "operation") from None
        operation_id = operation["id"]
        if mandate_row is None:
            raise PersistenceUnavailable(
                "invalid_stored_state", "operation", operation_id
            ) from None
        try:
            return _operation_from_rows(
                operation,
                _mapping(mandate_row),
                (_mapping(row) for row in status_rows),
            )
        except (InvalidDomainValue, IndexError, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable(
                "invalid_stored_state", "operation", operation_id
            ) from None

    async def add(self, operation: Operation) -> None:
        try:
            inserted_id = (
                await self._session.execute(
                    postgresql_insert(_operations)
                    .values(_operation_to_values(operation))
                    .on_conflict_do_nothing(constraint="uq_volta_operations_source_draft_id")
                    .returning(_operations.c.id)
                )
            ).scalar_one_or_none()
            if inserted_id is None:
                existing_id = (
                    await self._session.execute(
                        select(_operations.c.id).where(
                            _operations.c.source_draft_id == operation.source_draft_id
                        )
                    )
                ).scalar_one_or_none()
                if existing_id is None:
                    raise PersistenceConflict(
                        "duplicate_state_unavailable", "operation", operation.id
                    )
                raise OperationAlreadyApproved(operation.source_draft_id, existing_id)
            await self._session.execute(
                insert(_mandates).values(_mandate_to_values(operation.mandate))
            )
            await self._session.execute(
                insert(_operation_status_history),
                [_status_to_values(entry) for entry in operation.status_history],
            )
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "operation", operation.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "operation", operation.id) from None

    async def update(self, operation: Operation) -> None:
        try:
            changed = (
                await self._session.execute(
                    update(_operations)
                    .where(_operations.c.id == operation.id)
                    .values(version=operation.version)
                    .returning(_operations.c.id)
                )
            ).scalar_one_or_none()
            if changed is None:
                raise PersistenceConflict("missing_state", "operation", operation.id)
            await self._session.execute(
                insert(_operation_status_history).values(
                    _status_to_values(operation.status_history[-1])
                )
            )
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "operation", operation.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "operation", operation.id) from None


class SqlAlchemyAuditEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: AuditEvent) -> None:
        try:
            await self._session.execute(insert(_audit_events).values(_audit_to_values(event)))
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "audit_event", event.event_id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "audit_event", event.event_id) from None

    async def list_by_operation(self, operation_id: UUID) -> tuple[AuditEvent, ...]:
        try:
            rows = (
                await self._session.execute(
                    select(_audit_events)
                    .where(_audit_events.c.operation_id == operation_id)
                    .order_by(_audit_events.c.occurred_at, _audit_events.c.event_id)
                )
            ).all()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "audit_event", operation_id) from None
        try:
            return tuple(_audit_from_row(_mapping(row)) for row in rows)
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable(
                "invalid_stored_state", "audit_event", operation_id
            ) from None


class SqlAlchemyNegotiationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, negotiation_id: UUID) -> Negotiation | None:
        return await self._get_by(_negotiations.c.id == negotiation_id)

    async def get_by_operation(self, operation_id: UUID) -> Negotiation | None:
        return await self._get_by(_negotiations.c.operation_id == operation_id)

    async def get_by_call(self, call_id: UUID) -> Negotiation | None:
        try:
            negotiation_id = (
                await self._session.execute(
                    select(_carrier_sessions.c.negotiation_id).where(
                        _carrier_sessions.c.call_id == call_id
                    )
                )
            ).scalar_one_or_none()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "carrier_session", call_id) from None
        return None if negotiation_id is None else await self.get(negotiation_id)

    async def _get_by(self, criterion: Any) -> Negotiation | None:
        try:
            row = (await self._session.execute(select(_negotiations).where(criterion))).first()
            if row is None:
                return None
            identity = _mapping(row)
            sessions = (
                await self._session.execute(
                    select(_carrier_sessions)
                    .where(_carrier_sessions.c.negotiation_id == identity["id"])
                    .order_by(_carrier_sessions.c.selection_rank, _carrier_sessions.c.carrier_id)
                )
            ).all()
            escalation = (
                await self._session.execute(
                    select(_pre_contact_escalations).where(
                        _pre_contact_escalations.c.negotiation_id == identity["id"]
                    )
                )
            ).first()
            return _negotiation_from_rows(
                identity,
                (_mapping(item) for item in sessions),
                None if escalation is None else _mapping(escalation),
            )
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "negotiation") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "negotiation") from None

    async def add(self, negotiation: Negotiation) -> None:
        try:
            await self._session.execute(
                insert(_negotiations).values(
                    id=negotiation.id,
                    operation_id=negotiation.operation_id,
                    operation_version=negotiation.operation_version,
                    mandate_version=negotiation.mandate_version,
                    started_at=negotiation.started_at,
                )
            )
            if negotiation.sessions:
                await self._session.execute(
                    insert(_carrier_sessions),
                    [_session_to_values(item) for item in negotiation.sessions],
                )
            if negotiation.pre_contact_escalation is not None:
                await self._session.execute(
                    insert(_pre_contact_escalations).values(
                        _escalation_to_values(negotiation.pre_contact_escalation)
                    )
                )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "negotiation", negotiation.id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "negotiation", negotiation.id) from None


class SqlAlchemyQuoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, quote_id: UUID) -> Quote | None:
        try:
            row = (
                await self._session.execute(select(_quotes).where(_quotes.c.id == quote_id))
            ).first()
            return None if row is None else _quote_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "quote", quote_id) from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "quote", quote_id) from None

    async def list_by_operation(self, operation_id: UUID) -> tuple[Quote, ...]:
        try:
            rows = (
                await self._session.execute(
                    select(_quotes)
                    .where(_quotes.c.operation_id == operation_id)
                    .order_by(_quotes.c.created_at, _quotes.c.id)
                )
            ).all()
            return tuple(_quote_from_row(_mapping(row)) for row in rows)
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "quote", operation_id) from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "quote", operation_id) from None

    async def add(self, quote: Quote) -> None:
        try:
            await self._session.execute(insert(_quotes).values(_quote_to_values(quote)))
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "quote", quote.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "quote", quote.id) from None


class SqlAlchemyCommitmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, commitment_id: UUID) -> Commitment | None:
        return await self._get_by(_commitments.c.id == commitment_id)

    async def get_active(self, operation_id: UUID) -> Commitment | None:
        return await self._get_by(
            (_commitments.c.operation_id == operation_id) & (_commitments.c.disposition == "ACTIVE")
        )

    async def _get_by(self, criterion: Any) -> Commitment | None:
        try:
            row = (await self._session.execute(select(_commitments).where(criterion))).first()
            return None if row is None else _commitment_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "commitment") from None
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable("invalid_stored_state", "commitment") from None

    async def list_by_operation(self, operation_id: UUID) -> tuple[Commitment, ...]:
        try:
            rows = (
                await self._session.execute(
                    select(_commitments)
                    .where(_commitments.c.operation_id == operation_id)
                    .order_by(_commitments.c.created_at, _commitments.c.id)
                )
            ).all()
            return tuple(_commitment_from_row(_mapping(row)) for row in rows)
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "commitment", operation_id) from None

    async def add(self, commitment: Commitment) -> None:
        try:
            await self._session.execute(
                insert(_commitments).values(_commitment_to_values(commitment))
            )
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "commitment", commitment.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "commitment", commitment.id) from None

    async def update(self, commitment: Commitment) -> None:
        try:
            changed = (
                await self._session.execute(
                    update(_commitments)
                    .where(_commitments.c.id == commitment.id)
                    .values(_commitment_to_values(commitment))
                    .returning(_commitments.c.id)
                )
            ).scalar_one_or_none()
            if changed is None:
                raise PersistenceConflict("missing_state", "commitment", commitment.id)
        except IntegrityError:
            raise PersistenceConflict("integrity_constraint", "commitment", commitment.id) from None
        except DBAPIError:
            raise PersistenceUnavailable("write_failed", "commitment", commitment.id) from None

    async def lock_winner_scope(self, operation_id: UUID) -> None:
        try:
            await self._session.execute(
                select(_commitments.c.id)
                .where(_commitments.c.operation_id == operation_id)
                .order_by(_commitments.c.id)
                .with_for_update()
            )
        except DBAPIError:
            raise PersistenceUnavailable("lock_failed", "commitment", operation_id) from None


class SqlAlchemyIdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, operation_name: str, key: str) -> MutationIdempotency | None:
        try:
            row = (
                await self._session.execute(
                    select(_mutation_idempotency).where(
                        _mutation_idempotency.c.operation_name == operation_name,
                        _mutation_idempotency.c.idempotency_key == key,
                    )
                )
            ).first()
            return None if row is None else _idempotency_from_row(_mapping(row))
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "idempotency") from None

    async def add(self, record: MutationIdempotency) -> None:
        try:
            await self._session.execute(
                insert(_mutation_idempotency).values(_idempotency_to_values(record))
            )
        except IntegrityError:
            raise PersistenceConflict(
                "integrity_constraint", "idempotency", record.operation_id
            ) from None
        except DBAPIError:
            raise PersistenceUnavailable(
                "write_failed", "idempotency", record.operation_id
            ) from None
