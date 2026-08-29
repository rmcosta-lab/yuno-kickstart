"""Persistence-neutral append/list port for operation audit evidence."""

from typing import Protocol, runtime_checkable
from uuid import UUID

from yuno_backend.volta.audit.models import AuditEvent

__all__ = ["AuditEventRepository"]


@runtime_checkable
class AuditEventRepository(Protocol):
    async def add(self, event: AuditEvent) -> None: ...

    async def list_by_operation(self, operation_id: UUID) -> tuple[AuditEvent, ...]: ...
