from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from yuno_backend.volta.audit.models import AuditEvent
from yuno_backend.volta.evidence.models import AgreementEvidence, CallBrief, Recap
from yuno_backend.volta.mandates.models import (
    Mandate,
    MandateAction,
    Money,
    Operation,
    OperationStatus,
    OperationStatusEntry,
    PickupWindow,
    Route,
)
from yuno_backend.volta.negotiations.models import (
    Commitment,
    CommitmentDisposition,
    CommitmentLifecycle,
    QuoteTerms,
)

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
OPERATION_ID = UUID(int=100)


@dataclass
class Ids:
    next_value: int = 1000

    def new_id(self) -> UUID:
        value = UUID(int=self.next_value)
        self.next_value += 1
        return value


@dataclass(frozen=True)
class Clock:
    value: datetime = NOW

    def now(self) -> datetime:
        return self.value


@dataclass
class Operations:
    value: Operation

    async def get(self, operation_id: UUID, *, for_update: bool = False) -> Operation | None:
        del for_update
        return self.value if operation_id == self.value.id else None

    async def update(self, operation: Operation) -> None:
        self.value = operation


@dataclass
class Commitments:
    values: dict[UUID, Commitment] = field(default_factory=dict)

    async def get(self, commitment_id: UUID) -> Commitment | None:
        return self.values.get(commitment_id)

    async def get_active(self, operation_id: UUID) -> Commitment | None:
        return next(
            (
                item
                for item in self.values.values()
                if item.operation_id == operation_id
                and item.disposition is CommitmentDisposition.ACTIVE
            ),
            None,
        )

    async def list_by_operation(self, operation_id: UUID) -> tuple[Commitment, ...]:
        return tuple(item for item in self.values.values() if item.operation_id == operation_id)

    async def add(self, commitment: Commitment) -> None:
        self.values[commitment.id] = commitment

    async def update(self, commitment: Commitment) -> None:
        self.values[commitment.id] = commitment

    async def lock_winner_scope(self, operation_id: UUID) -> None:
        del operation_id


@dataclass
class Evidence:
    values: dict[UUID, AgreementEvidence] = field(default_factory=dict)

    async def get(self, evidence_id: UUID) -> AgreementEvidence | None:
        return self.values.get(evidence_id)

    async def get_by_commitment(self, commitment_id: UUID) -> AgreementEvidence | None:
        return next(
            (item for item in self.values.values() if item.commitment_id == commitment_id), None
        )

    async def add(self, evidence: AgreementEvidence) -> None:
        self.values[evidence.id] = evidence


@dataclass
class Briefs:
    values: dict[UUID, CallBrief] = field(default_factory=dict)

    async def get(self, brief_id: UUID) -> CallBrief | None:
        return self.values.get(brief_id)

    async def get_by_commitment(self, commitment_id: UUID) -> CallBrief | None:
        return next(
            (item for item in self.values.values() if item.commitment_id == commitment_id), None
        )

    async def add(self, brief: CallBrief) -> None:
        self.values[brief.id] = brief


@dataclass
class Recaps:
    values: dict[UUID, Recap] = field(default_factory=dict)

    async def get(self, recap_id: UUID) -> Recap | None:
        return self.values.get(recap_id)

    async def get_by_commitment(self, commitment_id: UUID) -> Recap | None:
        return next(
            (item for item in self.values.values() if item.commitment_id == commitment_id), None
        )

    async def add(self, recap: Recap) -> None:
        self.values[recap.id] = recap


@dataclass
class Audits:
    values: dict[UUID, AuditEvent] = field(default_factory=dict)

    async def add(self, event: AuditEvent) -> None:
        self.values[event.event_id] = event

    async def list_by_operation(self, operation_id: UUID) -> tuple[AuditEvent, ...]:
        return tuple(item for item in self.values.values() if item.operation_id == operation_id)


class Uow:
    def __init__(
        self, operation: Operation, commitments: dict[UUID, Commitment] | None = None
    ) -> None:
        self.operations = Operations(operation)
        self.commitments = Commitments(commitments or {})
        self.evidence = Evidence()
        self.briefs = Briefs()
        self.recaps = Recaps()
        self.audit_events = Audits()
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> Uow:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def operation(
    *, status: OperationStatus = OperationStatus.COMMITTED, version: int = 2
) -> Operation:
    mandate = Mandate(
        UUID(int=101),
        OPERATION_ID,
        1,
        Money(Decimal("1500"), "MXN"),
        PickupWindow(date(2026, 9, 1), date(2026, 9, 3)),
        ("sealed",),
        (),
        (MandateAction.NEGOTIATE, MandateAction.COMMIT),
        "synthetic-coordinator",
        NOW,
    )
    ready = OperationStatusEntry(UUID(int=102), OPERATION_ID, 1, OperationStatus.READY, NOW)
    history = [ready]
    if version > 1:
        history.append(OperationStatusEntry(UUID(int=103), OPERATION_ID, version, status, NOW))
    return Operation(
        OPERATION_ID,
        version,
        UUID(int=104),
        1,
        Route("Port A", "Depot B"),
        date(2026, 9, 2),
        mandate,
        status if version > 1 else OperationStatus.READY,
        tuple(history),
        NOW,
    )


def commitment(
    *,
    commitment_id: UUID | None = None,
    disposition: CommitmentDisposition = CommitmentDisposition.ACTIVE,
) -> Commitment:
    return Commitment(
        commitment_id if commitment_id is not None else UUID(int=200),
        OPERATION_ID,
        UUID(int=201),
        UUID(int=202),
        UUID(int=203),
        QuoteTerms(Decimal("1000"), "MXN", date(2026, 9, 1), date(2026, 9, 2), ()),
        1,
        UUID(int=204),
        CommitmentLifecycle.CANDIDATE,
        disposition,
        None,
        None if disposition is CommitmentDisposition.ACTIVE else UUID(int=205),
        NOW,
        None if disposition is CommitmentDisposition.ACTIVE else NOW,
    )
