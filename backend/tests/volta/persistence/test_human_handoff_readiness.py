import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
import pytest
from alembic import command as alembic_command
from alembic.config import Config
from sqlalchemy import func, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from yuno_backend.integrations.twilio import (
    SqlAlchemyTwilioExistingCallResolver,
    SqlAlchemyTwilioHandoffBindingStore,
    TwilioDestinationAllowlist,
    TwilioHandoffStatusCallback,
    TwilioHumanHandoffConfig,
    TwilioHumanHandoffGateway,
)
from yuno_backend.volta.persistence import SqlAlchemyOutboundCallAttemptStore
from yuno_backend.volta.persistence.handoffs import (
    SqlAlchemyHumanHandoffRepository,
    _readiness_operation_statement,
)
from yuno_backend.volta.persistence.tables import _audit_events
from yuno_backend.volta.telephony import (
    HumanHandoff,
    HumanHandoffAuthorityError,
    HumanHandoffCommand,
    HumanHandoffStatus,
    HumanHandoffStatusEvent,
    OutboundCall,
    OutboundCallAttempt,
    OutboundCallAttemptState,
    OutboundCallStatus,
)
from yuno_backend.volta.text_slice import CreateCallBriefInput

from . import conftest as persistence_conftest
from .test_negotiation_repositories import _seed_winner
from .test_text_slice import application


def test_readiness_sql_labels_operation_and_mandate_versions_explicitly() -> None:
    compiled = str(_readiness_operation_statement(uuid4()).compile(dialect=postgresql.dialect()))

    assert "volta_operations.version AS operation_version" in compiled
    assert "volta_mandates.version AS mandate_version" in compiled


def test_readiness_projection_keeps_mandate_and_audit_operation_versions_distinct() -> None:
    call_id, operation_id = uuid4(), uuid4()
    now = datetime(2026, 8, 30, 15, tzinfo=UTC)

    readiness, projected_operation_id, audit_operation_version = (
        SqlAlchemyHumanHandoffRepository._project_readiness(
            call_id,
            {"status_updated_at": now, "call_status": "IN_PROGRESS"},
            {
                "operation_id": operation_id,
                "operation_version": 9,
                "mandate_version": 3,
                "route_origin": "Synthetic origin",
                "route_destination": "Synthetic destination",
                "cargo_label": "Synthetic cargo",
                "maximum_amount": Decimal("1250.00"),
                "currency": "MXN",
                "pickup_window_start_date": date(2026, 9, 1),
                "pickup_window_end_date": date(2026, 9, 2),
            },
            {
                "facts": ("Fact",),
                "objections": (),
                "changes": (),
                "unresolved_items": (),
            },
            (
                {
                    "carrier_priority": 1,
                    "amount": Decimal("1000.00"),
                    "currency": "MXN",
                },
            ),
        )
    )

    assert readiness.context.mandate_version == 3
    assert projected_operation_id == operation_id
    assert audit_operation_version == 9


class _FailingFence:
    async def fence(self, call_id: UUID, handoff_id: UUID, *, fenced_at: datetime) -> None:
        del call_id, handoff_id, fenced_at
        raise RuntimeError("synthetic fence failure")

    async def ensure_speech_allowed(self, call_id: UUID) -> None:
        del call_id

    async def ensure_commitment_allowed(self, call_id: UUID) -> None:
        del call_id


