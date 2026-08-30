"""Typed recovery application inputs."""

from dataclasses import dataclass
from uuid import UUID

from yuno_backend.volta.mandates.models import Money, PickupWindow
from yuno_backend.volta.negotiations.models import QuoteTerms

__all__ = [
    "AcknowledgeNotificationCommand",
    "CreateEscalationCommand",
    "ReplaceMandateCommand",
    "ResumeAfterEscalationCommand",
    "SimulateInboundRecoveryCommand",
]


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


@dataclass(frozen=True, slots=True)
class ResumeAfterEscalationCommand:
    operation_id: UUID
    expected_operation_version: int
    escalation_id: UUID
    new_mandate_version: int
    correlation_id: UUID
