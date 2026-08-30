from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from yuno_backend.volta.telephony import (
    HumanHandoffCommand,
    HumanHandoffContext,
    HumanHandoffIdempotencyConflict,
    HumanHandoffOutcomeUncertain,
    HumanHandoffProviderError,
    HumanHandoffReadiness,
    HumanHandoffService,
    HumanHandoffStatus,
    HumanHandoffStatusEvent,
    HumanHandoffTimeoutError,
    InMemoryAIAuthorityFence,
    InMemoryHumanHandoffRepository,
)

NOW = datetime(2026, 8, 30, 15, tzinfo=UTC)
CALL_ID = UUID("10000000-0000-0000-0000-000000000001")
HANDOFF_ID = UUID("20000000-0000-0000-0000-000000000001")
CORRELATION_ID = UUID("30000000-0000-0000-0000-000000000001")


class Clock:
    def now(self) -> datetime:
        return NOW


class Gateway:
    def __init__(self) -> None:
        self.calls = 0

    async def begin_handoff(self, handoff) -> None:
        self.calls += 1


class Audit:
    def __init__(self) -> None:
        self.events: list[str] = []

    async def handoff_requested(self, handoff, command) -> None:
        self.events.append("requested")

    async def handoff_outcome(self, handoff) -> None:
        self.events.append(handoff.status.value)


async def context(call_id: UUID, expected: datetime) -> HumanHandoffContext:
    assert call_id == CALL_ID
    assert expected == NOW - timedelta(seconds=1)
    return HumanHandoffContext(
        mandate_version=4,
        mandate_facts=("Route: synthetic",),
        eligible_quote_summaries=("Priority 1: 100 MXN",),
        structured_call_brief=("Dispatcher accepted the window",),
        call_status="IN_PROGRESS",
    )


async def readiness(call_id: UUID) -> HumanHandoffReadiness | None:
    if call_id != CALL_ID:
        return None
    return HumanHandoffReadiness(
        call_id=call_id,
        call_status_updated_at=NOW - timedelta(seconds=1),
        context=await context(call_id, NOW - timedelta(seconds=1)),
    )


def command(*, key: str = "handoff-key-0001", label: str = "coordinator-demo"):
    return HumanHandoffCommand(
        call_id=CALL_ID,
        idempotency_key=key,
        coordinator_destination_label=label,
        authorized_by="demo-coordinator",
        authorized_at=NOW - timedelta(seconds=2),
        expected_call_status_updated_at=NOW - timedelta(seconds=1),
        correlation_id=CORRELATION_ID,
    )


async def test_reservation_fences_before_provider_and_replay_has_no_second_io() -> None:
    fence = InMemoryAIAuthorityFence()
    repository = InMemoryHumanHandoffRepository(
        context, allowed_destination_labels=frozenset({"coordinator-demo"})
    )
    gateway, audit = Gateway(), Audit()
    service = HumanHandoffService(
        repository,
        gateway,
        audit,
        Clock(),
        fence,
        id_generator=lambda: HANDOFF_ID,
    )

    first = await service.request_handoff(command())
    replay = await service.request_handoff(command())

    assert replay == first
    assert gateway.calls == 1
    assert audit.events == ["requested"]
    with pytest.raises(Exception, match="ai_authority_revoked"):
        await fence.ensure_commitment_allowed(CALL_ID)


async def test_readiness_returns_durable_version_and_bounded_context_without_provider_io() -> None:
    gateway = Gateway()
    repository = InMemoryHumanHandoffRepository(
        context,
        allowed_destination_labels=frozenset({"coordinator-demo"}),
        readiness_resolver=readiness,
    )
    service = HumanHandoffService(
        repository,
        gateway,
        Audit(),
        Clock(),
        InMemoryAIAuthorityFence(),
    )

    snapshot = await service.get_handoff_readiness(CALL_ID)

    assert snapshot.call_status_updated_at == NOW - timedelta(seconds=1)
    assert snapshot.context.call_status == "IN_PROGRESS"
    assert snapshot.context.mandate_version == 4
    assert gateway.calls == 0


