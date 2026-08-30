from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from yuno_backend.volta.evidence.commands import (
    GenerateBriefCommand,
    GenerateRecapCommand,
    RecordEvidenceCommand,
)
from yuno_backend.volta.evidence.models import RecapDisclosureState
from yuno_backend.volta.evidence.services import (
    GenerateBriefService,
    GenerateRecapService,
    RecordEvidenceService,
)
from yuno_backend.volta.mandates.models import Money
from yuno_backend.volta.mandates.services import MandatePolicy
from yuno_backend.volta.negotiations.models import CommitmentDisposition
from yuno_backend.volta.persistence import SqlAlchemyOperationUnitOfWork
from yuno_backend.volta.persistence import repositories as repository_module
from yuno_backend.volta.persistence.tables import (
    _agreement_evidence,
    _audit_events,
    _commitments,
    _mandates,
    _notifications,
    _post_contact_escalations,
)
from yuno_backend.volta.recovery.commands import (
    AcknowledgeNotificationCommand,
    CreateEscalationCommand,
    ReplaceMandateCommand,
    ResumeAfterEscalationCommand,
    SimulateInboundRecoveryCommand,
)
from yuno_backend.volta.recovery.errors import OperationBlockedByEscalation, StaleOperationVersion
from yuno_backend.volta.recovery.models import RecoveryAttempt, RecoveryOutcome
from yuno_backend.volta.recovery.services import (
    AcknowledgeNotificationService,
    CreateEscalationService,
    ReplaceMandateService,
    ResumeAfterEscalationService,
    SimulateInboundRecoveryService,
)

from . import conftest as persistence_conftest
from .test_negotiation_repositories import _seed_winner
from .test_repositories import FixedClock, FixedIds, _factory

# This module exercises real evidence/recovery services and therefore leaves durable
# rows in `volta_audit_events`, which is append-only by trigger (Fase 06) and cannot be
# cleaned up afterwards. The shared, session-scoped `isolated_database_url` fixture in
# `conftest.py` fully downgrades to base at teardown, and this migration's downgrade
# reverts `ck_volta_audit_events_metadata_schema` to Fase 08's stricter allowlist form
# (mirroring how Fase 08 reverted Fase 06's constraint) -- a form that cannot be
# satisfied by already-persisted Fase 14 event types. Using a private, module-scoped
# database that is dropped outright (never downgraded) avoids that irreversibility
# entirely while still exercising the exact same migrated schema.


@pytest.fixture(scope="module")
def phase14_database_url() -> Iterator[str]:
    configured_url = os.environ.get("TEST_DATABASE_URL")
    if not configured_url:
        pytest.skip("TEST_DATABASE_URL is required for isolated PostgreSQL tests")
    parsed = make_url(configured_url)
    if parsed.drivername != "postgresql+asyncpg":
        pytest.skip("isolated PostgreSQL URL must use asyncpg")
    if parsed.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.skip("isolated PostgreSQL tests require an explicit loopback host")

    database_name = f"volta_phase14_{uuid4().hex}"
    test_url = parsed.set(database=database_name)
    rendered_admin_url = persistence_conftest._render_url(parsed)
    rendered_test_url = persistence_conftest._render_url(test_url)
    asyncio.run(persistence_conftest._create_database(rendered_admin_url, database_name))

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = rendered_test_url
    alembic_config = Config(str(persistence_conftest.ROOT / "backend" / "alembic.ini"))
    try:
        command.upgrade(alembic_config, "head")
        yield rendered_test_url
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        asyncio.run(persistence_conftest._drop_database(rendered_admin_url, database_name))


