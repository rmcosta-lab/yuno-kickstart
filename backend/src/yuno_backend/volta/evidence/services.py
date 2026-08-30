"""Deterministic evidence, brief, and recap application services."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from yuno_backend.volta.audit.models import AuditActorKind, AuditEvent
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
from yuno_backend.volta.evidence.models import (
    AgreementEvidence,
    CallBrief,
    Recap,
    RecapDisclosureState,
)
from yuno_backend.volta.evidence.repositories import OperationUnitOfWork
from yuno_backend.volta.mandates.models import Operation
from yuno_backend.volta.mandates.repositories import Clock, IdGenerator
from yuno_backend.volta.negotiations.errors import OperationNotFound, StaleOperationVersion
from yuno_backend.volta.negotiations.models import (
    Commitment,
    CommitmentDisposition,
    CommitmentLifecycle,
)

__all__ = ["GenerateBriefService", "GenerateRecapService", "RecordEvidenceService"]


async def _locked_operation(uow: OperationUnitOfWork, operation_id: UUID) -> Operation:
    operation = await uow.operations.get(operation_id, for_update=True)
    if operation is None:
        raise OperationNotFound(operation_id)
    return operation


def _check_version(operation: Operation, expected: int) -> None:
    if operation.version != expected:
        raise StaleOperationVersion(operation.id, expected, operation.version)


async def _owned_commitment(
    uow: OperationUnitOfWork, operation: Operation, commitment_id: UUID
) -> Commitment:
    commitment = await uow.commitments.get(commitment_id)
    if commitment is None or commitment.operation_id != operation.id:
        raise CommitmentNotFound(commitment_id)
    return commitment


def _audit(
    ids: IdGenerator,
    operation: Operation,
    event_type: str,
    now: datetime,
    correlation_id: UUID,
) -> AuditEvent:
    return AuditEvent(
        event_id=ids.new_id(),
        operation_id=operation.id,
        operation_version=operation.version,
        actor_kind=AuditActorKind.SYSTEM,
        event_type=event_type,
        occurred_at=now,
        correlation_id=correlation_id,
        metadata={},
    )


class RecordEvidenceService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = unit_of_work
        self._clock = clock
        self._ids = id_generator

    async def record(self, command: RecordEvidenceCommand) -> AgreementEvidence:
        async with self._uow:
            try:
                operation = await _locked_operation(self._uow, command.operation_id)
                _check_version(operation, command.expected_operation_version)
                commitment = await _owned_commitment(self._uow, operation, command.commitment_id)
                if (
                    commitment.lifecycle is not CommitmentLifecycle.CANDIDATE
                    or commitment.disposition is not CommitmentDisposition.ACTIVE
                ):
                    raise InvalidCommitmentDisposition(commitment.id, commitment.disposition.value)

                existing = await self._uow.evidence.get_by_commitment(commitment.id)
                if existing is not None:
                    candidate = AgreementEvidence(
                        id=existing.id,
                        commitment_id=commitment.id,
                        recording_reference=command.recording_reference,
                        audio_start_ms=command.audio_start_ms,
                        item_id=command.item_id,
                        event_id=command.event_id,
                        created_at=existing.created_at,
                    )
                    if candidate != existing:
                        raise EvidenceAlreadyRecorded(commitment.id)
                    await self._uow.rollback()
                    return existing

                now = self._clock.now()
                evidence = AgreementEvidence(
                    id=self._ids.new_id(),
                    commitment_id=commitment.id,
                    recording_reference=command.recording_reference,
                    audio_start_ms=command.audio_start_ms,
                    item_id=command.item_id,
                    event_id=command.event_id,
                    created_at=now,
                )
                await self._uow.evidence.add(evidence)
                await self._uow.audit_events.add(
                    _audit(self._ids, operation, "EVIDENCE_RECORDED", now, command.correlation_id)
                )
                await self._uow.commit()
                return evidence
            except Exception:
                await self._uow.rollback()
                raise


class GenerateBriefService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = unit_of_work
        self._clock = clock
        self._ids = id_generator

    async def generate(self, command: GenerateBriefCommand) -> CallBrief:
        async with self._uow:
            try:
                operation = await _locked_operation(self._uow, command.operation_id)
                _check_version(operation, command.expected_operation_version)
                commitment = await _owned_commitment(self._uow, operation, command.commitment_id)

                existing = await self._uow.briefs.get_by_commitment(commitment.id)
                if existing is not None:
                    await self._uow.rollback()
                    return existing

                now = self._clock.now()
                brief = CallBrief(
                    id=self._ids.new_id(),
                    commitment_id=commitment.id,
                    operation_id=operation.id,
                    route=operation.route,
                    carrier_id=commitment.carrier_id,
                    agreed_terms_reference=commitment.quote_id,
                    mandate_version=commitment.mandate_version,
                    generated_at=now,
                )
                await self._uow.briefs.add(brief)
                await self._uow.audit_events.add(
                    _audit(self._ids, operation, "BRIEF_GENERATED", now, command.correlation_id)
                )
                await self._uow.commit()
                return brief
            except Exception:
                await self._uow.rollback()
                raise


class GenerateRecapService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = unit_of_work
        self._clock = clock
        self._ids = id_generator

    async def generate(self, command: GenerateRecapCommand) -> Recap:
        async with self._uow:
            try:
                operation = await _locked_operation(self._uow, command.operation_id)
                _check_version(operation, command.expected_operation_version)
                commitment = await _owned_commitment(self._uow, operation, command.commitment_id)

                existing = await self._uow.recaps.get_by_commitment(commitment.id)
                if existing is not None:
                    await self._uow.rollback()
                    return existing

                now = self._clock.now()
                recap = Recap(
                    id=self._ids.new_id(),
                    commitment_id=commitment.id,
                    operation_id=operation.id,
                    disclosure_state=RecapDisclosureState.SIMULATED,
                    generated_at=now,
                )
                await self._uow.recaps.add(recap)
                await self._uow.audit_events.add(
                    _audit(self._ids, operation, "RECAP_GENERATED", now, command.correlation_id)
                )
                await self._uow.commit()
                return recap
            except Exception:
                await self._uow.rollback()
                raise
