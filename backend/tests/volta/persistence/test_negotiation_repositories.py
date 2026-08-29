import asyncio
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from yuno_backend.volta.mandates import MandatePolicy
from yuno_backend.volta.negotiations import (
    BrowserChannel,
    CarrierProfile,
    Commitment,
    CreateCommitmentCommand,
    CreateCommitmentService,
    IdempotencyConflict,
    MutationIdempotency,
    QuoteComparisonService,
    QuoteTerms,
    RecordQuoteCommand,
    RecordQuoteService,
    StaleOperationVersion,
    StartNegotiationCommand,
    StartNegotiationService,
    SyntheticCarrierCatalog,
)
from yuno_backend.volta.persistence import PersistenceConflict, SqlAlchemyOperationUnitOfWork
from yuno_backend.volta.persistence import repositories as repository_module
from yuno_backend.volta.persistence.tables import (
    _audit_events,
    _carrier_sessions,
    _commitments,
    _mutation_idempotency,
    _negotiations,
    _operation_status_history,
    _operations,
    _pre_contact_escalations,
    _quotes,
)

from .test_repositories import NOW, FixedClock, FixedIds, _approve, _create_draft, _factory


async def _seed_started(
    factory: async_sessionmaker[AsyncSession], base: int
) -> tuple[UUID, UUID, UUID]:
    draft_id = UUID(int=base)
    operation_id = UUID(int=base + 1)
    carrier_id = UUID(int=base + 9)
    await _create_draft(factory, draft_id)
    await _approve(
        factory,
        draft_id,
        [operation_id, UUID(int=base + 2), UUID(int=base + 3), UUID(int=base + 4)],
        UUID(int=base + 5),
    )
    negotiation = await StartNegotiationService(
        SqlAlchemyOperationUnitOfWork(factory),
        SyntheticCarrierCatalog(
            (
                CarrierProfile(
                    carrier_id,
                    "Synthetic Carrier",
                    (("Synthetic Port", "Synthetic Inland Depot"),),
                    True,
                    1,
                ),
            )
        ),
        FixedClock(),
        FixedIds([UUID(int=value) for value in range(base + 10, base + 14)]),
    ).start(
        StartNegotiationCommand(
            operation_id,
            1,
            1,
            BrowserChannel.BROWSER_TEXT,
            f"start-{base:08d}",
            UUID(int=base + 6),
        )
    )
    return operation_id, carrier_id, negotiation.sessions[0].call_id


def _quote_command(base: int, call_id: UUID, carrier_id: UUID) -> RecordQuoteCommand:
    return RecordQuoteCommand(
        call_id,
        2,
        carrier_id,
        1,
        QuoteTerms(
            Decimal("1400.125"),
            "MXN",
            date(2026, 9, 1),
            date(2026, 9, 2),
            ("sealed container",),
        ),
        NOW + timedelta(hours=1),
        f"quote-{base:08d}",
        UUID(int=base + 7),
    )


async def _row_counts(
    factory: async_sessionmaker[AsyncSession], operation_id: UUID
) -> tuple[int, int, int, int, int, int]:
    async with factory() as session:
        operation_version = (
            await session.execute(
                select(_operations.c.version).where(_operations.c.id == operation_id)
            )
        ).scalar_one()
        counts = []
        for table in (
            _operation_status_history,
            _audit_events,
            _quotes,
            _commitments,
            _mutation_idempotency,
        ):
            counts.append(
                (
                    await session.execute(
                        select(func.count())
                        .select_from(table)
                        .where(table.c.operation_id == operation_id)
                    )
                ).scalar_one()
            )
    return operation_version, *counts


async def _seed_winner(
    factory: async_sessionmaker[AsyncSession], base: int
) -> tuple[UUID, Commitment]:
    operation_id, carrier_id, call_id = await _seed_started(factory, base)
    quote = await RecordQuoteService(
        SqlAlchemyOperationUnitOfWork(factory),
        MandatePolicy(),
        FixedClock(),
        FixedIds([UUID(int=value) for value in range(base + 20, base + 23)]),
    ).record(_quote_command(base, call_id, carrier_id))
    commitment = await CreateCommitmentService(
        SqlAlchemyOperationUnitOfWork(factory),
        MandatePolicy(),
        FixedClock(),
        FixedIds([UUID(int=value) for value in range(base + 30, base + 33)]),
    ).create(
        CreateCommitmentCommand(
            call_id,
            3,
            quote.id,
            1,
            UUID(int=base + 40),
            f"commit-{base:08d}",
            UUID(int=base + 41),
        )
    )
    return operation_id, commitment


