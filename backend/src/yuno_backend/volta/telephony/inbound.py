"""Provider-neutral inbound-call contracts and orchestration."""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from typing import Protocol, Self
from uuid import UUID

from yuno_backend.volta.audit.models import AuditActorKind, AuditEvent
from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.evidence.commands import GenerateBriefCommand
from yuno_backend.volta.evidence.repositories import EvidenceStorage
from yuno_backend.volta.evidence.services import GenerateBriefService
from yuno_backend.volta.mandates.models import OperationStatus
from yuno_backend.volta.mandates.repositories import Clock, IdGenerator
from yuno_backend.volta.mandates.services import MandatePolicy
from yuno_backend.volta.recovery.commands import (
    ReplacementEvidence,
    SimulateInboundRecoveryCommand,
)
from yuno_backend.volta.recovery.fixtures import (
    DeterministicRecoveryFixtureCatalog,
    RecoveryFixtureCatalog,
)
from yuno_backend.volta.recovery.models import RecoveryOutcome, RecoveryScenario
from yuno_backend.volta.recovery.services import SimulateInboundRecoveryService

__all__ = [
    "AcceptInboundCallInput",
    "CompleteInboundRecoveryInput",
    "FailInboundCallInput",
    "InboundCallApplication",
    "InboundCallAttempt",
    "InboundCallAttemptRepository",
    "InboundCallBinding",
    "InboundCallerBinding",
    "InboundCallerCorrelationRepository",
    "InboundCallLimits",
    "InboundCallStatus",
    "InboundOperationUnitOfWork",
    "InboundOperationUnitOfWorkFactory",
    "RecordInboundConsentInput",
    "StartInboundStreamInput",
]

_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _uuid(value: object, name: str) -> None:
    if not isinstance(value, UUID):
        raise InvalidDomainValue(name, "uuid_required")


def _safe(value: object, name: str) -> None:
    if not isinstance(value, str) or _SAFE.fullmatch(value) is None:
        raise InvalidDomainValue(name, "safe_identifier_required")


