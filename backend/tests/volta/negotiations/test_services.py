from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from yuno_backend.volta.audit import AuditEvent
from yuno_backend.volta.mandates import (
    InvalidDomainValue,
    Mandate,
    MandateAction,
    MandatePolicy,
    Money,
    Operation,
    OperationStatus,
    OperationStatusEntry,
    PickupWindow,
    Route,
)
from yuno_backend.volta.negotiations import (
    BrowserChannel,
    CallState,
    CarrierProfile,
    CarrierSession,
    CarrierSessionMismatch,
    Commitment,
    CommitmentDisposition,
    CreateCommitmentCommand,
    CreateCommitmentService,
    IdempotencyConflict,
    MutationIdempotency,
    Negotiation,
    Quote,
    QuoteComparisonService,
    QuoteEligibility,
    QuoteExpired,
    QuoteNotBestCandidate,
    QuoteNotEligible,
    QuoteNotFound,
    QuoteTerms,
    RecordQuoteCommand,
    RecordQuoteService,
    StaleMandateVersion,
    StartNegotiationCommand,
    StartNegotiationService,
    SyntheticCarrierCatalog,
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
class Negotiations:
    values: dict[UUID, Negotiation] = field(default_factory=dict)

    async def get(self, negotiation_id: UUID) -> Negotiation | None:
        return self.values.get(negotiation_id)

    async def get_by_operation(self, operation_id: UUID) -> Negotiation | None:
        return next(
            (item for item in self.values.values() if item.operation_id == operation_id), None
        )

    async def get_by_call(self, call_id: UUID) -> Negotiation | None:
        return next(
            (
                item
                for item in self.values.values()
                if any(s.call_id == call_id for s in item.sessions)
            ),
            None,
        )

    async def add(self, negotiation: Negotiation) -> None:
        self.values[negotiation.id] = negotiation


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
class Idempotency:
    values: dict[tuple[str, str], MutationIdempotency] = field(default_factory=dict)

    async def get(self, operation_name: str, key: str) -> MutationIdempotency | None:
        return self.values.get((operation_name, key))

    async def add(self, record: MutationIdempotency) -> None:
        self.values[(record.operation_name, record.key)] = record


@dataclass
class Audits:
    values: dict[UUID, AuditEvent] = field(default_factory=dict)

    async def add(self, event: AuditEvent) -> None:
        self.values[event.event_id] = event

    async def list_by_operation(self, operation_id: UUID) -> tuple[AuditEvent, ...]:
        return tuple(item for item in self.values.values() if item.operation_id == operation_id)


class Uow:
    def __init__(self, operation: Operation) -> None:
        self.operations = Operations(operation)
        self.negotiations = Negotiations()
        self.quotes = Quotes()
        self.commitments = Commitments()
        self.idempotency = Idempotency()
        self.audit_events = Audits()
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


def operation() -> Operation:
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
    status = OperationStatusEntry(UUID(int=102), OPERATION_ID, 1, OperationStatus.READY, NOW)
    return Operation(
        OPERATION_ID,
        1,
        UUID(int=103),
        1,
        Route("Port A", "Depot B"),
        date(2026, 9, 2),
        "Synthetic sealed container",
        mandate,
        OperationStatus.READY,
        (status,),
        NOW,
    )


def test_catalog_uses_only_exact_route_availability_and_fixed_ranking() -> None:
    carriers = (
        CarrierProfile(UUID(int=3), "Synthetic C", (("Port A", "Depot B"),), True, 3),
        CarrierProfile(UUID(int=1), "Synthetic A", (("port a", "depot b"),), True, 1),
        CarrierProfile(UUID(int=4), "Unavailable", (("Port A", "Depot B"),), False, 4),
        CarrierProfile(UUID(int=2), "Wrong route", (("Port A", "Other"),), True, 2),
    )
    selected = SyntheticCarrierCatalog(reversed(carriers)).select(Route("PORT A", "DEPOT B"))
    assert tuple(item.id for item in selected) == (UUID(int=1), UUID(int=3))


@pytest.mark.parametrize(
    ("eligible_count", "selected_count"), [(0, 0), (1, 1), (2, 2), (3, 3), (5, 3)]
)
def test_catalog_selects_zero_to_three_for_all_input_permutations(
    eligible_count: int, selected_count: int
) -> None:
    carriers = tuple(
        CarrierProfile(
            UUID(int=index + 1),
            f"Synthetic {index + 1}",
            (("Port A", "Depot B"),),
            True,
            index + 1,
        )
        for index in range(eligible_count)
    )
    expected = tuple(item.id for item in carriers[:3])
    for permutation in (carriers, tuple(reversed(carriers))):
        selected = SyntheticCarrierCatalog(permutation).select(Route("Port A", "Depot B"))
        assert len(selected) == selected_count
        assert tuple(item.id for item in selected) == expected


def test_catalog_rejects_duplicate_ids_and_priorities() -> None:
    first = CarrierProfile(UUID(int=1), "Synthetic One", (("A", "B"),), True, 1)
    with pytest.raises(InvalidDomainValue):
        SyntheticCarrierCatalog((first, replace(first, display_label="Duplicate")))
    with pytest.raises(InvalidDomainValue):
        SyntheticCarrierCatalog(
            (first, CarrierProfile(UUID(int=2), "Synthetic Two", (("A", "B"),), True, 1))
        )


async def test_zero_carrier_start_escalates_without_sessions_and_replays() -> None:
    uow = Uow(operation())
    command = StartNegotiationCommand(
        OPERATION_ID, 1, 1, BrowserChannel.BROWSER_TEXT, " AbCd  X", UUID(int=600)
    )
    service = StartNegotiationService(uow, SyntheticCarrierCatalog(()), Clock(), Ids())
    result = await service.start(command)
    replay = await service.start(replace(command, correlation_id=UUID(int=601)))
    assert replay == result
    assert result.sessions == ()
    assert result.pre_contact_escalation is not None
    assert uow.operations.value.status is OperationStatus.ESCALATED
    assert uow.operations.value.version == 2
    assert len(uow.audit_events.values) == 1
    assert uow.commits == 1
    assert ("start_negotiation", " AbCd  X") in uow.idempotency.values


async def test_full_journey_rejects_out_of_mandate_selects_winner_and_replays() -> None:
    uow = Uow(operation())
    ids = Ids()
    catalog = SyntheticCarrierCatalog(
        (CarrierProfile(UUID(int=200), "Synthetic One", (("Port A", "Depot B"),), True, 1),)
    )
    start_command = StartNegotiationCommand(
        OPERATION_ID, 1, 1, BrowserChannel.BROWSER_TEXT, "start-key-001", UUID(int=300)
    )
    negotiation = await StartNegotiationService(uow, catalog, Clock(), ids).start(start_command)
    start_replay = await StartNegotiationService(uow, catalog, Clock(), ids).start(
        replace(start_command, correlation_id=UUID(int=399))
    )
    assert start_replay == negotiation
    assert uow.operations.value.status is OperationStatus.NEGOTIATING
    assert len(negotiation.sessions) == 1
    call_id = negotiation.sessions[0].call_id

    rejected = await RecordQuoteService(uow, MandatePolicy(), Clock(), ids).record(
        RecordQuoteCommand(
            call_id,
            2,
            UUID(int=200),
            1,
            QuoteTerms(Decimal("1501"), "MXN", date(2026, 9, 1), date(2026, 9, 3), ("sealed",)),
            NOW + timedelta(hours=1),
            "quote-key-bad",
            UUID(int=301),
        )
    )
    assert rejected.eligibility is QuoteEligibility.REJECTED
    assert rejected.rejection_reasons == ("amount_exceeds_maximum",)

    quote_command = RecordQuoteCommand(
        call_id,
        3,
        UUID(int=200),
        1,
        QuoteTerms(Decimal("1400"), "MXN", date(2026, 9, 1), date(2026, 9, 2), ("sealed",)),
        NOW + timedelta(hours=1),
        "quote-key-good",
        UUID(int=302),
    )
    quote = await RecordQuoteService(uow, MandatePolicy(), Clock(), ids).record(quote_command)
    quote_replay = await RecordQuoteService(uow, MandatePolicy(), Clock(), ids).record(
        replace(quote_command, correlation_id=UUID(int=398))
    )
    assert quote_replay == quote
    commitment_command = CreateCommitmentCommand(
        call_id, 4, quote.id, 1, UUID(int=400), "commit-key-01", UUID(int=303)
    )
    service = CreateCommitmentService(uow, MandatePolicy(), Clock(), ids)
    commitment = await service.create(commitment_command)
    replay = await service.create(replace(commitment_command, correlation_id=UUID(int=397)))

    assert replay == commitment
    assert commitment.evidence_id == UUID(int=400)
    assert uow.operations.value.version == 5
    assert len(uow.commitments.values) == 1
    assert uow.commits == 4

    with pytest.raises(IdempotencyConflict):
        await service.create(replace(commitment_command, evidence_id=UUID(int=401)))

    replacement_quote = await RecordQuoteService(uow, MandatePolicy(), Clock(), ids).record(
        RecordQuoteCommand(
            call_id,
            5,
            UUID(int=200),
            1,
            QuoteTerms(
                Decimal("1300"),
                "MXN",
                date(2026, 9, 1),
                date(2026, 9, 2),
                ("sealed",),
            ),
            NOW + timedelta(hours=1),
            "quote-key-next",
            UUID(int=304),
        )
    )
    replacement = await service.create(
        CreateCommitmentCommand(
            call_id,
            6,
            replacement_quote.id,
            1,
            UUID(int=402),
            "commit-key-02",
            UUID(int=305),
        )
    )
    original = uow.commitments.values[commitment.id]
    assert original.disposition is CommitmentDisposition.SUPERSEDED
    assert original.replaced_by_commitment_id == replacement.id
    assert replacement.replaces_commitment_id == original.id
    assert len(uow.commitments.values) == 2
    assert uow.operations.value.version == 7


async def test_stale_mandate_quote_attempt_writes_nothing() -> None:
    uow = Uow(operation())
    ids = Ids()
    negotiation = await StartNegotiationService(
        uow,
        SyntheticCarrierCatalog(
            (CarrierProfile(UUID(int=200), "Synthetic", (("Port A", "Depot B"),), True, 1),)
        ),
        Clock(),
        ids,
    ).start(
        StartNegotiationCommand(
            OPERATION_ID, 1, 1, BrowserChannel.BROWSER_TEXT, "start-key-002", UUID(int=500)
        )
    )

    with pytest.raises(StaleMandateVersion):
        await RecordQuoteService(uow, MandatePolicy(), Clock(), ids).record(
            RecordQuoteCommand(
                negotiation.sessions[0].call_id,
                2,
                UUID(int=200),
                2,
                QuoteTerms(Decimal("1000"), "MXN", date(2026, 9, 1), date(2026, 9, 2)),
                NOW + timedelta(hours=1),
                "quote-key-stale",
                UUID(int=501),
            )
        )

    assert uow.quotes.values == {}
    assert uow.operations.value.version == 2


async def test_quote_checks_both_pickup_endpoints_and_preserves_reason_order() -> None:
    uow = Uow(operation())
    ids = Ids(1500)
    negotiation = await StartNegotiationService(
        uow,
        SyntheticCarrierCatalog(
            (CarrierProfile(UUID(int=200), "Synthetic", (("Port A", "Depot B"),), True, 1),)
        ),
        Clock(),
        ids,
    ).start(
        StartNegotiationCommand(
            OPERATION_ID, 1, 1, BrowserChannel.BROWSER_TEXT, "reason-start-key", UUID(int=650)
        )
    )
    quote = await RecordQuoteService(uow, MandatePolicy(), Clock(), ids).record(
        RecordQuoteCommand(
            negotiation.sessions[0].call_id,
            2,
            UUID(int=200),
            1,
            QuoteTerms(
                Decimal("1501"),
                "USD",
                date(2026, 8, 31),
                date(2026, 9, 4),
                ("unapproved",),
            ),
            NOW + timedelta(hours=1),
            "reason-quote-key",
            UUID(int=651),
        )
    )
    assert quote.rejection_reasons == (
        "amount_exceeds_maximum",
        "currency_mismatch",
        "pickup_outside_window",
        "conditions_not_allowed",
    )


def _quote(
    identifier: int,
    *,
    amount: str = "1000",
    pickup: date = date(2026, 9, 1),
    priority: int = 1,
    created_at: datetime = NOW,
    valid_until: datetime = NOW + timedelta(hours=1),
    mandate_version: int = 1,
    eligibility: QuoteEligibility = QuoteEligibility.ELIGIBLE,
) -> Quote:
    return Quote(
        UUID(int=identifier),
        OPERATION_ID,
        UUID(int=identifier + 100),
        UUID(int=identifier + 200),
        priority,
        QuoteTerms(Decimal(amount), "MXN", pickup, pickup, ()),
        valid_until,
        mandate_version,
        eligibility,
        () if eligibility is QuoteEligibility.ELIGIBLE else ("amount_exceeds_maximum",),
        created_at,
    )


def test_comparison_filters_current_mandate_rejected_and_expired_then_uses_all_ties() -> None:
    old_cheaper = _quote(1, amount="1", mandate_version=1)
    rejected = _quote(2, amount="2", mandate_version=2, eligibility=QuoteEligibility.REJECTED)
    expired = _quote(3, amount="3", mandate_version=2, valid_until=NOW)
    later_pickup = _quote(4, amount="1000", pickup=date(2026, 9, 2), mandate_version=2)
    lower_priority = _quote(5, amount="1000", priority=2, mandate_version=2)
    later_created = _quote(
        6, amount="1000", mandate_version=2, created_at=NOW + timedelta(microseconds=1)
    )
    best = _quote(7, amount="1000", mandate_version=2)
    uuid_tie = _quote(8, amount="1000", mandate_version=2)

    result = QuoteComparisonService(Clock()).compare(
        OPERATION_ID,
        2,
        (
            old_cheaper,
            rejected,
            expired,
            later_pickup,
            lower_priority,
            later_created,
            uuid_tie,
            best,
        ),
    )

    assert result.selected_quote_id == best.id
    assert tuple(item.id for item in result.ranked_quotes) == (
        best.id,
        uuid_tie.id,
        later_created.id,
        lower_priority.id,
        later_pickup.id,
    )


async def test_commitment_rejects_missing_rejected_expired_and_non_best_quotes() -> None:
    uow = Uow(operation())
    ids = Ids(2000)
    negotiation = await StartNegotiationService(
        uow,
        SyntheticCarrierCatalog(
            (CarrierProfile(UUID(int=200), "Synthetic", (("Port A", "Depot B"),), True, 1),)
        ),
        Clock(),
        ids,
    ).start(
        StartNegotiationCommand(
            OPERATION_ID, 1, 1, BrowserChannel.BROWSER_TEXT, "errors-start-key", UUID(int=700)
        )
    )
    call_id = negotiation.sessions[0].call_id
    service = CreateCommitmentService(uow, MandatePolicy(), Clock(), ids)

    with pytest.raises(QuoteNotFound):
        await service.create(
            CreateCommitmentCommand(
                call_id, 2, UUID(int=999), 1, UUID(int=800), "missing-quote-key", UUID(int=701)
            )
        )

    rejected = _quote(20, amount="1600", eligibility=QuoteEligibility.REJECTED)
    expired = _quote(21, valid_until=NOW)
    best = _quote(22, amount="900")
    non_best = _quote(23, amount="1000")
    for quote in (rejected, expired, best, non_best):
        uow.quotes.values[quote.id] = replace(
            quote,
            call_id=call_id,
            carrier_id=UUID(int=200),
        )

    second_call = UUID(int=850)
    second_session = CarrierSession(
        second_call,
        negotiation.id,
        OPERATION_ID,
        UUID(int=201),
        "Synthetic Two",
        operation().route,
        True,
        2,
        2,
        BrowserChannel.BROWSER_TEXT,
        CallState.SELECTED,
        NOW,
    )
    uow.negotiations.values[negotiation.id] = replace(
        negotiation, sessions=(*negotiation.sessions, second_session)
    )

    base = CreateCommitmentCommand(
        call_id, 2, rejected.id, 1, UUID(int=801), "rejected-key-01", UUID(int=702)
    )
    with pytest.raises(QuoteNotEligible):
        await service.create(base)
    with pytest.raises(CarrierSessionMismatch):
        await service.create(
            replace(base, call_id=second_call, quote_id=best.id, idempotency_key="wrong-call-key01")
        )
    with pytest.raises(QuoteExpired):
        await service.create(replace(base, quote_id=expired.id, idempotency_key="expired-key-01"))
    with pytest.raises(QuoteNotBestCandidate):
        await service.create(replace(base, quote_id=non_best.id, idempotency_key="non-best-key-01"))
    assert uow.operations.value.version == 2
    assert uow.commitments.values == {}
