"""Persistence-neutral ports used by mandate application services."""

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

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
class OperationUnitOfWork(Protocol):
    intake_drafts: IntakeDraftRepository
    operations: OperationRepository

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...
