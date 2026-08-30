"""Persistence-neutral ports for negotiation application services."""

from datetime import datetime
from types import TracebackType
from typing import Protocol, Self, runtime_checkable
from uuid import UUID

from yuno_backend.volta.audit.repositories import AuditEventRepository
from yuno_backend.volta.mandates.models import Operation, Route
from yuno_backend.volta.mandates.repositories import Clock, IdGenerator
from yuno_backend.volta.negotiations.models import (
    CarrierProfile,
    Commitment,
    MutationIdempotency,
    Negotiation,
    Quote,
)

__all__ = [
    "CarrierCatalog",
    "CommitmentRepository",
    "IdempotencyRepository",
    "NegotiationRepository",
    "OperationUnitOfWork",
    "QuoteRepository",
]


@runtime_checkable
class CarrierCatalog(Protocol):
    def select(self, route: Route, *, limit: int = 3) -> tuple[CarrierProfile, ...]: ...


@runtime_checkable
class NegotiationRepository(Protocol):
    async def get(self, negotiation_id: UUID) -> Negotiation | None: ...
    async def get_by_operation(self, operation_id: UUID) -> Negotiation | None: ...
    async def get_by_call(self, call_id: UUID) -> Negotiation | None: ...
    async def add(self, negotiation: Negotiation) -> None: ...


@runtime_checkable
class QuoteRepository(Protocol):
    async def get(self, quote_id: UUID) -> Quote | None: ...
    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[Quote, ...]: ...
    async def add(self, quote: Quote) -> None: ...


@runtime_checkable
class CommitmentRepository(Protocol):
    async def get(self, commitment_id: UUID) -> Commitment | None: ...
    async def get_active(self, operation_id: UUID) -> Commitment | None: ...
    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[Commitment, ...]: ...
    async def add(self, commitment: Commitment) -> None: ...
    async def update(self, commitment: Commitment) -> None: ...
    async def lock_winner_scope(self, operation_id: UUID) -> None: ...


@runtime_checkable
class IdempotencyRepository(Protocol):
    async def get(self, operation_name: str, key: str) -> MutationIdempotency | None: ...
    async def add(self, record: MutationIdempotency) -> None: ...


@runtime_checkable
class MutableOperationRepository(Protocol):
    async def get(self, operation_id: UUID, *, for_update: bool = False) -> Operation | None: ...
    async def update(self, operation: Operation) -> None: ...


@runtime_checkable
class OperationUnitOfWork(Protocol):
    operations: MutableOperationRepository
    negotiations: NegotiationRepository
    quotes: QuoteRepository
    commitments: CommitmentRepository
    idempotency: IdempotencyRepository
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
    async def stabilize_read_snapshot(self) -> None: ...


ClockPort = Clock
IdGeneratorPort = IdGenerator