async def test_negotiation_journey_round_trips_and_replays_after_restart(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id = UUID(int=8001)
    operation_id = UUID(int=8002)
    try:
        await _create_draft(factory, draft_id)
        await _approve(
            factory,
            draft_id,
            [operation_id, UUID(int=8003), UUID(int=8004), UUID(int=8005)],
            UUID(int=8006),
        )
        catalog = SyntheticCarrierCatalog(
            (
                CarrierProfile(
                    UUID(int=8010),
                    "Synthetic Carrier",
                    (("Synthetic Port", "Synthetic Inland Depot"),),
                    True,
                    1,
                ),
            )
        )
        start_command = StartNegotiationCommand(
            operation_id,
            1,
            1,
            BrowserChannel.BROWSER_TEXT,
            "persist-start-001",
            UUID(int=8011),
        )
        negotiation = await StartNegotiationService(
            SqlAlchemyOperationUnitOfWork(factory),
            catalog,
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(8020, 8024)]),
        ).start(start_command)
        call_id = negotiation.sessions[0].call_id

        quote_command = RecordQuoteCommand(
            call_id,
            2,
            UUID(int=8010),
            1,
            QuoteTerms(
                Decimal("1400.125"),
                "MXN",
                date(2026, 9, 1),
                date(2026, 9, 2),
                ("sealed container",),
            ),
            NOW + timedelta(hours=1),
            "persist-quote-001",
            UUID(int=8012),
        )
        quote = await RecordQuoteService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(8030, 8033)]),
        ).record(quote_command)
        commitment_command = CreateCommitmentCommand(
            call_id,
            3,
            quote.id,
            1,
            UUID(int=8040),
            "persist-commit-01",
            UUID(int=8013),
        )
        commitment = await CreateCommitmentService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(8050, 8053)]),
        ).create(commitment_command)

        replayed_start = await StartNegotiationService(
            SqlAlchemyOperationUnitOfWork(factory), catalog, FixedClock(), FixedIds([])
        ).start(replace(start_command, correlation_id=UUID(int=8990)))
        replayed_quote = await RecordQuoteService(
            SqlAlchemyOperationUnitOfWork(factory), MandatePolicy(), FixedClock(), FixedIds([])
        ).record(replace(quote_command, correlation_id=UUID(int=8991)))
        replayed_commitment = await CreateCommitmentService(
            SqlAlchemyOperationUnitOfWork(factory), MandatePolicy(), FixedClock(), FixedIds([])
        ).create(replace(commitment_command, correlation_id=UUID(int=8992)))

        assert replayed_start == negotiation
        assert replayed_quote == quote
        assert replayed_commitment == commitment
        assert replayed_commitment.evidence_id == UUID(int=8040)
        assert replayed_commitment.agreed_terms.amount == Decimal("1400.125")
        with pytest.raises(IdempotencyConflict):
            await RecordQuoteService(
                SqlAlchemyOperationUnitOfWork(factory),
                MandatePolicy(),
                FixedClock(),
                FixedIds([]),
            ).record(
                replace(
                    quote_command,
                    terms=replace(quote_command.terms, amount=Decimal("1399")),
                )
            )

        replacement_quote = await RecordQuoteService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(8060, 8063)]),
        ).record(
            replace(
                quote_command,
                expected_operation_version=4,
                terms=replace(quote_command.terms, amount=Decimal("1300")),
                idempotency_key="persist-quote-002",
                correlation_id=UUID(int=8014),
            )
        )
        replacement = await CreateCommitmentService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(8070, 8074)]),
        ).create(
            replace(
                commitment_command,
                expected_operation_version=5,
                quote_id=replacement_quote.id,
                evidence_id=UUID(int=8041),
                idempotency_key="persist-commit-02",
                correlation_id=UUID(int=8015),
            )
        )
        async with factory() as session:
            history = await repository_module.SqlAlchemyCommitmentRepository(
                session
            ).list_by_operation(operation_id)
            reloaded_quotes = await repository_module.SqlAlchemyQuoteRepository(
                session
            ).list_by_operation(operation_id)
        assert len(history) == 2
        assert history[0].replaced_by_commitment_id == replacement.id
        assert history[1].replaces_commitment_id == commitment.id
        assert history[1].evidence_id == UUID(int=8041)
        comparison = QuoteComparisonService(FixedClock()).compare(operation_id, 1, reloaded_quotes)
        assert comparison.selected_quote_id == replacement_quote.id
        with pytest.raises(PersistenceConflict):
            await CreateCommitmentService(
                SqlAlchemyOperationUnitOfWork(factory),
                MandatePolicy(),
                FixedClock(),
                FixedIds([UUID(int=value) for value in range(8080, 8084)]),
            ).create(
                replace(
                    commitment_command,
                    expected_operation_version=6,
                    quote_id=replacement_quote.id,
                    evidence_id=UUID(int=8042),
                    idempotency_key="persist-commit-03",
                    correlation_id=UUID(int=8016),
                )
            )
        async with factory() as session:
            durable_history = await repository_module.SqlAlchemyCommitmentRepository(
                session
            ).list_by_operation(operation_id)
            durable_operation = await repository_module.SqlAlchemyOperationRepository(session).get(
                operation_id
            )
        assert durable_history == history
        assert durable_operation is not None and durable_operation.version == 6
    finally:
        await engine.dispose()


