"""Deterministic draft, approval, and mandate policy services."""

from collections.abc import Iterable
from datetime import date

from yuno_backend.volta.audit.models import AuditActorKind, AuditEvent
from yuno_backend.volta.idempotency import (
    IdempotencyConflict,
    IdempotencyResultMissing,
    TextMutationIdempotency,
    fingerprint,
    validate_idempotency_key,
)
from yuno_backend.volta.mandates.commands import (
    ApproveOperationCommand,
    CheckMandateCommand,
    CreateIntakeDraftCommand,
)
from yuno_backend.volta.mandates.errors import (
    DraftNotApprovable,
    DraftNotFound,
    MandateConflict,
    OperationAlreadyApproved,
    StaleDraftVersion,
)
from yuno_backend.volta.mandates.models import (
    DraftValidationIssue,
    IntakeDraft,
    Mandate,
    MandateAction,
    MandateDecision,
    Operation,
    OperationProposal,
    OperationStatus,
    OperationStatusEntry,
)
from yuno_backend.volta.mandates.repositories import Clock, IdGenerator, OperationUnitOfWork

__all__ = ["ApproveOperationService", "CreateIntakeDraftService", "MandatePolicy"]

SUPPORTED_LANGUAGES = frozenset({"EN_US", "ES_MX"})
MAX_CONDITIONS = 25
MAX_CONDITION_LENGTH = 500


def validate_draft(
    proposal: OperationProposal,
    requested_language: str,
    extraction_policy_version: str,
) -> tuple[DraftValidationIssue, ...]:
    """Return all semantic issues in stable contract order without submitted values."""
    issues: list[DraftValidationIssue] = []
    mandate = proposal.mandate

    if not proposal.route.origin.strip():
        issues.append(DraftValidationIssue("route.origin", "required"))
    if not proposal.route.destination.strip():
        issues.append(DraftValidationIssue("route.destination", "required"))
    if not proposal.cargo_label.strip():
        issues.append(DraftValidationIssue("cargo_label", "required"))
    elif len(proposal.cargo_label) > 500:
        issues.append(DraftValidationIssue("cargo_label", "too_long"))
    if mandate.pickup_window.end_date < mandate.pickup_window.start_date:
        issues.append(DraftValidationIssue("mandate.pickup_window", "invalid_order"))
    if not (
        mandate.pickup_window.start_date
        <= proposal.pickup_date
        <= mandate.pickup_window.end_date
    ):
        issues.append(DraftValidationIssue("pickup_date", "outside_mandate_window"))
    if mandate.maximum_amount.amount < 0:
        issues.append(DraftValidationIssue("mandate.maximum_amount", "must_be_non_negative"))
    if mandate.maximum_amount.currency != "MXN":
        issues.append(DraftValidationIssue("mandate.currency", "unsupported"))
    if requested_language not in SUPPORTED_LANGUAGES:
        issues.append(DraftValidationIssue("requested_language", "unsupported"))
    issues.extend(_condition_issues("mandate.allowed_conditions", mandate.allowed_conditions))
    issues.extend(
        _condition_issues("mandate.escalation_conditions", mandate.escalation_conditions)
    )
    if not extraction_policy_version.strip():
        issues.append(DraftValidationIssue("extraction_policy_version", "required"))
    return tuple(issues)


def _condition_issues(field: str, conditions: tuple[str, ...]) -> Iterable[DraftValidationIssue]:
    if len(conditions) > MAX_CONDITIONS:
        yield DraftValidationIssue(field, "too_many")
    if any(not isinstance(condition, str) or not condition.strip() for condition in conditions):
        yield DraftValidationIssue(field, "contains_empty")
    if any(
        isinstance(condition, str) and len(condition) > MAX_CONDITION_LENGTH
        for condition in conditions
    ):
        yield DraftValidationIssue(field, "contains_too_long")