async def test_evidence_brief_recap_round_trip_and_are_idempotent(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 20000
    try:
        operation_id, commitment = await _seed_winner(factory, base)

        record_command = RecordEvidenceCommand(
            operation_id,
            4,
            commitment.id,
            "recordings/synthetic/one.bin",
            1500,
            "item-1",
            "event-1",
            UUID(int=base + 100),
        )
        evidence = await RecordEvidenceService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 101, base + 103)]),
        ).record(record_command)
        replay = await RecordEvidenceService(
            SqlAlchemyOperationUnitOfWork(factory), FixedClock(), FixedIds([])
        ).record(replace(record_command, correlation_id=UUID(int=base + 102)))
        assert replay == evidence

        brief_command = GenerateBriefCommand(operation_id, 4, commitment.id, UUID(int=base + 103))
        brief = await GenerateBriefService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 104, base + 106)]),
        ).generate(brief_command)
        brief_replay = await GenerateBriefService(
            SqlAlchemyOperationUnitOfWork(factory), FixedClock(), FixedIds([])
        ).generate(replace(brief_command, correlation_id=UUID(int=base + 105)))
        assert brief_replay == brief
        assert brief.carrier_id == commitment.carrier_id
        assert brief.agreed_terms_reference == commitment.quote_id

        recap_command = GenerateRecapCommand(operation_id, 4, commitment.id, UUID(int=base + 110))
        recap = await GenerateRecapService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 111, base + 113)]),
        ).generate(recap_command)
        recap_replay = await GenerateRecapService(
            SqlAlchemyOperationUnitOfWork(factory), FixedClock(), FixedIds([])
        ).generate(replace(recap_command, correlation_id=UUID(int=base + 114)))
        assert recap_replay == recap
        assert recap.disclosure_state is RecapDisclosureState.SIMULATED

        async with factory() as session:
            reloaded_evidence = await repository_module.SqlAlchemyEvidenceRepository(
                session
            ).get_by_commitment(commitment.id)
            reloaded_brief = await repository_module.SqlAlchemyBriefRepository(
                session
            ).get_by_commitment(commitment.id)
            reloaded_recap = await repository_module.SqlAlchemyRecapRepository(
                session
            ).get_by_commitment(commitment.id)
        assert reloaded_evidence == evidence
        assert reloaded_brief == brief
        assert reloaded_recap == recap
    finally:
        await engine.dispose()


async def test_second_evidence_row_for_same_commitment_is_rejected_by_constraint(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 21000
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        await RecordEvidenceService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 1, base + 3)]),
        ).record(
            RecordEvidenceCommand(
                operation_id,
                4,
                commitment.id,
                "recordings/a.bin",
                0,
                "item",
                "event",
                UUID(int=base + 2),
            )
        )
        async with factory.begin() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    insert(_agreement_evidence).values(
                        id=UUID(int=base + 3),
                        commitment_id=commitment.id,
                        recording_reference="recordings/b.bin",
                        audio_start_ms=0,
                        item_id="item2",
                        event_id="event2",
                        created_at=FixedClock().now(),
                    )
                )
        async with factory.begin() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    insert(_agreement_evidence).values(
                        id=UUID(int=base + 4),
                        commitment_id=UUID(int=base + 5),
                        recording_reference="recordings/c.bin",
                        audio_start_ms=0,
                        item_id="item3",
                        event_id="event3",
                        created_at=FixedClock().now(),
                    )
                )
    finally:
        await engine.dispose()


async def test_second_unresolved_escalation_for_same_operation_is_rejected(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 23000
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        async with factory.begin() as session:
            await session.execute(
                insert(_post_contact_escalations).values(
                    id=UUID(int=base + 1),
                    operation_id=operation_id,
                    commitment_id=commitment.id,
                    reason_code="OUT_OF_MANDATE",
                    operation_version=4,
                    mandate_version=1,
                    resolved=False,
                    correlation_id=UUID(int=base + 2),
                    created_at=FixedClock().now(),
                    resolved_at=None,
                )
            )
        async with factory.begin() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    insert(_post_contact_escalations).values(
                        id=UUID(int=base + 3),
                        operation_id=operation_id,
                        commitment_id=commitment.id,
                        reason_code="OUT_OF_MANDATE",
                        operation_version=4,
                        mandate_version=1,
                        resolved=False,
                        correlation_id=UUID(int=base + 4),
                        created_at=FixedClock().now(),
                        resolved_at=None,
                    )
                )
    finally:
        await engine.dispose()


