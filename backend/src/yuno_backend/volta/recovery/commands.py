"""Typed recovery application inputs."""

from dataclasses import dataclass
from uuid import UUID

from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.mandates.models import Money, PickupWindow
from yuno_backend.volta.negotiations.models import QuoteTerms
from yuno_backend.volta.recovery.models import EscalationContext, RecoveryScenario

__all__ = [
    "AcknowledgeNotificationCommand",
    "CreateEscalationCommand",
    "ReplaceMandateCommand",
    "ResumeAfterEscalationCommand",
    "SimulateInboundRecoveryCommand",
    "ReplacementEvidence",
]


@dataclass(frozen=True, slots=True)
class ReplacementEvidence:
    recording_reference: str
    audio_start_ms: int
    item_id: str
    event_id: str

    def __post_init__(self) -> None:
        for field in ("recording_reference", "item_id", "event_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip() or len(value) > 200:
                raise InvalidDomainValue(field, "bounded_text_required")
        if (
            not isinstance(self.audio_start_ms, int)
            or isinstance(self.audio_start_ms, bool)
            or self.audio_start_ms < 0
        ):
            raise InvalidDomainValue("audio_start_ms", "non_negative_integer_required")


@dataclass(frozen=True, slots=True)
class ReplaceMandateCommand:
    operation_id: UUID
    expected_operation_version: int
    resolved_escalation_id: UUID
    maximum_amount: Money
    pickup_window: PickupWindow
    allowed_conditions: tuple[str, ...]
    escalation_conditions: tuple[str, ...]
    approval_actor: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class CreateEscalationCommand:
    call_id: UUID
    expected_operation_version: int
    conflict: str
    attempted_alternatives: tuple[str, ...]
    recommended_action: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class AcknowledgeNotificationCommand:
    notification_id: UUID
    expected_operation_version: int
    acknowledged_by: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class SimulateInboundRecoveryCommand:
    operation_id: UUID
    expected_operation_version: int
    commitment_id: UUID
    mandate_version: int
    proposed_terms: QuoteTerms
    correlation_id: UUID
    scenario: RecoveryScenario
    decision_reason: str
    evidence: ReplacementEvidence | None
    escalation_context: EscalationContext | None


@dataclass(frozen=True, slots=True)
class ResumeAfterEscalationCommand:
    operation_id: UUID
    expected_operation_version: int
    escalation_id: UUID
    new_mandate_version: int
    correlation_id: UUID
