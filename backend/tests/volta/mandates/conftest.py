from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
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


@dataclass
class InMemoryUnitOfWork:
    intake_drafts: InMemoryDraftRepository = field(default_factory=InMemoryDraftRepository)
    operations: InMemoryOperationRepository = field(default_factory=InMemoryOperationRepository)
    commit_calls: int = 0
    rollback_calls: int = 0

    async def commit(self) -> None:
        self.commit_calls += 1

    async def rollback(self) -> None:
        self.rollback_calls += 1


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
