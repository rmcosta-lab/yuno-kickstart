"""Deterministic negotiation, quote, comparison, and commitment services."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from uuid import UUID

from yuno_backend.volta.audit.models import AuditActorKind, AuditEvent
from yuno_backend.volta.mandates.commands import CheckMandateCommand
from yuno_backend.volta.mandates.models import (
    MandateAction,
    Money,
    Operation,
    OperationStatus,
    OperationStatusEntry,
)
from yuno_backend.volta.mandates.repositories import Clock, IdGenerator
from yuno_backend.volta.mandates.services import MandatePolicy
from yuno_backend.volta.negotiations.commands import (
    CreateCommitmentCommand,
    RecordQuoteCommand,
    StartNegotiationCommand,
)
from yuno_backend.volta.negotiations.errors import (
    CallSessionNotFound,
    CarrierSessionMismatch,
    IdempotencyConflict,
    InvalidNegotiationTransition,
    NegotiationAlreadyStarted,
    OperationNotFound,
    QuoteExpired,
    QuoteNotBestCandidate,
    QuoteNotEligible,
    QuoteNotFound,
    StaleMandateVersion,
    StaleOperationVersion,
)
from yuno_backend.volta.negotiations.models import (
    CallState,
    CarrierSession,
    Commitment,
    CommitmentDisposition,
    CommitmentLifecycle,
    MutationIdempotency,
    Negotiation,
    PreContactEscalation,
    Quote,
    QuoteComparison,
    QuoteEligibility,
)
from yuno_backend.volta.negotiations.repositories import CarrierCatalog, OperationUnitOfWork

__all__ = [
    "CreateCommitmentService",
    "QuoteComparisonService",
    "RecordQuoteService",
    "StartNegotiationService",
]


def _canonical(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return _canonical(asdict(value))
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in value.items()}
    return value


def _fingerprint(command: object) -> str:
    values = asdict(command)  # type: ignore[arg-type]
    values.pop("idempotency_key", None)
    values.pop("correlation_id", None)
    payload = json.dumps(_canonical(values), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_idempotency_key(key: str) -> None:
    if (
        not isinstance(key, str)
        or not 8 <= len(key) <= 128
        or not key.isascii()
        or not key.isprintable()
    ):
        from yuno_backend.volta.errors import InvalidDomainValue

        raise InvalidDomainValue("idempotency_key", "printable_ascii_8_128_required")


def _transition(
    operation: Operation,
    status: OperationStatus,
    now: datetime,
    entry_id: UUID,
) -> Operation:
    version = operation.version + 1
    latest = operation.status_history[-1]
    if (now, entry_id) <= (latest.occurred_at, latest.id):
        now = latest.occurred_at + timedelta(microseconds=1)
    entry = OperationStatusEntry(entry_id, operation.id, version, status, now)
    return replace(
        operation,
        version=version,
        status=status,
        status_history=(*operation.status_history, entry),
    )


def _audit(
    ids: IdGenerator,
    operation: Operation,
    event_type: str,
    now: datetime,
    correlation_id: UUID,
    actor: AuditActorKind = AuditActorKind.SYSTEM,
) -> AuditEvent:
    return AuditEvent(
        event_id=ids.new_id(),
        operation_id=operation.id,
        operation_version=operation.version,
        actor_kind=actor,
        event_type=event_type,
        occurred_at=now,
        correlation_id=correlation_id,
        metadata={},
    )


async def _operation(uow: OperationUnitOfWork, operation_id: UUID) -> Operation:
    result = await uow.operations.get(operation_id, for_update=True)
    if result is None:
        raise OperationNotFound(operation_id)
    return result


def _versions(operation: Operation, expected: int, mandate: int) -> None:
    if operation.version != expected:
        raise StaleOperationVersion(operation.id, expected, operation.version)
    if operation.mandate.version != mandate:
        raise StaleMandateVersion(operation.id, mandate, operation.mandate.version)


async def _replay_record(uow: OperationUnitOfWork, name: str, key: str, fingerprint: str):
    record = await uow.idempotency.get(name, key)
    if record is None:
        return None
    if record.fingerprint != fingerprint:
        raise IdempotencyConflict(record.operation_id, name, key)
    if name == "start_negotiation":
        result = await uow.negotiations.get(record.result_id)
    elif name == "record_quote":
        result = await uow.quotes.get(record.result_id)
    else:
        result = await uow.commitments.get(record.result_id)
    if result is None:
        raise InvalidNegotiationTransition(record.operation_id, "idempotency_result_missing")
    return result


class StartNegotiationService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        catalog: CarrierCatalog,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = unit_of_work
        self._catalog = catalog
        self._clock = clock
        self._ids = id_generator

    async def start(self, command: StartNegotiationCommand) -> Negotiation:
        _validate_idempotency_key(command.idempotency_key)
        fingerprint = _fingerprint(command)
        async with self._uow:
            try:
                replay = await _replay_record(
                    self._uow, "start_negotiation", command.idempotency_key, fingerprint
                )
                if replay is not None:
                    return replay
                operation = await _operation(self._uow, command.operation_id)
                replay = await _replay_record(
                    self._uow, "start_negotiation", command.idempotency_key, fingerprint
                )
                if replay is not None:
                    return replay
                _versions(operation, command.expected_operation_version, command.mandate_version)
                existing = await self._uow.negotiations.get_by_operation(operation.id)
                if existing is not None:
                    raise NegotiationAlreadyStarted(operation.id, existing.id)
                if operation.status is not OperationStatus.READY:
                    raise InvalidNegotiationTransition(operation.id, "operation_not_ready")
                if MandateAction.NEGOTIATE not in operation.mandate.authorized_actions:
                    raise InvalidNegotiationTransition(operation.id, "negotiate_not_authorized")

                now = self._clock.now()
                negotiation_id = self._ids.new_id()
                carriers = self._catalog.select(operation.route)
                sessions = tuple(
                    CarrierSession(
                        call_id=self._ids.new_id(),
                        negotiation_id=negotiation_id,
                        operation_id=operation.id,
                        carrier_id=carrier.id,
                        carrier_display_label=carrier.display_label,
                        route=operation.route,
                        available_snapshot=carrier.available,
                        fixed_priority=carrier.priority,
                        selection_rank=rank,
                        channel=command.channel,
                        state=CallState.SELECTED,
                        created_at=now,
                    )
                    for rank, carrier in enumerate(carriers, 1)
                )
                escalation = (
                    None
                    if sessions
                    else PreContactEscalation(
                        self._ids.new_id(),
                        negotiation_id,
                        operation.id,
                        "no_eligible_carrier",
                        command.correlation_id,
                        now,
                    )
                )
                updated = _transition(
                    operation,
                    OperationStatus.NEGOTIATING if sessions else OperationStatus.ESCALATED,
                    now,
                    self._ids.new_id(),
                )
                negotiation = Negotiation(
                    negotiation_id,
                    operation.id,
                    updated.version,
                    operation.mandate.version,
                    sessions,
                    escalation,
                    now,
                )
                await self._uow.negotiations.add(negotiation)
                await self._uow.operations.update(updated)
                await self._uow.audit_events.add(
                    _audit(
                        self._ids,
                        updated,
                        "NEGOTIATION_STARTED" if sessions else "PRE_CONTACT_ESCALATED",
                        now,
                        command.correlation_id,
                    )
                )
                await self._uow.idempotency.add(
                    MutationIdempotency(
                        operation.id,
                        "start_negotiation",
                        command.idempotency_key,
                        fingerprint,
                        negotiation.id,
                        now,
                    )
                )
                await self._uow.commit()
                return negotiation
            except Exception:
                await self._uow.rollback()
                raise


class RecordQuoteService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        mandate_policy: MandatePolicy,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = unit_of_work
        self._policy = mandate_policy
        self._clock = clock
        self._ids = id_generator

    async def record(self, command: RecordQuoteCommand) -> Quote:
        _validate_idempotency_key(command.idempotency_key)
        fingerprint = _fingerprint(command)
        async with self._uow:
            try:
                replay = await _replay_record(
                    self._uow, "record_quote", command.idempotency_key, fingerprint
                )
                if replay is not None:
                    return replay
                negotiation = await self._uow.negotiations.get_by_call(command.call_id)
                if negotiation is None:
                    raise CallSessionNotFound(command.call_id)
                operation = await _operation(self._uow, negotiation.operation_id)
                replay = await _replay_record(
                    self._uow, "record_quote", command.idempotency_key, fingerprint
                )
                if replay is not None:
                    return replay
                _versions(operation, command.expected_operation_version, command.mandate_version)
                if operation.status not in (OperationStatus.NEGOTIATING, OperationStatus.COMMITTED):
                    raise InvalidNegotiationTransition(operation.id, "quotes_not_accepted")
                session = next(
                    (item for item in negotiation.sessions if item.call_id == command.call_id), None
                )
                if session is None:
                    raise CallSessionNotFound(command.call_id)
                if session.carrier_id != command.carrier_id:
                    raise CarrierSessionMismatch(command.call_id, command.carrier_id)
                reasons = self._quote_reasons(operation, command)
                now = self._clock.now()
                quote = Quote(
                    self._ids.new_id(),
                    operation.id,
                    command.call_id,
                    command.carrier_id,
                    session.fixed_priority,
                    command.terms,
                    command.valid_until,
                    command.mandate_version,
                    QuoteEligibility.REJECTED if reasons else QuoteEligibility.ELIGIBLE,
                    reasons,
                    now,
                )
                updated = _transition(operation, operation.status, now, self._ids.new_id())
                await self._uow.quotes.add(quote)
                await self._uow.operations.update(updated)
                await self._uow.audit_events.add(
                    _audit(
                        self._ids,
                        updated,
                        "QUOTE_REJECTED" if reasons else "QUOTE_RECORDED",
                        now,
                        command.correlation_id,
                        AuditActorKind.CARRIER_SIMULATOR,
                    )
                )
                await self._uow.idempotency.add(
                    MutationIdempotency(
                        operation.id,
                        "record_quote",
                        command.idempotency_key,
                        fingerprint,
                        quote.id,
                        now,
                    )
                )
                await self._uow.commit()
                return quote
            except Exception:
                await self._uow.rollback()
                raise

    def _quote_reasons(self, operation: Operation, command: RecordQuoteCommand) -> tuple[str, ...]:
        reasons: list[str] = []
        for pickup_date in (command.terms.pickup_window_start, command.terms.pickup_window_end):
            decision = self._policy.evaluate(
                operation.mandate,
                CheckMandateCommand(
                    operation.id,
                    command.mandate_version,
                    MandateAction.COMMIT,
                    Money(command.terms.amount, command.terms.currency),
                    pickup_date,
                    command.terms.conditions,
                ),
            )
            for reason in decision.reason_codes:
                if reason not in reasons:
                    reasons.append(reason)
        return tuple(reasons)


class QuoteComparisonService:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def compare(
        self,
        operation_id: UUID,
        mandate_version: int,
        quotes: tuple[Quote, ...],
        *,
        at: datetime | None = None,
    ) -> QuoteComparison:
        now = self._clock.now() if at is None else at
        eligible = tuple(
            sorted(
                (
                    quote
                    for quote in quotes
                    if quote.operation_id == operation_id
                    and quote.mandate_version == mandate_version
                    and quote.eligibility is QuoteEligibility.ELIGIBLE
                    and quote.valid_until > now
                ),
                key=lambda quote: (
                    quote.terms.amount,
                    quote.terms.pickup_window_start,
                    quote.carrier_priority,
                    quote.created_at,
                    quote.id,
                ),
            )
        )
        return QuoteComparison(operation_id, eligible, eligible[0].id if eligible else None, now)


class CreateCommitmentService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        mandate_policy: MandatePolicy,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = unit_of_work
        self._policy = mandate_policy
        self._clock = clock
        self._ids = id_generator

    async def create(self, command: CreateCommitmentCommand) -> Commitment:
        _validate_idempotency_key(command.idempotency_key)
        fingerprint = _fingerprint(command)
        async with self._uow:
            try:
                replay = await _replay_record(
                    self._uow, "create_commitment", command.idempotency_key, fingerprint
                )
                if replay is not None:
                    return replay
                negotiation = await self._uow.negotiations.get_by_call(command.call_id)
                if negotiation is None:
                    raise CallSessionNotFound(command.call_id)
                operation = await _operation(self._uow, negotiation.operation_id)
                replay = await _replay_record(
                    self._uow, "create_commitment", command.idempotency_key, fingerprint
                )
                if replay is not None:
                    return replay
                _versions(operation, command.expected_operation_version, command.mandate_version)
                if operation.status not in (OperationStatus.NEGOTIATING, OperationStatus.COMMITTED):
                    raise InvalidNegotiationTransition(operation.id, "commitment_not_allowed")
                quote = await self._uow.quotes.get(command.quote_id)
                if quote is None or quote.operation_id != operation.id:
                    raise QuoteNotFound(command.quote_id)
                if quote.call_id != command.call_id:
                    raise CarrierSessionMismatch(command.call_id, quote.carrier_id)
                if quote.mandate_version != operation.mandate.version:
                    raise StaleMandateVersion(
                        operation.id, quote.mandate_version, operation.mandate.version
                    )
                now = self._clock.now()
                if quote.eligibility is QuoteEligibility.REJECTED:
                    raise QuoteNotEligible(quote.id, quote.rejection_reasons)
                if quote.valid_until <= now:
                    raise QuoteExpired(quote.id)
                comparison = QuoteComparisonService(self._clock).compare(
                    operation.id,
                    operation.mandate.version,
                    await self._uow.quotes.list_by_operation(operation.id),
                    at=now,
                )
                if comparison.selected_quote_id != quote.id:
                    if comparison.selected_quote_id is None:
                        raise QuoteNotEligible(quote.id)
                    raise QuoteNotBestCandidate(quote.id, comparison.selected_quote_id)
                await self._uow.commitments.lock_winner_scope(operation.id)
                active = await self._uow.commitments.get_active(operation.id)
                commitment_id = self._ids.new_id()
                commitment = Commitment(
                    commitment_id,
                    operation.id,
                    quote.call_id,
                    quote.id,
                    quote.carrier_id,
                    quote.terms,
                    command.mandate_version,
                    command.evidence_id,
                    CommitmentLifecycle.CANDIDATE,
                    CommitmentDisposition.ACTIVE,
                    active.id if active else None,
                    None,
                    now,
                )
                if active is not None:
                    superseded = replace(
                        active,
                        disposition=CommitmentDisposition.SUPERSEDED,
                        replaced_by_commitment_id=commitment_id,
                        superseded_at=now,
                    )
                    await self._uow.commitments.update(superseded)
                await self._uow.commitments.add(commitment)
                updated = _transition(operation, OperationStatus.COMMITTED, now, self._ids.new_id())
                await self._uow.operations.update(updated)
                if active is not None:
                    await self._uow.audit_events.add(
                        _audit(
                            self._ids, updated, "COMMITMENT_SUPERSEDED", now, command.correlation_id
                        )
                    )
                await self._uow.audit_events.add(
                    _audit(self._ids, updated, "COMMITMENT_ACTIVATED", now, command.correlation_id)
                )
                await self._uow.idempotency.add(
                    MutationIdempotency(
                        operation.id,
                        "create_commitment",
                        command.idempotency_key,
                        fingerprint,
                        commitment.id,
                        now,
                    )
                )
                await self._uow.commit()
                return commitment
            except Exception:
                await self._uow.rollback()
                raise
