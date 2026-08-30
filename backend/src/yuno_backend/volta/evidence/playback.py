"""Provider-neutral retrieval of private agreement audio evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from yuno_backend.volta.evidence.repositories import EvidenceStorage, OperationUnitOfWork

__all__ = [
    "EvidenceAudio",
    "EvidenceAudioNotFound",
    "EvidenceAudioTooLarge",
    "RetrieveEvidenceAudioService",
]

_AUDIO_WAV = "audio/wav"
_MAX_AUDIO_BYTES = 25 * 1024 * 1024


class _OperationUnitOfWorkFactory(Protocol):
    def __call__(self) -> OperationUnitOfWork: ...


@dataclass(frozen=True, slots=True)
class EvidenceAudio:
    """Validated playable bytes without the private storage reference."""

    content: bytes
    media_type: str
    content_length: int


class EvidenceAudioNotFound(LookupError):
    """The requested evidence has no safely playable audio artifact."""


class EvidenceAudioTooLarge(RuntimeError):
    """The artifact exceeds the trusted-demo response acceptance cap."""


class RetrieveEvidenceAudioService:
    """Resolve private evidence metadata, then read storage outside the UoW."""

    def __init__(
        self,
        unit_of_work_factory: _OperationUnitOfWorkFactory,
        evidence_storage: EvidenceStorage,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._storage = evidence_storage

    async def retrieve(self, evidence_id: UUID) -> EvidenceAudio:
        recording_reference = await self._recording_reference(evidence_id)

        try:
            content = await self._storage.retrieve(recording_reference)
        except (OSError, ValueError):
            raise EvidenceAudioNotFound from None

        if not self._is_wave(content):
            raise EvidenceAudioNotFound
        if len(content) > _MAX_AUDIO_BYTES:
            raise EvidenceAudioTooLarge
        return EvidenceAudio(
            content=content,
            media_type=_AUDIO_WAV,
            content_length=len(content),
        )

    async def _recording_reference(self, evidence_id: UUID) -> str:
        unit_of_work = self._uow_factory()
        async with unit_of_work:
            try:
                evidence = await unit_of_work.evidence.get(evidence_id)
                if evidence is None:
                    raise EvidenceAudioNotFound
                return evidence.recording_reference
            finally:
                await unit_of_work.rollback()

    @staticmethod
    def _is_wave(content: object) -> bool:
        return (
            isinstance(content, bytes)
            and len(content) >= 12
            and content[:4] == b"RIFF"
            and content[8:12] == b"WAVE"
        )
