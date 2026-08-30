from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from yuno_backend.volta.audit.models import AuditEvent
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
    Quote,
    QuoteEligibility,
    QuoteTerms,
)
from yuno_backend.volta.recovery.models import Notification, PostContactEscalation, RecoveryAttempt

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
OPERATION_ID = UUID(int=100)
CARRIER_ID = UUID(int=203)
CALL_ID = UUID(int=201)
ORIGINAL_QUOTE_ID = UUID(int=202)


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

    async def replace_mandate(self, operation: Operation) -> None:
        self.value = operation


@dataclass
class Negotiations:
    operation_id: UUID

    async def get_by_call(self, call_id: UUID) -> object | None:
        if call_id != CALL_ID:
            return None
        return SimpleNamespace(operation_id=self.operation_id)


@dataclass
class Quotes:
    values: dict[UUID, Quote] = field(default_factory=dict)

    async def get(self, quote_id: UUID) -> Quote | None:
        return self.values.get(quote_id)

    async def list_by_operation(self, operation_id: UUID) -> tuple[Quote, ...]:
        return tuple(item for item in self.values.values() if item.operation_id == operation_id)

    async def add(self, quote: Quote) -> None:
        self.values[quote.id] = quote


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
class PostContactEscalations:
    values: dict[UUID, PostContactEscalation] = field(default_factory=dict)

    async def get(self, escalation_id: UUID) -> PostContactEscalation | None:
        return self.values.get(escalation_id)

    async def get_unresolved_by_operation(
        self, operation_id: UUID
    ) -> PostContactEscalation | None:
        return next(
            (
                item
                for item in self.values.values()
                if item.operation_id == operation_id and not item.resolved
            ),
            None,
        )

    async def add(self, escalation: PostContactEscalation) -> None:
        self.values[escalation.id] = escalation

    async def update(self, escalation: PostContactEscalation) -> None:
        self.values[escalation.id] = escalation


@dataclass
class RecoveryAttempts:
    values: dict[UUID, RecoveryAttempt] = field(default_factory=dict)

    async def get(self, attempt_id: UUID) -> RecoveryAttempt | None:
        return self.values.get(attempt_id)

    async def list_by_operation(self, operation_id: UUID) -> tuple[RecoveryAttempt, ...]:
        return tuple(item for item in self.values.values() if item.operation_id == operation_id)

    async def add(self, attempt: RecoveryAttempt) -> None:
        self.values[attempt.id] = attempt


@dataclass
class Notifications:
    values: dict[UUID, Notification] = field(default_factory=dict)

    async def get(
        self, notification_id: UUID, *, for_update: bool = False
    ) -> Notification | None:
        del for_update
        return self.values.get(notification_id)

    async def list_by_operation(self, operation_id: UUID) -> tuple[Notification, ...]:
        return tuple(item for item in self.values.values() if item.operation_id == operation_id)

    async def add(self, notification: Notification) -> None:
        self.values[notification.id] = notification

    async def update(self, notification: Notification) -> None:
        self.values[notification.id] = notification


@dataclass
class Audits:
    values: dict[UUID, AuditEvent] = field(default_factory=dict)

    async def add(self, event: AuditEvent) -> None:
        self.values[event.event_id] = event

    async def list_by_operation(self, operation_id: UUID) -> tuple[AuditEvent, ...]:
        return tuple(item for item in self.values.values() if item.operation_id == operation_id)


class Uow:
    def __init__(
        self,
        operation: Operation,
        commitments: dict[UUID, Commitment] | None = None,
        quotes: dict[UUID, Quote] | None = None,
        escalations: dict[UUID, PostContactEscalation] | None = None,
    ) -> None:
        self.operations = Operations(operation)
        self.negotiations = Negotiations(operation.id)
        self.commitments = Commitments(commitments or {})
        self.quotes = Quotes(quotes or {})
        self.post_contact_escalations = PostContactEscalations(escalations or {})
        self.recovery_attempts = RecoveryAttempts()
        self.notifications = Notifications()
        self.audit_events = Audits()
        self.commits = 0
        self.rollbacks = 0
        self._snapshot: tuple[object, ...] | None = None

    async def __aenter__(self) -> Uow:
        self._snapshot = (
            self.operations.value,
            dict(self.commitments.values),
            dict(self.quotes.values),
            dict(self.post_contact_escalations.values),
            dict(self.recovery_attempts.values),
            dict(self.notifications.values),
            dict(self.audit_events.values),
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1
        self._snapshot = None

    async def rollback(self) -> None:
        self.rollbacks += 1
        if self._snapshot is not None:
            (
                self.operations.value,
                commitments,
                quotes,
                escalations,
                attempts,
                notifications,
                audits,
            ) = self._snapshot
            self.commitments.values = commitments  # type: ignore[assignment]
            self.quotes.values = quotes  # type: ignore[assignment]
            self.post_contact_escalations.values = escalations  # type: ignore[assignment]
            self.recovery_attempts.values = attempts  # type: ignore[assignment]
            self.notifications.values = notifications  # type: ignore[assignment]
            self.audit_events.values = audits  # type: ignore[assignment]
            self._snapshot = None


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
        "Synthetic recovery cargo",
        mandate,
        status if version > 1 else OperationStatus.READY,
        tuple(history),
        NOW,
    )


def original_quote() -> Quote:
    return Quote(
        ORIGINAL_QUOTE_ID,
        OPERATION_ID,
        CALL_ID,
        CARRIER_ID,
        1,
        QuoteTerms(Decimal("1000"), "MXN", date(2026, 9, 1), date(2026, 9, 2), ("sealed",)),
        NOW,
        1,
        QuoteEligibility.ELIGIBLE,
        (),
        NOW,
    )


def active_commitment(*, commitment_id: UUID | None = None) -> Commitment:
    return Commitment(
        commitment_id if commitment_id is not None else UUID(int=200),
        OPERATION_ID,
        CALL_ID,
        ORIGINAL_QUOTE_ID,
        CARRIER_ID,
        QuoteTerms(Decimal("1000"), "MXN", date(2026, 9, 1), date(2026, 9, 2), ("sealed",)),
        1,
        UUID(int=204),
        CommitmentLifecycle.CANDIDATE,
        CommitmentDisposition.ACTIVE,
        None,
        None,
        NOW,
        None,
    )


def safe_terms(**overrides: object) -> QuoteTerms:
    values: dict[str, object] = {
        "amount": Decimal("1000"),
        "currency": "MXN",
        "pickup_window_start": date(2026, 9, 1),
        "pickup_window_end": date(2026, 9, 2),
        "conditions": ("sealed",),
    }
    values.update(overrides)
    return QuoteTerms(**values)  # type: ignore[arg-type]
