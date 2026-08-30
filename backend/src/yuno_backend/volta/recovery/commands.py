"""Typed recovery application inputs."""

from dataclasses import dataclass
from uuid import UUID

from yuno_backend.volta.negotiations.models import QuoteTerms

__all__ = ["ResumeAfterEscalationCommand", "SimulateInboundRecoveryCommand"]


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
