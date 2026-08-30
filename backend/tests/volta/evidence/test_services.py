from uuid import UUID

import pytest
from yuno_backend.volta.evidence.commands import (
    GenerateBriefCommand,
    GenerateRecapCommand,
    RecordEvidenceCommand,
)
from yuno_backend.volta.evidence.errors import (
    CommitmentNotFound,
    EvidenceAlreadyRecorded,
    InvalidCommitmentDisposition,
)
from yuno_backend.volta.evidence.models import RecapDisclosureState
from yuno_backend.volta.evidence.services import (
    GenerateBriefService,
    GenerateRecapService,
    RecordEvidenceService,
)
from yuno_backend.volta.negotiations.errors import OperationNotFound, StaleOperationVersion
from yuno_backend.volta.negotiations.models import CommitmentDisposition

from .conftest import OPERATION_ID, Clock, Ids, Uow, commitment, operation


def _record_command(**overrides: object) -> RecordEvidenceCommand:
    values: dict[str, object] = {
        "operation_id": OPERATION_ID,
        "expected_operation_version": 2,
        "commitment_id": UUID(int=200),
        "recording_reference": "recordings/200/a.bin",
        "audio_start_ms": 0,
        "item_id": "item-1",
        "event_id": "event-1",
        "correlation_id": UUID(int=900),
    }
    values.update(overrides)
    return RecordEvidenceCommand(**values)  # type: ignore[arg-type]


async def test_record_evidence_attaches_evidence_and_emits_audit() -> None:
    active = commitment()
    uow = Uow(operation(), {active.id: active})
    service = RecordEvidenceService(uow, Clock(), Ids())

    evidence = await service.record(_record_command())

    assert evidence.commitment_id == active.id
    assert uow.commits == 1
    assert len(uow.evidence.values) == 1
    assert len(uow.audit_events.values) == 1
    event = next(iter(uow.audit_events.values.values()))
    assert event.event_type == "EVIDENCE_RECORDED"
    assert event.metadata == {}


async def test_record_evidence_is_idempotent_for_identical_payload() -> None:
    active = commitment()
    uow = Uow(operation(), {active.id: active})
    service = RecordEvidenceService(uow, Clock(), Ids())

    first = await service.record(_record_command())
    second = await service.record(_record_command(correlation_id=UUID(int=901)))

    assert second == first
    assert len(uow.evidence.values) == 1
    assert uow.commits == 1
    assert uow.rollbacks == 1


async def test_record_evidence_rejects_mismatched_replay() -> None:
    active = commitment()
    uow = Uow(operation(), {active.id: active})
    service = RecordEvidenceService(uow, Clock(), Ids())

    await service.record(_record_command())
    with pytest.raises(EvidenceAlreadyRecorded):
        await service.record(_record_command(recording_reference="recordings/200/b.bin"))


async def test_record_evidence_rejects_missing_or_superseded_commitment() -> None:
    superseded = commitment(disposition=CommitmentDisposition.SUPERSEDED)
    uow = Uow(operation(), {superseded.id: superseded})
    service = RecordEvidenceService(uow, Clock(), Ids())

    with pytest.raises(CommitmentNotFound):
        await service.record(_record_command(commitment_id=UUID(int=999)))
    with pytest.raises(InvalidCommitmentDisposition):
        await service.record(_record_command())
    assert uow.evidence.values == {}


async def test_record_evidence_rejects_stale_operation_version_and_writes_nothing() -> None:
    active = commitment()
    uow = Uow(operation(), {active.id: active})
    service = RecordEvidenceService(uow, Clock(), Ids())

    with pytest.raises(StaleOperationVersion):
        await service.record(_record_command(expected_operation_version=99))
    assert uow.evidence.values == {}
    assert uow.commits == 0


async def test_record_evidence_rejects_unknown_operation() -> None:
    active = commitment()
    uow = Uow(operation(), {active.id: active})
    service = RecordEvidenceService(uow, Clock(), Ids())

    with pytest.raises(OperationNotFound):
        await service.record(_record_command(operation_id=UUID(int=999)))


async def test_generate_brief_builds_bounded_summary_and_is_idempotent() -> None:
    active = commitment()
    uow = Uow(operation(), {active.id: active})
    service = GenerateBriefService(uow, Clock(), Ids())
    command = GenerateBriefCommand(OPERATION_ID, 2, active.id, UUID(int=900))

    brief = await service.generate(command)
    replay = await service.generate(command)

    assert replay == brief
    assert brief.carrier_id == active.carrier_id
    assert brief.agreed_terms_reference == active.quote_id
    assert brief.route.origin == "Port A"
    assert len(uow.briefs.values) == 1
    assert uow.commits == 1


async def test_generate_recap_is_always_simulated_and_idempotent() -> None:
    active = commitment()
    uow = Uow(operation(), {active.id: active})
    service = GenerateRecapService(uow, Clock(), Ids())
    command = GenerateRecapCommand(OPERATION_ID, 2, active.id, UUID(int=900))

    recap = await service.generate(command)
    replay = await service.generate(command)

    assert replay == recap
    assert recap.disclosure_state is RecapDisclosureState.SIMULATED
    assert len(uow.recaps.values) == 1
