"""Persistence-neutral ports for recovery application services."""

from typing import Protocol, runtime_checkable
from uuid import UUID

from yuno_backend.volta.evidence.repositories import (
    OperationUnitOfWork as _EvidenceOperationUnitOfWork,
)
from yuno_backend.volta.recovery.models import Notification, PostContactEscalation, RecoveryAttempt

__all__ = [
    "NotificationRepository",
    "OperationUnitOfWork",
    "PostContactEscalationRepository",
    "RecoveryAttemptRepository",
]


@runtime_checkable
class RecoveryAttemptRepository(Protocol):
    async def get(self, attempt_id: UUID) -> RecoveryAttempt | None: ...
    async def list_by_operation(self, operation_id: UUID) -> tuple[RecoveryAttempt, ...]: ...
    async def add(self, attempt: RecoveryAttempt) -> None: ...


@runtime_checkable
class PostContactEscalationRepository(Protocol):
    async def get(self, escalation_id: UUID) -> PostContactEscalation | None: ...
    async def get_unresolved_by_operation(
        self, operation_id: UUID
    ) -> PostContactEscalation | None: ...
    async def add(self, escalation: PostContactEscalation) -> None: ...
    async def update(self, escalation: PostContactEscalation) -> None: ...


@runtime_checkable
class NotificationRepository(Protocol):
    async def get(self, notification_id: UUID) -> Notification | None: ...
    async def list_by_operation(self, operation_id: UUID) -> tuple[Notification, ...]: ...
    async def add(self, notification: Notification) -> None: ...


@runtime_checkable
class OperationUnitOfWork(_EvidenceOperationUnitOfWork, Protocol):
    """Evidence unit of work additively extended with recovery repositories."""

    recovery_attempts: RecoveryAttemptRepository
    post_contact_escalations: PostContactEscalationRepository
    notifications: NotificationRepository
