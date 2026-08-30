from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from yuno_backend.volta.mandates import (
    ApproveOperationCommand,
    ApproveOperationService,
    CreateIntakeDraftCommand,
    CreateIntakeDraftService,
    MandateProposal,
    Money,
    Operation,
    OperationAlreadyApproved,
    OperationProposal,
    PickupWindow,
    Route,
)
from yuno_backend.volta.persistence import (
    PersistenceUnavailable,
    SqlAlchemyAuditEventRepository,
    SqlAlchemyIntakeDraftRepository,
    SqlAlchemyOperationRepository,
    SqlAlchemyOperationUnitOfWork,
)
from yuno_backend.volta.persistence import repositories as repository_module
from yuno_backend.volta.persistence.tables import (
    _audit_events,
    _intake_drafts,
    _mandates,
    _operation_status_history,
    _operations,
)

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class FixedIds:
    def __init__(self, values: list[UUID]) -> None:
        self._values = values

    def new_id(self) -> UUID:
        return self._values.pop(0)


def _proposal() -> OperationProposal:
    return OperationProposal(
        route=Route("Synthetic Port", "Synthetic Inland Depot"),
        pickup_date=date(2026, 9, 2),
        cargo_label="Synthetic sealed container",
        mandate=MandateProposal(
            maximum_amount=Money(Decimal("1500.125"), "MXN"),
            pickup_window=PickupWindow(date(2026, 9, 1), date(2026, 9, 3)),
            allowed_conditions=("sealed container", "daylight pickup"),
            escalation_conditions=("amount exceeds mandate",),
        ),
    )


