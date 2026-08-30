from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from yuno_backend.volta.persistence import SqlAlchemyOutboundCallAttemptStore
from yuno_backend.volta.persistence.mappers import (
    _outbound_call_attempt_from_row,
    _outbound_call_attempt_to_values,
)
from yuno_backend.volta.persistence.repositories import _is_monotonic_call_update
from yuno_backend.volta.telephony.errors import OutboundCallIdempotencyConflict
from yuno_backend.volta.telephony.models import (
    OutboundCall,
    OutboundCallAttempt,
    OutboundCallAttemptState,
    OutboundCallFailure,
    OutboundCallFailureCategory,
    OutboundCallStatus,
    OutboundCallUncertainReason,
    OutboundCallUncertainState,
)

from .test_repositories import _approve, _create_draft

NOW = datetime(2026, 9, 2, 12, tzinfo=UTC)
FINGERPRINT = "a" * 64


def _factory(database_url: str):
    engine = create_async_engine(database_url, hide_parameters=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _operation(factory: async_sessionmaker[AsyncSession]) -> UUID:
    draft_id, operation_id = uuid4(), uuid4()
    await _create_draft(factory, draft_id)
    await _approve(
        factory,
        draft_id,
        [operation_id, uuid4(), uuid4(), uuid4()],
        uuid4(),
    )
    return operation_id


def _pending(operation_id: UUID, key: str = "outbound-attempt-0001") -> OutboundCallAttempt:
    return OutboundCallAttempt(
        operation_id=operation_id,
        idempotency_key=key,
        request_fingerprint=FINGERPRINT,
        state=OutboundCallAttemptState.PENDING,
        result=None,
        uncertainty=None,
        failure=None,
        created_at=NOW,
        updated_at=NOW,
    )


def _result() -> OutboundCall:
    return OutboundCall(
        call_session_id=uuid4(),
        provider_call_id=f"CA{uuid4().hex}",
        status=OutboundCallStatus.RINGING,
        created_at=NOW + timedelta(seconds=1),
        status_updated_at=NOW + timedelta(seconds=2),
        last_status_event_id="event-2",
        last_status_sequence_number=2,
        processed_status_event_ids=("event-1", "event-2"),
    )


def test_mapper_round_trips_normalized_result_without_sensitive_request_data() -> None:
    attempt = replace(
        _pending(uuid4()),
        state=OutboundCallAttemptState.SUCCEEDED,
        result=_result(),
        updated_at=NOW + timedelta(seconds=3),
    )
    values = _outbound_call_attempt_to_values(attempt)
    assert _outbound_call_attempt_from_row(values) == attempt
    assert "destination" not in values
    assert "payload" not in values
    assert "authorization" not in values
    assert attempt.idempotency_key not in repr(attempt)


@pytest.mark.parametrize(
    "category",
    [OutboundCallFailureCategory.TIMEOUT, OutboundCallFailureCategory.CONNECTION],
)
def test_mapper_round_trips_definitive_transport_failures(
    category: OutboundCallFailureCategory,
) -> None:
    attempt = replace(
        _pending(uuid4()),
        state=OutboundCallAttemptState.FAILED,
        failure=OutboundCallFailure(category, NOW + timedelta(seconds=1)),
        updated_at=NOW + timedelta(seconds=1),
    )
    assert _outbound_call_attempt_from_row(
        _outbound_call_attempt_to_values(attempt)
    ) == attempt


def test_monotonic_result_guard_rejects_every_stale_or_regressive_snapshot() -> None:
    result = _result()
    stored = replace(
        _pending(uuid4()),
        state=OutboundCallAttemptState.SUCCEEDED,
        result=result,
        updated_at=NOW + timedelta(seconds=3),
    )
    newer = replace(
        result,
        status=OutboundCallStatus.IN_PROGRESS,
        status_updated_at=NOW + timedelta(seconds=4),
        last_status_event_id="event-3",
        last_status_sequence_number=3,
        processed_status_event_ids=("event-1", "event-2", "event-3"),
    )
    assert _is_monotonic_call_update(stored, newer, NOW + timedelta(seconds=4))
    assert not _is_monotonic_call_update(stored, result, NOW + timedelta(seconds=4))
    assert not _is_monotonic_call_update(
        stored,
        replace(
            newer,
            last_status_event_id="event-2b",
            last_status_sequence_number=2,
            processed_status_event_ids=("event-1", "event-2", "event-2b"),
        ),
        NOW + timedelta(seconds=4),
    )
    assert not _is_monotonic_call_update(
        stored,
        replace(
            newer,
            processed_status_event_ids=("event-2", "event-3"),
        ),
        NOW + timedelta(seconds=4),
    )
    assert not _is_monotonic_call_update(
        stored,
        replace(newer, status_updated_at=NOW + timedelta(seconds=1)),
        NOW + timedelta(seconds=4),
    )
    assert not _is_monotonic_call_update(
        stored, newer, NOW + timedelta(seconds=2)
    )
    assert not _is_monotonic_call_update(
        stored,
        replace(newer, status=OutboundCallStatus.INITIATED),
        NOW + timedelta(seconds=4),
    )

    terminal = replace(
        stored,
        result=replace(result, status=OutboundCallStatus.COMPLETED),
    )
    assert not _is_monotonic_call_update(
        terminal,
        replace(newer, status=OutboundCallStatus.FAILED),
        NOW + timedelta(seconds=4),
    )


async def test_reservation_completion_and_event_cursor_survive_restart(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    operation_id = await _operation(factory)
    attempt = _pending(operation_id)
    first = await SqlAlchemyOutboundCallAttemptStore(factory).reserve(attempt)
    assert first.created
    await engine.dispose()

    restarted_engine, restarted_factory = _factory(isolated_database_url)
    try:
        store = SqlAlchemyOutboundCallAttemptStore(restarted_factory)
        replay = await store.reserve(attempt)
        assert not replay.created
        assert replay.attempt == attempt

        result = _result()
        completed = await store.complete(
            attempt.idempotency_key,
            attempt.request_fingerprint,
            result,
            NOW + timedelta(seconds=3),
        )
        assert completed.state is OutboundCallAttemptState.SUCCEEDED
        assert completed.result == result

        updated_result = replace(
            result,
            status=OutboundCallStatus.COMPLETED,
            status_updated_at=NOW + timedelta(seconds=4),
            last_status_event_id="event-3",
            last_status_sequence_number=3,
            processed_status_event_ids=("event-1", "event-2", "event-3"),
        )
        updated = await store.complete(
            attempt.idempotency_key,
            attempt.request_fingerprint,
            updated_result,
            NOW + timedelta(seconds=4),
        )
        assert updated.result == updated_result
        assert await store.complete(
            attempt.idempotency_key,
            attempt.request_fingerprint,
            updated_result,
            NOW + timedelta(seconds=5),
        ) == updated

        after_restart = await store.reserve(attempt)
        assert not after_restart.created
        assert after_restart.attempt == updated
        non_regressed = await store.mark_uncertain(
            attempt.idempotency_key,
            attempt.request_fingerprint,
            OutboundCallUncertainState(
                OutboundCallUncertainReason.CONNECTION_LOST,
                NOW + timedelta(seconds=5),
            ),
        )
        assert non_regressed == updated

        stale = replace(
            result,
            status=OutboundCallStatus.INITIATED,
            status_updated_at=NOW + timedelta(seconds=1),
            last_status_event_id="event-1",
            last_status_sequence_number=1,
            processed_status_event_ids=("event-1",),
        )
        assert await store.complete(
            attempt.idempotency_key,
            attempt.request_fingerprint,
            stale,
            NOW + timedelta(seconds=6),
        ) == updated
        changed_terminal = replace(
            updated_result,
            status=OutboundCallStatus.FAILED,
            status_updated_at=NOW + timedelta(seconds=7),
            last_status_event_id="event-4",
            last_status_sequence_number=4,
            processed_status_event_ids=("event-1", "event-2", "event-3", "event-4"),
        )
        assert await store.complete(
            attempt.idempotency_key,
            attempt.request_fingerprint,
            changed_terminal,
            NOW + timedelta(seconds=7),
        ) == updated
    finally:
        await restarted_engine.dispose()


async def test_uncertain_and_failure_outcomes_are_durable_and_monotonic(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    operation_id = await _operation(factory)
    store = SqlAlchemyOutboundCallAttemptStore(factory)
    uncertain_attempt = _pending(operation_id, "outbound-uncertain-0001")
    failed_attempt = _pending(operation_id, "outbound-failed-0001")
    try:
        await store.reserve(uncertain_attempt)
        uncertainty = OutboundCallUncertainState(
            OutboundCallUncertainReason.INVALID_RESPONSE,
            NOW + timedelta(seconds=1),
        )
        uncertain = await store.mark_uncertain(
            uncertain_attempt.idempotency_key, FINGERPRINT, uncertainty
        )
        assert uncertain.uncertainty == uncertainty
        assert await store.fail(
            uncertain_attempt.idempotency_key,
            FINGERPRINT,
            OutboundCallFailure(
                OutboundCallFailureCategory.PROVIDER_REJECTED,
                NOW + timedelta(seconds=2),
                503,
            ),
        ) == uncertain

        await store.reserve(failed_attempt)
        failure = OutboundCallFailure(
            OutboundCallFailureCategory.RATE_LIMIT,
            NOW + timedelta(seconds=1),
            429,
        )
        failed = await store.fail(failed_attempt.idempotency_key, FINGERPRINT, failure)
        assert failed.failure == failure
        assert (await store.reserve(failed_attempt)).attempt == failed
    finally:
        await engine.dispose()


async def test_concurrent_reserve_elects_exactly_one_dispatcher_and_conflicts_safely(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    operation_id = await _operation(factory)
    attempt = _pending(operation_id, "outbound-concurrent-0001")
    store = SqlAlchemyOutboundCallAttemptStore(factory)
    try:
        reservations = await asyncio.gather(*(store.reserve(attempt) for _ in range(8)))
        assert sum(item.created for item in reservations) == 1
        assert all(item.attempt == attempt for item in reservations)

        with pytest.raises(OutboundCallIdempotencyConflict) as captured:
            await store.reserve(replace(attempt, request_fingerprint="b" * 64))
        assert attempt.idempotency_key not in str(captured.value)
        assert attempt.idempotency_key not in repr(reservations[0])
    finally:
        await engine.dispose()


async def test_failed_insert_transaction_rolls_back_cleanly(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    operation_id = await _operation(factory)
    attempt = _pending(operation_id, "outbound-rollback-0001")

    def fail_insert(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.startswith("INSERT INTO volta_outbound_call_attempts"):
            raise RuntimeError("synthetic insert failure")

    event.listen(engine.sync_engine, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic insert failure"):
            await SqlAlchemyOutboundCallAttemptStore(factory).reserve(attempt)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", fail_insert)

    try:
        retry = await SqlAlchemyOutboundCallAttemptStore(factory).reserve(attempt)
        assert retry.created
    finally:
        await engine.dispose()


async def test_database_constraints_reject_invalid_attempt_state_and_cursor(
    isolated_database_url: str,
) -> None:
    engine, factory = _factory(isolated_database_url)
    operation_id = await _operation(factory)
    attempt = _pending(operation_id, "outbound-constraints-0001")
    store = SqlAlchemyOutboundCallAttemptStore(factory)
    try:
        await store.reserve(attempt)
        async with factory() as session:
            with pytest.raises(DBAPIError):
                await session.execute(
                    text(
                        "UPDATE volta_outbound_call_attempts SET state='SUCCEEDED' "
                        "WHERE idempotency_key=:key"
                    ),
                    {"key": attempt.idempotency_key},
                )
                await session.commit()
            await session.rollback()

        await store.complete(
            attempt.idempotency_key,
            FINGERPRINT,
            _result(),
            NOW + timedelta(seconds=3),
        )
        async with factory() as session:
            with pytest.raises(DBAPIError):
                await session.execute(
                    text(
                        "UPDATE volta_outbound_call_attempts "
                        "SET processed_status_event_ids=ARRAY['bad,event']::text[] "
                        "WHERE idempotency_key=:key"
                    ),
                    {"key": attempt.idempotency_key},
                )
                await session.commit()
            await session.rollback()
    finally:
        await engine.dispose()
