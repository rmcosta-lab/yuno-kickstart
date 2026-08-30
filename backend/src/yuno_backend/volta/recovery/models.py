"""Frozen provider-neutral values for post-contact recovery."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.mandates.models import OperationStatus
from yuno_backend.volta.negotiations.models import QuoteTerms

__all__ = [
    "EscalationContext",
    "Notification",
    "PostContactEscalation",
    "RecoveryAttempt",
    "RecoveryDecision",
    "RecoveryDecisionState",
    "RecoveryOutcome",
    "RecoveryScenario",
]

_MAX_TEXT_LENGTH = 200


def _uuid(value: object, field: str) -> None:
    if not isinstance(value, UUID):
        raise InvalidDomainValue(field, "uuid_required")


def _optional_uuid(value: object, field: str) -> None:
    if value is not None and not isinstance(value, UUID):
        raise InvalidDomainValue(field, "uuid_or_none_required")


def _version(value: object, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise InvalidDomainValue(field, "positive_integer_required")


def _utc(value: object, field: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise InvalidDomainValue(field, "aware_utc_required")


def _safe_code(value: object, field: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > _MAX_TEXT_LENGTH
        or not value.isascii()
        or not value.isprintable()
    ):
        raise InvalidDomainValue(field, "safe_code_required")


def _bounded_text(value: object, field: str) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 500
        or not value.isprintable()
    ):
        raise InvalidDomainValue(field, "bounded_printable_text_required")


@dataclass(frozen=True, slots=True)
class EscalationContext:
    conflict: str
    attempted_alternatives: tuple[str, ...]
    recommended_action: str

    def __post_init__(self) -> None:
        _bounded_text(self.conflict, "conflict")
        if not isinstance(self.attempted_alternatives, tuple) or len(
            self.attempted_alternatives
        ) > 25:
            raise InvalidDomainValue("attempted_alternatives", "bounded_tuple_required")
        for alternative in self.attempted_alternatives:
            _bounded_text(alternative, "attempted_alternatives")
        _bounded_text(self.recommended_action, "recommended_action")


@dataclass(frozen=True, slots=True)
class RecoveryDecisionState:
    operation_version: int
    operation_status: OperationStatus
    active_commitment_id: UUID | None = None
    carrier_id: UUID | None = None
    agreed_terms: QuoteTerms | None = None

    def __post_init__(self) -> None:
        _version(self.operation_version, "operation_version")
        if not isinstance(self.operation_status, OperationStatus):
            raise InvalidDomainValue("operation_status", "operation_status_required")
        _optional_uuid(self.active_commitment_id, "active_commitment_id")
        _optional_uuid(self.carrier_id, "carrier_id")
        commitment_context = (
            self.active_commitment_id,
            self.carrier_id,
            self.agreed_terms,
        )
        if any(value is None for value in commitment_context) and any(
            value is not None for value in commitment_context
        ):
            raise InvalidDomainValue("active_commitment_id", "commitment_context_incomplete")


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    before: RecoveryDecisionState
    after: RecoveryDecisionState
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.before, RecoveryDecisionState) or not isinstance(
            self.after, RecoveryDecisionState
        ):
            raise InvalidDomainValue("recovery_decision", "decision_state_required")
        _bounded_text(self.reason, "reason")


class RecoveryOutcome(StrEnum):
    REPLACED = "REPLACED"
    ESCALATED = "ESCALATED"


class RecoveryScenario(StrEnum):
    MANDATE_SAFE = "MANDATE_SAFE"
    OUT_OF_MANDATE = "OUT_OF_MANDATE"


@dataclass(frozen=True, slots=True)
class RecoveryAttempt:
    id: UUID
    operation_id: UUID
    commitment_id: UUID
    scenario: RecoveryScenario
    before_operation_version: int
    after_operation_version: int
    decision_reason: str
    outcome: RecoveryOutcome
    resulting_commitment_id: UUID | None
    escalation_id: UUID | None
    correlation_id: UUID
    created_at: datetime
    resulting_evidence_id: UUID | None = None

    def __post_init__(self) -> None:
        for field in ("id", "operation_id", "commitment_id", "correlation_id"):
            _uuid(getattr(self, field), field)
        if not isinstance(self.outcome, RecoveryOutcome):
            raise InvalidDomainValue("outcome", "recovery_outcome_required")
        if not isinstance(self.scenario, RecoveryScenario):
            raise InvalidDomainValue("scenario", "recovery_scenario_required")
        _version(self.before_operation_version, "before_operation_version")
        _version(self.after_operation_version, "after_operation_version")
        if self.after_operation_version != self.before_operation_version + 1:
            raise InvalidDomainValue("after_operation_version", "must_advance_once")
        _bounded_text(self.decision_reason, "decision_reason")
        _optional_uuid(self.resulting_commitment_id, "resulting_commitment_id")
        _optional_uuid(self.escalation_id, "escalation_id")
        _optional_uuid(self.resulting_evidence_id, "resulting_evidence_id")
        if self.outcome is RecoveryOutcome.REPLACED:
            if (
                self.resulting_commitment_id is None
                or self.resulting_evidence_id is None
                or self.escalation_id is not None
            ):
                raise InvalidDomainValue("outcome", "replaced_requires_resulting_commitment_only")
        elif (
            self.resulting_commitment_id is not None
            or self.resulting_evidence_id is not None
            or self.escalation_id is None
        ):
            raise InvalidDomainValue("outcome", "escalated_requires_escalation_only")
        if (self.scenario is RecoveryScenario.MANDATE_SAFE) != (
            self.outcome is RecoveryOutcome.REPLACED
        ):
            raise InvalidDomainValue("scenario", "must_match_outcome")
        _utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class PostContactEscalation:
    id: UUID
    operation_id: UUID
    commitment_id: UUID | None
    reason_code: str
    operation_version: int
    mandate_version: int
    resolved: bool
    correlation_id: UUID
    created_at: datetime
    resolved_at: datetime | None = None
    call_id: UUID | None = None
    context: EscalationContext | None = None

    def __post_init__(self) -> None:
        for field in ("id", "operation_id", "correlation_id"):
            _uuid(getattr(self, field), field)
        _optional_uuid(self.commitment_id, "commitment_id")
        _optional_uuid(self.call_id, "call_id")
        _safe_code(self.reason_code, "reason_code")
        _version(self.operation_version, "operation_version")
        _version(self.mandate_version, "mandate_version")
        _utc(self.created_at, "created_at")
        if self.resolved_at is not None:
            _utc(self.resolved_at, "resolved_at")
        if self.resolved != (self.resolved_at is not None):
            raise InvalidDomainValue("resolved", "must_match_resolved_at")
        if self.context is not None and not isinstance(self.context, EscalationContext):
            raise InvalidDomainValue("context", "escalation_context_required")
        if (self.call_id is None) != (self.context is None):
            raise InvalidDomainValue("context", "call_and_context_required_together")


@dataclass(frozen=True, slots=True)
class Notification:
    id: UUID
    operation_id: UUID
    commitment_id: UUID
    reason_code: str
    created_at: datetime
    operation_version: int | None = None
    recovery_decision: RecoveryDecision | None = None
    message: str | None = None
    correlation_id: UUID | None = None
    acknowledged_by: str | None = None
    acknowledged_at: datetime | None = None

    def __post_init__(self) -> None:
        for field in ("id", "operation_id", "commitment_id"):
            _uuid(getattr(self, field), field)
        _safe_code(self.reason_code, "reason_code")
        _utc(self.created_at, "created_at")
        if self.operation_version is not None:
            _version(self.operation_version, "operation_version")
        if self.recovery_decision is not None and not isinstance(
            self.recovery_decision, RecoveryDecision
        ):
            raise InvalidDomainValue("recovery_decision", "recovery_decision_required")
        if self.message is not None:
            _bounded_text(self.message, "message")
        _optional_uuid(self.correlation_id, "correlation_id")
        recovery_context = (
            self.operation_version,
            self.recovery_decision,
            self.message,
            self.correlation_id,
        )
        if any(value is None for value in recovery_context) and any(
            value is not None for value in recovery_context
        ):
            raise InvalidDomainValue("recovery_decision", "recovery_context_incomplete")
        if (self.acknowledged_by is None) != (self.acknowledged_at is None):
            raise InvalidDomainValue("acknowledged", "actor_and_timestamp_required_together")
        if self.acknowledged_by is not None:
            _bounded_text(self.acknowledged_by, "acknowledged_by")
            _utc(self.acknowledged_at, "acknowledged_at")

    @property
    def acknowledged(self) -> bool:
        return self.acknowledged_at is not None