async def test_concurrent_commitment_attempts_leave_exactly_one_active_winner(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    base = 9000
    try:
        operation_id, carrier_id, call_id = await _seed_started(factory, base)
        quote = await RecordQuoteService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 20, base + 23)]),
        ).record(_quote_command(base, call_id, carrier_id))

        async def create(offset: int) -> Commitment | Exception:
            try:
                return await CreateCommitmentService(
                    SqlAlchemyOperationUnitOfWork(factory),
                    MandatePolicy(),
                    FixedClock(),
                    FixedIds(
                        [UUID(int=value) for value in range(base + offset, base + offset + 3)]
                    ),
                ).create(
                    CreateCommitmentCommand(
                        call_id,
                        3,
                        quote.id,
                        1,
                        UUID(int=base + offset + 10),
                        f"commit-{base + offset:08d}",
                        UUID(int=base + offset + 11),
                    )
                )
            except Exception as error:
                return error

        results = await asyncio.gather(create(30), create(50))
        assert sum(isinstance(result, Commitment) for result in results) == 1
        loser = next(result for result in results if isinstance(result, Exception))
        assert isinstance(loser, StaleOperationVersion)

        async with factory() as session:
            active_count = (
                await session.execute(
                    select(func.count())
                    .select_from(_commitments)
                    .where(
                        _commitments.c.operation_id == operation_id,
                        _commitments.c.disposition == "ACTIVE",
                    )
                )
            ).scalar_one()
        assert active_count == 1
        assert await _row_counts(factory, operation_id) == (4, 4, 4, 1, 1, 3)
    finally:
        await engine.dispose()


