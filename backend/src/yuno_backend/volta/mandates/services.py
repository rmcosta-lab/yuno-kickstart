"""Deterministic draft, approval, and mandate policy services."""

from collections.abc import Iterable

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
        try:
            now = self._clock.now()
            issues = validate_draft(
                command.proposal,
                command.requested_language,
                command.extraction_policy_version,
            )
            draft = IntakeDraft(
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
            await self._unit_of_work.intake_drafts.add(draft)
            await self._unit_of_work.commit()
        except Exception:
            await self._unit_of_work.rollback()
            raise
        return draft


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
        try:
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
            operation = Operation(
                id=operation_id,
                version=1,
                source_draft_id=draft.id,
                source_draft_version=draft.version,
                route=proposal.route,
                pickup_date=proposal.pickup_date,
                mandate=mandate,
                created_at=now,
            )
            await self._unit_of_work.operations.add(operation)
            await self._unit_of_work.commit()
        except Exception:
            await self._unit_of_work.rollback()
            raise
        return operation


class MandatePolicy:
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
