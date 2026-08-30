from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from yuno_backend.volta.evidence.commands import RecordEvidenceCommand
from yuno_backend.volta.evidence.services import RecordEvidenceService
from yuno_backend.volta.negotiations import (
    IdempotencyConflict,
    QuoteEligibility,
    StaleOperationVersion,
)
from yuno_backend.volta.negotiations.models import QuoteTerms
from yuno_backend.volta.persistence import SqlAlchemyOperationUnitOfWork
from yuno_backend.volta.recovery.commands import ReplacementEvidence
from yuno_backend.volta.recovery.fixtures import (
    DeterministicRecoveryFixtureCatalog,
    RecoveryFixture,
)
from yuno_backend.volta.recovery.models import (
    EscalationContext,
    RecoveryScenario,
)
from yuno_backend.volta.text_slice import (
    AcknowledgeNotificationInput,
    ApproveOperationInput,
    AttachCommitmentEvidenceInput,
    BrowserChannel,
    CommitmentEvidenceNotFound,
    CreateCallBriefInput,
    CreateCommitmentInput,
    CreateEscalationInput,
    CreateOperationDraftInput,
    CreateSimulatedRecapInput,
    EvidenceArtifactUnavailable,
    EvidenceReservationNotFound,
    RecordQuoteInput,
    ReplaceMandateInput,
    StartInboundRecoveryInput,
    StartNegotiationInput,
    TextNegotiationApplication,
    create_demo_carrier_catalog,
    create_demo_evidence_storage,
    create_demo_text_extractor,
)
from yuno_backend.volta.text_slice.models import EscalationResolutionState

from .test_negotiation_repositories import _seed_winner

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)
CANONICAL_PROMPT = (
    "Find ground transport for Thursday from the port of Manzanillo to our warehouse "
    "in Guadalajara for at most MXN 9,000. One 40-foot dry container, standard handling."
)


class Clock:
    def now(self) -> datetime:
        return NOW


class Ids:
    def new_id(self) -> UUID:
        return uuid4()


def application(
    factory: async_sessionmaker[AsyncSession],
    *,
    ids: Ids | None = None,
    evidence_dir: Path | None = None,
    recovery_catalog: DeterministicRecoveryFixtureCatalog | None = None,
    unit_of_work_factory: Callable[[], SqlAlchemyOperationUnitOfWork] | None = None,
) -> TextNegotiationApplication:
    return TextNegotiationApplication(
        unit_of_work_factory=(
            (lambda: SqlAlchemyOperationUnitOfWork(factory))
            if unit_of_work_factory is None
            else unit_of_work_factory
        ),
        extractor=create_demo_text_extractor(),
        carrier_catalog=create_demo_carrier_catalog(),
        clock=Clock(),
        id_generator=ids or Ids(),
        evidence_storage=create_demo_evidence_storage(evidence_dir),
        recovery_fixture_catalog=recovery_catalog,
        extraction_policy_version="volta-text-v1",
    )


async def artifact_count(path: Path) -> int:
    return await asyncio.to_thread(lambda: len(tuple(path.rglob("*.wav"))))


