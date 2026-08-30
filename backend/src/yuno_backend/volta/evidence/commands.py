"""Typed evidence application inputs."""

from dataclasses import dataclass
from uuid import UUID

__all__ = ["GenerateBriefCommand", "GenerateRecapCommand", "RecordEvidenceCommand"]


@dataclass(frozen=True, slots=True)
class RecordEvidenceCommand:
    operation_id: UUID
    expected_operation_version: int
    commitment_id: UUID
    recording_reference: str
    audio_start_ms: int
    item_id: str
    event_id: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class GenerateBriefCommand:
    operation_id: UUID
    expected_operation_version: int
    commitment_id: UUID
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class GenerateRecapCommand:
    operation_id: UUID
    expected_operation_version: int
    commitment_id: UUID
    correlation_id: UUID