async def test_zero_carrier_and_rejected_quote_round_trip(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    zero_base = 13000
    rejected_base = 14000
    try:
        zero_draft = UUID(int=zero_base)
        zero_operation = UUID(int=zero_base + 1)
        await _create_draft(factory, zero_draft)
        await _approve(
            factory,
            zero_draft,
            [
                zero_operation,
                UUID(int=zero_base + 2),
                UUID(int=zero_base + 3),
                UUID(int=zero_base + 4),
            ],
            UUID(int=zero_base + 5),
        )
        command = StartNegotiationCommand(
            zero_operation,
            1,
            1,
            BrowserChannel.BROWSER_TEXT,
            "persist-zero-001",
            UUID(int=zero_base + 6),
        )
        result = await StartNegotiationService(
            SqlAlchemyOperationUnitOfWork(factory),
            SyntheticCarrierCatalog(()),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(zero_base + 10, zero_base + 14)]),
        ).start(command)
        replay = await StartNegotiationService(
            SqlAlchemyOperationUnitOfWork(factory),
            SyntheticCarrierCatalog(()),
            FixedClock(),
            FixedIds([]),
        ).start(replace(command, correlation_id=UUID(int=zero_base + 7)))
        assert replay == result
        async with factory() as session:
            counts = []
            for table in (_negotiations, _carrier_sessions, _pre_contact_escalations):
                counts.append(
                    (
                        await session.execute(
                            select(func.count())
                            .select_from(table)
                            .where(table.c.operation_id == zero_operation)
                        )
                    ).scalar_one()
                )
        assert tuple(counts) == (1, 0, 1)

        rejected_operation, carrier_id, call_id = await _seed_started(factory, rejected_base)
        rejected = await RecordQuoteService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(rejected_base + 20, rejected_base + 23)]),
        ).record(
            replace(
                _quote_command(rejected_base, call_id, carrier_id),
                terms=QuoteTerms(
                    Decimal("1600"),
                    "MXN",
                    date(2026, 9, 1),
                    date(2026, 9, 2),
                    ("sealed container",),
                ),
            )
        )
        async with factory() as session:
            loaded = await repository_module.SqlAlchemyQuoteRepository(session).get(rejected.id)
        assert loaded == rejected
        assert loaded is not None and loaded.rejection_reasons == ("amount_exceeds_maximum",)
        assert await _row_counts(factory, rejected_operation) == (3, 3, 3, 1, 0, 2)
    finally:
        await engine.dispose()


async def test_phase08_mapper_failure_rolls_back_quote_and_all_correlated_state(
    isolated_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, factory = _factory(isolated_database_url)
    base = 10000

    def fail_idempotency_mapping(record: MutationIdempotency) -> dict[str, object]:
        del record
        raise RuntimeError("synthetic phase08 mapper failure")

    try:
        operation_id, carrier_id, call_id = await _seed_started(factory, base)
        monkeypatch.setattr(repository_module, "_idempotency_to_values", fail_idempotency_mapping)
        with pytest.raises(RuntimeError, match="synthetic phase08 mapper failure"):
            await RecordQuoteService(
                SqlAlchemyOperationUnitOfWork(factory),
                MandatePolicy(),
                FixedClock(),
                FixedIds([UUID(int=value) for value in range(base + 20, base + 23)]),
            ).record(_quote_command(base, call_id, carrier_id))

        assert await _row_counts(factory, operation_id) == (2, 2, 2, 0, 0, 1)
    finally:
        await engine.dispose()


@pytest.mark.parametrize("failure_mode", ["flush", "commit"])
async def test_phase08_flush_and_commit_failures_roll_back_every_quote_write(
    isolated_database_url: str,
    failure_mode: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    base = 11000 if failure_mode == "flush" else 12000

    class FlushFailureRepository:
        def __init__(self, delegate: object, session: AsyncSession) -> None:
            self._delegate = delegate
            self._session = session

        async def get(self, operation_name: str, key: str) -> MutationIdempotency | None:
            return await self._delegate.get(operation_name, key)  # type: ignore[union-attr]

        async def add(self, record: MutationIdempotency) -> None:
            await self._delegate.add(record)  # type: ignore[union-attr]
            await self._session.flush()
            raise RuntimeError("synthetic phase08 flush failure")

    class FlushFailureUnitOfWork(SqlAlchemyOperationUnitOfWork):
        async def __aenter__(self):
            await super().__aenter__()
            assert self._session is not None
            self.idempotency = FlushFailureRepository(  # type: ignore[assignment]
                self.idempotency, self._session
            )
            return self

    class CommitFailureUnitOfWork(SqlAlchemyOperationUnitOfWork):
        async def commit(self) -> None:
            raise RuntimeError("synthetic phase08 commit failure")

    try:
        operation_id, carrier_id, call_id = await _seed_started(factory, base)
        unit_of_work = (
            FlushFailureUnitOfWork(factory)
            if failure_mode == "flush"
            else CommitFailureUnitOfWork(factory)
        )
        with pytest.raises(RuntimeError, match=f"synthetic phase08 {failure_mode} failure"):
            await RecordQuoteService(
                unit_of_work,
                MandatePolicy(),
                FixedClock(),
                FixedIds([UUID(int=value) for value in range(base + 20, base + 23)]),
            ).record(_quote_command(base, call_id, carrier_id))

        assert await _row_counts(factory, operation_id) == (2, 2, 2, 0, 0, 1)
    finally:
        await engine.dispose()


async def test_commit_failure_rolls_back_commitment_winner_and_operation_state(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    base = 15000

    class CommitFailureUnitOfWork(SqlAlchemyOperationUnitOfWork):
        async def commit(self) -> None:
            raise RuntimeError("synthetic commitment commit failure")

    try:
        operation_id, carrier_id, call_id = await _seed_started(factory, base)
        quote = await RecordQuoteService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 20, base + 23)]),
        ).record(_quote_command(base, call_id, carrier_id))
        with pytest.raises(RuntimeError, match="synthetic commitment commit failure"):
            await CreateCommitmentService(
                CommitFailureUnitOfWork(factory),
                MandatePolicy(),
                FixedClock(),
                FixedIds([UUID(int=value) for value in range(base + 30, base + 33)]),
            ).create(
                CreateCommitmentCommand(
                    call_id,
                    3,
                    quote.id,
                    1,
                    UUID(int=base + 40),
                    "rollback-commit-01",
                    UUID(int=base + 41),
                )
            )
        assert await _row_counts(factory, operation_id) == (3, 3, 3, 1, 0, 2)
    finally:
        await engine.dispose()