async def test_phase24_constraints_reject_unsafe_context_and_partial_acknowledgement(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 23500
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        async with factory.begin() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    insert(_post_contact_escalations).values(
                        id=UUID(int=base + 1),
                        operation_id=operation_id,
                        commitment_id=commitment.id,
                        call_id=commitment.call_id,
                        reason_code="EXPLICIT_COORDINATOR_ESCALATION",
                        operation_version=4,
                        mandate_version=1,
                        resolved=False,
                        correlation_id=UUID(int=base + 2),
                        created_at=FixedClock().now(),
                        resolved_at=None,
                        conflict="x" * 501,
                        attempted_alternatives=[],
                        recommended_action="review",
                    )
                )
        async with factory.begin() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    insert(_post_contact_escalations).values(
                        id=UUID(int=base + 8),
                        operation_id=operation_id,
                        commitment_id=commitment.id,
                        call_id=commitment.call_id,
                        reason_code="EXPLICIT_COORDINATOR_ESCALATION",
                        operation_version=4,
                        mandate_version=1,
                        resolved=False,
                        correlation_id=UUID(int=base + 9),
                        created_at=FixedClock().now(),
                        resolved_at=None,
                        conflict="Valid conflict.",
                        attempted_alternatives=[""],
                        recommended_action="Review.",
                    )
                )
        async with factory.begin() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    insert(_post_contact_escalations).values(
                        id=UUID(int=base + 10),
                        operation_id=operation_id,
                        commitment_id=commitment.id,
                        call_id=commitment.call_id,
                        reason_code="EXPLICIT_COORDINATOR_ESCALATION",
                        operation_version=4,
                        mandate_version=1,
                        resolved=False,
                        correlation_id=UUID(int=base + 11),
                        created_at=FixedClock().now(),
                        resolved_at=None,
                        conflict="Valid conflict.",
                        attempted_alternatives=["x" * 501],
                        recommended_action="Review.",
                    )
                )
        async with factory.begin() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    insert(_post_contact_escalations).values(
                        id=UUID(int=base + 4),
                        operation_id=operation_id,
                        commitment_id=commitment.id,
                        call_id=commitment.call_id,
                        reason_code="EXPLICIT_COORDINATOR_ESCALATION",
                        operation_version=4,
                        mandate_version=1,
                        resolved=False,
                        correlation_id=UUID(int=base + 5),
                        created_at=FixedClock().now(),
                        resolved_at=None,
                        conflict=None,
                        attempted_alternatives=None,
                        recommended_action=None,
                    )
                )
        async with factory.begin() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    insert(_post_contact_escalations).values(
                        id=UUID(int=base + 6),
                        operation_id=operation_id,
                        commitment_id=commitment.id,
                        call_id=None,
                        reason_code="EXPLICIT_COORDINATOR_ESCALATION",
                        operation_version=4,
                        mandate_version=1,
                        resolved=False,
                        correlation_id=UUID(int=base + 7),
                        created_at=FixedClock().now(),
                        resolved_at=None,
                        conflict="Conflict.",
                        attempted_alternatives=[],
                        recommended_action="Review.",
                    )
                )
        async with factory.begin() as session:
            with pytest.raises(IntegrityError):
                await session.execute(
                    insert(_notifications).values(
                        id=UUID(int=base + 3),
                        operation_id=operation_id,
                        commitment_id=commitment.id,
                        reason_code="MANDATE_SAFE_REPLACEMENT",
                        created_at=FixedClock().now(),
                        acknowledged_by="coordinator",
                        acknowledged_at=None,
                    )
                )
    finally:
        await engine.dispose()


