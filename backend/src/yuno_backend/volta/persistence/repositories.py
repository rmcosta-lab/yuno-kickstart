"""Async SQLAlchemy repositories returning only frozen provider-neutral values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from yuno_backend.volta.audit.models import AuditEvent
from yuno_backend.volta.mandates.errors import InvalidDomainValue, OperationAlreadyApproved
from yuno_backend.volta.mandates.models import IntakeDraft, Operation
from yuno_backend.volta.persistence.errors import PersistenceConflict, PersistenceUnavailable
from yuno_backend.volta.persistence.mappers import (
    _audit_from_row,
    _audit_to_values,
    _draft_from_row,
    _draft_to_values,
    _mandate_to_values,
    _operation_from_rows,
    _operation_to_values,
    _status_to_values,
)
from yuno_backend.volta.persistence.tables import (
    _audit_events,
    _intake_drafts,
    _mandates,
    _operation_status_history,
    _operations,
)

__all__ = [
    "SqlAlchemyAuditEventRepository",
    "SqlAlchemyIntakeDraftRepository",
    "SqlAlchemyOperationRepository",
]

def _mapping(row: Any) -> Mapping[str, Any]:
    return row._mapping  # noqa: SLF001 - SQLAlchemy's documented Row mapping view


class SqlAlchemyIntakeDraftRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, draft_id: UUID) -> IntakeDraft | None:
        try:
            row = (await self._session.execute(
                select(_intake_drafts).where(_intake_drafts.c.id == draft_id)
            )).first()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "intake_draft", draft_id) from None
        if row is None:
            return None
        try:
            return _draft_from_row(_mapping(row))
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable(
                "invalid_stored_state", "intake_draft", draft_id
            ) from None

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

    async def _get_by(self, criterion: Any) -> Operation | None:
        try:
            operation_row = (await self._session.execute(
                select(_operations).where(criterion)
            )).first()
            if operation_row is None:
                return None
            operation = _mapping(operation_row)
            mandate_row = (await self._session.execute(
                select(_mandates).where(
                    _mandates.c.operation_id == operation["id"],
                    _mandates.c.id == operation["active_mandate_id"],
                )
            )).first()
            status_rows = (await self._session.execute(
                select(_operation_status_history)
                .where(_operation_status_history.c.operation_id == operation["id"])
                .order_by(
                    _operation_status_history.c.occurred_at,
                    _operation_status_history.c.id,
                )
            )).all()
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
            inserted_id = (await self._session.execute(
                postgresql_insert(_operations)
                .values(_operation_to_values(operation))
                .on_conflict_do_nothing(constraint="uq_volta_operations_source_draft_id")
                .returning(_operations.c.id)
            )).scalar_one_or_none()
            if inserted_id is None:
                existing_id = (await self._session.execute(
                    select(_operations.c.id).where(
                        _operations.c.source_draft_id == operation.source_draft_id
                    )
                )).scalar_one_or_none()
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
            rows = (await self._session.execute(
                select(_audit_events)
                .where(_audit_events.c.operation_id == operation_id)
                .order_by(_audit_events.c.occurred_at, _audit_events.c.event_id)
            )).all()
        except DBAPIError:
            raise PersistenceUnavailable("read_failed", "audit_event", operation_id) from None
        try:
            return tuple(_audit_from_row(_mapping(row)) for row in rows)
        except (InvalidDomainValue, KeyError, TypeError, ValueError):
            raise PersistenceUnavailable(
                "invalid_stored_state", "audit_event", operation_id
            ) from None