class CreateIntakeDraftService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._id_generator = id_generator

    async def create(self, command: CreateIntakeDraftCommand) -> IntakeDraft:
        async with self._unit_of_work:
            try:
                draft = self._new_draft(command)
                await self._unit_of_work.intake_drafts.add(draft)
                await self._unit_of_work.commit()
            except Exception:
                await self._unit_of_work.rollback()
                raise
        return draft

    async def create_with_replay(
        self,
        command: CreateIntakeDraftCommand,
        idempotency_key: str,
    ) -> tuple[IntakeDraft, bool]:
        validate_idempotency_key(idempotency_key)
        request_fingerprint = fingerprint(command)
        async with self._unit_of_work:
            try:
                await self._unit_of_work.text_idempotency.lock(
                    "create_operation_draft", idempotency_key
                )
                record = await self._unit_of_work.text_idempotency.get(
                    "create_operation_draft", idempotency_key
                )
                if record is not None:
                    if record.fingerprint != request_fingerprint:
                        raise IdempotencyConflict(
                            record.result_id, "create_operation_draft", idempotency_key
                        )
                    replay = await self._unit_of_work.intake_drafts.get(record.result_id)
                    if replay is None:
                        raise IdempotencyResultMissing(
                            record.result_id, "create_operation_draft"
                        )
                    return replay, True
                draft = self._new_draft(command)
                await self._unit_of_work.intake_drafts.add(draft)
                await self._unit_of_work.text_idempotency.add(
                    TextMutationIdempotency(
                        "create_operation_draft",
                        idempotency_key,
                        request_fingerprint,
                        draft.id,
                        draft.created_at,
                    )
                )
                await self._unit_of_work.commit()
                return draft, False
            except Exception:
                await self._unit_of_work.rollback()
                raise

    def _new_draft(self, command: CreateIntakeDraftCommand) -> IntakeDraft:
        now = self._clock.now()
        issues = validate_draft(
            command.proposal,
            command.requested_language,
            command.extraction_policy_version,
        )
        return IntakeDraft(
            id=self._id_generator.new_id(),
            source_prompt=command.source_prompt,
            requested_language=command.requested_language,
            extraction_policy_version=command.extraction_policy_version,
            proposal=command.proposal,
            validation_issues=issues,
            approval_eligible=not issues,
            version=1,
            created_at=now,
            updated_at=now,
        )


