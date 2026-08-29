"""P0 browser request and response contracts for the Volta journey."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import (
    ActorKind,
    BrowserChannel,
    CallState,
    CommitmentDisposition,
    CurrencyCode,
    EvidenceLifecycle,
    LongText,
    MinorAmount,
    MoneyTerms,
    NonNegativeMilliseconds,
    OpaqueCursor,
    OperationStatus,
    PickupWindow,
    PositiveVersion,
    QuoteEligibility,
    RecoveryScenario,
    RequestedLanguage,
    ResolutionState,
    ResponseModel,
    RouteDetails,
    SafeIdentifier,
    ShortText,
    SimulatedDirection,
    StrictRequestModel,
    UtcTimestamp,
)


class ValidationIssue(ResponseModel):
    field: ShortText
    message: ShortText


class ProposedMandate(ResponseModel):
    maximum_amount_minor: MinorAmount
    currency: CurrencyCode
    pickup_window: PickupWindow
    allowed_conditions: list[ShortText] = Field(default_factory=list, max_length=25)
    escalation_conditions: list[ShortText] = Field(default_factory=list, max_length=25)


class CreateOperationDraftRequest(StrictRequestModel):
    source_prompt: LongText
    requested_language: RequestedLanguage
    extraction_policy_version: SafeIdentifier


class OperationDraftResponse(ResponseModel):
    draft_id: UUID
    source_prompt: LongText
    requested_language: RequestedLanguage
    extraction_policy_version: SafeIdentifier
    proposed_route: RouteDetails
    proposed_pickup_date: date
    proposed_mandate: ProposedMandate
    validation_issues: list[ValidationIssue] = Field(default_factory=list, max_length=50)
    approval_eligible: bool
    draft_version: PositiveVersion
    created_at: UtcTimestamp
    updated_at: UtcTimestamp


class ApproveOperationRequest(StrictRequestModel):
    draft_id: UUID
    expected_draft_version: PositiveVersion
    approval_actor: ShortText


class MandateResponse(ResponseModel):
    mandate_id: UUID
    version: PositiveVersion
    maximum_amount_minor: MinorAmount
    currency: CurrencyCode
    pickup_window: PickupWindow
    allowed_conditions: list[ShortText] = Field(default_factory=list, max_length=25)
    escalation_conditions: list[ShortText] = Field(default_factory=list, max_length=25)
    approval_actor: ShortText
    approved_at: UtcTimestamp


class CarrierResponse(ResponseModel):
    carrier_id: UUID
    display_name: ShortText
    eligible: bool
    deterministic_rank: Annotated[int, Field(ge=1, le=3)]
    ranking_evidence: list[ShortText] = Field(default_factory=list, max_length=10)


class CarrierSessionResponse(ResponseModel):
    call_id: UUID
    carrier: CarrierResponse
    channel: BrowserChannel
    direction: SimulatedDirection
    state: CallState
    started_at: UtcTimestamp | None = None
    ended_at: UtcTimestamp | None = None


class NegotiationSummary(ResponseModel):
    negotiation_id: UUID
    selected_carrier_count: Annotated[int, Field(ge=0, le=3)]
    active_session_count: Annotated[int, Field(ge=0, le=3)]
    valid_quote_count: Annotated[int, Field(ge=0)]


class CommitmentEvidenceResponse(ResponseModel):
    evidence_id: UUID
    call_id: UUID
    recording_reference: SafeIdentifier
    audio_start_ms: NonNegativeMilliseconds
    item_id: SafeIdentifier
    event_id: SafeIdentifier
    lifecycle: EvidenceLifecycle
    created_at: UtcTimestamp


class CommitmentResponse(ResponseModel):
    commitment_id: UUID
    operation_id: UUID
    call_id: UUID
    quote_id: UUID
    carrier_id: UUID
    agreed_terms: MoneyTerms
    mandate_version: PositiveVersion
    evidence: CommitmentEvidenceResponse
    lifecycle: EvidenceLifecycle
    disposition: CommitmentDisposition
    replaces_commitment_id: UUID | None = None
    created_at: UtcTimestamp
    superseded_at: UtcTimestamp | None = None


class EscalationResponse(ResponseModel):
    escalation_id: UUID
    operation_id: UUID
    call_id: UUID | None = None
    conflict: ShortText
    attempted_alternatives: list[ShortText] = Field(default_factory=list, max_length=25)
    recommended_action: ShortText
    resolution_state: ResolutionState
    correlation_id: UUID
    created_at: UtcTimestamp
    resolved_at: UtcTimestamp | None = None


class CoordinatorNotificationResponse(ResponseModel):
    notification_id: UUID
    operation_id: UUID
    message: ShortText
    acknowledged: bool
    acknowledged_by: ShortText | None = None
    acknowledged_at: UtcTimestamp | None = None
    correlation_id: UUID
    created_at: UtcTimestamp


class OperationResponse(ResponseModel):
    operation_id: UUID
    route: RouteDetails
    cargo_label: ShortText
    status: OperationStatus
    operation_version: PositiveVersion
    active_mandate: MandateResponse
    negotiation_summary: NegotiationSummary | None = None
    active_commitment: CommitmentResponse | None = None
    open_escalation: EscalationResponse | None = None
    notifications: list[CoordinatorNotificationResponse] = Field(default_factory=list)
    created_at: UtcTimestamp
    updated_at: UtcTimestamp


class StartNegotiationRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    channel: BrowserChannel


class NegotiationResponse(ResponseModel):
    negotiation_id: UUID
    operation_id: UUID
    operation_version: PositiveVersion
    sessions: list[CarrierSessionResponse] = Field(default_factory=list, max_length=3)
    pre_contact_escalation: EscalationResponse | None = None
    started_at: UtcTimestamp


class QuoteTermsRequest(StrictRequestModel):
    amount_minor: MinorAmount
    currency: CurrencyCode
    pickup_window: PickupWindow
    conditions: list[ShortText] = Field(default_factory=list, max_length=25)


class CreateQuoteRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    carrier_id: UUID
    mandate_version: PositiveVersion
    terms: QuoteTermsRequest
    valid_until: UtcTimestamp


class QuoteResponse(ResponseModel):
    quote_id: UUID
    operation_id: UUID
    call_id: UUID
    carrier_id: UUID
    terms: MoneyTerms
    valid_until: UtcTimestamp
    mandate_version: PositiveVersion
    eligibility: QuoteEligibility
    rejection_reasons: list[ShortText] = Field(default_factory=list, max_length=25)
    created_at: UtcTimestamp


class CreateCommitmentEvidenceRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    recording_reference: SafeIdentifier
    audio_start_ms: NonNegativeMilliseconds
    item_id: SafeIdentifier
    event_id: SafeIdentifier


class CreateCommitmentRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    quote_id: UUID
    mandate_version: PositiveVersion
    evidence_id: UUID


class CreateSimulatedRecapRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    commitment_id: UUID
    rendered_content: LongText


class WrittenRecapResponse(ResponseModel):
    recap_id: UUID
    operation_id: UUID
    call_id: UUID
    commitment_id: UUID
    channel: Literal["SIMULATED"]
    content_hash: SafeIdentifier
    rendered_content: LongText
    created_at: UtcTimestamp


class CreateCallBriefRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    facts: list[ShortText] = Field(default_factory=list, max_length=50)
    objections: list[ShortText] = Field(default_factory=list, max_length=50)
    changes: list[ShortText] = Field(default_factory=list, max_length=50)
    unresolved_items: list[ShortText] = Field(default_factory=list, max_length=50)


class CallBriefResponse(ResponseModel):
    brief_id: UUID
    operation_id: UUID
    call_id: UUID
    facts: list[ShortText] = Field(default_factory=list, max_length=50)
    objections: list[ShortText] = Field(default_factory=list, max_length=50)
    changes: list[ShortText] = Field(default_factory=list, max_length=50)
    unresolved_items: list[ShortText] = Field(default_factory=list, max_length=50)
    created_at: UtcTimestamp


class StartInboundSimulationRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    scenario: RecoveryScenario
    active_commitment_id: UUID


class RecoverySimulationResponse(ResponseModel):
    recovery_id: UUID
    operation_id: UUID
    scenario: RecoveryScenario
    before_operation_version: PositiveVersion
    after_operation_version: PositiveVersion
    decision_reason: ShortText
    active_commitment: CommitmentResponse | None = None
    escalation: EscalationResponse | None = None
    correlation_id: UUID
    created_at: UtcTimestamp


class ReplaceMandateRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    resolved_escalation_id: UUID
    maximum_amount_minor: MinorAmount
    currency: CurrencyCode
    pickup_window: PickupWindow
    allowed_conditions: list[ShortText] = Field(default_factory=list, max_length=25)
    escalation_conditions: list[ShortText] = Field(default_factory=list, max_length=25)
    approval_actor: ShortText


class CreateEscalationRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    conflict: ShortText
    attempted_alternatives: list[ShortText] = Field(default_factory=list, max_length=25)
    recommended_action: ShortText


class AcknowledgeNotificationRequest(StrictRequestModel):
    expected_operation_version: PositiveVersion
    acknowledged_by: ShortText


SafeMetadataValue = str | int | bool | None


class AuditEventResponse(ResponseModel):
    event_id: UUID
    operation_version: PositiveVersion
    actor_kind: ActorKind
    event_type: SafeIdentifier
    occurred_at: UtcTimestamp
    correlation_id: UUID
    metadata: dict[str, SafeMetadataValue] = Field(default_factory=dict)


class QuoteComparisonRow(ResponseModel):
    quote_id: UUID
    carrier_id: UUID
    amount_minor: MinorAmount
    currency: CurrencyCode
    eligible: bool
    selected: bool
    rejection_reasons: list[ShortText] = Field(default_factory=list, max_length=25)


class AuditTimelineResponse(ResponseModel):
    operation_id: UUID
    events: list[AuditEventResponse]
    quote_comparison: list[QuoteComparisonRow]
    next_cursor: OpaqueCursor | None = None
