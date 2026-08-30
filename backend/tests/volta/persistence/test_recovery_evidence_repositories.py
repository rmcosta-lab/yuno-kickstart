from __future__ import annotations

import asyncio
import base64
import json
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
from sqlalchemy.ext.asyncio import AsyncEngine
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
from yuno_backend.volta.negotiations.errors import (
    IdempotencyConflict,
    InvalidNegotiationTransition,
)
from yuno_backend.volta.negotiations.models import CommitmentDisposition
from yuno_backend.volta.persistence import SqlAlchemyOperationUnitOfWork
from yuno_backend.volta.persistence import repositories as repository_module
from yuno_backend.volta.persistence.tables import (
    _agreement_evidence,
    _audit_events,
    _call_briefs,
    _carrier_sessions,
    _commitments,
    _mandates,
    _notifications,
    _post_contact_escalations,
    _recaps,
    _recovery_attempts,
    _text_mutation_idempotency,
)
from yuno_backend.volta.recovery.commands import (
    AcknowledgeNotificationCommand,
    CreateEscalationCommand,
    ReplaceMandateCommand,
    ReplacementEvidence,
    ResumeAfterEscalationCommand,
    SimulateInboundRecoveryCommand,
)
from yuno_backend.volta.recovery.errors import OperationBlockedByEscalation, StaleOperationVersion
from yuno_backend.volta.recovery.models import (
    EscalationContext,
    RecoveryAttempt,
    RecoveryOutcome,
    RecoveryScenario,
)
from yuno_backend.volta.recovery.services import (
    AcknowledgeNotificationService,
    CreateEscalationService,
    ReplaceMandateService,
    ResumeAfterEscalationService,
    SimulateInboundRecoveryService,
)
from yuno_backend.volta.text_slice.models import AuditQuery, CreateSimulatedRecapInput

from . import conftest as persistence_conftest
from .test_negotiation_repositories import _seed_winner
from .test_repositories import FixedClock, FixedIds, _factory
from .test_text_slice import application


def _recovery_command(
    operation_id: UUID,
    version: int,
    commitment_id: UUID,
    proposed_terms: object,
    correlation_id: UUID,
    *,
    safe: bool,
) -> SimulateInboundRecoveryCommand:
    return SimulateInboundRecoveryCommand(
        operation_id,
        version,
        commitment_id,
        1,
        proposed_terms,  # type: ignore[arg-type]
        correlation_id,
        RecoveryScenario.MANDATE_SAFE if safe else RecoveryScenario.OUT_OF_MANDATE,
        "MANDATE_SAFE_REPLACEMENT" if safe else "OUT_OF_MANDATE",
        ReplacementEvidence("recovery.webm", 100, "item", "event") if safe else None,
        None
        if safe
        else EscalationContext("Over mandate", ("Keep winner",), "Review mandate"),
    )

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


