"""Deterministic mandate-safe replacement and post-contact escalation services."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID

from yuno_backend.volta.audit.models import AuditActorKind, AuditEvent
from yuno_backend.volta.mandates.commands import CheckMandateCommand
from yuno_backend.volta.mandates.models import (
    Mandate,
    MandateAction,
    Money,
    Operation,
    OperationStatus,
    OperationStatusEntry,
)
from yuno_backend.volta.mandates.repositories import Clock, IdGenerator
from yuno_backend.volta.mandates.services import MandatePolicy
from yuno_backend.volta.negotiations.errors import CallSessionNotFound, OperationNotFound
from yuno_backend.volta.negotiations.models import (
    Commitment,
    CommitmentDisposition,
    CommitmentLifecycle,
    Quote,
    QuoteEligibility,
    QuoteTerms,
)
from yuno_backend.volta.recovery.commands import (
    AcknowledgeNotificationCommand,
    CreateEscalationCommand,
    ReplaceMandateCommand,
    ResumeAfterEscalationCommand,
    SimulateInboundRecoveryCommand,
)
from yuno_backend.volta.recovery.errors import (
    CommitmentNotFound,
    EscalationAlreadyResolved,
    EscalationContextConflict,
    EscalationNotFound,
    InvalidCommitmentDisposition,
    MandateVersionNotAdvanced,
    NotificationAlreadyAcknowledged,
    NotificationNotFound,
    OperationBlockedByEscalation,
    StaleOperationVersion,
)
from yuno_backend.volta.recovery.models import (
    EscalationContext,
    Notification,
    PostContactEscalation,
    RecoveryAttempt,
    RecoveryDecision,
    RecoveryDecisionState,
    RecoveryOutcome,
)
from yuno_backend.volta.recovery.repositories import OperationUnitOfWork

__all__ = [
    "AcknowledgeNotificationService",
    "CreateEscalationService",
    "ReplaceMandateService",
    "ResumeAfterEscalationService",
    "SimulateInboundRecoveryService",
]

_QUOTE_VALIDITY = timedelta(hours=1)


async def _locked_operation(uow: OperationUnitOfWork, operation_id: UUID) -> Operation:
    operation = await uow.operations.get(operation_id, for_update=True)
    if operation is None:
        raise OperationNotFound(operation_id)
    return operation


def _check_version(operation: Operation, expected: int) -> None:
    if operation.version != expected:
        raise StaleOperationVersion(operation.id, expected, operation.version)


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
    *,
    actor_kind: AuditActorKind = AuditActorKind.SYSTEM,
) -> AuditEvent:
    return AuditEvent(
        event_id=ids.new_id(),
        operation_id=operation.id,
        operation_version=operation.version,
        actor_kind=actor_kind,
        event_type=event_type,
        occurred_at=now,
        correlation_id=correlation_id,
        metadata={},
    )


def _decision_state(operation: Operation, commitment: Commitment | None) -> RecoveryDecisionState:
    return RecoveryDecisionState(
        operation_version=operation.version,
        operation_status=operation.status,
        active_commitment_id=None if commitment is None else commitment.id,
        carrier_id=None if commitment is None else commitment.carrier_id,
        agreed_terms=None if commitment is None else commitment.agreed_terms,
    )


class ReplaceMandateService:
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

    async def replace(self, command: ReplaceMandateCommand) -> Operation:
        async with self._uow:
            try:
                operation = await _locked_operation(self._uow, command.operation_id)
                _check_version(operation, command.expected_operation_version)
                escalation = await self._uow.post_contact_escalations.get(
                    command.resolved_escalation_id
                )
                if escalation is None or escalation.operation_id != operation.id:
                    raise EscalationNotFound(command.resolved_escalation_id)
                if escalation.resolved:
                    raise EscalationAlreadyResolved(escalation.id)

                now = self._clock.now()
                mandate = Mandate(
                    id=self._ids.new_id(),
                    operation_id=operation.id,
                    version=operation.mandate.version + 1,
                    maximum_amount=command.maximum_amount,
                    pickup_window=command.pickup_window,
                    allowed_conditions=command.allowed_conditions,
                    escalation_conditions=command.escalation_conditions,
                    authorized_actions=operation.mandate.authorized_actions,
                    approval_actor=command.approval_actor,
                    approved_at=now,
                )
                self._policy.require_valid_mandate(mandate, operation.pickup_date)
                self._policy.require_allowed(
                    mandate,
                    CheckMandateCommand(
                        operation.id,
                        mandate.version,
                        MandateAction.NEGOTIATE,
                        mandate.maximum_amount,
                        mandate.pickup_window.start_date,
                        (),
                    ),
                )
                active = await self._uow.commitments.get_active(operation.id)
                status = (
                    OperationStatus.COMMITTED
                    if active is not None
                    else OperationStatus.NEGOTIATING
                )
                updated = _transition(
                    replace(operation, mandate=mandate), status, now, self._ids.new_id()
                )
                resolved = replace(escalation, resolved=True, resolved_at=now)
                await self._uow.operations.replace_mandate(updated)
                await self._uow.post_contact_escalations.update(resolved)
                for event_type in ("MANDATE_REPLACED", "ESCALATION_RESOLVED"):
                    await self._uow.audit_events.add(
                        _audit(
                            self._ids,
                            updated,
                            event_type,
                            now,
                            command.correlation_id,
                            actor_kind=AuditActorKind.COORDINATOR,
                        )
                    )
                await self._uow.commit()
                return updated
            except Exception:
                await self._uow.rollback()
                raise


class CreateEscalationService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = unit_of_work
        self._clock = clock
        self._ids = id_generator

    async def create(self, command: CreateEscalationCommand) -> PostContactEscalation:
        async with self._uow:
            try:
                negotiation = await self._uow.negotiations.get_by_call(command.call_id)
                if negotiation is None:
                    raise CallSessionNotFound(command.call_id)
                operation = await _locked_operation(self._uow, negotiation.operation_id)
                _check_version(operation, command.expected_operation_version)
                unresolved = await self._uow.post_contact_escalations.get_unresolved_by_operation(
                    operation.id
                )
                if unresolved is not None:
                    raise EscalationContextConflict(operation.id, unresolved.id)
                now = self._clock.now()
                active = await self._uow.commitments.get_active(operation.id)
                escalation = PostContactEscalation(
                    id=self._ids.new_id(),
                    operation_id=operation.id,
                    commitment_id=(
                        active.id
                        if active is not None and active.call_id == command.call_id
                        else None
                    ),
                    reason_code="EXPLICIT_COORDINATOR_ESCALATION",
                    operation_version=operation.version,
                    mandate_version=operation.mandate.version,
                    resolved=False,
                    correlation_id=command.correlation_id,
                    created_at=now,
                    call_id=command.call_id,
                    context=EscalationContext(
                        command.conflict,
                        command.attempted_alternatives,
                        command.recommended_action,
                    ),
                )
                await self._uow.post_contact_escalations.add(escalation)
                updated = _transition(operation, OperationStatus.ESCALATED, now, self._ids.new_id())
                await self._uow.operations.update(updated)
                await self._uow.audit_events.add(
                    _audit(
                        self._ids,
                        updated,
                        "EXPLICIT_ESCALATION_CREATED",
                        now,
                        command.correlation_id,
                        actor_kind=AuditActorKind.COORDINATOR,
                    )
                )
                await self._uow.commit()
                return escalation
            except Exception:
                await self._uow.rollback()
                raise


class AcknowledgeNotificationService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = unit_of_work
        self._clock = clock
        self._ids = id_generator

    async def acknowledge(self, command: AcknowledgeNotificationCommand) -> Notification:
        async with self._uow:
            try:
                initial = await self._uow.notifications.get(command.notification_id)
                if initial is None:
                    raise NotificationNotFound(command.notification_id)
                operation = await _locked_operation(self._uow, initial.operation_id)
                notification = await self._uow.notifications.get(
                    command.notification_id, for_update=True
                )
                if notification is None or notification.operation_id != operation.id:
                    raise NotificationNotFound(command.notification_id)
                if notification.acknowledged:
                    if notification.acknowledged_by != command.acknowledged_by:
                        raise NotificationAlreadyAcknowledged(notification.id)
                    await self._uow.commit()
                    return notification
                _check_version(operation, command.expected_operation_version)
                now = self._clock.now()
                updated_operation = _transition(
                    operation, operation.status, now, self._ids.new_id()
                )
                updated_notification = replace(
                    notification,
                    acknowledged_by=command.acknowledged_by,
                    acknowledged_at=now,
                )
                await self._uow.operations.update(updated_operation)
                await self._uow.notifications.update(updated_notification)
                await self._uow.audit_events.add(
                    _audit(
                        self._ids,
                        updated_operation,
                        "NOTIFICATION_ACKNOWLEDGED",
                        now,
                        command.correlation_id,
                        actor_kind=AuditActorKind.COORDINATOR,
                    )
                )
                await self._uow.commit()
                return updated_notification
            except Exception:
                await self._uow.rollback()
                raise


def _mandate_reasons(
    policy: MandatePolicy, operation: Operation, mandate_version: int, terms: QuoteTerms
) -> tuple[str, ...]:
    reasons: list[str] = []
    for pickup_date in (terms.pickup_window_start, terms.pickup_window_end):
        decision = policy.evaluate(
            operation.mandate,
            CheckMandateCommand(
                operation.id,
                mandate_version,
                MandateAction.COMMIT,
                Money(terms.amount, terms.currency),
                pickup_date,
                terms.conditions,
            ),
        )
        for reason in decision.reason_codes:
            if reason not in reasons:
                reasons.append(reason)
    return tuple(reasons)


class SimulateInboundRecoveryService:
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

    async def simulate(self, command: SimulateInboundRecoveryCommand) -> RecoveryAttempt:
        async with self._uow:
            try:
                operation = await _locked_operation(self._uow, command.operation_id)
                _check_version(operation, command.expected_operation_version)

                unresolved = await self._uow.post_contact_escalations.get_unresolved_by_operation(
                    operation.id
                )
                if unresolved is not None:
                    raise OperationBlockedByEscalation(operation.id, unresolved.id)

                commitment = await self._uow.commitments.get(command.commitment_id)
                if commitment is None or commitment.operation_id != operation.id:
                    raise CommitmentNotFound(command.commitment_id)
                if commitment.disposition is not CommitmentDisposition.ACTIVE:
                    raise InvalidCommitmentDisposition(commitment.id, commitment.disposition.value)

                now = self._clock.now()
                reasons = _mandate_reasons(
                    self._policy, operation, command.mandate_version, command.proposed_terms
                )
                attempt_id = self._ids.new_id()

                if reasons:
                    return await self._escalate(
                        operation, commitment, command, now, attempt_id
                    )
                return await self._replace(operation, commitment, command, now, attempt_id)
            except Exception:
                await self._uow.rollback()
                raise

    async def _escalate(
        self,
        operation: Operation,
        commitment: Commitment,
        command: SimulateInboundRecoveryCommand,
        now: datetime,
        attempt_id: UUID,
    ) -> RecoveryAttempt:
        escalation = PostContactEscalation(
            id=self._ids.new_id(),
            operation_id=operation.id,
            commitment_id=commitment.id,
            reason_code="OUT_OF_MANDATE",
            operation_version=operation.version,
            mandate_version=operation.mandate.version,
            resolved=False,
            correlation_id=command.correlation_id,
            created_at=now,
        )
        await self._uow.post_contact_escalations.add(escalation)
        attempt = RecoveryAttempt(
            id=attempt_id,
            operation_id=operation.id,
            commitment_id=commitment.id,
            outcome=RecoveryOutcome.ESCALATED,
            resulting_commitment_id=None,
            escalation_id=escalation.id,
            correlation_id=command.correlation_id,
            created_at=now,
        )
        await self._uow.recovery_attempts.add(attempt)
        updated = _transition(operation, OperationStatus.ESCALATED, now, self._ids.new_id())
        await self._uow.operations.update(updated)
        await self._uow.audit_events.add(
            _audit(self._ids, updated, "POST_CONTACT_ESCALATED", now, command.correlation_id)
        )
        await self._uow.commit()
        return attempt

    async def _replace(
        self,
        operation: Operation,
        commitment: Commitment,
        command: SimulateInboundRecoveryCommand,
        now: datetime,
        attempt_id: UUID,
    ) -> RecoveryAttempt:
        original_quote = await self._uow.quotes.get(commitment.quote_id)
        carrier_priority = original_quote.carrier_priority if original_quote is not None else 1
        quote = Quote(
            id=self._ids.new_id(),
            operation_id=operation.id,
            call_id=commitment.call_id,
            carrier_id=commitment.carrier_id,
            carrier_priority=carrier_priority,
            terms=command.proposed_terms,
            valid_until=now + _QUOTE_VALIDITY,
            mandate_version=command.mandate_version,
            eligibility=QuoteEligibility.ELIGIBLE,
            rejection_reasons=(),
            created_at=now,
        )
        await self._uow.quotes.add(quote)

        # Mirrors Fase 08's `CreateCommitmentService`: acquire the winner-scope lock
        # first, then re-fetch the active commitment under that lock and confirm it is
        # still the one this attempt targets, rather than superseding the pre-lock
        # `commitment` snapshot. The enclosing `operations.get(..., for_update=True)`
        # call in `_locked_operation` already serializes every writer on this
        # operation, so this re-check is defense-in-depth rather than the sole
        # safety net -- but relying only on the outer lock is fragile if a future
        # caller ever reaches `_replace` without holding it.
        await self._uow.commitments.lock_winner_scope(operation.id)
        active = await self._uow.commitments.get_active(operation.id)
        if active is None or active.id != commitment.id:
            raise InvalidCommitmentDisposition(
                commitment.id, "unknown" if active is None else active.disposition.value
            )

        new_commitment_id = self._ids.new_id()
        new_commitment = Commitment(
            id=new_commitment_id,
            operation_id=operation.id,
            call_id=commitment.call_id,
            quote_id=quote.id,
            carrier_id=commitment.carrier_id,
            agreed_terms=command.proposed_terms,
            mandate_version=command.mandate_version,
            # Opaque placeholder, not a live FK to `AgreementEvidence` -- same
            # convention Fase 08 uses for `Commitment.evidence_id`. The durable link
            # to recorded evidence is `AgreementEvidence.commitment_id`, attached
            # afterward via `RecordEvidenceService` against this commitment's id.
            evidence_id=self._ids.new_id(),
            lifecycle=CommitmentLifecycle.CANDIDATE,
            disposition=CommitmentDisposition.ACTIVE,
            replaces_commitment_id=commitment.id,
            replaced_by_commitment_id=None,
            created_at=now,
        )
        superseded = replace(
            active,
            disposition=CommitmentDisposition.SUPERSEDED,
            replaced_by_commitment_id=new_commitment_id,
            superseded_at=now,
        )
        await self._uow.commitments.update(superseded)
        await self._uow.commitments.add(new_commitment)

        attempt = RecoveryAttempt(
            id=attempt_id,
            operation_id=operation.id,
            commitment_id=commitment.id,
            outcome=RecoveryOutcome.REPLACED,
            resulting_commitment_id=new_commitment_id,
            escalation_id=None,
            correlation_id=command.correlation_id,
            created_at=now,
        )
        await self._uow.recovery_attempts.add(attempt)

        updated = _transition(operation, OperationStatus.COMMITTED, now, self._ids.new_id())
        await self._uow.operations.update(updated)
        notification = Notification(
            id=self._ids.new_id(),
            operation_id=operation.id,
            commitment_id=new_commitment_id,
            reason_code="MANDATE_SAFE_REPLACEMENT",
            created_at=now,
            operation_version=updated.version,
            recovery_decision=RecoveryDecision(
                before=_decision_state(operation, active),
                after=_decision_state(updated, new_commitment),
                reason="MANDATE_SAFE_REPLACEMENT",
            ),
            message="A mandate-safe replacement commitment was activated.",
            correlation_id=command.correlation_id,
        )
        await self._uow.notifications.add(notification)
        await self._uow.audit_events.add(
            _audit(self._ids, updated, "COMMITMENT_SUPERSEDED", now, command.correlation_id)
        )
        await self._uow.audit_events.add(
            _audit(self._ids, updated, "COMMITMENT_ACTIVATED", now, command.correlation_id)
        )
        await self._uow.audit_events.add(
            _audit(self._ids, updated, "RECOVERY_REPLACEMENT_APPLIED", now, command.correlation_id)
        )
        await self._uow.commit()
        return attempt


class ResumeAfterEscalationService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._uow = unit_of_work
        self._clock = clock
        self._ids = id_generator

    async def resume(self, command: ResumeAfterEscalationCommand) -> PostContactEscalation:
        async with self._uow:
            try:
                operation = await _locked_operation(self._uow, command.operation_id)
                _check_version(operation, command.expected_operation_version)

                escalation = await self._uow.post_contact_escalations.get(command.escalation_id)
                if escalation is None or escalation.operation_id != operation.id:
                    raise EscalationNotFound(command.escalation_id)
                if escalation.resolved:
                    await self._uow.rollback()
                    return escalation
                if command.new_mandate_version <= escalation.mandate_version:
                    raise MandateVersionNotAdvanced(
                        operation.id, escalation.mandate_version, command.new_mandate_version
                    )

                now = self._clock.now()
                resolved = replace(escalation, resolved=True, resolved_at=now)
                await self._uow.post_contact_escalations.update(resolved)

                active = await self._uow.commitments.get_active(operation.id)
                next_status = (
                    OperationStatus.COMMITTED if active is not None else OperationStatus.NEGOTIATING
                )
                updated = _transition(operation, next_status, now, self._ids.new_id())
                await self._uow.operations.update(updated)
                await self._uow.audit_events.add(
                    _audit(self._ids, updated, "ESCALATION_RESUMED", now, command.correlation_id)
                )
                await self._uow.commit()
                return resolved
            except Exception:
                await self._uow.rollback()
                raise