async def test_database_rejects_typed_idempotency_and_cross_operation_links(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    try:
        first_operation, first_commitment = await _seed_winner(factory, 16000)
        second_operation, second_commitment = await _seed_winner(factory, 17000)
        async with factory() as session:
            first_negotiation = (
                await session.execute(
                    select(_negotiations.c.id).where(
                        _negotiations.c.operation_id == first_operation
                    )
                )
            ).scalar_one()

        invalid_idempotency_values = (
            {
                "operation_name": "start_negotiation",
                "idempotency_key": "dangling-result-01",
                "operation_id": first_operation,
                "fingerprint": "a" * 64,
                "negotiation_id": UUID(int=999999),
                "quote_id": None,
                "commitment_id": None,
                "created_at": NOW,
            },
            {
                "operation_name": "record_quote",
                "idempotency_key": "wrong-result-type",
                "operation_id": first_operation,
                "fingerprint": "b" * 64,
                "negotiation_id": first_negotiation,
                "quote_id": None,
                "commitment_id": None,
                "created_at": NOW,
            },
            {
                "operation_name": "start_negotiation",
                "idempotency_key": "cross-operation1",
                "operation_id": second_operation,
                "fingerprint": "c" * 64,
                "negotiation_id": first_negotiation,
                "quote_id": None,
                "commitment_id": None,
                "created_at": NOW,
            },
        )
        for values in invalid_idempotency_values:
            with pytest.raises(IntegrityError):
                async with factory.begin() as session:
                    await session.execute(insert(_mutation_idempotency).values(values))

        async with factory() as session:
            first_call, first_carrier = (
                await session.execute(
                    select(
                        _carrier_sessions.c.call_id,
                        _carrier_sessions.c.carrier_id,
                    ).where(_carrier_sessions.c.operation_id == first_operation)
                )
            ).one()
        invalid_quote_values = {
            "id": UUID(int=18000),
            "operation_id": first_operation,
            "call_id": first_call,
            "carrier_id": first_carrier,
            "carrier_priority": 1,
            "amount": Decimal("-1"),
            "currency": "MXN",
            "pickup_window_start": date(2026, 9, 1),
            "pickup_window_end": date(2026, 9, 2),
            "conditions": [],
            "valid_until": NOW + timedelta(hours=1),
            "mandate_version": 1,
            "eligibility": "ELIGIBLE",
            "rejection_reasons": [],
            "created_at": NOW,
        }
        with pytest.raises(IntegrityError):
            async with factory.begin() as session:
                await session.execute(insert(_quotes).values(invalid_quote_values))

        invalid_updates = (
            update(_negotiations)
            .where(_negotiations.c.operation_id == first_operation)
            .values(operation_version=0),
            update(_quotes)
            .where(_quotes.c.id == first_commitment.quote_id)
            .values(mandate_version=0),
            update(_carrier_sessions)
            .where(_carrier_sessions.c.call_id == first_call)
            .values(channel="INVALID_CHANNEL"),
            update(_carrier_sessions)
            .where(_carrier_sessions.c.call_id == first_call)
            .values(state="INVALID_STATE"),
            update(_quotes)
            .where(_quotes.c.id == first_commitment.quote_id)
            .values(eligibility="INVALID_ELIGIBILITY"),
            update(_commitments)
            .where(_commitments.c.id == first_commitment.id)
            .values(lifecycle="INVALID_LIFECYCLE"),
            update(_commitments)
            .where(_commitments.c.id == first_commitment.id)
            .values(disposition="INVALID_DISPOSITION"),
            update(_quotes)
            .where(_quotes.c.id == first_commitment.quote_id)
            .values(
                pickup_window_start=date(2026, 9, 3),
                pickup_window_end=date(2026, 9, 2),
            ),
            update(_quotes)
            .where(_quotes.c.id == first_commitment.quote_id)
            .values(eligibility="ELIGIBLE", rejection_reasons=["inconsistent"]),
            update(_quotes)
            .where(_quotes.c.id == first_commitment.quote_id)
            .values(eligibility="REJECTED", rejection_reasons=[]),
        )
        for statement in invalid_updates:
            with pytest.raises(IntegrityError):
                async with factory.begin() as session:
                    await session.execute(statement)

        second_quote_id = UUID(int=18001)
        async with factory.begin() as session:
            await session.execute(
                insert(_quotes).values(
                    {**invalid_quote_values, "id": second_quote_id, "amount": Decimal("100")}
                )
            )
        with pytest.raises(IntegrityError):
            async with factory.begin() as session:
                await session.execute(
                    insert(_commitments).values(
                        id=UUID(int=18002),
                        operation_id=first_operation,
                        call_id=first_call,
                        quote_id=second_quote_id,
                        carrier_id=first_carrier,
                        amount=Decimal("100"),
                        currency="MXN",
                        pickup_window_start=date(2026, 9, 1),
                        pickup_window_end=date(2026, 9, 2),
                        conditions=[],
                        mandate_version=1,
                        evidence_id=UUID(int=18003),
                        lifecycle="CANDIDATE",
                        disposition="ACTIVE",
                        replaces_commitment_id=None,
                        replaced_by_commitment_id=None,
                        created_at=NOW,
                        superseded_at=None,
                    )
                )

        with pytest.raises(IntegrityError):
            async with factory.begin() as session:
                await session.execute(
                    update(_commitments)
                    .where(_commitments.c.id == first_commitment.id)
                    .values(replaces_commitment_id=first_commitment.id)
                )
        with pytest.raises(IntegrityError):
            async with factory.begin() as session:
                await session.execute(
                    update(_commitments)
                    .where(_commitments.c.id == first_commitment.id)
                    .values(replaces_commitment_id=second_commitment.id)
                )

        async with factory() as session:
            second_carrier = (
                await session.execute(
                    select(_carrier_sessions.c.carrier_id).where(
                        _carrier_sessions.c.operation_id == second_operation
                    )
                )
            ).scalar_one()
        with pytest.raises(IntegrityError):
            async with factory.begin() as session:
                await session.execute(
                    insert(_quotes).values(
                        id=UUID(int=18000),
                        operation_id=second_operation,
                        call_id=first_call,
                        carrier_id=second_carrier,
                        carrier_priority=1,
                        amount=Decimal("100"),
                        currency="MXN",
                        pickup_window_start=date(2026, 9, 1),
                        pickup_window_end=date(2026, 9, 2),
                        conditions=[],
                        valid_until=NOW + timedelta(hours=1),
                        mandate_version=1,
                        eligibility="ELIGIBLE",
                        rejection_reasons=[],
                        created_at=NOW,
                    )
                )
    finally:
        await engine.dispose()