@pytest.mark.asyncio
async def test_handoff_round_trip_rollback_replay_join_and_audit_survive_restart(
    isolated_database_url: str,
) -> None:
    engine = create_async_engine(isolated_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 9, 3, 12, tzinfo=UTC)
    operation_id, commitment = await _seed_winner(factory, 128000)
    try:
        await application(factory).create_call_brief(
            CreateCallBriefInput(
                commitment.call_id,
                4,
                ("Synthetic terms confirmed",),
                (),
                (),
                (),
                "brief-handoff-0001",
                UUID(int=128100),
            )
        )
        attempt = OutboundCallAttempt(
            operation_id=operation_id,
            idempotency_key="outbound-handoff-0001",
            request_fingerprint="a" * 64,
            state=OutboundCallAttemptState.PENDING,
            result=None,
            uncertainty=None,
            failure=None,
            created_at=now,
            updated_at=now,
        )
        call_store = SqlAlchemyOutboundCallAttemptStore(factory)
        await call_store.reserve(attempt)
        call = OutboundCall(
            call_session_id=commitment.call_id,
            provider_call_id=f"CA{uuid4().hex}",
            status=OutboundCallStatus.IN_PROGRESS,
            created_at=now,
            status_updated_at=now + timedelta(seconds=1),
            last_status_event_id="call-live-1",
            last_status_sequence_number=1,
            processed_status_event_ids=("call-live-1",),
        )
        await call_store.complete(
            attempt.idempotency_key,
            attempt.request_fingerprint,
            call,
            now + timedelta(seconds=1),
        )

        repository = SqlAlchemyHumanHandoffRepository(
            factory, allowed_destination_labels=frozenset({"coordinator-1"})
        )
        readiness = await repository.get_readiness(call.call_session_id)
        assert readiness is not None
        command = HumanHandoffCommand(
            call.call_session_id,
            "handoff-postgres-0001",
            "coordinator-1",
            "synthetic-operator",
            now + timedelta(seconds=1),
            readiness.call_status_updated_at,
            UUID(int=128101),
        )
        proposed = HumanHandoff(
            UUID(int=128102),
            call.call_session_id,
            command.coordinator_destination_label,
            command.idempotency_key,
            "b" * 64,
            HumanHandoffStatus.CONNECTING,
            now + timedelta(seconds=2),
            now + timedelta(seconds=2),
            readiness.context,
        )

        with pytest.raises(RuntimeError, match="synthetic fence failure"):
            await repository.reserve(command, proposed, _FailingFence(), repository)
        assert await repository.get(call.call_session_id, proposed.handoff_id) is None
        await repository.ensure_speech_allowed(call.call_session_id)

        reserved = await repository.reserve(command, proposed, repository, repository)
        assert reserved.created and reserved.handoff.context == readiness.context

        account_sid = "AC" + "4" * 32
        conference_sid = "CF" + "5" * 32
        coordinator_sid = "CA" + "6" * 32
        gateway: TwilioHumanHandoffGateway

        async def provider(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("Participants.json"):
                remote_join = await gateway.map_status_callback(
                    TwilioHandoffStatusCallback(
                        "7" * 64,
                        account_sid,
                        call.provider_call_id,
                        conference_sid,
                        "participant-join",
                        1,
                        now + timedelta(seconds=3),
                    )
                )
                assert remote_join.remote_participant_present
                return httpx.Response(
                    201,
                    json={
                        "call_sid": coordinator_sid,
                        "conference_sid": conference_sid,
                    },
                )
            return httpx.Response(200)

        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            gateway = TwilioHumanHandoffGateway(
                client,
                TwilioHumanHandoffConfig(
                    account_sid=account_sid,
                    api_key_sid="SK" + "8" * 32,
                    api_key_secret="synthetic-secret",
                    coordinator_caller_id_e164="+15555550101",
                    status_callback_url=(
                        "https://demo.example.com/v1/telephony/twilio/handoff-status"
                    ),
                ),
                TwilioDestinationAllowlist({"coordinator-1": "+15555550102"}),
                SqlAlchemyTwilioExistingCallResolver(factory),
                SqlAlchemyTwilioHandoffBindingStore(factory),
            )
            await gateway.begin_handoff(reserved.handoff)
            joined_binding = await gateway.map_status_callback(
                TwilioHandoffStatusCallback(
                    "9" * 64,
                    account_sid,
                    coordinator_sid,
                    conference_sid,
                    "participant-join",
                    2,
                    now + timedelta(seconds=4),
                )
            )
        assert joined_binding.status is HumanHandoffStatus.JOINED
    finally:
        await engine.dispose()

    restarted_engine = create_async_engine(isolated_database_url, hide_parameters=True)
    restarted_factory = async_sessionmaker(restarted_engine, expire_on_commit=False)
    try:
        restarted = SqlAlchemyHumanHandoffRepository(
            restarted_factory,
            allowed_destination_labels=frozenset({"coordinator-1"}),
        )
        replay = await restarted.reserve(command, proposed, restarted, restarted)
        assert not replay.created and replay.handoff == reserved.handoff
        event = HumanHandoffStatusEvent(
            "handoff-joined-1",
            proposed.handoff_id,
            call.call_session_id,
            HumanHandoffStatus.JOINED,
            1,
            now + timedelta(seconds=3),
            True,
            True,
        )
        joined = await restarted.observe(event, restarted)
        assert joined is not None and joined.status is HumanHandoffStatus.JOINED
        assert await restarted.observe(event, restarted) == joined
        with pytest.raises(HumanHandoffAuthorityError):
            await restarted.ensure_commitment_allowed(call.call_session_id)

        async with restarted_factory() as session:
            audit_counts = dict(
                (
                    await session.execute(
                        select(_audit_events.c.event_type, func.count())
                        .where(
                            _audit_events.c.operation_id == operation_id,
                            _audit_events.c.event_type.in_(("HANDOFF_REQUESTED", "HANDOFF_JOINED")),
                        )
                        .group_by(_audit_events.c.event_type)
                    )
                ).all()
            )
        assert audit_counts == {"HANDOFF_REQUESTED": 1, "HANDOFF_JOINED": 1}

        alembic_config = Config(str(persistence_conftest.ROOT / "backend" / "alembic.ini"))
        with pytest.raises(RuntimeError, match="phase 28 downgrade refused"):
            await asyncio.to_thread(alembic_command.downgrade, alembic_config, "-1")
        async with restarted_factory() as session:
            migration_revision = (
                await session.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar_one()
        assert migration_revision == "20260830_28"
    finally:
        await restarted_engine.dispose()
