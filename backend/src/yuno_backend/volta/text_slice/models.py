"""Provider-neutral commands and projections for the integrated text slice."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from yuno_backend.volta.audit.models import AuditEvent
from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.evidence.models import AgreementEvidence
from yuno_backend.volta.mandates.models import IntakeDraft, Operation
from yuno_backend.volta.negotiations.models import (
    BrowserChannel,
    CarrierSession,
    Commitment,
    Negotiation,
    PreContactEscalation,
    Quote,
    QuoteComparison,
    QuoteTerms,
)

__all__ = [
    "ApproveOperationInput",
    "AuditQuoteProjection",
    "AuditProjection",
    "AttachCommitmentEvidenceInput",
    "CommitmentProjection",
    "CreateCommitmentInput",
    "CreateOperationDraftInput",
    "DraftProjection",
    "EscalationResolutionState",
    "MutationOutcome",
    "NegotiationProjection",
    "NegotiationSummaryProjection",
    "OperationProjection",
    "PreContactEscalationProjection",
    "RecordQuoteInput",
    "StartNegotiationInput",
    "SessionProjection",
]


@dataclass(frozen=True, slots=True)
class MutationOutcome[T]:
    value: T
    idempotency_replayed: bool


@dataclass(frozen=True, slots=True)
class CreateOperationDraftInput:
    source_prompt: str = field(repr=False)
    requested_language: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class ApproveOperationInput:
    draft_id: UUID
    expected_draft_version: int
    approval_actor: str
    correlation_id: UUID
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class StartNegotiationInput:
    operation_id: UUID
    expected_operation_version: int
    channel: BrowserChannel
    idempotency_key: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class RecordQuoteInput:
    call_id: UUID
    expected_operation_version: int
    carrier_id: UUID
    mandate_version: int
    terms: QuoteTerms
    valid_until: datetime
    idempotency_key: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class AttachCommitmentEvidenceInput:
    call_id: UUID
    expected_operation_version: int
    recording_reference: str
    audio_start_ms: int
    item_id: str
    event_id: str
    idempotency_key: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class EvidenceReservation:
    id: UUID
    operation_id: UUID
    call_id: UUID
    quote_id: UUID
    recording_reference: str
    audio_start_ms: int
    item_id: str
    event_id: str
    created_at: datetime
    consumed_by_commitment_id: UUID | None = None

    def __post_init__(self) -> None:
        for name in ("id", "operation_id", "call_id", "quote_id"):
            if not isinstance(getattr(self, name), UUID):
                raise InvalidDomainValue(name, "uuid_required")
        for name in ("recording_reference", "item_id", "event_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise InvalidDomainValue(name, "bounded_text_required")
        if isinstance(self.audio_start_ms, bool) or not isinstance(self.audio_start_ms, int):
            raise InvalidDomainValue("audio_start_ms", "non_negative_integer_required")
        if self.audio_start_ms < 0:
            raise InvalidDomainValue("audio_start_ms", "non_negative_integer_required")
        if self.created_at.utcoffset() != timedelta(0):
            raise InvalidDomainValue("created_at", "aware_utc_required")
        if self.consumed_by_commitment_id is not None and not isinstance(
            self.consumed_by_commitment_id, UUID
        ):
            raise InvalidDomainValue("consumed_by_commitment_id", "uuid_required")


@dataclass(frozen=True, slots=True)
class CreateCommitmentInput:
    call_id: UUID
    expected_operation_version: int
    quote_id: UUID
    mandate_version: int
    evidence_id: UUID
    idempotency_key: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class DraftProjection:
    draft: IntakeDraft


class EscalationResolutionState(StrEnum):
    OPEN = "OPEN"


@dataclass(frozen=True, slots=True)
class SessionProjection:
    session: CarrierSession
    ranking_evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PreContactEscalationProjection:
    escalation: PreContactEscalation
    conflict: str
    attempted_alternatives: tuple[str, ...]
    recommended_action: str
    resolution_state: EscalationResolutionState


@dataclass(frozen=True, slots=True)
class NegotiationProjection:
    negotiation: Negotiation
    sessions: tuple[SessionProjection, ...]
    pre_contact_escalation: PreContactEscalationProjection | None


@dataclass(frozen=True, slots=True)
class NegotiationSummaryProjection:
    negotiation_id: UUID
    selected_carrier_count: int
    active_session_count: int
    valid_quote_count: int


@dataclass(frozen=True, slots=True)
class CommitmentProjection:
    commitment: Commitment
    evidence: AgreementEvidence | None


@dataclass(frozen=True, slots=True)
class OperationProjection:
    operation: Operation
    negotiation: NegotiationProjection | None
    negotiation_summary: NegotiationSummaryProjection | None
    quotes: tuple[Quote, ...]
    quote_comparison: QuoteComparison | None
    active_commitment: CommitmentProjection | None
    audit_events: tuple[AuditEvent, ...]
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AuditProjection:
    operation_id: UUID
    events: tuple[AuditEvent, ...]
    negotiation: NegotiationProjection | None
    quote_comparison: tuple["AuditQuoteProjection", ...]
    commitment_history: tuple[CommitmentProjection, ...]


@dataclass(frozen=True, slots=True)
class AuditQuoteProjection:
    quote: Quote
    carrier_display_name: str
    selected: bool
