from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from yuno_backend.volta.audit import AuditEvent
from yuno_backend.volta.mandates import (
    IntakeDraft,
    MandateProposal,
    Money,
    Operation,
    OperationProposal,
    PickupWindow,
    Route,
)

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
DRAFT_ID = UUID("00000000-0000-0000-0000-000000000501")
OPERATION_ID = UUID("00000000-0000-0000-0000-000000000502")
MANDATE_ID = UUID("00000000-0000-0000-0000-000000000503")
STATUS_ID = UUID("00000000-0000-0000-0000-000000000504")
AUDIT_ID = UUID("00000000-0000-0000-0000-000000000505")
CORRELATION_ID = UUID("00000000-0000-0000-0000-000000000506")


@dataclass
class InMemoryDraftRepository:
    values: dict[UUID, IntakeDraft] = field(default_factory=dict)
    add_calls: int = 0

    async def get(self, draft_id: UUID) -> IntakeDraft | None:
        return self.values.get(draft_id)

    async def add(self, draft: IntakeDraft) -> None:
        self.add_calls += 1
        self.values[draft.id] = draft


@dataclass
class InMemoryOperationRepository:
    values: dict[UUID, Operation] = field(default_factory=dict)
    add_calls: int = 0

    async def get_by_draft_id(self, draft_id: UUID) -> Operation | None:
        return next(
            (value for value in self.values.values() if value.source_draft_id == draft_id),
            None,
        )

    async def add(self, operation: Operation) -> None:
        self.add_calls += 1
        self.values[operation.id] = operation

    async def replace_mandate(self, operation: Operation) -> None:
        self.values[operation.id] = operation


@dataclass
class InMemoryAuditEventRepository:
    values: dict[UUID, AuditEvent] = field(default_factory=dict)
    add_calls: int = 0

    async def add(self, event: AuditEvent) -> None:
        self.add_calls += 1
        self.values[event.event_id] = event

    async def list_by_operation(self, operation_id: UUID) -> tuple[AuditEvent, ...]:
        return tuple(
            sorted(
                (event for event in self.values.values() if event.operation_id == operation_id),
                key=lambda event: (event.occurred_at, event.event_id),
            )
        )


@dataclass
class InMemoryUnitOfWork:
    intake_drafts: InMemoryDraftRepository = field(default_factory=InMemoryDraftRepository)
    operations: InMemoryOperationRepository = field(default_factory=InMemoryOperationRepository)
    audit_events: InMemoryAuditEventRepository = field(
        default_factory=InMemoryAuditEventRepository
    )
    commit_calls: int = 0
    rollback_calls: int = 0
    _snapshots: tuple[
        dict[UUID, IntakeDraft], dict[UUID, Operation], dict[UUID, AuditEvent]
    ] | None = None

    async def __aenter__(self) -> "InMemoryUnitOfWork":
        if self._snapshots is not None:
            raise RuntimeError("unit of work is already active")
        self._snapshots = (
            dict(getattr(self.intake_drafts, "values", {})),
            dict(getattr(self.operations, "values", {})),
            dict(getattr(self.audit_events, "values", {})),
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._snapshots is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.commit_calls += 1
        self._snapshots = None

    async def rollback(self) -> None:
        if self._snapshots is None:
            return
        self.rollback_calls += 1
        drafts, operations, events = self._snapshots
        self.intake_drafts.values = drafts
        self.operations.values = operations
        self.audit_events.values = events
        self._snapshots = None


@dataclass(frozen=True)
class FixedClock:
    value: datetime = NOW

    def now(self) -> datetime:
        return self.value


@dataclass
class FixedIds:
    values: list[UUID]

    def new_id(self) -> UUID:
        return self.values.pop(0)


@pytest.fixture
def proposal() -> OperationProposal:
    return OperationProposal(
        route=Route(origin="Synthetic Port", destination="Synthetic Inland Depot"),
        pickup_date=date(2026, 9, 2),
        cargo_label="Synthetic sealed container",
        mandate=MandateProposal(
            maximum_amount=Money(amount=Decimal("1500.00"), currency="MXN"),
            pickup_window=PickupWindow(
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 3),
            ),
            allowed_conditions=("sealed container", "daylight pickup"),
            escalation_conditions=("amount exceeds mandate",),
        ),
    )
