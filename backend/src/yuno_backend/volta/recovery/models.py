"""Frozen provider-neutral values for post-contact recovery."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from yuno_backend.volta.errors import InvalidDomainValue

__all__ = ["Notification", "PostContactEscalation", "RecoveryAttempt", "RecoveryOutcome"]

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


class RecoveryOutcome(StrEnum):
    REPLACED = "REPLACED"
    ESCALATED = "ESCALATED"


@dataclass(frozen=True, slots=True)
class RecoveryAttempt:
    id: UUID
    operation_id: UUID
    commitment_id: UUID
    outcome: RecoveryOutcome
    resulting_commitment_id: UUID | None
    escalation_id: UUID | None
    correlation_id: UUID
    created_at: datetime

    def __post_init__(self) -> None:
        for field in ("id", "operation_id", "commitment_id", "correlation_id"):
            _uuid(getattr(self, field), field)
        if not isinstance(self.outcome, RecoveryOutcome):
            raise InvalidDomainValue("outcome", "recovery_outcome_required")
        _optional_uuid(self.resulting_commitment_id, "resulting_commitment_id")
        _optional_uuid(self.escalation_id, "escalation_id")
        if self.outcome is RecoveryOutcome.REPLACED:
            if self.resulting_commitment_id is None or self.escalation_id is not None:
                raise InvalidDomainValue("outcome", "replaced_requires_resulting_commitment_only")
        elif self.resulting_commitment_id is not None or self.escalation_id is None:
            raise InvalidDomainValue("outcome", "escalated_requires_escalation_only")
        _utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class PostContactEscalation:
    id: UUID
    operation_id: UUID
    commitment_id: UUID
    reason_code: str
    operation_version: int
    mandate_version: int
    resolved: bool
    correlation_id: UUID
    created_at: datetime
    resolved_at: datetime | None = None

    def __post_init__(self) -> None:
        for field in ("id", "operation_id", "commitment_id", "correlation_id"):
            _uuid(getattr(self, field), field)
        _safe_code(self.reason_code, "reason_code")
        _version(self.operation_version, "operation_version")
        _version(self.mandate_version, "mandate_version")
        _utc(self.created_at, "created_at")
        if self.resolved_at is not None:
            _utc(self.resolved_at, "resolved_at")
        if self.resolved != (self.resolved_at is not None):
            raise InvalidDomainValue("resolved", "must_match_resolved_at")


@dataclass(frozen=True, slots=True)
class Notification:
    id: UUID
    operation_id: UUID
    commitment_id: UUID
    reason_code: str
    created_at: datetime

    def __post_init__(self) -> None:
        for field in ("id", "operation_id", "commitment_id"):
            _uuid(getattr(self, field), field)
        _safe_code(self.reason_code, "reason_code")
        _utc(self.created_at, "created_at")
