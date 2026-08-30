"""Immutable provider-neutral values for authorized outbound calls."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.idempotency import validate_idempotency_key

__all__ = [
    "HumanHandoff",
    "HumanHandoffCommand",
    "HumanHandoffContext",
    "HumanHandoffReservation",
    "HumanHandoffReadiness",
    "HumanHandoffStatus",
    "HumanHandoffStatusEvent",
    "OutboundCall",
    "OutboundCallAttempt",
    "OutboundCallAttemptReservation",
    "OutboundCallAttemptState",
    "OutboundCallAuthorization",
    "OutboundCallFailure",
    "OutboundCallFailureCategory",
    "OutboundCallRequest",
    "OutboundCallStatus",
    "OutboundCallStatusEvent",
    "OutboundCallUncertainReason",
    "OutboundCallUncertainState",
    "RecordingMode",
]

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256_HEX = re.compile(r"^[a-f0-9]{64}$")


def _uuid(value: object, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise InvalidDomainValue(field_name, "uuid_required")


def _safe_identifier(value: object, field_name: str) -> None:
    if not isinstance(value, str) or _SAFE_IDENTIFIER.fullmatch(value) is None:
        raise InvalidDomainValue(field_name, "safe_identifier_required")


def _utc(value: object, field_name: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise InvalidDomainValue(field_name, "aware_utc_required")


def _non_negative_integer(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise InvalidDomainValue(field_name, "non_negative_integer_required")


class RecordingMode(StrEnum):
    """Recording policy selected before provider dispatch."""

    DISABLED = "DISABLED"
    AFTER_EXPLICIT_CONSENT = "AFTER_EXPLICIT_CONSENT"


class HumanHandoffStatus(StrEnum):
    """Truthful, provider-neutral state of one coordinator takeover."""

    CONNECTING = "CONNECTING"
    JOINED = "JOINED"
    FAILED_SAFE = "FAILED_SAFE"
    TIMED_OUT_SAFE = "TIMED_OUT_SAFE"

    @property
    def is_terminal(self) -> bool:
        return self is not HumanHandoffStatus.CONNECTING


def _bounded_safe_texts(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        value = tuple(value) if isinstance(value, list) else value
    if (
        not isinstance(value, tuple)
        or len(value) > 20
        or any(
            not isinstance(item, str)
            or not item.strip()
            or len(item) > 300
            for item in value
        )
    ):
        raise InvalidDomainValue(field_name, "bounded_safe_texts_required")
    return value


@dataclass(frozen=True, slots=True)
class HumanHandoffContext:
    """Bounded coordinator context; raw transcripts and provider data are forbidden."""

    mandate_version: int
    mandate_facts: tuple[str, ...]
    eligible_quote_summaries: tuple[str, ...]
    structured_call_brief: tuple[str, ...]
    call_status: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.mandate_version, int)
            or isinstance(self.mandate_version, bool)
            or self.mandate_version < 1
        ):
            raise InvalidDomainValue("mandate_version", "positive_integer_required")
        object.__setattr__(
            self, "mandate_facts", _bounded_safe_texts(self.mandate_facts, "mandate_facts")
        )
        object.__setattr__(
            self,
            "eligible_quote_summaries",
            _bounded_safe_texts(
                self.eligible_quote_summaries, "eligible_quote_summaries"
            ),
        )
        object.__setattr__(
            self,
            "structured_call_brief",
            _bounded_safe_texts(self.structured_call_brief, "structured_call_brief"),
        )
        _safe_identifier(self.call_status, "call_status")


@dataclass(frozen=True, slots=True)
class HumanHandoffCommand:
    call_id: UUID
    idempotency_key: str = field(repr=False)
    coordinator_destination_label: str
    authorized_by: str
    authorized_at: datetime
    expected_call_status_updated_at: datetime
    correlation_id: UUID

    def __post_init__(self) -> None:
        _uuid(self.call_id, "call_id")
        validate_idempotency_key(self.idempotency_key)
        _safe_identifier(
            self.coordinator_destination_label, "coordinator_destination_label"
        )
        _safe_identifier(self.authorized_by, "authorized_by")
        _utc(self.authorized_at, "authorized_at")
        _utc(self.expected_call_status_updated_at, "expected_call_status_updated_at")
        _uuid(self.correlation_id, "correlation_id")


@dataclass(frozen=True, slots=True)
class HumanHandoff:
    handoff_id: UUID
    call_id: UUID
    coordinator_destination_label: str
    idempotency_key: str = field(repr=False)
    request_fingerprint: str = field(repr=False)
    status: HumanHandoffStatus
    requested_at: datetime
    status_updated_at: datetime
    context: HumanHandoffContext
    last_status_event_id: str | None = None
    last_status_sequence_number: int | None = None
    processed_status_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _uuid(self.handoff_id, "handoff_id")
        _uuid(self.call_id, "call_id")
        _safe_identifier(
            self.coordinator_destination_label, "coordinator_destination_label"
        )
        validate_idempotency_key(self.idempotency_key)
        if _SHA256_HEX.fullmatch(self.request_fingerprint) is None:
            raise InvalidDomainValue("request_fingerprint", "sha256_hex_required")
        if not isinstance(self.status, HumanHandoffStatus):
            raise InvalidDomainValue("status", "human_handoff_status_required")
        _utc(self.requested_at, "requested_at")
        _utc(self.status_updated_at, "status_updated_at")
        if self.status_updated_at < self.requested_at:
            raise InvalidDomainValue("status_updated_at", "must_not_precede_requested_at")
        if not isinstance(self.context, HumanHandoffContext):
            raise InvalidDomainValue("context", "human_handoff_context_required")
        cursor = (self.last_status_event_id, self.last_status_sequence_number)
        if (cursor[0] is None) != (cursor[1] is None):
            raise InvalidDomainValue("status_event_cursor", "complete_cursor_required")
        if self.last_status_event_id is not None:
            _safe_identifier(self.last_status_event_id, "last_status_event_id")
            _non_negative_integer(
                self.last_status_sequence_number, "last_status_sequence_number"
            )
        if not isinstance(self.processed_status_event_ids, tuple):
            object.__setattr__(
                self, "processed_status_event_ids", tuple(self.processed_status_event_ids)
            )
        if (
            len(self.processed_status_event_ids) > 128
            or len(set(self.processed_status_event_ids))
            != len(self.processed_status_event_ids)
        ):
            raise InvalidDomainValue(
                "processed_status_event_ids", "unique_bounded_events_required"
            )
        for event_id in self.processed_status_event_ids:
            _safe_identifier(event_id, "processed_status_event_ids")


@dataclass(frozen=True, slots=True)
class HumanHandoffReservation:
    handoff: HumanHandoff
    created: bool

    def __post_init__(self) -> None:
        if not isinstance(self.handoff, HumanHandoff):
            raise InvalidDomainValue("handoff", "human_handoff_required")
        if not isinstance(self.created, bool):
            raise InvalidDomainValue("created", "boolean_required")


@dataclass(frozen=True, slots=True)
class HumanHandoffReadiness:
    """Durable safe snapshot required before an explicit takeover request."""

    call_id: UUID
    call_status_updated_at: datetime
    context: HumanHandoffContext

    def __post_init__(self) -> None:
        _uuid(self.call_id, "call_id")
        _utc(self.call_status_updated_at, "call_status_updated_at")
        if not isinstance(self.context, HumanHandoffContext):
            raise InvalidDomainValue("context", "human_handoff_context_required")


@dataclass(frozen=True, slots=True)
class HumanHandoffStatusEvent:
    provider_event_id: str
    handoff_id: UUID
    call_id: UUID
    status: HumanHandoffStatus
    sequence_number: int
    observed_at: datetime
    remote_participant_present: bool
    coordinator_participant_present: bool

    def __post_init__(self) -> None:
        _safe_identifier(self.provider_event_id, "provider_event_id")
        _uuid(self.handoff_id, "handoff_id")
        _uuid(self.call_id, "call_id")
        if not isinstance(self.status, HumanHandoffStatus):
            raise InvalidDomainValue("status", "human_handoff_status_required")
        _non_negative_integer(self.sequence_number, "sequence_number")
        _utc(self.observed_at, "observed_at")
        if not isinstance(self.remote_participant_present, bool) or not isinstance(
            self.coordinator_participant_present, bool
        ):
            raise InvalidDomainValue("participant_evidence", "boolean_required")
        if self.status is HumanHandoffStatus.JOINED and not (
            self.remote_participant_present and self.coordinator_participant_present
        ):
            raise InvalidDomainValue(
                "participant_evidence", "joined_requires_both_participants"
            )


class OutboundCallStatus(StrEnum):
    """Allowlisted provider-neutral outbound call lifecycle."""

    QUEUED = "QUEUED"
    INITIATED = "INITIATED"
    RINGING = "RINGING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BUSY = "BUSY"
    FAILED = "FAILED"
    NO_ANSWER = "NO_ANSWER"
    CANCELED = "CANCELED"

    @property
    def is_terminal(self) -> bool:
        return self in {
            OutboundCallStatus.COMPLETED,
            OutboundCallStatus.BUSY,
            OutboundCallStatus.FAILED,
            OutboundCallStatus.NO_ANSWER,
            OutboundCallStatus.CANCELED,
        }


class OutboundCallAttemptState(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    UNCERTAIN = "UNCERTAIN"
    FAILED = "FAILED"


class OutboundCallUncertainReason(StrEnum):
    TIMEOUT = "TIMEOUT"
    CONNECTION_LOST = "CONNECTION_LOST"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"


class OutboundCallFailureCategory(StrEnum):
    AUTHENTICATION = "AUTHENTICATION"
    PERMISSION = "PERMISSION"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    CONNECTION = "CONNECTION"
    INVALID_REQUEST = "INVALID_REQUEST"
    PROVIDER_REJECTED = "PROVIDER_REJECTED"
    INVALID_RESPONSE = "INVALID_RESPONSE"


@dataclass(frozen=True, slots=True)
class OutboundCallAuthorization:
    """Bounded evidence of one explicit human dialing authorization."""

    actor_id: str
    authorized_at: datetime
    ai_disclosure_required: bool = True
    recording_mode: RecordingMode = RecordingMode.DISABLED
    recording_consent_required: bool = False

    def __post_init__(self) -> None:
        _safe_identifier(self.actor_id, "actor_id")
        _utc(self.authorized_at, "authorized_at")
        if self.ai_disclosure_required is not True:
            raise InvalidDomainValue("ai_disclosure_required", "true_required")
        if not isinstance(self.recording_mode, RecordingMode):
            raise InvalidDomainValue("recording_mode", "recording_mode_required")
        if not isinstance(self.recording_consent_required, bool):
            raise InvalidDomainValue("recording_consent_required", "boolean_required")
        consent_expected = self.recording_mode is RecordingMode.AFTER_EXPLICIT_CONSENT
        if self.recording_consent_required is not consent_expected:
            raise InvalidDomainValue(
                "recording_consent_required", "must_match_recording_mode"
            )


@dataclass(frozen=True, slots=True)
class OutboundCallRequest:
    """Logical call request with no destination number or provider payload."""

    operation_id: UUID
    call_session_id: UUID
    correlation_id: UUID
    idempotency_key: str
    destination_label: str
    authorization: OutboundCallAuthorization

    def __post_init__(self) -> None:
        _uuid(self.operation_id, "operation_id")
        _uuid(self.call_session_id, "call_session_id")
        _uuid(self.correlation_id, "correlation_id")
        validate_idempotency_key(self.idempotency_key)
        _safe_identifier(self.destination_label, "destination_label")
        if not isinstance(self.authorization, OutboundCallAuthorization):
            raise InvalidDomainValue("authorization", "outbound_authorization_required")


@dataclass(frozen=True, slots=True)
class OutboundCall:
    """Normalized call result and latest accepted lifecycle cursor."""

    call_session_id: UUID
    provider_call_id: str
    status: OutboundCallStatus
    created_at: datetime
    status_updated_at: datetime | None = None
    last_status_event_id: str | None = None
    last_status_sequence_number: int | None = None
    processed_status_event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _uuid(self.call_session_id, "call_session_id")
        _safe_identifier(self.provider_call_id, "provider_call_id")
        if not isinstance(self.status, OutboundCallStatus):
            raise InvalidDomainValue("status", "outbound_call_status_required")
        _utc(self.created_at, "created_at")
        if self.status_updated_at is None:
            object.__setattr__(self, "status_updated_at", self.created_at)
        else:
            _utc(self.status_updated_at, "status_updated_at")
            if self.status_updated_at < self.created_at:
                raise InvalidDomainValue("status_updated_at", "must_not_precede_created_at")
        event_cursor_values = (
            self.last_status_event_id,
            self.last_status_sequence_number,
        )
        if (event_cursor_values[0] is None) != (event_cursor_values[1] is None):
            raise InvalidDomainValue("status_event_cursor", "complete_cursor_required")
        if self.last_status_event_id is not None:
            _safe_identifier(self.last_status_event_id, "last_status_event_id")
            _non_negative_integer(
                self.last_status_sequence_number, "last_status_sequence_number"
            )
        if not isinstance(self.processed_status_event_ids, tuple):
            object.__setattr__(
                self, "processed_status_event_ids", tuple(self.processed_status_event_ids)
            )
        if (
            len(self.processed_status_event_ids) > 128
            or len(set(self.processed_status_event_ids))
            != len(self.processed_status_event_ids)
        ):
            raise InvalidDomainValue(
                "processed_status_event_ids", "unique_bounded_events_required"
            )
        for event_id in self.processed_status_event_ids:
            _safe_identifier(event_id, "processed_status_event_ids")
        if (
            self.last_status_event_id is not None
            and self.last_status_event_id not in self.processed_status_event_ids
        ):
            raise InvalidDomainValue(
                "processed_status_event_ids", "must_include_last_status_event"
            )


@dataclass(frozen=True, slots=True)
class OutboundCallStatusEvent:
    """Normalized callback observation with provider ordering metadata."""

    provider_event_id: str
    provider_call_id: str
    status: OutboundCallStatus
    sequence_number: int
    observed_at: datetime

    def __post_init__(self) -> None:
        _safe_identifier(self.provider_event_id, "provider_event_id")
        _safe_identifier(self.provider_call_id, "provider_call_id")
        if not isinstance(self.status, OutboundCallStatus):
            raise InvalidDomainValue("status", "outbound_call_status_required")
        _non_negative_integer(self.sequence_number, "sequence_number")
        _utc(self.observed_at, "observed_at")


@dataclass(frozen=True, slots=True)
class OutboundCallUncertainState:
    """Safe durable marker for a dispatch whose provider outcome is unknown."""

    reason: OutboundCallUncertainReason
    occurred_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.reason, OutboundCallUncertainReason):
            raise InvalidDomainValue("reason", "uncertain_reason_required")
        _utc(self.occurred_at, "occurred_at")


@dataclass(frozen=True, slots=True)
class OutboundCallFailure:
    """Durable definitive failure without provider text or payloads."""

    category: OutboundCallFailureCategory
    occurred_at: datetime
    status_code: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.category, OutboundCallFailureCategory):
            raise InvalidDomainValue("category", "outbound_call_failure_category_required")
        _utc(self.occurred_at, "occurred_at")
        if self.status_code is not None and (
            not isinstance(self.status_code, int)
            or isinstance(self.status_code, bool)
            or not 100 <= self.status_code <= 599
        ):
            raise InvalidDomainValue("status_code", "http_status_code_required")


@dataclass(frozen=True, slots=True)
class OutboundCallAttempt:
    """Durable result of one logical idempotent call-creation attempt."""

    operation_id: UUID
    idempotency_key: str = field(repr=False)
    request_fingerprint: str
    state: OutboundCallAttemptState
    result: OutboundCall | None
    uncertainty: OutboundCallUncertainState | None
    failure: OutboundCallFailure | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _uuid(self.operation_id, "operation_id")
        validate_idempotency_key(self.idempotency_key)
        if not isinstance(self.request_fingerprint, str) or _SHA256_HEX.fullmatch(
            self.request_fingerprint
        ) is None:
            raise InvalidDomainValue("request_fingerprint", "sha256_hex_required")
        if not isinstance(self.state, OutboundCallAttemptState):
            raise InvalidDomainValue("state", "outbound_call_attempt_state_required")
        _utc(self.created_at, "created_at")
        _utc(self.updated_at, "updated_at")
        if self.updated_at < self.created_at:
            raise InvalidDomainValue("updated_at", "must_not_precede_created_at")
        if self.state is OutboundCallAttemptState.PENDING:
            valid_payload = (
                self.result is None and self.uncertainty is None and self.failure is None
            )
        elif self.state is OutboundCallAttemptState.SUCCEEDED:
            valid_payload = (
                isinstance(self.result, OutboundCall)
                and self.uncertainty is None
                and self.failure is None
            )
        elif self.state is OutboundCallAttemptState.UNCERTAIN:
            valid_payload = self.result is None and isinstance(
                self.uncertainty, OutboundCallUncertainState
            ) and self.failure is None
        else:
            valid_payload = (
                self.result is None
                and self.uncertainty is None
                and isinstance(self.failure, OutboundCallFailure)
            )
        if not valid_payload:
            raise InvalidDomainValue("attempt_payload", "must_match_attempt_state")


@dataclass(frozen=True, slots=True)
class OutboundCallAttemptReservation:
    """Atomic reservation result that elects exactly one provider dispatcher."""

    attempt: OutboundCallAttempt
    created: bool

    def __post_init__(self) -> None:
        if not isinstance(self.attempt, OutboundCallAttempt):
            raise InvalidDomainValue("attempt", "outbound_call_attempt_required")
        if not isinstance(self.created, bool):
            raise InvalidDomainValue("created", "boolean_required")
        if self.created and self.attempt.state is not OutboundCallAttemptState.PENDING:
            raise InvalidDomainValue("attempt", "new_reservation_must_be_pending")
