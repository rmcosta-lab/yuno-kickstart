"""Persistence-neutral ports used by mandate application services."""

from datetime import datetime
from types import TracebackType
from typing import Protocol, Self, runtime_checkable
from uuid import UUID

from yuno_backend.volta.audit.repositories import AuditEventRepository
from yuno_backend.volta.idempotency import TextMutationIdempotency
from yuno_backend.volta.mandates.models import IntakeDraft, Operation

__all__ = [
    "Clock",
    "IdGenerator",
    "IntakeDraftRepository",
    "OperationRepository",
    "OperationUnitOfWork",
]


@runtime_checkable
class IntakeDraftRepository(Protocol):
    async def get(self, draft_id: UUID) -> IntakeDraft | None: ...

    async def add(self, draft: IntakeDraft) -> None: ...


@runtime_checkable
class OperationRepository(Protocol):
    async def get_by_draft_id(self, draft_id: UUID) -> Operation | None: ...

    async def add(self, operation: Operation) -> None: ...

@runtime_checkable
class TextMutationIdempotencyRepository(Protocol):
    async def lock(self, operation_name: str, key: str) -> None: ...

    async def get(
        self, operation_name: str, key: str
    ) -> TextMutationIdempotency | None: ...

    async def add(self, record: TextMutationIdempotency) -> None: ...


@runtime_checkable
class OperationUnitOfWork(Protocol):
    intake_drafts: IntakeDraftRepository
    operations: OperationRepository
    audit_events: AuditEventRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...