async def test_mandate_safe_replacement_round_trips_and_out_of_mandate_escalation_blocks(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 22000
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        proposed_terms = replace(commitment.agreed_terms, amount=Decimal("900"))

        recovery_command = SimulateInboundRecoveryCommand(
            operation_id, 4, commitment.id, 1, proposed_terms, UUID(int=base + 1)
        )
        attempt = await SimulateInboundRecoveryService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 10, base + 19)]),
        ).simulate(recovery_command)
        assert attempt.outcome is RecoveryOutcome.REPLACED

        async with factory() as session:
            history = await repository_module.SqlAlchemyCommitmentRepository(
                session
            ).list_by_operation(operation_id)
            notifications = await repository_module.SqlAlchemyNotificationRepository(
                session
            ).list_by_operation(operation_id)
        assert len(history) == 2
        active = [item for item in history if item.disposition is CommitmentDisposition.ACTIVE]
        assert len(active) == 1
        assert active[0].id == attempt.resulting_commitment_id
        assert len(notifications) == 1

        out_of_mandate_terms = replace(proposed_terms, amount=Decimal("999999"))
        escalate_command = SimulateInboundRecoveryCommand(
            operation_id, 5, active[0].id, 1, out_of_mandate_terms, UUID(int=base + 20)
        )
        escalated = await SimulateInboundRecoveryService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 30, base + 34)]),
        ).simulate(escalate_command)
        assert escalated.outcome is RecoveryOutcome.ESCALATED

        with pytest.raises(OperationBlockedByEscalation):
            await SimulateInboundRecoveryService(
                SqlAlchemyOperationUnitOfWork(factory),
                MandatePolicy(),
                FixedClock(),
                FixedIds([UUID(int=value) for value in range(base + 40, base + 44)]),
            ).simulate(
                SimulateInboundRecoveryCommand(
                    operation_id, 6, active[0].id, 1, proposed_terms, UUID(int=base + 45)
                )
            )

        resolved = await ResumeAfterEscalationService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 50, base + 52)]),
        ).resume(
            ResumeAfterEscalationCommand(
                operation_id, 6, escalated.escalation_id, 2, UUID(int=base + 51)
            )
        )
        assert resolved.resolved is True

        async with factory() as session:
            unresolved = (
                await session.execute(
                    select(_post_contact_escalations.c.id).where(
                        _post_contact_escalations.c.operation_id == operation_id,
                        _post_contact_escalations.c.resolved.is_(False),
                    )
                )
            ).first()
        assert unresolved is None
    finally:
        await engine.dispose()


async def test_concurrent_recovery_replacement_attempts_leave_exactly_one_active_winner(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 24000
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        proposed_terms = replace(commitment.agreed_terms, amount=Decimal("900"))

        async def attempt(offset: int) -> RecoveryAttempt | Exception:
            try:
                return await SimulateInboundRecoveryService(
                    SqlAlchemyOperationUnitOfWork(factory),
                    MandatePolicy(),
                    FixedClock(),
                    FixedIds(
                        [UUID(int=value) for value in range(base + offset, base + offset + 9)]
                    ),
                ).simulate(
                    SimulateInboundRecoveryCommand(
                        operation_id,
                        4,
                        commitment.id,
                        1,
                        proposed_terms,
                        UUID(int=base + offset + 20),
                    )
                )
            except Exception as error:
                return error

        results = await asyncio.gather(attempt(100), attempt(200))
        assert sum(isinstance(result, RecoveryAttempt) for result in results) == 1
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
            history = await repository_module.SqlAlchemyCommitmentRepository(
                session
            ).list_by_operation(operation_id)
        assert active_count == 1
        assert len(history) == 2
        winner = next(result for result in results if isinstance(result, RecoveryAttempt))
        active = [item for item in history if item.disposition is CommitmentDisposition.ACTIVE]
        assert active[0].id == winner.resulting_commitment_id
    finally:
        await engine.dispose()


async def test_phase24_recovery_services_round_trip_immutable_state(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 25000
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        escalation = await CreateEscalationService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 100, base + 103)]),
        ).create(
            CreateEscalationCommand(
                commitment.call_id,
                4,
                "Carrier rejected the current pickup window.",
                ("Requested a later slot.",),
                "Approve a revised mandate.",
                UUID(int=base + 103),
            )
        )
        assert escalation.context is not None

        async with SqlAlchemyOperationUnitOfWork(factory) as uow:
            current = await uow.operations.get(operation_id)
        assert current is not None
        replaced = await ReplaceMandateService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 110, base + 114)]),
        ).replace(
            ReplaceMandateCommand(
                operation_id,
                5,
                escalation.id,
                Money(Decimal("2000"), "MXN"),
                current.mandate.pickup_window,
                current.mandate.allowed_conditions,
                current.mandate.escalation_conditions,
                "synthetic-coordinator",
                UUID(int=base + 114),
            )
        )
        assert replaced.mandate.version == 2
        async with factory() as session:
            mandate_count = (
                await session.execute(
                    select(func.count()).select_from(_mandates).where(
                        _mandates.c.operation_id == operation_id
                    )
                )
            ).scalar_one()
            stored_escalation = await repository_module.SqlAlchemyPostContactEscalationRepository(
                session
            ).get(escalation.id)
        assert mandate_count == 2
        assert stored_escalation is not None and stored_escalation.resolved
        assert stored_escalation.context == escalation.context
    finally:
        await engine.dispose()