class ApproveOperationService:
    def __init__(
        self,
        unit_of_work: OperationUnitOfWork,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._id_generator = id_generator

    async def approve(self, command: ApproveOperationCommand) -> Operation:
        async with self._unit_of_work:
            try:
                operation = await self._approve_in_active_uow(command)
                await self._unit_of_work.commit()
            except Exception:
                await self._unit_of_work.rollback()
                raise
        return operation

    async def approve_with_replay(
        self,
        command: ApproveOperationCommand,
        idempotency_key: str,
    ) -> tuple[Operation, bool]:
        validate_idempotency_key(idempotency_key)
        request_fingerprint = fingerprint(command, exclude=("correlation_id",))
        async with self._unit_of_work:
            try:
                await self._unit_of_work.text_idempotency.lock(
                    "approve_operation", idempotency_key
                )
                record = await self._unit_of_work.text_idempotency.get(
                    "approve_operation", idempotency_key
                )
                if record is not None:
                    if record.fingerprint != request_fingerprint:
                        raise IdempotencyConflict(
                            record.result_id, "approve_operation", idempotency_key
                        )
                    replay = await self._unit_of_work.operations.get_by_draft_id(
                        command.draft_id
                    )
                    if replay is None or replay.id != record.result_id:
                        raise IdempotencyResultMissing(record.result_id, "approve_operation")
                    return replay, True
                operation = await self._approve_in_active_uow(command)
                await self._unit_of_work.text_idempotency.add(
                    TextMutationIdempotency(
                        "approve_operation",
                        idempotency_key,
                        request_fingerprint,
                        operation.id,
                        operation.created_at,
                    )
                )
                await self._unit_of_work.commit()
                return operation, False
            except Exception:
                await self._unit_of_work.rollback()
                raise

    async def _approve_in_active_uow(
        self, command: ApproveOperationCommand
    ) -> Operation:
        draft = await self._unit_of_work.intake_drafts.get(command.draft_id)
        if draft is None:
            raise DraftNotFound(command.draft_id)
        if draft.version != command.expected_draft_version:
            raise StaleDraftVersion(
                command.draft_id,
                command.expected_draft_version,
                draft.version,
            )
        if not draft.approval_eligible:
            raise DraftNotApprovable(
                draft.id,
                tuple(issue.reason_code for issue in draft.validation_issues),
            )
        existing = await self._unit_of_work.operations.get_by_draft_id(draft.id)
        if existing is not None:
            raise OperationAlreadyApproved(draft.id, existing.id)

        now = self._clock.now()
        operation_id = self._id_generator.new_id()
        proposal = draft.proposal
        mandate_proposal = proposal.mandate
        mandate = Mandate(
            id=self._id_generator.new_id(),
            operation_id=operation_id,
            version=1,
            maximum_amount=mandate_proposal.maximum_amount,
            pickup_window=mandate_proposal.pickup_window,
            allowed_conditions=mandate_proposal.allowed_conditions,
            escalation_conditions=mandate_proposal.escalation_conditions,
            authorized_actions=(MandateAction.NEGOTIATE, MandateAction.COMMIT),
            approval_actor=command.approval_actor,
            approved_at=now,
        )
        status_entry = OperationStatusEntry(
            id=self._id_generator.new_id(),
            operation_id=operation_id,
            operation_version=1,
            status=OperationStatus.READY,
            occurred_at=now,
        )
        operation = Operation(
            id=operation_id,
            version=1,
            source_draft_id=draft.id,
            source_draft_version=draft.version,
            route=proposal.route,
            pickup_date=proposal.pickup_date,
            cargo_label=proposal.cargo_label,
            mandate=mandate,
            status=OperationStatus.READY,
            status_history=(status_entry,),
            created_at=now,
        )
        await self._unit_of_work.operations.add(operation)
        await self._unit_of_work.audit_events.add(
            AuditEvent(
                event_id=self._id_generator.new_id(),
                operation_id=operation.id,
                operation_version=operation.version,
                actor_kind=AuditActorKind.COORDINATOR,
                event_type="OPERATION_APPROVED",
                occurred_at=now,
                correlation_id=command.correlation_id,
                metadata={"draft_version": draft.version},
            )
        )
        return operation


class MandatePolicy:
    @classmethod
    def require_valid_mandate(cls, mandate: Mandate, pickup_date: date) -> None:
        """Reject an invalid active mandate before a persistence mutation."""
        reasons: list[str] = []
        if mandate.maximum_amount.amount < 0:
            reasons.append("amount_must_be_non_negative")
        if mandate.maximum_amount.currency != "MXN":
            reasons.append("currency_unsupported")
        if mandate.pickup_window.end_date < mandate.pickup_window.start_date:
            reasons.append("pickup_window_invalid_order")
        if not (
            mandate.pickup_window.start_date
            <= pickup_date
            <= mandate.pickup_window.end_date
        ):
            reasons.append("pickup_date_outside_mandate_window")
        for field, conditions in (
            ("allowed_conditions", mandate.allowed_conditions),
            ("escalation_conditions", mandate.escalation_conditions),
        ):
            if len(conditions) > MAX_CONDITIONS:
                reasons.append(f"{field}_too_many")
            if any(
                not isinstance(condition, str) or not condition.strip()
                for condition in conditions
            ):
                reasons.append(f"{field}_contains_empty")
            if any(
                isinstance(condition, str) and len(condition) > MAX_CONDITION_LENGTH
                for condition in conditions
            ):
                reasons.append(f"{field}_contains_too_long")
        if reasons:
            raise MandateConflict(mandate.operation_id, mandate.version, tuple(reasons))

    @staticmethod
    def evaluate(mandate: Mandate, command: CheckMandateCommand) -> MandateDecision:
        reasons: list[str] = []
        if command.action not in mandate.authorized_actions:
            reasons.append("action_not_authorized")
        if command.operation_id != mandate.operation_id:
            reasons.append("operation_mismatch")
        if command.mandate_version != mandate.version:
            reasons.append("mandate_version_mismatch")
        if command.proposed_amount.amount > mandate.maximum_amount.amount:
            reasons.append("amount_exceeds_maximum")
        if command.proposed_amount.currency != mandate.maximum_amount.currency:
            reasons.append("currency_mismatch")
        if not (
            mandate.pickup_window.start_date
            <= command.proposed_pickup_date
            <= mandate.pickup_window.end_date
        ):
            reasons.append("pickup_outside_window")
        if not set(command.proposed_conditions).issubset(mandate.allowed_conditions):
            reasons.append("conditions_not_allowed")
        return MandateDecision(allowed=not reasons, reason_codes=tuple(reasons))

    @classmethod
    def require_allowed(cls, mandate: Mandate, command: CheckMandateCommand) -> None:
        decision = cls.evaluate(mandate, command)
        if not decision.allowed:
            raise MandateConflict(
                operation_id=command.operation_id,
                mandate_version=command.mandate_version,
                reason_codes=decision.reason_codes,
            )
