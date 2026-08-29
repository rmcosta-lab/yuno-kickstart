"""Frozen provider-neutral values for deterministic carrier negotiation."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.mandates.models import Route

__all__ = [
    "BrowserChannel",
    "CallState",
    "CarrierProfile",
    "CarrierSession",
    "Commitment",
    "CommitmentDisposition",
    "CommitmentLifecycle",
    "MutationIdempotency",
    "Negotiation",
    "PreContactEscalation",
    "Quote",
    "QuoteComparison",
    "QuoteEligibility",
    "QuoteTerms",
]


def _uuid(value: object, field: str) -> None:
    if not isinstance(value, UUID):
        raise InvalidDomainValue(field, "uuid_required")


def _version(value: object, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise InvalidDomainValue(field, "positive_integer_required")


def _utc(value: object, field: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise InvalidDomainValue(field, "aware_utc_required")


class BrowserChannel(StrEnum):
    BROWSER_TEXT = "BROWSER_TEXT"
    BROWSER_VOICE = "BROWSER_VOICE"


class CallState(StrEnum):
    SELECTED = "SELECTED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class QuoteEligibility(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    REJECTED = "REJECTED"


class CommitmentLifecycle(StrEnum):
    CANDIDATE = "CANDIDATE"


class CommitmentDisposition(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True, slots=True)
class CarrierProfile:
    id: UUID
    display_label: str
    route_pairs: tuple[tuple[str, str], ...]
    available: bool
    priority: int

    def __post_init__(self) -> None:
        _uuid(self.id, "carrier.id")
        if not self.display_label.strip() or not self.route_pairs:
            raise InvalidDomainValue("carrier", "label_and_routes_required")
        if self.priority < 1:
            raise InvalidDomainValue("carrier.priority", "positive_integer_required")
        normalized = tuple(
            (a.strip().casefold(), b.strip().casefold()) for a, b in self.route_pairs
        )
        if any(not a or not b for a, b in normalized):
            raise InvalidDomainValue("carrier.route_pairs", "non_empty_endpoints_required")
        object.__setattr__(self, "route_pairs", normalized)

    def covers(self, route: Route) -> bool:
        return (
            route.origin.strip().casefold(),
            route.destination.strip().casefold(),
        ) in self.route_pairs


@dataclass(frozen=True, slots=True)
class CarrierSession:
    call_id: UUID
    negotiation_id: UUID
    operation_id: UUID
    carrier_id: UUID
    carrier_display_label: str
    route: Route
    available_snapshot: bool
    fixed_priority: int
    selection_rank: int
    channel: BrowserChannel
    state: CallState
    created_at: datetime

    def __post_init__(self) -> None:
        for field in ("call_id", "negotiation_id", "operation_id", "carrier_id"):
            _uuid(getattr(self, field), field)
        if not 1 <= self.selection_rank <= 3 or self.fixed_priority < 1:
            raise InvalidDomainValue("session.rank", "valid_rank_required")
        _utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class PreContactEscalation:
    id: UUID
    negotiation_id: UUID
    operation_id: UUID
    reason_code: str
    correlation_id: UUID
    created_at: datetime

    def __post_init__(self) -> None:
        _uuid(self.id, "id")
        _uuid(self.negotiation_id, "negotiation_id")
        _uuid(self.operation_id, "operation_id")
        _uuid(self.correlation_id, "correlation_id")
        _utc(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class Negotiation:
    id: UUID
    operation_id: UUID
    operation_version: int
    mandate_version: int
    sessions: tuple[CarrierSession, ...]
    pre_contact_escalation: PreContactEscalation | None
    started_at: datetime

    def __post_init__(self) -> None:
        _uuid(self.id, "id")
        _uuid(self.operation_id, "operation_id")
        _version(self.operation_version, "operation_version")
        _version(self.mandate_version, "mandate_version")
        if len(self.sessions) > 3 or bool(self.sessions) == (
            self.pre_contact_escalation is not None
        ):
            raise InvalidDomainValue("negotiation.result", "sessions_xor_escalation_required")
        _utc(self.started_at, "started_at")


@dataclass(frozen=True, slots=True)
class QuoteTerms:
    amount: Decimal
    currency: str
    pickup_window_start: date
    pickup_window_end: date
    conditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal) or not self.amount.is_finite() or self.amount < 0:
            raise InvalidDomainValue("amount", "finite_non_negative_decimal_required")
        if not self.currency.strip():
            raise InvalidDomainValue("currency", "non_empty_required")
        if self.pickup_window_end < self.pickup_window_start:
            raise InvalidDomainValue("pickup_window", "invalid_order")


@dataclass(frozen=True, slots=True)
class Quote:
    id: UUID
    operation_id: UUID
    call_id: UUID
    carrier_id: UUID
    carrier_priority: int
    terms: QuoteTerms
    valid_until: datetime
    mandate_version: int
    eligibility: QuoteEligibility
    rejection_reasons: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        for field in ("id", "operation_id", "call_id", "carrier_id"):
            _uuid(getattr(self, field), field)
        _version(self.mandate_version, "mandate_version")
        _utc(self.valid_until, "valid_until")
        _utc(self.created_at, "created_at")
        if self.carrier_priority < 1:
            raise InvalidDomainValue("carrier_priority", "positive_integer_required")
        if (self.eligibility is QuoteEligibility.ELIGIBLE) != (not self.rejection_reasons):
            raise InvalidDomainValue("eligibility", "must_match_rejection_reasons")


@dataclass(frozen=True, slots=True)
class QuoteComparison:
    operation_id: UUID
    ranked_quotes: tuple[Quote, ...]
    selected_quote_id: UUID | None
    compared_at: datetime


@dataclass(frozen=True, slots=True)
class Commitment:
    id: UUID
    operation_id: UUID
    call_id: UUID
    quote_id: UUID
    carrier_id: UUID
    agreed_terms: QuoteTerms
    mandate_version: int
    evidence_id: UUID
    lifecycle: CommitmentLifecycle
    disposition: CommitmentDisposition
    replaces_commitment_id: UUID | None
    replaced_by_commitment_id: UUID | None
    created_at: datetime
    superseded_at: datetime | None = None

    def __post_init__(self) -> None:
        for field in ("id", "operation_id", "call_id", "quote_id", "carrier_id", "evidence_id"):
            _uuid(getattr(self, field), field)
        _version(self.mandate_version, "mandate_version")
        _utc(self.created_at, "created_at")
        if self.superseded_at is not None:
            _utc(self.superseded_at, "superseded_at")
        if self.disposition is CommitmentDisposition.ACTIVE and self.superseded_at is not None:
            raise InvalidDomainValue("superseded_at", "active_must_not_be_superseded")


@dataclass(frozen=True, slots=True)
class MutationIdempotency:
    operation_id: UUID
    operation_name: str
    key: str
    fingerprint: str
    result_id: UUID
    created_at: datetime

    def __post_init__(self) -> None:
        _uuid(self.operation_id, "operation_id")
        _uuid(self.result_id, "result_id")
        if not 8 <= len(self.key) <= 128 or not self.key.isascii() or not self.key.isprintable():
            raise InvalidDomainValue("idempotency_key", "printable_ascii_8_128_required")
        _utc(self.created_at, "created_at")