def _factory(database_url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url, hide_parameters=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _create_draft(
    factory: async_sessionmaker[AsyncSession],
    draft_id: UUID,
):
    return await CreateIntakeDraftService(
        SqlAlchemyOperationUnitOfWork(factory),
        FixedClock(),
        FixedIds([draft_id]),
    ).create(
        CreateIntakeDraftCommand(
            "Move synthetic freight under approved constraints.",
            "EN_US",
            "intake-v1",
            _proposal(),
        )
    )


async def _approve(
    factory: async_sessionmaker[AsyncSession],
    draft_id: UUID,
    ids: list[UUID],
    correlation_id: UUID,
) -> Operation:
    return await ApproveOperationService(
        SqlAlchemyOperationUnitOfWork(factory), FixedClock(), FixedIds(ids)
    ).approve(
        ApproveOperationCommand(
            draft_id, 1, "synthetic-coordinator", correlation_id
        )
    )


async def _approval_row_counts(
    factory: async_sessionmaker[AsyncSession],
    draft_id: UUID,
    operation_id: UUID,
) -> tuple[int, int, int, int]:
    async with factory() as session:
        operation_count = (await session.execute(
            select(func.count()).select_from(_operations).where(
                _operations.c.source_draft_id == draft_id
            )
        )).scalar_one()
        dependent_counts = []
        for table in (_mandates, _operation_status_history, _audit_events):
            dependent_counts.append(
                (await session.execute(
                    select(func.count()).select_from(table).where(
                        table.c.operation_id == operation_id
                    )
                )).scalar_one()
            )
    return (operation_count, *dependent_counts)


async def test_round_trip_persists_exact_draft_operation_history_and_audit(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id, operation_id, mandate_id, status_id, audit_id, correlation_id = (
        uuid4() for _ in range(6)
    )
    try:
        draft = await _create_draft(factory, draft_id)
        operation = await _approve(
            factory,
            draft_id,
            [operation_id, mandate_id, status_id, audit_id],
            correlation_id,
        )

        async with factory() as session:
            loaded_draft = await SqlAlchemyIntakeDraftRepository(session).get(draft_id)
            loaded_operation = await SqlAlchemyOperationRepository(session).get_by_draft_id(
                draft_id
            )
            events = await SqlAlchemyAuditEventRepository(session).list_by_operation(operation_id)

        assert loaded_draft == draft
        assert loaded_operation == operation
        assert loaded_operation is not None
        assert loaded_operation.mandate.maximum_amount.amount == Decimal("1500.125")
        assert loaded_operation.status.value == "READY"
        assert isinstance(loaded_operation.status_history, tuple)
        assert loaded_operation.status_history[0].id == status_id
        assert events[0].event_id == audit_id
        assert events[0].correlation_id == correlation_id
        assert events[0].metadata == {"draft_version": 1}
        assert draft.source_prompt not in repr(loaded_draft)

        earlier_event_id = UUID(int=1)
        async with factory.begin() as session:
            await SqlAlchemyAuditEventRepository(session).add(
                replace(events[0], event_id=earlier_event_id)
            )
            await session.execute(
                insert(_operation_status_history).values(
                    id=UUID(int=1),
                    operation_id=operation_id,
                    operation_version=1,
                    status="READY",
                    occurred_at=NOW,
                )
            )
        async with factory() as session:
            ordered = await SqlAlchemyAuditEventRepository(session).list_by_operation(
                operation_id
            )
            ordered_operation = await SqlAlchemyOperationRepository(
                session
            ).get_by_draft_id(draft_id)
        assert tuple(event.event_id for event in ordered) == (earlier_event_id, audit_id)
        assert ordered_operation is not None
        assert tuple(entry.id for entry in ordered_operation.status_history) == (
            UUID(int=1),
            status_id,
        )
    finally:
        await engine.dispose()


async def test_invalid_draft_round_trip_preserves_ordered_validation_issues(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id = uuid4()
    invalid_proposal = OperationProposal(
        route=Route("", ""),
        pickup_date=date(2026, 9, 5),
        cargo_label="",
        mandate=MandateProposal(
            maximum_amount=Money(Decimal("-1.25"), "USD"),
            pickup_window=PickupWindow(date(2026, 9, 4), date(2026, 9, 3)),
            allowed_conditions=("",),
        ),
    )
    try:
        draft = await CreateIntakeDraftService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([draft_id]),
        ).create(
            CreateIntakeDraftCommand(
                "Synthetic invalid request.", "UNSUPPORTED", "intake-v1", invalid_proposal
            )
        )
        async with factory() as session:
            loaded = await SqlAlchemyIntakeDraftRepository(session).get(draft_id)

        assert loaded == draft
        assert not loaded.approval_eligible  # type: ignore[union-attr]
        assert tuple(issue.reason_code for issue in loaded.validation_issues) == (  # type: ignore[union-attr]
                "required",
                "required",
                "required",
                "invalid_order",
            "outside_mandate_window",
            "must_be_non_negative",
            "unsupported",
            "unsupported",
            "contains_empty",
        )
    finally:
        await engine.dispose()


async def test_invalid_stored_draft_json_is_translated_without_value_leak(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id = uuid4()
    try:
        await _create_draft(factory, draft_id)
        async with factory.begin() as session:
            await session.execute(
                update(_intake_drafts)
                .where(_intake_drafts.c.id == draft_id)
                .values(
                    validation_issues=[{"submitted_secret": "hidden-value"}],
                    approval_eligible=False,
                )
            )
        async with factory() as session:
            with pytest.raises(PersistenceUnavailable) as captured:
                await SqlAlchemyIntakeDraftRepository(session).get(draft_id)

        assert captured.value.reason_code == "invalid_stored_state"
        assert "hidden-value" not in str(captured.value)
        assert "submitted_secret" not in str(captured.value)
    finally:
        await engine.dispose()


async def test_failures_before_commit_roll_back_all_approval_rows(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id = uuid4()
    operation_id, mandate_id, status_id, audit_id = (uuid4() for _ in range(4))

    class FailingAuditRepository:
        async def add(self, event: object) -> None:
            raise RuntimeError("synthetic audit failure")

        async def list_by_operation(self, operation_id: UUID) -> tuple[()]:
            return ()

    class FailingAuditUnitOfWork(SqlAlchemyOperationUnitOfWork):
        async def __aenter__(self) -> FailingAuditUnitOfWork:
            await super().__aenter__()
            self.audit_events = FailingAuditRepository()  # type: ignore[assignment]
            return self

    try:
        await _create_draft(factory, draft_id)
        with pytest.raises(RuntimeError, match="synthetic audit failure"):
            await ApproveOperationService(
                FailingAuditUnitOfWork(factory),
                FixedClock(),
                FixedIds([operation_id, mandate_id, status_id, audit_id]),
            ).approve(
                ApproveOperationCommand(
                    draft_id, 1, "synthetic-coordinator", uuid4()
                )
            )

        async with factory() as session:
            assert await SqlAlchemyIntakeDraftRepository(session).get(draft_id) is not None
            assert await SqlAlchemyOperationRepository(session).get_by_draft_id(draft_id) is None
            counts = []
            for table in (_mandates, _operation_status_history, _audit_events):
                count = (await session.execute(
                    select(func.count()).select_from(table).where(
                        table.c.operation_id == operation_id
                    )
                )).scalar_one()
                counts.append(count)
        assert tuple(counts) == (0, 0, 0)
    finally:
        await engine.dispose()


async def test_injected_commit_failure_rolls_back_pending_approval(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id = uuid4()
    operation_id, mandate_id, status_id, audit_id = (uuid4() for _ in range(4))

    class FailingCommitUnitOfWork(SqlAlchemyOperationUnitOfWork):
        async def commit(self) -> None:
            raise RuntimeError("synthetic commit failure")

    try:
        await _create_draft(factory, draft_id)
        with pytest.raises(RuntimeError, match="synthetic commit failure"):
            await ApproveOperationService(
                FailingCommitUnitOfWork(factory),
                FixedClock(),
                FixedIds([operation_id, mandate_id, status_id, audit_id]),
            ).approve(
                ApproveOperationCommand(
                    draft_id, 1, "synthetic-coordinator", uuid4()
                )
            )
        async with factory() as session:
            assert await SqlAlchemyIntakeDraftRepository(session).get(draft_id) is not None
            assert await SqlAlchemyOperationRepository(session).get_by_draft_id(draft_id) is None
            counts = [
                (await session.execute(
                    select(func.count()).select_from(_operations).where(
                        _operations.c.source_draft_id == draft_id
                    )
                )).scalar_one()
            ]
            for table in (_mandates, _operation_status_history, _audit_events):
                counts.append(
                    (await session.execute(
                        select(func.count()).select_from(table).where(
                            table.c.operation_id == operation_id
                        )
                    )).scalar_one()
                )
        assert tuple(counts) == (0, 0, 0, 0)
    finally:
        await engine.dispose()


async def test_mapper_failure_after_operation_insert_rolls_back_every_row(
    isolated_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id = uuid4()
    operation_id = uuid4()

    def fail_mandate_mapping(mandate: object) -> dict[str, object]:
        raise RuntimeError("synthetic mapper failure")

    try:
        await _create_draft(factory, draft_id)
        monkeypatch.setattr(
            repository_module, "_mandate_to_values", fail_mandate_mapping
        )
        with pytest.raises(RuntimeError, match="synthetic mapper failure"):
            await _approve(
                factory,
                draft_id,
                [operation_id, uuid4(), uuid4(), uuid4()],
                uuid4(),
            )
        assert await _approval_row_counts(factory, draft_id, operation_id) == (0, 0, 0, 0)
    finally:
        await engine.dispose()


async def test_injected_failure_after_flush_rolls_back_every_row(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id = uuid4()
    operation_id = uuid4()

    class FailingAfterFlushRepository:
        def __init__(
            self,
            delegate: SqlAlchemyOperationRepository,
            session: AsyncSession,
        ) -> None:
            self._delegate = delegate
            self._session = session

        async def get_by_draft_id(self, requested_draft_id: UUID) -> Operation | None:
            return await self._delegate.get_by_draft_id(requested_draft_id)

        async def add(self, operation: Operation) -> None:
            await self._delegate.add(operation)
            await self._session.flush()
            raise RuntimeError("synthetic flush failure")

    class FailingFlushUnitOfWork(SqlAlchemyOperationUnitOfWork):
        async def __aenter__(self) -> FailingFlushUnitOfWork:
            await super().__aenter__()
            self.operations = FailingAfterFlushRepository(  # type: ignore[assignment]
                self.operations, self._require_session()
            )
            return self

    try:
        await _create_draft(factory, draft_id)
        with pytest.raises(RuntimeError, match="synthetic flush failure"):
            await ApproveOperationService(
                FailingFlushUnitOfWork(factory),
                FixedClock(),
                FixedIds([operation_id, uuid4(), uuid4(), uuid4()]),
            ).approve(
                ApproveOperationCommand(
                    draft_id, 1, "synthetic-coordinator", uuid4()
                )
            )
        assert await _approval_row_counts(factory, draft_id, operation_id) == (0, 0, 0, 0)
    finally:
        await engine.dispose()


async def test_sequential_and_concurrent_duplicates_return_safe_winner(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id = uuid4()

    class Barrier:
        def __init__(self) -> None:
            self.count = 0
            self.lock = asyncio.Lock()
            self.ready = asyncio.Event()

        async def wait(self) -> None:
            async with self.lock:
                self.count += 1
                if self.count == 2:
                    self.ready.set()
            await self.ready.wait()

    class CoordinatedOperationRepository:
        def __init__(self, delegate: SqlAlchemyOperationRepository, barrier: Barrier) -> None:
            self._delegate = delegate
            self._barrier = barrier

        async def get_by_draft_id(self, requested_draft_id: UUID) -> Operation | None:
            result = await self._delegate.get_by_draft_id(requested_draft_id)
            await self._barrier.wait()
            return result

        async def add(self, operation: Operation) -> None:
            await self._delegate.add(operation)

    barrier = Barrier()

    class RacingUnitOfWork(SqlAlchemyOperationUnitOfWork):
        async def __aenter__(self) -> RacingUnitOfWork:
            await super().__aenter__()
            self.operations = CoordinatedOperationRepository(  # type: ignore[assignment]
                self.operations, barrier
            )
            return self

    try:
        await _create_draft(factory, draft_id)
        services = [
            ApproveOperationService(
                RacingUnitOfWork(factory),
                FixedClock(),
                FixedIds([uuid4(), uuid4(), uuid4(), uuid4()]),
            )
            for _ in range(2)
        ]
        results = await asyncio.gather(
            *(
                service.approve(
                    ApproveOperationCommand(
                        draft_id, 1, "synthetic-coordinator", uuid4()
                    )
                )
                for service in services
            ),
            return_exceptions=True,
        )
        winner = next(result for result in results if isinstance(result, Operation))
        loser = next(
            result for result in results if isinstance(result, OperationAlreadyApproved)
        )
        assert loser.operation_id == winner.id
        assert "sql" not in str(loser).lower()

        with pytest.raises(OperationAlreadyApproved) as sequential:
            await _approve(
                factory,
                draft_id,
                [uuid4(), uuid4(), uuid4(), uuid4()],
                uuid4(),
            )
        assert sequential.value.operation_id == winner.id

        async with factory() as session:
            operation_count = (await session.execute(
                select(func.count()).select_from(_operations).where(
                    _operations.c.source_draft_id == draft_id
                )
            )).scalar_one()
            audit_count = (await session.execute(
                select(func.count()).select_from(_audit_events).where(
                    _audit_events.c.operation_id == winner.id
                )
            )).scalar_one()
            mandate_count = (await session.execute(
                select(func.count()).select_from(_mandates).where(
                    _mandates.c.operation_id == winner.id
                )
            )).scalar_one()
            status_count = (await session.execute(
                select(func.count()).select_from(_operation_status_history).where(
                    _operation_status_history.c.operation_id == winner.id
                )
            )).scalar_one()
        assert (operation_count, mandate_count, status_count, audit_count) == (1, 1, 1, 1)
    finally:
        await engine.dispose()


async def _assert_statement_rejected(
    factory: async_sessionmaker[AsyncSession],
    statement: str,
    parameters: dict[str, object],
) -> None:
    async with factory() as session:
        with pytest.raises(DBAPIError):
            await session.execute(text(statement), parameters)
            await session.commit()
        await session.rollback()


async def test_append_only_triggers_and_constraints_reject_invalid_rows(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    draft_id, operation_id, mandate_id, status_id, audit_id = (uuid4() for _ in range(5))
    try:
        await _create_draft(factory, draft_id)
        await _approve(
            factory,
            draft_id,
            [operation_id, mandate_id, status_id, audit_id],
            uuid4(),
        )
        mutations = (
            ("UPDATE volta_operation_status_history SET status='READY' WHERE id=:id", status_id),
            ("DELETE FROM volta_operation_status_history WHERE id=:id", status_id),
            ("UPDATE volta_audit_events SET event_type='CHANGED' WHERE event_id=:id", audit_id),
            ("DELETE FROM volta_audit_events WHERE event_id=:id", audit_id),
        )
        for statement, row_id in mutations:
            await _assert_statement_rejected(factory, statement, {"id": row_id})

        invalid_history = (
            "INSERT INTO volta_operation_status_history "
            "(id, operation_id, operation_version, status, occurred_at) "
            "VALUES (:id, :operation_id, :version, :status, :occurred_at)"
        )
        for values in (
            {"operation_id": operation_id, "version": 1, "status": "INVALID"},
            {"operation_id": operation_id, "version": 0, "status": "READY"},
            {"operation_id": uuid4(), "version": 1, "status": "READY"},
        ):
            await _assert_statement_rejected(
                factory,
                invalid_history,
                {"id": uuid4(), "occurred_at": NOW, **values},
            )

        await _assert_statement_rejected(
            factory,
            "INSERT INTO volta_audit_events "
            "(event_id, operation_id, operation_version, actor_kind, event_type, "
            "occurred_at, correlation_id, metadata) VALUES "
            "(:id, :operation_id, 1, 'INVALID', 'SAFE_EVENT', :occurred_at, :correlation, '{}')",
            {
                "id": uuid4(),
                "operation_id": operation_id,
                "occurred_at": NOW,
                "correlation": uuid4(),
            },
        )
        invalid_audit = (
            "INSERT INTO volta_audit_events "
            "(event_id, operation_id, operation_version, actor_kind, event_type, "
            "occurred_at, correlation_id, metadata) VALUES "
            "(:id, :operation_id, :version, :actor, :event_type, :occurred_at, "
            ":correlation, '{}')"
        )
        for values in (
            {
                "operation_id": operation_id,
                "version": 0,
                "actor": "SYSTEM",
                "event_type": "SAFE_EVENT",
            },
            {
                "operation_id": uuid4(),
                "version": 1,
                "actor": "SYSTEM",
                "event_type": "SAFE_EVENT",
            },
            {
                "operation_id": operation_id,
                "version": 1,
                "actor": "SYSTEM",
                "event_type": "invalid-event",
            },
        ):
            await _assert_statement_rejected(
                factory,
                invalid_audit,
                {
                    "id": uuid4(),
                    "occurred_at": NOW,
                    "correlation": uuid4(),
                    **values,
                },
            )
        invalid_audit_metadata = (
            "INSERT INTO volta_audit_events "
            "(event_id, operation_id, operation_version, actor_kind, event_type, "
            "occurred_at, correlation_id, metadata) VALUES "
            "(:id, :operation_id, 1, 'SYSTEM', 'OPERATION_APPROVED', "
            ":occurred_at, :correlation, CAST(:metadata AS jsonb))"
        )
        for metadata in (
            '{"authorization": "synthetic"}',
            '{"draft_version": 1, "extra": "synthetic"}',
            '{"draft_version": {"nested": "synthetic"}}',
            '{"draft_version": 1.5}',
            '{"draft_version": 9007199254740992}',
        ):
            await _assert_statement_rejected(
                factory,
                invalid_audit_metadata,
                {
                    "id": uuid4(),
                    "operation_id": operation_id,
                    "occurred_at": NOW,
                    "correlation": uuid4(),
                    "metadata": metadata,
                },
            )
        await _assert_statement_rejected(
            factory,
            "UPDATE volta_operations SET active_mandate_id=:mandate_id WHERE id=:operation_id",
            {"mandate_id": uuid4(), "operation_id": operation_id},
        )
        await _assert_statement_rejected(
            factory,
            "INSERT INTO volta_operations "
            "(id, version, source_draft_id, source_draft_version, route_origin, "
            "route_destination, pickup_date, active_mandate_id, created_at) VALUES "
            "(:id, 1, :source_draft_id, 1, 'Synthetic A', 'Synthetic B', "
            ":pickup_date, :mandate_id, :created_at)",
            {
                "id": uuid4(),
                "source_draft_id": uuid4(),
                "pickup_date": date(2026, 9, 2),
                "mandate_id": uuid4(),
                "created_at": NOW,
            },
        )
        await _assert_statement_rejected(
            factory,
            "INSERT INTO volta_mandates SELECT :id, operation_id, version, maximum_amount, "
            "currency, pickup_window_start_date, pickup_window_end_date, allowed_conditions, "
            "escalation_conditions, authorized_actions, approval_actor, approved_at "
            "FROM volta_mandates WHERE id=:existing_id",
            {"id": uuid4(), "existing_id": mandate_id},
        )
        await _assert_statement_rejected(
            factory,
            "INSERT INTO volta_mandates SELECT :id, :operation_id, 2, maximum_amount, "
            "currency, pickup_window_start_date, pickup_window_end_date, allowed_conditions, "
            "escalation_conditions, authorized_actions, approval_actor, approved_at "
            "FROM volta_mandates WHERE id=:existing_id",
            {"id": uuid4(), "operation_id": uuid4(), "existing_id": mandate_id},
        )
        for table, identifier_column, identifier in (
            ("volta_intake_drafts", "id", draft_id),
            ("volta_operations", "id", operation_id),
            ("volta_mandates", "id", mandate_id),
        ):
            await _assert_statement_rejected(
                factory,
                f"UPDATE {table} SET version=0 WHERE {identifier_column}=:id",
                {"id": identifier},
            )
        for special in ("NaN", "Infinity", "-Infinity"):
            await _assert_statement_rejected(
                factory,
                "UPDATE volta_mandates SET maximum_amount=CAST(:amount AS numeric) WHERE id=:id",
                {"amount": special, "id": mandate_id},
            )
            await _assert_statement_rejected(
                factory,
                "UPDATE volta_intake_drafts SET maximum_amount=CAST(:amount AS numeric) "
                "WHERE id=:id",
                {"amount": special, "id": draft_id},
            )

        assert not hasattr(SqlAlchemyAuditEventRepository, "update")
        assert not hasattr(SqlAlchemyAuditEventRepository, "delete")
    finally:
        await engine.dispose()