async def test_same_key_changed_payload_conflicts_before_provider_io() -> None:
    repository = InMemoryHumanHandoffRepository(
        context, allowed_destination_labels=frozenset({"coordinator-demo", "other"})
    )
    gateway = Gateway()
    service = HumanHandoffService(
        repository,
        gateway,
        Audit(),
        Clock(),
        InMemoryAIAuthorityFence(),
        id_generator=lambda: HANDOFF_ID,
    )
    await service.request_handoff(command())
    with pytest.raises(HumanHandoffIdempotencyConflict):
        await service.request_handoff(command(label="other"))
    assert gateway.calls == 1


async def test_join_requires_accumulated_two_party_evidence_and_is_monotonic() -> None:
    repository = InMemoryHumanHandoffRepository(
        context, allowed_destination_labels=frozenset({"coordinator-demo"})
    )
    service = HumanHandoffService(
        repository,
        Gateway(),
        Audit(),
        Clock(),
        InMemoryAIAuthorityFence(),
        id_generator=lambda: HANDOFF_ID,
    )
    handoff = await service.request_handoff(command())
    remote = HumanHandoffStatusEvent(
        "a" * 64,
        HANDOFF_ID,
        CALL_ID,
        HumanHandoffStatus.CONNECTING,
        1,
        NOW + timedelta(seconds=1),
        True,
        False,
    )
    assert (await service.observe_handoff(remote)).status is HumanHandoffStatus.CONNECTING
    joined = HumanHandoffStatusEvent(
        "b" * 64,
        HANDOFF_ID,
        CALL_ID,
        HumanHandoffStatus.JOINED,
        2,
        NOW + timedelta(seconds=2),
        True,
        True,
    )
    assert (await service.observe_handoff(joined)).status is HumanHandoffStatus.JOINED
    assert await service.observe_handoff(joined) == await service.get_handoff(
        CALL_ID, handoff.handoff_id
    )
    stale_failure = HumanHandoffStatusEvent(
        "c" * 64,
        HANDOFF_ID,
        CALL_ID,
        HumanHandoffStatus.FAILED_SAFE,
        1,
        NOW + timedelta(seconds=3),
        False,
        False,
    )
    assert (await service.observe_handoff(stale_failure)).status is HumanHandoffStatus.JOINED


@pytest.mark.parametrize(
    ("failure", "expected_status", "raised_type"),
    [
        (
            HumanHandoffTimeoutError(call_id=CALL_ID),
            HumanHandoffStatus.TIMED_OUT_SAFE,
            HumanHandoffTimeoutError,
        ),
        (
            HumanHandoffProviderError(call_id=CALL_ID),
            HumanHandoffStatus.FAILED_SAFE,
            HumanHandoffProviderError,
        ),
        (
            RuntimeError("unsafe provider detail"),
            HumanHandoffStatus.FAILED_SAFE,
            HumanHandoffOutcomeUncertain,
        ),
    ],
)
async def test_provider_failures_persist_safe_terminal_state_and_keep_ai_fenced(
    failure: Exception,
    expected_status: HumanHandoffStatus,
    raised_type: type[Exception],
) -> None:
    class FailingGateway:
        async def begin_handoff(self, handoff) -> None:
            raise failure

    repository = InMemoryHumanHandoffRepository(
        context, allowed_destination_labels=frozenset({"coordinator-demo"})
    )
    fence = InMemoryAIAuthorityFence()
    service = HumanHandoffService(
        repository,
        FailingGateway(),
        Audit(),
        Clock(),
        fence,
        id_generator=lambda: HANDOFF_ID,
    )
    with pytest.raises(raised_type):
        await service.request_handoff(command())
    stored = await service.get_handoff(CALL_ID, HANDOFF_ID)
    assert stored.status is expected_status
    with pytest.raises(Exception, match="ai_authority_revoked"):
        await fence.ensure_speech_allowed(CALL_ID)