async def test_phase24_notification_acknowledgement_round_trip_and_replay(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 26000
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        attempt = await SimulateInboundRecoveryService(
            SqlAlchemyOperationUnitOfWork(factory),
            MandatePolicy(),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 100, base + 109)]),
        ).simulate(
            SimulateInboundRecoveryCommand(
                operation_id,
                4,
                commitment.id,
                1,
                replace(commitment.agreed_terms, amount=Decimal("900")),
                UUID(int=base + 109),
            )
        )
        async with factory() as session:
            notification = (
                await repository_module.SqlAlchemyNotificationRepository(
                    session
                ).list_by_operation(operation_id)
            )[0]
        command = AcknowledgeNotificationCommand(
            notification.id, 5, "synthetic-coordinator", UUID(int=base + 120)
        )
        acknowledged = await AcknowledgeNotificationService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=base + 121), UUID(int=base + 122)]),
        ).acknowledge(command)
        replay = await AcknowledgeNotificationService(
            SqlAlchemyOperationUnitOfWork(factory), FixedClock(), FixedIds([])
        ).acknowledge(command)
        assert attempt.resulting_commitment_id == acknowledged.commitment_id
        assert replay == acknowledged
        assert acknowledged.operation_version == notification.operation_version == 5
        async with factory() as session:
            audit_count = (
                await session.execute(
                    select(func.count()).select_from(_audit_events).where(
                        _audit_events.c.operation_id == operation_id,
                        _audit_events.c.event_type == "NOTIFICATION_ACKNOWLEDGED",
                    )
                )
            ).scalar_one()
            stored = await repository_module.SqlAlchemyNotificationRepository(session).get(
                notification.id
            )
        assert audit_count == 1
        assert stored == acknowledged
        assert stored.operation_version == 5
    finally:
        await engine.dispose()


def test_phase24_downgrade_rejects_incompatible_durable_data_before_ddl(
    phase14_database_url: str,
) -> None:
    base = 27000
    async def seed_explicit_escalation() -> UUID:
        engine, factory = _factory(phase14_database_url)
        operation_id, commitment = await _seed_winner(factory, base)
        await CreateEscalationService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds(
                [
                    UUID(int=base + 100),
                    UUID(int=base + 101),
                    UUID(int=base + 102),
                ]
            ),
        ).create(
            CreateEscalationCommand(
                commitment.call_id,
                4,
                "Carrier needs a coordinator decision.",
                (),
                "Review the mandate.",
                UUID(int=base + 103),
            )
        )
        await engine.dispose()
        return operation_id

    async def current_revision() -> str:
        engine, _ = _factory(phase14_database_url)
        try:
            async with engine.connect() as connection:
                return (
                    await connection.execute(text("SELECT version_num FROM alembic_version"))
                ).scalar_one()
        finally:
            await engine.dispose()

    asyncio.run(seed_explicit_escalation())
    alembic_config = Config(str(persistence_conftest.ROOT / "backend" / "alembic.ini"))
    with pytest.raises(RuntimeError, match="reconcile data"):
        command.downgrade(alembic_config, "-1")
    assert asyncio.run(current_revision()) == "20260830_24"