def _utc(value: object, name: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise InvalidDomainValue(name, "aware_utc_required")


class InboundCallStatus(StrEnum):
    AWAITING_CONSENT = "AWAITING_CONSENT"
    CONSENTED = "CONSENTED"
    STREAMING = "STREAMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def active(self) -> bool:
        return self in {
            InboundCallStatus.AWAITING_CONSENT,
            InboundCallStatus.CONSENTED,
            InboundCallStatus.STREAMING,
        }


@dataclass(frozen=True, slots=True)
class InboundCallLimits:
    binding_ttl: timedelta = timedelta(minutes=5)
    maximum_audio_bytes: int = 2_000_000

    def __post_init__(self) -> None:
        if not timedelta(seconds=1) <= self.binding_ttl <= timedelta(minutes=30):
            raise InvalidDomainValue("binding_ttl", "bounded_duration_required")
        if not 44 <= self.maximum_audio_bytes <= 10_000_000:
            raise InvalidDomainValue("maximum_audio_bytes", "bounded_size_required")


@dataclass(frozen=True, slots=True)
class InboundCallerBinding:
    id: UUID
    caller_label: str
    operation_id: UUID
    active: bool
    created_at: datetime

    def __post_init__(self) -> None:
        _uuid(self.id, "id")
        _safe(self.caller_label, "caller_label")
        _uuid(self.operation_id, "operation_id")
        if not isinstance(self.active, bool):
            raise InvalidDomainValue("active", "boolean_required")
        _utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class InboundCallBinding:
    attempt_id: UUID
    operation_id: UUID
    commitment_id: UUID
    call_id: UUID
    provider_call_id: str
    stream_binding: str = field(repr=False)
    expires_at: datetime

    def __post_init__(self) -> None:
        for name in ("attempt_id", "operation_id", "commitment_id", "call_id"):
            _uuid(getattr(self, name), name)
        _safe(self.provider_call_id, "provider_call_id")
        _safe(self.stream_binding, "stream_binding")
        _utc(self.expires_at, "expires_at")


@dataclass(frozen=True, slots=True)
class InboundCallAttempt:
    id: UUID
    operation_id: UUID
    commitment_id: UUID
    call_id: UUID
    caller_label: str
    provider_call_id: str
    stream_binding_hash: str = field(repr=False)
    status: InboundCallStatus
    created_at: datetime
    expires_at: datetime
    consented_at: datetime | None = None
    stream_started_at: datetime | None = None
    provider_stream_id: str | None = None
    completed_at: datetime | None = None
    failure_reason: str | None = None
    completion_fingerprint: str | None = None
    resulting_commitment_id: UUID | None = None
    resulting_evidence_id: UUID | None = None
    resulting_brief_id: UUID | None = None
    recovery_attempt_id: UUID | None = None
    correlation_id: UUID | None = None

    def __post_init__(self) -> None:
        for name in ("id", "operation_id", "commitment_id", "call_id"):
            _uuid(getattr(self, name), name)
        _safe(self.caller_label, "caller_label")
        _safe(self.provider_call_id, "provider_call_id")
        if _SHA256.fullmatch(self.stream_binding_hash) is None:
            raise InvalidDomainValue("stream_binding_hash", "sha256_hex_required")
        if not isinstance(self.status, InboundCallStatus):
            raise InvalidDomainValue("status", "inbound_call_status_required")
        _utc(self.created_at, "created_at")
        _utc(self.expires_at, "expires_at")
        if self.expires_at <= self.created_at:
            raise InvalidDomainValue("expires_at", "must_follow_created_at")
        for name in ("consented_at", "stream_started_at", "completed_at"):
            value = getattr(self, name)
            if value is not None:
                _utc(value, name)
        if self.provider_stream_id is not None:
            _safe(self.provider_stream_id, "provider_stream_id")
        if self.failure_reason is not None:
            _safe(self.failure_reason, "failure_reason")
        if self.completion_fingerprint is not None and _SHA256.fullmatch(
            self.completion_fingerprint
        ) is None:
            raise InvalidDomainValue("completion_fingerprint", "sha256_hex_required")
        for name in (
            "resulting_commitment_id",
            "resulting_evidence_id",
            "resulting_brief_id",
            "recovery_attempt_id",
            "correlation_id",
        ):
            value = getattr(self, name)
            if value is not None:
                _uuid(value, name)
        if self.status is InboundCallStatus.AWAITING_CONSENT and any(
            value is not None
            for value in (self.consented_at, self.stream_started_at, self.completed_at)
        ):
            raise InvalidDomainValue("status", "attempt_state_mismatch")
        if self.status is InboundCallStatus.CONSENTED and self.consented_at is None:
            raise InvalidDomainValue("status", "consent_timestamp_required")
        if self.status is InboundCallStatus.STREAMING and (
            self.consented_at is None
            or self.stream_started_at is None
            or self.provider_stream_id is None
        ):
            raise InvalidDomainValue("status", "stream_context_required")
        if self.status is InboundCallStatus.COMPLETED and any(
            value is None
            for value in (
                self.consented_at,
                self.completed_at,
                self.completion_fingerprint,
                self.resulting_commitment_id,
                self.resulting_evidence_id,
                self.resulting_brief_id,
                self.recovery_attempt_id,
                self.correlation_id,
            )
        ):
            raise InvalidDomainValue("status", "completion_context_required")
        if self.status is InboundCallStatus.FAILED and (
            self.completed_at is None or self.failure_reason is None
        ):
            raise InvalidDomainValue("status", "failure_context_required")


@dataclass(frozen=True, slots=True)
class AcceptInboundCallInput:
    caller_label: str
    provider_call_id: str
    correlation_id: UUID

    def __post_init__(self) -> None:
        _safe(self.caller_label, "caller_label")
        _safe(self.provider_call_id, "provider_call_id")
        _uuid(self.correlation_id, "correlation_id")


@dataclass(frozen=True, slots=True)
class RecordInboundConsentInput:
    provider_call_id: str
    stream_binding: str = field(repr=False)

    def __post_init__(self) -> None:
        _safe(self.provider_call_id, "provider_call_id")
        _safe(self.stream_binding, "stream_binding")


@dataclass(frozen=True, slots=True)
class StartInboundStreamInput:
    provider_call_id: str
    stream_binding: str = field(repr=False)
    provider_stream_id: str

    def __post_init__(self) -> None:
        _safe(self.provider_call_id, "provider_call_id")
        _safe(self.stream_binding, "stream_binding")
        _safe(self.provider_stream_id, "provider_stream_id")


@dataclass(frozen=True, slots=True)
class CompleteInboundRecoveryInput:
    provider_call_id: str
    post_consent_audio: bytes = field(repr=False)
    audio_start_ms: int
    item_id: str
    event_id: str
    correlation_id: UUID

    def __post_init__(self) -> None:
        _safe(self.provider_call_id, "provider_call_id")
        if not isinstance(self.post_consent_audio, bytes) or not self.post_consent_audio:
            raise InvalidDomainValue("post_consent_audio", "non_empty_bytes_required")
        if not (
            self.post_consent_audio.startswith(b"RIFF")
            and self.post_consent_audio[8:12] == b"WAVE"
        ):
            raise InvalidDomainValue("post_consent_audio", "playable_wav_required")
        if (
            not isinstance(self.audio_start_ms, int)
            or isinstance(self.audio_start_ms, bool)
            or self.audio_start_ms < 0
        ):
            raise InvalidDomainValue("audio_start_ms", "non_negative_integer_required")
        _safe(self.item_id, "item_id")
        _safe(self.event_id, "event_id")
        _uuid(self.correlation_id, "correlation_id")


@dataclass(frozen=True, slots=True)
class FailInboundCallInput:
    provider_call_id: str
    reason_code: str

    def __post_init__(self) -> None:
        _safe(self.provider_call_id, "provider_call_id")
        _safe(self.reason_code, "reason_code")


class InboundCallAttemptRepository(Protocol):
    async def get_by_provider_call(
        self, provider_call_id: str, *, for_update: bool = False
    ) -> InboundCallAttempt | None: ...
    async def get_active_by_operation(
        self, operation_id: UUID, *, for_update: bool = False
    ) -> InboundCallAttempt | None: ...
    async def add(self, attempt: InboundCallAttempt) -> None: ...
    async def update(self, attempt: InboundCallAttempt) -> None: ...


class InboundCallerCorrelationRepository(Protocol):
    async def list_active_by_caller(
        self, caller_label: str, *, for_update: bool = False
    ) -> tuple[InboundCallerBinding, ...]: ...
    async def add(self, binding: InboundCallerBinding) -> None: ...


class InboundOperationUnitOfWork(Protocol):
    operations: object
    commitments: object
    post_contact_escalations: object
    audit_events: object
    inbound_call_attempts: InboundCallAttemptRepository
    inbound_caller_correlations: InboundCallerCorrelationRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class InboundOperationUnitOfWorkFactory(Protocol):
    def __call__(self) -> InboundOperationUnitOfWork: ...


class InboundCallApplication:
    """Fail-closed facade for correlation, consent, and one fixed recovery."""

    def __init__(
        self,
        unit_of_work_factory: InboundOperationUnitOfWorkFactory,
        evidence_storage: EvidenceStorage,
        clock: Clock,
        id_generator: IdGenerator,
        recovery_fixture_catalog: RecoveryFixtureCatalog | None = None,
        limits: InboundCallLimits | None = None,
    ) -> None:
        self._uow_factory = unit_of_work_factory
        self._storage = evidence_storage
        self._clock = clock
        self._ids = id_generator
        self._fixtures = recovery_fixture_catalog or DeterministicRecoveryFixtureCatalog()
        self._limits = limits or InboundCallLimits()

    async def accept_inbound_call(self, command: AcceptInboundCallInput) -> InboundCallBinding:
        from yuno_backend.volta.telephony.errors import (
            InboundCallReplayConflict,
            InboundCorrelationAmbiguous,
            InboundCorrelationNotFound,
        )

        async with self._uow_factory() as uow:
            try:
                existing = await uow.inbound_call_attempts.get_by_provider_call(
                    command.provider_call_id, for_update=True
                )
                if existing is not None:
                    if (
                        existing.caller_label != command.caller_label
                        or existing.status
                        not in {
                            InboundCallStatus.AWAITING_CONSENT,
                            InboundCallStatus.CONSENTED,
                        }
                    ):
                        raise InboundCallReplayConflict()
                    await uow.rollback()
                    return self._binding(existing)
                candidates = []
                bindings = await uow.inbound_caller_correlations.list_active_by_caller(
                    command.caller_label, for_update=True
                )
                for binding in bindings:
                    operation = await uow.operations.get(binding.operation_id, for_update=True)
                    if operation is None or operation.status is not OperationStatus.COMMITTED:
                        continue
                    active = await uow.commitments.get_active(operation.id)
                    if active is None:
                        continue
                    escalation = await uow.post_contact_escalations.get_unresolved_by_operation(
                        operation.id
                    )
                    concurrent = await uow.inbound_call_attempts.get_active_by_operation(
                        operation.id, for_update=True
                    )
                    if escalation is None and concurrent is None:
                        candidates.append((binding, operation, active))
                if not candidates:
                    raise InboundCorrelationNotFound()
                if len(candidates) != 1:
                    raise InboundCorrelationAmbiguous()
                _, operation, commitment = candidates[0]
                now = self._clock.now()
                attempt_id = self._ids.new_id()
                token = attempt_id.hex
                attempt = InboundCallAttempt(
                    attempt_id,
                    operation.id,
                    commitment.id,
                    commitment.call_id,
                    command.caller_label,
                    command.provider_call_id,
                    sha256(token.encode()).hexdigest(),
                    InboundCallStatus.AWAITING_CONSENT,
                    now,
                    now + self._limits.binding_ttl,
                    correlation_id=command.correlation_id,
                )
                await uow.inbound_call_attempts.add(attempt)
                await uow.audit_events.add(
                    self._audit(operation, "INBOUND_CALL_ACCEPTED", command.correlation_id)
                )
                await uow.commit()
                return self._binding(attempt)
            except Exception:
                await uow.rollback()
                raise

    async def record_inbound_consent(
        self, command: RecordInboundConsentInput
    ) -> InboundCallBinding:
        from yuno_backend.volta.telephony.errors import (
            InboundCallReplayConflict,
            InboundCallStateConflict,
        )

        async with self._uow_factory() as uow:
            try:
                attempt = await self._attempt(uow, command.provider_call_id)
                self._require_binding(attempt, command.stream_binding)
                if attempt.status is InboundCallStatus.AWAITING_CONSENT:
                    now = self._clock.now()
                    if now >= attempt.expires_at:
                        raise InboundCallReplayConflict()
                    attempt = replace(
                        attempt, status=InboundCallStatus.CONSENTED, consented_at=now
                    )
                    await uow.inbound_call_attempts.update(attempt)
                    operation = await uow.operations.get(attempt.operation_id)
                    await uow.audit_events.add(
                        self._audit(operation, "INBOUND_CONSENT_RECORDED", attempt.correlation_id)
                    )
                    await uow.commit()
                elif attempt.status is not InboundCallStatus.CONSENTED:
                    raise InboundCallStateConflict()
                else:
                    await uow.rollback()
                return self._binding(attempt)
            except Exception:
                await uow.rollback()
                raise

    async def start_inbound_stream(
        self, command: StartInboundStreamInput
    ) -> InboundCallAttempt:
        from yuno_backend.volta.telephony.errors import InboundCallStateConflict

        async with self._uow_factory() as uow:
            try:
                attempt = await self._attempt(uow, command.provider_call_id)
                self._require_binding(attempt, command.stream_binding)
                if attempt.status is InboundCallStatus.STREAMING:
                    if attempt.provider_stream_id != command.provider_stream_id:
                        raise InboundCallStateConflict()
                    await uow.rollback()
                    return attempt
                if attempt.status is not InboundCallStatus.CONSENTED:
                    raise InboundCallStateConflict()
                now = self._clock.now()
                if now >= attempt.expires_at:
                    raise InboundCallStateConflict()
                attempt = replace(
                    attempt,
                    status=InboundCallStatus.STREAMING,
                    stream_started_at=now,
                    provider_stream_id=command.provider_stream_id,
                )
                await uow.inbound_call_attempts.update(attempt)
                await uow.commit()
                return attempt
            except Exception:
                await uow.rollback()
                raise

    async def complete_inbound_recovery(
        self, command: CompleteInboundRecoveryInput
    ) -> InboundCallAttempt:
        from yuno_backend.volta.telephony.errors import (
            InboundCallReplayConflict,
            InboundCallStateConflict,
        )

        if len(command.post_consent_audio) > self._limits.maximum_audio_bytes:
            raise InboundCallStateConflict()
        digest = self._completion_fingerprint(command)
        # Read/idempotency check happens before storage, preventing replay artifacts.
        async with self._uow_factory() as uow:
            attempt = await self._attempt(uow, command.provider_call_id)
            if attempt.status is InboundCallStatus.COMPLETED:
                await uow.rollback()
                if attempt.completion_fingerprint != digest:
                    raise InboundCallReplayConflict()
                return attempt
            if attempt.status not in {
                InboundCallStatus.CONSENTED,
                InboundCallStatus.STREAMING,
            }:
                await uow.rollback()
                raise InboundCallStateConflict()
            commitment_id = attempt.commitment_id
            await uow.rollback()

        recording_reference = await self._storage.store(
            commitment_id, command.post_consent_audio
        )
        try:
            async with self._uow_factory() as uow:
                try:
                    attempt = await self._attempt(uow, command.provider_call_id)
                    if attempt.status is InboundCallStatus.COMPLETED:
                        if attempt.completion_fingerprint != digest:
                            raise InboundCallReplayConflict()
                        await uow.rollback()
                        await self._storage.delete(recording_reference)
                        return attempt
                    if attempt.status not in {
                        InboundCallStatus.CONSENTED,
                        InboundCallStatus.STREAMING,
                    }:
                        raise InboundCallStateConflict()
                    operation = await uow.operations.get(attempt.operation_id, for_update=True)
                    active = await uow.commitments.get_active(attempt.operation_id)
                    if operation is None or active is None or active.id != attempt.commitment_id:
                        raise InboundCallStateConflict()
                    fixture = self._fixtures.get(RecoveryScenario.MANDATE_SAFE)
                    recovery = await SimulateInboundRecoveryService(
                        uow, MandatePolicy(), self._clock, self._ids
                    ).simulate_in_transaction(
                        SimulateInboundRecoveryCommand(
                            operation.id,
                            operation.version,
                            active.id,
                            operation.mandate.version,
                            fixture.proposed_terms,
                            command.correlation_id,
                            RecoveryScenario.MANDATE_SAFE,
                            fixture.decision_reason,
                            ReplacementEvidence(
                                recording_reference,
                                command.audio_start_ms,
                                command.item_id,
                                command.event_id,
                            ),
                            None,
                        )
                    )
                    if (
                        recovery.outcome is not RecoveryOutcome.REPLACED
                        or recovery.resulting_commitment_id is None
                        or recovery.resulting_evidence_id is None
                    ):
                        raise InboundCallStateConflict()
                    resulting = await uow.commitments.get(recovery.resulting_commitment_id)
                    if resulting is None:
                        raise InboundCallStateConflict()
                    brief_service = GenerateBriefService(uow, self._clock, self._ids)
                    brief = await brief_service.generate_in_transaction(
                        GenerateBriefCommand(
                            operation.id,
                            resulting.call_id,
                            recovery.after_operation_version,
                            resulting.id,
                            ("Driver delay was resolved inside the approved mandate.",),
                            ("The original pickup plan was no longer viable.",),
                            ("Activated the mandate-safe driver-delay replacement.",),
                            (),
                            command.correlation_id,
                        )
                    )
                    completed = replace(
                        attempt,
                        status=InboundCallStatus.COMPLETED,
                        completed_at=self._clock.now(),
                        completion_fingerprint=digest,
                        resulting_commitment_id=resulting.id,
                        resulting_evidence_id=recovery.resulting_evidence_id,
                        resulting_brief_id=brief.id,
                        recovery_attempt_id=recovery.id,
                        correlation_id=command.correlation_id,
                    )
                    await uow.inbound_call_attempts.update(completed)
                    updated_operation = await uow.operations.get(operation.id)
                    await uow.audit_events.add(
                        self._audit(
                            updated_operation,
                            "INBOUND_RECOVERY_COMPLETED",
                            command.correlation_id,
                        )
                    )
                    await uow.commit()
                    return completed
                except Exception:
                    await uow.rollback()
                    raise
        except Exception:
            await self._storage.delete(recording_reference)
            raise

    async def fail_inbound_call(self, command: FailInboundCallInput) -> InboundCallAttempt:
        from yuno_backend.volta.telephony.errors import InboundCallStateConflict

        async with self._uow_factory() as uow:
            try:
                attempt = await self._attempt(uow, command.provider_call_id)
                if attempt.status is InboundCallStatus.FAILED:
                    if attempt.failure_reason != command.reason_code:
                        raise InboundCallStateConflict()
                    await uow.rollback()
                    return attempt
                if attempt.status is InboundCallStatus.COMPLETED:
                    raise InboundCallStateConflict()
                failed = replace(
                    attempt,
                    status=InboundCallStatus.FAILED,
                    completed_at=self._clock.now(),
                    failure_reason=command.reason_code,
                )
                await uow.inbound_call_attempts.update(failed)
                await uow.commit()
                return failed
            except Exception:
                await uow.rollback()
                raise

    accept = accept_inbound_call
    record_consent = record_inbound_consent
    start_stream = start_inbound_stream
    complete = complete_inbound_recovery
    fail = fail_inbound_call

    async def _attempt(self, uow, provider_call_id: str) -> InboundCallAttempt:
        from yuno_backend.volta.telephony.errors import InboundCorrelationNotFound

        attempt = await uow.inbound_call_attempts.get_by_provider_call(
            provider_call_id, for_update=True
        )
        if attempt is None:
            raise InboundCorrelationNotFound()
        return attempt

    @staticmethod
    def _require_binding(attempt: InboundCallAttempt, token: str) -> None:
        from hmac import compare_digest

        from yuno_backend.volta.telephony.errors import InboundCallReplayConflict

        if not compare_digest(attempt.stream_binding_hash, sha256(token.encode()).hexdigest()):
            raise InboundCallReplayConflict()

    @staticmethod
    def _binding(attempt: InboundCallAttempt) -> InboundCallBinding:
        return InboundCallBinding(
            attempt.id,
            attempt.operation_id,
            attempt.commitment_id,
            attempt.call_id,
            attempt.provider_call_id,
            attempt.id.hex,
            attempt.expires_at,
        )

    @staticmethod
    def _completion_fingerprint(command: CompleteInboundRecoveryInput) -> str:
        value = "\x1f".join(
            (
                command.provider_call_id,
                sha256(command.post_consent_audio).hexdigest(),
                str(command.audio_start_ms),
                command.item_id,
                command.event_id,
                str(command.correlation_id),
            )
        )
        return sha256(value.encode()).hexdigest()

    def _audit(self, operation, event_type: str, correlation_id: UUID | None) -> AuditEvent:
        return AuditEvent(
            self._ids.new_id(),
            operation.id,
            operation.version,
            AuditActorKind.SYSTEM,
            event_type,
            self._clock.now(),
            correlation_id or self._ids.new_id(),
            {},
        )
