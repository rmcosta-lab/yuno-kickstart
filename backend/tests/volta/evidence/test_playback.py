from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

import pytest
from yuno_backend.volta.evidence.models import AgreementEvidence
from yuno_backend.volta.evidence.playback import (
    EvidenceAudioNotFound,
    EvidenceAudioTooLarge,
    RetrieveEvidenceAudioService,
)

EVIDENCE_ID = UUID(int=1600)
REFERENCE = "recordings/private/agreement.wav"
WAV = b"RIFF\x04\x00\x00\x00WAVEaudio"


@dataclass
class EvidenceRepository:
    evidence: AgreementEvidence | None

    async def get(self, evidence_id: UUID) -> AgreementEvidence | None:
        if self.evidence is not None and evidence_id == self.evidence.id:
            return self.evidence
        return None


@dataclass
class UnitOfWork:
    evidence: EvidenceRepository
    active: bool = False
    rollbacks: int = 0
    exits: int = 0

    async def __aenter__(self) -> UnitOfWork:
        self.active = True
        return self

    async def __aexit__(self, *args: object) -> None:
        self.active = False
        self.exits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


@dataclass
class Storage:
    unit_of_work: UnitOfWork
    payload: bytes = WAV
    failure: Exception | None = None
    references: list[str] = field(default_factory=list)

    async def retrieve(self, recording_reference: str) -> bytes:
        assert not self.unit_of_work.active
        assert self.unit_of_work.rollbacks == 1
        assert self.unit_of_work.exits == 1
        self.references.append(recording_reference)
        if self.failure is not None:
            raise self.failure
        return self.payload


def evidence(*, reference: str = REFERENCE) -> AgreementEvidence:
    return AgreementEvidence(
        id=EVIDENCE_ID,
        commitment_id=UUID(int=1601),
        recording_reference=reference,
        audio_start_ms=1234,
        item_id="item-private",
        event_id="event-private",
        created_at=datetime(2026, 8, 30, tzinfo=UTC),
    )


def service(
    stored_evidence: AgreementEvidence | None,
    *,
    payload: bytes = WAV,
    failure: Exception | None = None,
) -> tuple[RetrieveEvidenceAudioService, UnitOfWork, Storage]:
    unit_of_work = UnitOfWork(EvidenceRepository(stored_evidence))
    storage = Storage(unit_of_work, payload, failure)
    return (
        RetrieveEvidenceAudioService(lambda: unit_of_work, storage),
        unit_of_work,
        storage,
    )


async def test_retrieve_returns_validated_wave_without_reference() -> None:
    playback, unit_of_work, storage = service(evidence())

    audio = await playback.retrieve(EVIDENCE_ID)

    assert audio.content == WAV
    assert audio.media_type == "audio/wav"
    assert audio.content_length == len(WAV)
    assert not hasattr(audio, "recording_reference")
    assert storage.references == [REFERENCE]
    assert unit_of_work.rollbacks == 1
    assert unit_of_work.exits == 1


async def test_missing_evidence_does_not_access_storage() -> None:
    playback, unit_of_work, storage = service(None)

    with pytest.raises(EvidenceAudioNotFound):
        await playback.retrieve(EVIDENCE_ID)

    assert storage.references == []
    assert unit_of_work.rollbacks == 1
    assert unit_of_work.exits == 1


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"RIFF",
        b"RIFF\x04\x00\x00\x00NOPEaudio",
        b"OggS\x04\x00\x00\x00WAVEaudio",
    ],
)
async def test_invalid_media_is_not_found(payload: bytes) -> None:
    playback, _, _ = service(evidence(), payload=payload)

    with pytest.raises(EvidenceAudioNotFound):
        await playback.retrieve(EVIDENCE_ID)


@pytest.mark.parametrize("failure", [FileNotFoundError(), OSError("unreadable"), ValueError()])
async def test_unreadable_or_invalid_storage_reference_is_not_found(failure: Exception) -> None:
    playback, _, _ = service(evidence(), failure=failure)

    with pytest.raises(EvidenceAudioNotFound) as captured:
        await playback.retrieve(EVIDENCE_ID)

    assert captured.value.__cause__ is None
    assert str(captured.value) == ""


async def test_unexpected_storage_failure_is_not_misclassified() -> None:
    failure = RuntimeError("storage adapter unavailable")
    playback, _, _ = service(evidence(), failure=failure)

    with pytest.raises(RuntimeError) as captured:
        await playback.retrieve(EVIDENCE_ID)

    assert captured.value is failure


async def test_wave_above_response_cap_is_too_large() -> None:
    payload = b"RIFF\x04\x00\x00\x00WAVE" + bytes(25 * 1024 * 1024 - 11)
    playback, _, _ = service(evidence(), payload=payload)

    with pytest.raises(EvidenceAudioTooLarge):
        await playback.retrieve(EVIDENCE_ID)


async def test_invalid_oversize_media_is_still_not_found() -> None:
    payload = b"NOPE\x04\x00\x00\x00WAVE" + bytes(25 * 1024 * 1024)
    playback, _, _ = service(evidence(), payload=payload)

    with pytest.raises(EvidenceAudioNotFound):
        await playback.retrieve(EVIDENCE_ID)
