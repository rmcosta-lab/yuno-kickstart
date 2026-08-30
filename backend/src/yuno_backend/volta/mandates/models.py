"""Immutable provider-neutral operation and mandate domain values."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from yuno_backend.volta.mandates.errors import InvalidDomainValue

__all__ = [
    "DraftValidationIssue",
    "IntakeDraft",
    "Mandate",
    "MandateAction",
    "MandateDecision",
    "MandateProposal",
    "Money",
    "Operation",
    "OperationStatus",
    "OperationStatusEntry",
    "OperationProposal",
    "PickupWindow",
    "Route",
]


def _require_uuid(value: object, field_name: str) -> None:
    if not isinstance(value, UUID):
        raise InvalidDomainValue(field_name, "uuid_required")


def _require_positive_version(value: object, field_name: str = "version") -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise InvalidDomainValue(field_name, "positive_integer_required")


def _require_utc(value: object, field_name: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise InvalidDomainValue(field_name, "aware_utc_required")


def _require_tuple(value: object, field_name: str) -> None:
    if not isinstance(value, tuple):
        raise InvalidDomainValue(field_name, "tuple_required")


def _require_date(value: object, field_name: str) -> None:
    if type(value) is not date:
        raise InvalidDomainValue(field_name, "date_required")


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite():
            raise InvalidDomainValue("amount", "finite_decimal_required")
        if not isinstance(self.currency, str):
            raise InvalidDomainValue("currency", "string_required")


@dataclass(frozen=True, slots=True)
class Route:
    origin: str
    destination: str

    def __post_init__(self) -> None:
        if not isinstance(self.origin, str) or not isinstance(self.destination, str):
            raise InvalidDomainValue("route", "string_endpoints_required")


@dataclass(frozen=True, slots=True)
class PickupWindow:
    start_date: date
    end_date: date

    def __post_init__(self) -> None:
        _require_date(self.start_date, "pickup_window.start_date")
        _require_date(self.end_date, "pickup_window.end_date")


@dataclass(frozen=True, slots=True)
class MandateProposal:
    maximum_amount: Money
    pickup_window: PickupWindow
    allowed_conditions: tuple[str, ...] = ()
    escalation_conditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.maximum_amount, Money):
            raise InvalidDomainValue("maximum_amount", "money_required")
        if not isinstance(self.pickup_window, PickupWindow):
            raise InvalidDomainValue("pickup_window", "pickup_window_required")
        _require_tuple(self.allowed_conditions, "allowed_conditions")
        _require_tuple(self.escalation_conditions, "escalation_conditions")


@dataclass(frozen=True, slots=True)
class OperationProposal:
    route: Route
    pickup_date: date
    cargo_label: str
    mandate: MandateProposal

    def __post_init__(self) -> None:
        if not isinstance(self.route, Route):
            raise InvalidDomainValue("route", "route_required")
        _require_date(self.pickup_date, "pickup_date")
        if not isinstance(self.cargo_label, str):
            raise InvalidDomainValue("cargo_label", "string_required")
        if not isinstance(self.mandate, MandateProposal):
            raise InvalidDomainValue("mandate", "mandate_proposal_required")


@dataclass(frozen=True, slots=True)
class DraftValidationIssue:
    field: str
    reason_code: str

    def __post_init__(self) -> None:
        if not self.field or not self.reason_code:
            raise InvalidDomainValue("validation_issue", "safe_codes_required")


@dataclass(frozen=True, slots=True)
class IntakeDraft:
    id: UUID
    source_prompt: str = field(repr=False)
    requested_language: str
    extraction_policy_version: str
    proposal: OperationProposal
    validation_issues: tuple[DraftValidationIssue, ...]
    approval_eligible: bool
    version: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        _require_uuid(self.id, "id")
        if not isinstance(self.source_prompt, str):
            raise InvalidDomainValue("source_prompt", "string_required")
        if not isinstance(self.requested_language, str):
            raise InvalidDomainValue("requested_language", "string_required")
        if not isinstance(self.extraction_policy_version, str):
            raise InvalidDomainValue("extraction_policy_version", "string_required")
        if not isinstance(self.proposal, OperationProposal):
            raise InvalidDomainValue("proposal", "operation_proposal_required")
        _require_tuple(self.validation_issues, "validation_issues")
        if not all(isinstance(issue, DraftValidationIssue) for issue in self.validation_issues):
            raise InvalidDomainValue("validation_issues", "validation_issue_items_required")
        _require_positive_version(self.version)
        _require_utc(self.created_at, "created_at")
        _require_utc(self.updated_at, "updated_at")
        if self.approval_eligible != (not self.validation_issues):
            raise InvalidDomainValue("approval_eligible", "must_match_validation_issues")


class MandateAction(StrEnum):
    NEGOTIATE = "NEGOTIATE"
    COMMIT = "COMMIT"


class OperationStatus(StrEnum):
    READY = "READY"
    NEGOTIATING = "NEGOTIATING"
    COMMITTED = "COMMITTED"
    ESCALATED = "ESCALATED"
    COMPLETED = "COMPLETED"


@dataclass(frozen=True, slots=True)
class OperationStatusEntry:
    id: UUID
    operation_id: UUID
    operation_version: int
    status: OperationStatus
    occurred_at: datetime

    def __post_init__(self) -> None:
        _require_uuid(self.id, "id")
        _require_uuid(self.operation_id, "operation_id")
        _require_positive_version(self.operation_version, "operation_version")
        if not isinstance(self.status, OperationStatus):
            raise InvalidDomainValue("status", "operation_status_required")
        _require_utc(self.occurred_at, "occurred_at")


@dataclass(frozen=True, slots=True)
class Mandate:
    id: UUID
    operation_id: UUID
    version: int
    maximum_amount: Money
    pickup_window: PickupWindow
    allowed_conditions: tuple[str, ...]
    escalation_conditions: tuple[str, ...]
    authorized_actions: tuple[MandateAction, ...]
    approval_actor: str
    approved_at: datetime

    def __post_init__(self) -> None:
        _require_uuid(self.id, "id")
        _require_uuid(self.operation_id, "operation_id")
        _require_positive_version(self.version)
        if not isinstance(self.maximum_amount, Money):
            raise InvalidDomainValue("maximum_amount", "money_required")
        if not isinstance(self.pickup_window, PickupWindow):
            raise InvalidDomainValue("pickup_window", "pickup_window_required")
        _require_tuple(self.allowed_conditions, "allowed_conditions")
        _require_tuple(self.escalation_conditions, "escalation_conditions")
        _require_tuple(self.authorized_actions, "authorized_actions")
        if not all(isinstance(action, MandateAction) for action in self.authorized_actions):
            raise InvalidDomainValue("authorized_actions", "mandate_action_items_required")
        if (
            not isinstance(self.approval_actor, str)
            or not self.approval_actor.strip()
            or len(self.approval_actor) > 500
        ):
            raise InvalidDomainValue("approval_actor", "bounded_non_empty_required")
        _require_utc(self.approved_at, "approved_at")


@dataclass(frozen=True, slots=True)
class Operation:
    id: UUID
    version: int
    source_draft_id: UUID
    source_draft_version: int
    route: Route
    pickup_date: date
    cargo_label: str
    mandate: Mandate
    status: OperationStatus
    status_history: tuple[OperationStatusEntry, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        _require_uuid(self.id, "id")
        _require_uuid(self.source_draft_id, "source_draft_id")
        _require_positive_version(self.version)
        _require_positive_version(self.source_draft_version, "source_draft_version")
        if not isinstance(self.route, Route):
            raise InvalidDomainValue("route", "route_required")
        _require_date(self.pickup_date, "pickup_date")
        if not self.cargo_label.strip() or len(self.cargo_label) > 500:
            raise InvalidDomainValue("cargo_label", "bounded_non_empty_required")
        if not isinstance(self.mandate, Mandate):
            raise InvalidDomainValue("mandate", "mandate_required")
        if self.mandate.operation_id != self.id:
            raise InvalidDomainValue("mandate", "operation_id_mismatch")
        if not isinstance(self.status, OperationStatus):
            raise InvalidDomainValue("status", "operation_status_required")
        _require_tuple(self.status_history, "status_history")
        if not self.status_history:
            raise InvalidDomainValue("status_history", "non_empty_required")
        if not all(isinstance(entry, OperationStatusEntry) for entry in self.status_history):
            raise InvalidDomainValue("status_history", "operation_status_entry_items_required")
        if any(entry.operation_id != self.id for entry in self.status_history):
            raise InvalidDomainValue("status_history", "operation_id_mismatch")
        if len({entry.id for entry in self.status_history}) != len(self.status_history):
            raise InvalidDomainValue("status_history", "duplicate_entry_id")
        if any(entry.operation_version > self.version for entry in self.status_history):
            raise InvalidDomainValue("status_history", "future_operation_version")
        if tuple(sorted(self.status_history, key=lambda item: (item.occurred_at, item.id))) != (
            self.status_history
        ):
            raise InvalidDomainValue("status_history", "ordered_entries_required")
        if self.status_history[-1].status is not self.status:
            raise InvalidDomainValue("status", "must_match_latest_history")
        _require_utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class MandateDecision:
    allowed: bool
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_tuple(self.reason_codes, "reason_codes")
        if self.allowed != (not self.reason_codes):
            raise InvalidDomainValue("allowed", "must_match_reason_codes")