async def test_phase25_facade_persists_exact_replay_and_complete_recovery(
    isolated_database_url: str,
    tmp_path: Path,
) -> None:
    engine = create_async_engine(isolated_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        operation_id, commitment = await _seed_winner(factory, 101000)
        await RecordEvidenceService(
            SqlAlchemyOperationUnitOfWork(factory), Clock(), Ids()
        ).record(
            RecordEvidenceCommand(
                operation_id,
                4,
                commitment.id,
                "original.webm",
                50,
                "original-item",
                "original-event",
                UUID(int=101100),
            )
        )
        storage = create_demo_evidence_storage(tmp_path)
        reference = await storage.store(
            UUID(int=101101), b"RIFF\x00\x00\x00\x00WAVErecovery-evidence"
        )
        safe_terms = replace(commitment.agreed_terms, amount=Decimal("900"))
        bad_terms = replace(commitment.agreed_terms, amount=Decimal("999999"))
        catalog = DeterministicRecoveryFixtureCatalog(
            (
                RecoveryFixture(
                    RecoveryScenario.MANDATE_SAFE,
                    safe_terms,
                    "MANDATE_SAFE_REPLACEMENT",
                    ReplacementEvidence(reference, 250, "safe-item", "safe-event"),
                    None,
                ),
                RecoveryFixture(
                    RecoveryScenario.OUT_OF_MANDATE,
                    bad_terms,
                    "OUT_OF_MANDATE",
                    None,
                    EscalationContext(
                        "Replacement exceeds mandate.",
                        ("Keep active commitment",),
                        "Review the mandate.",
                    ),
                ),
            )
        )
        app = application(factory, evidence_dir=tmp_path, recovery_catalog=catalog)

        recap_input = CreateSimulatedRecapInput(
            commitment.call_id,
            4,
            commitment.id,
            "Confirmed terms\nSimulated recap",
            "recap-phase25-0001",
            UUID(int=101102),
        )
        recap = await app.create_simulated_recap(recap_input)
        recap_replay = await application(
            factory, evidence_dir=tmp_path, recovery_catalog=catalog
        ).create_simulated_recap(replace(recap_input, correlation_id=UUID(int=101103)))
        assert recap_replay.idempotency_replayed and recap_replay.value == recap.value

        brief_input = CreateCallBriefInput(
            commitment.call_id,
            4,
            ("Terms reconfirmed",),
            (),
            ("Rate reduced",),
            (),
            "brief-phase25-0001",
            UUID(int=101104),
        )
        brief = await app.create_call_brief(brief_input)
        brief_replay = await app.create_call_brief(
            replace(brief_input, correlation_id=UUID(int=101105))
        )
        assert brief_replay.idempotency_replayed and brief_replay.value == brief.value

        safe_input = StartInboundRecoveryInput(
            operation_id,
            4,
            RecoveryScenario.MANDATE_SAFE,
            commitment.id,
            "recovery-phase25-0001",
            UUID(int=101106),
        )
        safe = await app.start_inbound_simulation(safe_input)
        assert safe.value.active_commitment is not None
        await storage.delete(reference)
        safe_replay = await application(
            factory, evidence_dir=tmp_path, recovery_catalog=catalog
        ).start_inbound_simulation(replace(safe_input, correlation_id=UUID(int=101107)))
        assert safe_replay.idempotency_replayed and safe_replay.value == safe.value

        bad_input = StartInboundRecoveryInput(
            operation_id,
            5,
            RecoveryScenario.OUT_OF_MANDATE,
            safe.value.active_commitment.commitment.id,
            "recovery-phase25-0002",
            UUID(int=101108),
        )
        bad = await app.start_inbound_simulation(bad_input)
        assert bad.value.escalation is not None
        projection_after_bad = await app.get_operation(operation_id)
        assert projection_after_bad.open_escalation == bad.value.escalation
        assert len(projection_after_bad.notifications) == 1

        mandate = projection_after_bad.operation.mandate
        replace_input = ReplaceMandateInput(
            operation_id,
            6,
            bad.value.escalation.id,
            mandate.maximum_amount,
            mandate.pickup_window,
            mandate.allowed_conditions,
            mandate.escalation_conditions,
            "synthetic-coordinator",
            "mandate-phase25-0001",
            UUID(int=101109),
        )
        replaced = await app.replace_mandate(replace_input)
        assert replaced.value.open_escalation is None

        escalation_input = CreateEscalationInput(
            commitment.call_id,
            7,
            "Coordinator review requested.",
            ("Keep active commitment",),
            "Review current carrier terms.",
            "escalation-phase25-0001",
            UUID(int=101110),
        )
        explicit = await app.create_escalation(escalation_input)
        explicit_replay = await app.create_escalation(
            replace(escalation_input, correlation_id=UUID(int=101111))
        )
        assert explicit_replay.idempotency_replayed and explicit_replay.value == explicit.value

        replaced_replay = await app.replace_mandate(
            replace(replace_input, correlation_id=UUID(int=101112))
        )
        assert replaced_replay.idempotency_replayed
        assert replaced_replay.value == replaced.value
        assert replaced_replay.value.open_escalation is None

        notification = projection_after_bad.notifications[0]
        acknowledge_input = AcknowledgeNotificationInput(
            notification.id,
            8,
            "synthetic-coordinator",
            "notification-phase25-0001",
            UUID(int=101113),
        )
        acknowledged = await app.acknowledge_notification(acknowledge_input)
        acknowledge_replay = await app.acknowledge_notification(
            replace(acknowledge_input, correlation_id=UUID(int=101114))
        )
        assert acknowledge_replay.idempotency_replayed
        assert acknowledge_replay.value == acknowledged.value

        projection = await app.get_operation(operation_id)
        assert projection.open_escalation == explicit.value
        assert projection.notifications[0].acknowledged
        audit = await app.get_operation_audit(operation_id)
        assert audit.recaps == (recap.value,)
        assert audit.briefs == (brief.value,)
        assert len(audit.recoveries) == 2
        assert len(audit.escalations) == 2
        assert len(audit.notifications) == 1
    finally:
        await engine.dispose()


async def test_read_projections_reject_commitment_missing_durable_evidence(
    isolated_database_url: str,
) -> None:
    engine = create_async_engine(isolated_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        operation_id, commitment = await _seed_winner(factory, 99000)
        with pytest.raises(CommitmentEvidenceNotFound):
            await application(factory).get_operation(operation_id)
    finally:
        await engine.dispose()


async def test_text_slice_replays_and_reloads_prompt_through_quote_comparison(
    isolated_database_url: str,
    tmp_path: Path,
) -> None:
    engine = create_async_engine(isolated_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app = application(factory, evidence_dir=tmp_path)
    try:
        draft_input = CreateOperationDraftInput(
            CANONICAL_PROMPT,
            "EN_US",
            "draft-idempotency-0001",
        )
        created = await app.create_operation_draft(draft_input)
        replayed_draft = await application(factory).create_operation_draft(draft_input)
        assert not created.idempotency_replayed
        assert replayed_draft.idempotency_replayed
        assert replayed_draft.value == created.value
        assert created.value.draft.proposal.cargo_label == "40ft dry container"

        with pytest.raises(IdempotencyConflict):
            await app.create_operation_draft(
                CreateOperationDraftInput(
                    f"{CANONICAL_PROMPT} changed",
                    "EN_US",
                    draft_input.idempotency_key,
                )
            )

        approval = ApproveOperationInput(
            created.value.draft.id,
            1,
            "synthetic-coordinator",
            UUID(int=9001),
            "approve-idempotency-0001",
        )
        approved = await app.approve_operation(approval)
        approval_replay = await application(factory).approve_operation(
            ApproveOperationInput(
                approval.draft_id,
                approval.expected_draft_version,
                approval.approval_actor,
                UUID(int=9002),
                approval.idempotency_key,
            )
        )
        assert not approved.idempotency_replayed
        assert approval_replay.idempotency_replayed
        operation_id = approved.value.operation.id
        assert approval_replay.value.operation.id == operation_id
        assert approved.value.operation.cargo_label == "40ft dry container"

        started = await app.start_negotiation(
            StartNegotiationInput(
                operation_id,
                1,
                BrowserChannel.BROWSER_TEXT,
                "start-idempotency-0001",
                UUID(int=9003),
            )
        )
        start_replay = await application(factory).start_negotiation(
            StartNegotiationInput(
                operation_id,
                1,
                BrowserChannel.BROWSER_TEXT,
                "start-idempotency-0001",
                UUID(int=9004),
            )
        )
        assert start_replay.idempotency_replayed
        assert len(started.value.sessions) == 3
        assert started.value.sessions[0].ranking_evidence[-1] == (
            "Fixed priority 1; selected rank 1"
        )

        first, second = (item.session for item in started.value.sessions[:2])
        first_quote = await app.record_quote(
            RecordQuoteInput(
                first.call_id,
                2,
                first.carrier_id,
                1,
                QuoteTerms(
                    Decimal("8500"),
                    "MXN",
                    approved.value.operation.pickup_date,
                    approved.value.operation.pickup_date,
                    ("40ft dry container",),
                ),
                NOW + timedelta(days=1),
                "quote-idempotency-0001",
                UUID(int=9005),
            )
        )
        rejected = await app.record_quote(
            RecordQuoteInput(
                second.call_id,
                3,
                second.carrier_id,
                1,
                QuoteTerms(
                    Decimal("9500"),
                    "MXN",
                    approved.value.operation.pickup_date,
                    approved.value.operation.pickup_date,
                ),
                NOW + timedelta(days=1),
                "quote-idempotency-0002",
                UUID(int=9006),
            )
        )
        assert first_quote.value.eligibility is QuoteEligibility.ELIGIBLE
        assert rejected.value.eligibility is QuoteEligibility.REJECTED

        reloaded = await application(factory).get_operation(operation_id)
        assert reloaded.operation.version == 4
        assert reloaded.operation.cargo_label == "40ft dry container"
        assert {quote.id for quote in reloaded.quotes} == {
            first_quote.value.id,
            rejected.value.id,
        }
        assert reloaded.quote_comparison is not None
        assert reloaded.quote_comparison.selected_quote_id == first_quote.value.id

        audit = await application(factory).get_operation_audit(operation_id)
        # Quote comparison is a ranked business projection: eligible quotes keep
        # QuoteComparisonService order and rejected quotes follow afterwards.
        # It must never inherit the UUID order used only as a timeline tie-break.
        assert tuple(row.quote.id for row in audit.quote_comparison) == (
            first_quote.value.id,
            rejected.value.id,
        )
        comparison_by_id = {row.quote.id: row for row in audit.quote_comparison}
        assert comparison_by_id[first_quote.value.id].selected
        assert not comparison_by_id[rejected.value.id].selected
        assert (
            comparison_by_id[first_quote.value.id].carrier_display_name
            == first.carrier_display_label
        )

        with pytest.raises(EvidenceArtifactUnavailable):
            await app.attach_commitment_evidence(
                AttachCommitmentEvidenceInput(
                    first.call_id,
                    4,
                    "missing/agreement.wav",
                    640,
                    "fixture-item-missing",
                    "fixture-event-missing",
                    "evidence-missing-0001",
                    UUID(int=9016),
                )
            )

        with pytest.raises(EvidenceReservationNotFound) as missing_reservation:
            await app.create_candidate_commitment(
                CreateCommitmentInput(
                    first.call_id,
                    4,
                    first_quote.value.id,
                    1,
                    UUID(int=42),
                    "commit-mismatch-0001",
                    UUID(int=9007),
                )
            )
        assert missing_reservation.value.evidence_id == UUID(int=42)
        assert await artifact_count(tmp_path) == 0

        storage = create_demo_evidence_storage(tmp_path)
        recording_reference = await storage.store(
            UUID(int=7001), b"RIFF\x00\x00\x00\x00WAVEagreement-fixture-one"
        )
        attached = await app.attach_commitment_evidence(
            AttachCommitmentEvidenceInput(
                first.call_id,
                4,
                recording_reference,
                640,
                "fixture-item-agreement-one",
                "fixture-event-agreement-one",
                "evidence-idempotency-01",
                UUID(int=9007),
            )
        )
        attached_replay = await application(
            factory, evidence_dir=tmp_path
        ).attach_commitment_evidence(
            AttachCommitmentEvidenceInput(
                first.call_id,
                4,
                recording_reference,
                640,
                "fixture-item-agreement-one",
                "fixture-event-agreement-one",
                "evidence-idempotency-01",
                UUID(int=9017),
            )
        )
        assert attached_replay.idempotency_replayed
        assert attached_replay.value == attached.value
        assert attached.value.quote_id == first_quote.value.id

        with pytest.raises(StaleOperationVersion):
            await app.create_candidate_commitment(
                CreateCommitmentInput(
                    first.call_id,
                    99,
                    first_quote.value.id,
                    1,
                    attached.value.id,
                    "commit-stale-000001",
                    UUID(int=9007),
                )
            )
        assert await artifact_count(tmp_path) == 1

        commitment_input = CreateCommitmentInput(
            first.call_id,
            4,
            first_quote.value.id,
            1,
            attached.value.id,
            "commit-idempotency-01",
            UUID(int=9007),
        )
        committed = await app.create_candidate_commitment(commitment_input)
        assert committed.value.evidence is not None
        stored_audio = await storage.retrieve(
            committed.value.evidence.recording_reference
        )
        assert stored_audio.startswith(b"RIFF")
        assert stored_audio[8:12] == b"WAVE"
        with pytest.raises(EvidenceReservationNotFound):
            await app.create_candidate_commitment(
                CreateCommitmentInput(
                    first.call_id,
                    5,
                    first_quote.value.id,
                    1,
                    attached.value.id,
                    "commit-consumed-0001",
                    UUID(int=9019),
                )
            )
        stored_artifact_count = await artifact_count(tmp_path)

        replayed_commitment = await application(
            factory, evidence_dir=tmp_path
        ).create_candidate_commitment(commitment_input)
        assert replayed_commitment.idempotency_replayed
        assert replayed_commitment.value == committed.value
        assert await artifact_count(tmp_path) == stored_artifact_count

        committed_reload = await application(factory, evidence_dir=tmp_path).get_operation(
            operation_id
        )
        assert committed_reload.operation.version == 5
        assert committed_reload.active_commitment == committed.value
        committed_audit = await application(
            factory, evidence_dir=tmp_path
        ).get_operation_audit(operation_id)
        assert committed_audit.commitment_history == (committed.value,)

        better_quote = await app.record_quote(
            RecordQuoteInput(
                first.call_id,
                5,
                first.carrier_id,
                1,
                QuoteTerms(
                    Decimal("8000"),
                    "MXN",
                    approved.value.operation.pickup_date,
                    approved.value.operation.pickup_date,
                    ("40ft dry container",),
                ),
                NOW + timedelta(days=1),
                "quote-idempotency-0003",
                UUID(int=9008),
            )
        )
        replacement_reference = await storage.store(
            UUID(int=7002), b"RIFF\x00\x00\x00\x00WAVEagreement-fixture-two"
        )
        replacement_evidence = await app.attach_commitment_evidence(
            AttachCommitmentEvidenceInput(
                first.call_id,
                6,
                replacement_reference,
                920,
                "fixture-item-agreement-two",
                "fixture-event-agreement-two",
                "evidence-idempotency-02",
                UUID(int=9018),
            )
        )
        replacement = await app.create_candidate_commitment(
            CreateCommitmentInput(
                first.call_id,
                6,
                better_quote.value.id,
                1,
                replacement_evidence.value.id,
                "commit-idempotency-02",
                UUID(int=9009),
            )
        )
        superseded_audit = await application(
            factory, evidence_dir=tmp_path
        ).get_operation_audit(operation_id)
        history_by_id = {
            item.commitment.id: item for item in superseded_audit.commitment_history
        }
        assert history_by_id[
            committed.value.commitment.id
        ].commitment.disposition.value == "SUPERSEDED"
        assert history_by_id[
            replacement.value.commitment.id
        ].commitment.disposition.value == "ACTIVE"
        assert history_by_id[
            committed.value.commitment.id
        ].commitment.replaced_by_commitment_id == replacement.value.commitment.id
        assert replacement.value.commitment.replaces_commitment_id == committed.value.commitment.id

        async with factory() as session:
            counts = (
                await session.execute(
                    text(
                        "SELECT count(*), "
                        "count(*) FILTER (WHERE disposition = 'ACTIVE') "
                        "FROM volta_commitments WHERE operation_id = :operation_id"
                    ),
                    {"operation_id": operation_id},
                )
            ).one()
            evidence_count = await session.scalar(
                text(
                    "SELECT count(*) FROM volta_agreement_evidence e "
                    "JOIN volta_commitments c ON c.id = e.commitment_id "
                    "WHERE c.operation_id = :operation_id"
                ),
                {"operation_id": operation_id},
            )
            consumed_reservation_count = await session.scalar(
                text(
                    "SELECT count(*) FROM volta_evidence_reservations "
                    "WHERE operation_id = :operation_id "
                    "AND consumed_by_commitment_id IS NOT NULL"
                ),
                {"operation_id": operation_id},
            )
        assert counts == (2, 1)
        assert evidence_count == 2
        assert consumed_reservation_count == 2
    finally:
        await engine.dispose()


async def test_text_slice_persists_validation_feedback_and_pre_contact_escalation(
    isolated_database_url: str,
) -> None:
    engine = create_async_engine(isolated_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    app = application(factory)
    try:
        missing_cargo = await app.create_operation_draft(
            CreateOperationDraftInput(
                "Find transport Thursday from Manzanillo to Guadalajara for MXN 9,000.",
                "EN_US",
                "draft-missing-cargo",
            )
        )
        assert not missing_cargo.value.draft.approval_eligible
        assert ("cargo_label", "required") in {
            (issue.field, issue.reason_code)
            for issue in missing_cargo.value.draft.validation_issues
        }

        no_carrier_draft = await app.create_operation_draft(
            CreateOperationDraftInput(
                "Find transport Thursday from Veracruz to Puebla for MXN 9,000, "
                "one 40-foot dry container.",
                "EN_US",
                "draft-no-carrier-0001",
            )
        )
        approved = await app.approve_operation(
            ApproveOperationInput(
                no_carrier_draft.value.draft.id,
                1,
                "synthetic-coordinator",
                UUID(int=9101),
                "approve-no-carrier-01",
            )
        )
        started = await app.start_negotiation(
            StartNegotiationInput(
                approved.value.operation.id,
                1,
                BrowserChannel.BROWSER_TEXT,
                "start-no-carrier-0001",
                UUID(int=9102),
            )
        )
        assert started.value.sessions == ()
        escalation = started.value.pre_contact_escalation
        assert escalation is not None
        assert escalation.resolution_state is EscalationResolutionState.OPEN
        assert escalation.recommended_action
    finally:
        await engine.dispose()


async def test_concurrent_draft_and_approval_retries_return_one_durable_replay(
    isolated_database_url: str,
) -> None:
    engine = create_async_engine(isolated_database_url, hide_parameters=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    draft_input = CreateOperationDraftInput(
        CANONICAL_PROMPT,
        "EN_US",
        "concurrent-draft-key-01",
    )
    try:
        drafts = await asyncio.gather(
            application(factory).create_operation_draft(draft_input),
            application(factory).create_operation_draft(draft_input),
        )
        assert sorted(item.idempotency_replayed for item in drafts) == [False, True]
        assert drafts[0].value.draft.id == drafts[1].value.draft.id

        approvals = await asyncio.gather(
            application(factory).approve_operation(
                ApproveOperationInput(
                    drafts[0].value.draft.id,
                    1,
                    "synthetic-coordinator",
                    UUID(int=9201),
                    "concurrent-approve-01",
                )
            ),
            application(factory).approve_operation(
                ApproveOperationInput(
                    drafts[0].value.draft.id,
                    1,
                    "synthetic-coordinator",
                    UUID(int=9202),
                    "concurrent-approve-01",
                )
            ),
        )
        assert sorted(item.idempotency_replayed for item in approvals) == [False, True]
        assert approvals[0].value.operation.id == approvals[1].value.operation.id

        async with factory() as session:
            stored = (
                await session.execute(
                    text(
                        "SELECT operation_name, count(*) "
                        "FROM volta_text_mutation_idempotency "
                        "WHERE idempotency_key IN "
                        "('concurrent-draft-key-01', 'concurrent-approve-01') "
                        "GROUP BY operation_name ORDER BY operation_name"
                    )
                )
            ).all()
        assert stored == [("approve_operation", 1), ("create_operation_draft", 1)]
    finally:
        await engine.dispose()
