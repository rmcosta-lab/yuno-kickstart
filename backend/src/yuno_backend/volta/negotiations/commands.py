"""Typed negotiation application inputs."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from yuno_backend.volta.negotiations.models import BrowserChannel, QuoteTerms

__all__ = ["CreateCommitmentCommand", "RecordQuoteCommand", "StartNegotiationCommand"]


@dataclass(frozen=True, slots=True)
class StartNegotiationCommand:
    operation_id: UUID
    expected_operation_version: int
    mandate_version: int
    channel: BrowserChannel
    idempotency_key: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class RecordQuoteCommand:
    call_id: UUID
    expected_operation_version: int
    carrier_id: UUID
    mandate_version: int
    terms: QuoteTerms
    valid_until: datetime
    idempotency_key: str
    correlation_id: UUID


@dataclass(frozen=True, slots=True)
class CreateCommitmentCommand:
    call_id: UUID
    expected_operation_version: int
    quote_id: UUID
    mandate_version: int
    evidence_id: UUID
    idempotency_key: str
    correlation_id: UUID
