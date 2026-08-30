"""Persistence-neutral ports for evidence application services."""

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from yuno_backend.volta.evidence.models import AgreementEvidence, CallBrief, Recap
from yuno_backend.volta.negotiations.repositories import (
    OperationUnitOfWork as _NegotiationOperationUnitOfWork,
)

__all__ = ["BriefRepository", "EvidenceRepository", "EvidenceStorage", "RecapRepository"]


@runtime_checkable
class EvidenceRepository(Protocol):
    async def get(self, evidence_id: UUID) -> AgreementEvidence | None: ...
    async def get_by_commitment(self, commitment_id: UUID) -> AgreementEvidence | None: ...
    async def add(self, evidence: AgreementEvidence) -> None: ...


@runtime_checkable
class BriefRepository(Protocol):
    async def get(self, brief_id: UUID) -> CallBrief | None: ...
    async def get_by_commitment(self, commitment_id: UUID) -> CallBrief | None: ...
    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[CallBrief, ...]: ...
    async def add(self, brief: CallBrief) -> None: ...


@runtime_checkable
class RecapRepository(Protocol):
    async def get(self, recap_id: UUID) -> Recap | None: ...
    async def get_by_commitment(self, commitment_id: UUID) -> Recap | None: ...
    async def list_by_operation(
        self, operation_id: UUID, *, after: tuple[datetime, UUID] | None = None,
        inclusive: bool = False, limit: int | None = None
    ) -> tuple[Recap, ...]: ...
    async def add(self, recap: Recap) -> None: ...


@runtime_checkable
class EvidenceStorage(Protocol):
    """Private-storage port for opaque call recording bytes.

    Implementations own access control and deletion outside PostgreSQL and
    outside Git; only the opaque `recording_reference` string returned by
    `store` is ever persisted in the database or crosses back into the
    domain layer. No raw path, transcript, or contact content is exposed by
    this protocol. Callers await `store`/`retrieve`/`delete` before
    beginning or after committing a persistence transaction; this port must
    never be awaited while a database transaction is open.
    """

    async def store(self, commitment_id: UUID, payload: bytes) -> str: ...
    async def retrieve(self, recording_reference: str) -> bytes: ...
    async def delete(self, recording_reference: str) -> None: ...


@runtime_checkable
class OperationUnitOfWork(_NegotiationOperationUnitOfWork, Protocol):
    """Negotiation unit of work additively extended with evidence repositories."""

    evidence: EvidenceRepository
    briefs: BriefRepository
    recaps: RecapRepository
