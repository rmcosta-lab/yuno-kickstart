"""Typed inputs for mandate application services."""

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from yuno_backend.volta.mandates.models import MandateAction, Money, OperationProposal

__all__ = ["ApproveOperationCommand", "CheckMandateCommand", "CreateIntakeDraftCommand"]


@dataclass(frozen=True, slots=True)
class CreateIntakeDraftCommand:
    source_prompt: str = field(repr=False)
    requested_language: str
    extraction_policy_version: str
    proposal: OperationProposal


@dataclass(frozen=True, slots=True)
class ApproveOperationCommand:
    draft_id: UUID
    expected_draft_version: int
    approval_actor: str


@dataclass(frozen=True, slots=True)
class CheckMandateCommand:
    operation_id: UUID
    mandate_version: int
    action: MandateAction
    proposed_amount: Money
    proposed_pickup_date: date
    proposed_conditions: tuple[str, ...] = ()