@pytest.fixture
def phase24_legacy_database() -> Iterator[tuple[str, Config]]:
    configured_url = os.environ.get("TEST_DATABASE_URL")
    if not configured_url:
        pytest.skip("TEST_DATABASE_URL is required for isolated PostgreSQL tests")
    parsed = make_url(configured_url)
    if parsed.drivername != "postgresql+asyncpg" or parsed.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        pytest.skip("isolated PostgreSQL tests require asyncpg on loopback")

    database_name = f"volta_phase24_legacy_{uuid4().hex}"
    test_url = parsed.set(database=database_name)
    rendered_admin_url = persistence_conftest._render_url(parsed)
    rendered_test_url = persistence_conftest._render_url(test_url)
    asyncio.run(persistence_conftest._create_database(rendered_admin_url, database_name))
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = rendered_test_url
    config = Config(str(persistence_conftest.ROOT / "backend" / "alembic.ini"))
    try:
        command.upgrade(config, "20260830_24")
        yield rendered_test_url, config
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

        brief_command = GenerateBriefCommand(
            operation_id, commitment.call_id, 4, commitment.id,
            ("fact",), (), (), (), UUID(int=base + 103)
        )
        brief = await GenerateBriefService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 104, base + 106)]),
        ).generate(brief_command)
        assert brief.carrier_id == commitment.carrier_id
        assert brief.agreed_terms_reference == commitment.quote_id

        recap_command = GenerateRecapCommand(
            operation_id, commitment.call_id, 4, commitment.id,
            "Confirmed terms", UUID(int=base + 110)
        )
        recap = await GenerateRecapService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=value) for value in range(base + 111, base + 113)]),
        ).generate(recap_command)
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

        recovery_command = _recovery_command(
            operation_id, 4, commitment.id, proposed_terms, UUID(int=base + 1), safe=True
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
        escalate_command = _recovery_command(
            operation_id, 5, active[0].id, out_of_mandate_terms,
            UUID(int=base + 20), safe=False
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
                _recovery_command(
                    operation_id, 6, active[0].id, proposed_terms,
                    UUID(int=base + 45), safe=True
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


async def test_phase25_database_rejects_cross_call_artifacts_missing_recovery_evidence_and_kind(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 28000
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        async with factory.begin() as session:
            session_row = (
                await session.execute(
                    select(_carrier_sessions).where(
                        _carrier_sessions.c.operation_id == operation_id
                    )
                )
            ).mappings().one()
            other_call = UUID(int=base + 50)
            await session.execute(
                insert(_carrier_sessions).values(
                    call_id=other_call,
                    negotiation_id=session_row["negotiation_id"],
                    operation_id=operation_id,
                    carrier_id=UUID(int=base + 51),
                    carrier_display_label="Synthetic alternate carrier",
                    route_origin=session_row["route_origin"],
                    route_destination=session_row["route_destination"],
                    available_snapshot=True,
                    fixed_priority=2,
                    selection_rank=2,
                    channel=session_row["channel"],
                    state="ACTIVE",
                    created_at=FixedClock().now(),
                )
            )

        for table, values in (
            (
                _recaps,
                {
                    "id": UUID(int=base + 1),
                    "commitment_id": commitment.id,
                    "operation_id": operation_id,
                    "call_id": other_call,
                    "disclosure_state": "SIMULATED",
                    "content_hash": "a" * 64,
                    "rendered_content": "Synthetic recap",
                    "generated_at": FixedClock().now(),
                },
            ),
            (
                _call_briefs,
                {
                    "id": UUID(int=base + 2),
                    "commitment_id": commitment.id,
                    "operation_id": operation_id,
                    "call_id": other_call,
                    "route_origin": "A",
                    "route_destination": "B",
                    "carrier_id": commitment.carrier_id,
                    "agreed_terms_reference": commitment.quote_id,
                    "mandate_version": 1,
                    "facts": [],
                    "objections": [],
                    "changes": [],
                    "unresolved_items": [],
                    "generated_at": FixedClock().now(),
                },
            ),
        ):
            with pytest.raises(IntegrityError):
                async with factory.begin() as session:
                    await session.execute(insert(table).values(values))

        with pytest.raises(IntegrityError):
            async with factory.begin() as session:
                await session.execute(
                    insert(_recovery_attempts).values(
                        id=UUID(int=base + 3),
                        operation_id=operation_id,
                        commitment_id=commitment.id,
                        scenario="MANDATE_SAFE",
                        before_operation_version=4,
                        after_operation_version=5,
                        decision_reason="MANDATE_SAFE_REPLACEMENT",
                        outcome="REPLACED",
                        resulting_commitment_id=commitment.id,
                        resulting_evidence_id=commitment.evidence_id,
                        escalation_id=None,
                        correlation_id=UUID(int=base + 4),
                        created_at=FixedClock().now(),
                    )
                )

        async with factory.begin() as session:
            await session.execute(
                insert(_text_mutation_idempotency).values(
                    operation_name="create_simulated_recap",
                    idempotency_key="phase25-unicode-valid-snapshot",
                    fingerprint="c" * 64,
                    draft_id=None,
                    operation_id=None,
                    result_id=UUID(int=base + 6),
                    result_kind="Recap",
                    # More than 8 MiB in UTF-8 while remaining below the
                    # calculated 32 MiB maximum response envelope.
                    result_snapshot={"payload": "á" * (5 * 1024 * 1024)},
                    created_at=FixedClock().now(),
                )
            )
        with pytest.raises(IntegrityError):
            async with factory.begin() as session:
                await session.execute(
                    insert(_text_mutation_idempotency).values(
                        operation_name="create_simulated_recap",
                        idempotency_key="phase25-oversize-snapshot",
                        fingerprint="d" * 64,
                        draft_id=None,
                        operation_id=None,
                        result_id=UUID(int=base + 7),
                        result_kind="Recap",
                        result_snapshot={"payload": "x" * (32 * 1024 * 1024)},
                        created_at=FixedClock().now(),
                    )
                )

        with pytest.raises(IntegrityError):
            async with factory.begin() as session:
                await session.execute(
                    insert(_text_mutation_idempotency).values(
                        operation_name="create_simulated_recap",
                        idempotency_key="phase25-kind-invalid",
                        fingerprint="b" * 64,
                        draft_id=None,
                        operation_id=None,
                        result_id=UUID(int=base + 5),
                        result_kind="Notification",
                        result_snapshot={},
                        created_at=FixedClock().now(),
                    )
                )
    finally:
        await engine.dispose()


async def test_audit_keyset_pages_101_equal_timestamps_without_gaps(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 29000
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        await RecordEvidenceService(
            SqlAlchemyOperationUnitOfWork(factory),
            FixedClock(),
            FixedIds([UUID(int=base + 1)]),
        ).record(
            RecordEvidenceCommand(
                operation_id,
                4,
                commitment.id,
                "audit-pagination.webm",
                0,
                "item",
                "event",
                UUID(int=base + 2),
            )
        )
        inserted_ids = tuple(UUID(int=base + 100 + index) for index in range(101))
        notification_ids = tuple(UUID(int=base + 1_000 + index) for index in range(101))
        async with factory.begin() as session:
            await session.execute(
                insert(_audit_events),
                [
                    {
                        "event_id": event_id,
                        "operation_id": operation_id,
                        "operation_version": 4,
                        "actor_kind": "SYSTEM",
                        "event_type": "EVIDENCE_RECORDED",
                        "occurred_at": FixedClock().now(),
                        "correlation_id": UUID(int=base + 300 + index),
                        "metadata": {},
                    }
                    for index, event_id in enumerate(inserted_ids)
                ],
            )
            await session.execute(
                insert(_notifications),
                [
                    {
                        "id": notification_id,
                        "operation_id": operation_id,
                        "commitment_id": commitment.id,
                        "reason_code": "MANDATE_SAFE_REPLACEMENT",
                        "created_at": FixedClock().now(),
                        "operation_version": 4,
                        "recovery_before": {
                            "operation_version": 4,
                            "operation_status": "COMMITTED",
                            "active_commitment_id": None,
                            "carrier_id": None,
                            "agreed_terms": None,
                        },
                        "recovery_after": {
                            "operation_version": 4,
                            "operation_status": "COMMITTED",
                            "active_commitment_id": None,
                            "carrier_id": None,
                            "agreed_terms": None,
                        },
                        "decision_reason": "Pagination test.",
                        "message": "Pagination test notification.",
                        "correlation_id": UUID(int=base + 2_000 + index),
                        "acknowledged_by": None,
                        "acknowledged_at": None,
                    }
                    for index, notification_id in enumerate(notification_ids)
                ],
            )

        app = application(factory)
        cursor = None
        seen: list[UUID] = []
        seen_notifications: list[UUID] = []
        while True:
            page = await app.get_operation_audit(AuditQuery(operation_id, cursor, 100))
            seen.extend(event.event_id for event in page.events if event.event_id in inserted_ids)
            seen_notifications.extend(
                notification.id
                for notification in page.notifications
                if notification.id in notification_ids
            )
            if page.next_cursor is None:
                break
            cursor = page.next_cursor
        assert len(seen) == len(set(seen)) == 101
        assert set(seen) == set(inserted_ids)
        assert len(seen_notifications) == len(set(seen_notifications)) == 101
        assert set(seen_notifications) == set(notification_ids)

        missing_boundary = base64.urlsafe_b64encode(
            json.dumps(
                [FixedClock().now().isoformat(), str(UUID(int=base + 999)), "event"]
            ).encode()
        ).decode().rstrip("=")
        with pytest.raises(InvalidNegotiationTransition):
            await app.get_operation_audit(AuditQuery(operation_id, missing_boundary, 100))
    finally:
        await engine.dispose()


async def test_concurrent_f25_recap_same_key_replays_and_changed_payload_conflicts(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 30000
    try:
        operation_id, commitment = await _seed_winner(factory, base)
        command_input = CreateSimulatedRecapInput(
            commitment.call_id,
            4,
            commitment.id,
            "The carrier and coordinator confirmed the synthetic terms.",
            "phase25-concurrent-recap",
            UUID(int=base + 1),
        )
        first, second = await asyncio.gather(
            application(factory).create_simulated_recap(command_input),
            application(factory).create_simulated_recap(
                replace(command_input, correlation_id=UUID(int=base + 2))
            ),
        )
        assert first.value == second.value
        assert sorted((first.idempotency_replayed, second.idempotency_replayed)) == [
            False,
            True,
        ]

        with pytest.raises(IdempotencyConflict):
            await application(factory).create_simulated_recap(
                replace(
                    command_input,
                    rendered_content="A conflicting synthetic recap must not persist.",
                    correlation_id=UUID(int=base + 3),
                )
            )

        async with factory() as session:
            recap_count = (
                await session.execute(
                    select(func.count()).select_from(_recaps).where(
                        _recaps.c.operation_id == operation_id
                    )
                )
            ).scalar_one()
            event_count = (
                await session.execute(
                    select(func.count()).select_from(_audit_events).where(
                        _audit_events.c.operation_id == operation_id,
                        _audit_events.c.event_type == "RECAP_GENERATED",
                    )
                )
            ).scalar_one()
            idempotency_count = (
                await session.execute(
                    select(func.count()).select_from(_text_mutation_idempotency).where(
                        _text_mutation_idempotency.c.operation_name
                        == "create_simulated_recap",
                        _text_mutation_idempotency.c.idempotency_key
                        == command_input.idempotency_key,
                    )
                )
            ).scalar_one()
        assert recap_count == event_count == idempotency_count == 1
    finally:
        await engine.dispose()


async def test_f25_facade_rolls_back_mutation_and_audit_when_snapshot_write_fails(
    phase14_database_url: str,
) -> None:
    engine, factory = _factory(phase14_database_url)
    base = 32000

    class FailingTextIdempotency:
        def __init__(self, delegate: object) -> None:
            self._delegate = delegate

        async def lock(self, operation_name: str, key: str) -> None:
            await self._delegate.lock(operation_name, key)  # type: ignore[attr-defined]

        async def get(self, operation_name: str, key: str):
            return await self._delegate.get(operation_name, key)  # type: ignore[attr-defined]

        async def add(self, record: object) -> None:
            raise RuntimeError("injected snapshot write failure")

    class FailingSnapshotUow(SqlAlchemyOperationUnitOfWork):
        async def __aenter__(self):
            await super().__aenter__()
            self.text_idempotency = FailingTextIdempotency(  # type: ignore[assignment]
                self.text_idempotency
            )
            return self

    try:
        operation_id, commitment = await _seed_winner(factory, base)
        command_input = CreateSimulatedRecapInput(
            commitment.call_id,
            4,
            commitment.id,
            "Atomic rollback synthetic recap.",
            "phase25-rollback-recap",
            UUID(int=base + 1),
        )
        with pytest.raises(RuntimeError, match="injected snapshot write failure"):
            await application(
                factory,
                unit_of_work_factory=lambda: FailingSnapshotUow(factory),
            ).create_simulated_recap(command_input)

        async with factory() as session:
            assert (
                await session.execute(
                    select(func.count()).select_from(_recaps).where(
                        _recaps.c.operation_id == operation_id
                    )
                )
            ).scalar_one() == 0
            assert (
                await session.execute(
                    select(func.count()).select_from(_audit_events).where(
                        _audit_events.c.operation_id == operation_id,
                        _audit_events.c.event_type == "RECAP_GENERATED",
                    )
                )
            ).scalar_one() == 0
            assert (
                await session.execute(
                    select(func.count()).select_from(_text_mutation_idempotency).where(
                        _text_mutation_idempotency.c.idempotency_key
                        == command_input.idempotency_key
                    )
                )
            ).scalar_one() == 0

        retry = await application(factory).create_simulated_recap(command_input)
        assert not retry.idempotency_replayed
    finally:
        await engine.dispose()


def test_phase25_upgrade_refuses_legacy_recap_before_schema_or_data_change(
    phase24_legacy_database: tuple[str, Config],
) -> None:
    database_url, config = phase24_legacy_database
    base = 31000

    async def seed_and_snapshot() -> tuple[str, tuple[str, ...], tuple[object, ...]]:
        engine, factory = _factory(database_url)
        try:
            operation_id, commitment = await _seed_winner(factory, base)
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "INSERT INTO volta_recaps "
                        "(id, commitment_id, operation_id, disclosure_state, generated_at) "
                        "VALUES (:id, :commitment_id, :operation_id, 'SIMULATED', :at)"
                    ),
                    {
                        "id": UUID(int=base + 1),
                        "commitment_id": commitment.id,
                        "operation_id": operation_id,
                        "at": FixedClock().now(),
                    },
                )
            return await snapshot(engine)
        finally:
            await engine.dispose()

    async def snapshot(engine: AsyncEngine) -> tuple[str, tuple[str, ...], tuple[object, ...]]:
        async with engine.connect() as connection:
            revision = (
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar_one()
            columns = tuple(
                (
                    await connection.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema = 'public' AND table_name = 'volta_recaps' "
                            "ORDER BY ordinal_position"
                        )
                    )
                ).scalars()
            )
            row = (
                await connection.execute(
                    text(
                        "SELECT id, commitment_id, operation_id, disclosure_state, generated_at "
                        "FROM volta_recaps WHERE id = :id"
                    ),
                    {"id": UUID(int=base + 1)},
                )
            ).one()
            return revision, columns, tuple(row)

    before = asyncio.run(seed_and_snapshot())
    with pytest.raises(RuntimeError, match="phase 25 upgrade refused"):
        command.upgrade(config, "head")

    async def read_after() -> tuple[str, tuple[str, ...], tuple[object, ...]]:
        engine, _ = _factory(database_url)
        try:
            return await snapshot(engine)
        finally:
            await engine.dispose()

    after = asyncio.run(read_after())
    assert before == after
    assert before[0] == "20260830_24"
    assert "rendered_content" not in before[1]


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
                    _recovery_command(
                        operation_id, 4, commitment.id, proposed_terms,
                        UUID(int=base + offset + 20), safe=True
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
            _recovery_command(
                operation_id, 4, commitment.id,
                replace(commitment.agreed_terms, amount=Decimal("900")),
                UUID(int=base + 109), safe=True
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


def test_phase25_downgrade_rejects_incompatible_durable_data_before_ddl(
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
    command.downgrade(alembic_config, "20260830_25")
    with pytest.raises(RuntimeError, match="phase 25 downgrade refused"):
        command.downgrade(alembic_config, "-1")
    assert asyncio.run(current_revision()) == "20260830_25"
