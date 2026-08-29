from collections.abc import Callable
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from yuno_backend.volta.mandates import (
    ApproveOperationCommand,
    ApproveOperationService,
    CreateIntakeDraftCommand,
    CreateIntakeDraftService,
    IntakeDraft,
    InvalidDomainValue,
    MandateProposal,
    Money,
    OperationProposal,
    OperationStatus,
    OperationStatusEntry,
    PickupWindow,
    Route,
)
from yuno_backend.volta.mandates.services import validate_draft

from .conftest import (
    AUDIT_ID,
    CORRELATION_ID,
    DRAFT_ID,
    MANDATE_ID,
    NOW,
    OPERATION_ID,
    STATUS_ID,
    FixedClock,
    FixedIds,
    InMemoryUnitOfWork,
)


async def test_create_retains_redacted_prompt_policy_and_injected_values(
    proposal: OperationProposal,
) -> None:
    prompt = "Move synthetic freight under the approved test constraints."
    command = CreateIntakeDraftCommand(
        source_prompt=prompt,
        requested_language="EN_US",
        extraction_policy_version="intake-v1",
        proposal=proposal,
    )
    uow = InMemoryUnitOfWork()

    draft = await CreateIntakeDraftService(uow, FixedClock(), FixedIds([DRAFT_ID])).create(
        command
    )

    assert draft.source_prompt == prompt
    assert draft.extraction_policy_version == "intake-v1"
    assert draft.id == DRAFT_ID
    assert draft.version == 1
    assert draft.created_at == draft.updated_at == NOW
    assert draft.approval_eligible
    assert draft.validation_issues == ()
    assert prompt not in repr(command)
    assert prompt not in repr(draft)
    assert uow.intake_drafts.values == {DRAFT_ID: draft}
    assert uow.intake_drafts.add_calls == uow.commit_calls == 1
    assert uow.rollback_calls == 0


def test_validation_returns_every_issue_in_stable_safe_order() -> None:
    proposal = OperationProposal(
        route=Route(origin=" submitted-origin ", destination=" "),
        pickup_date=date(2026, 9, 5),
        mandate=MandateProposal(
            maximum_amount=Money(amount=Decimal("-0.01"), currency="USD-SECRET"),
            pickup_window=PickupWindow(
                start_date=date(2026, 9, 4),
                end_date=date(2026, 9, 3),
            ),
            allowed_conditions=("",),
            escalation_conditions=tuple(["safe"] * 25 + ["hidden-submitted-value"]),
        ),
    )

    issues = validate_draft(proposal, "UNSUPPORTED-SECRET", " ")

    assert [(issue.field, issue.reason_code) for issue in issues] == [
        ("route.destination", "required"),
        ("mandate.pickup_window", "invalid_order"),
        ("pickup_date", "outside_mandate_window"),
        ("mandate.maximum_amount", "must_be_non_negative"),
        ("mandate.currency", "unsupported"),
        ("requested_language", "unsupported"),
        ("mandate.allowed_conditions", "contains_empty"),
        ("mandate.escalation_conditions", "too_many"),
        ("extraction_policy_version", "required"),
    ]
    rendered = repr(issues)
    for submitted in ("USD-SECRET", "UNSUPPORTED-SECRET", "hidden-submitted-value"):
        assert submitted not in rendered


def test_overlong_condition_returns_only_safe_issue(proposal: OperationProposal) -> None:
    submitted_condition = "sensitive-submitted-condition-" + ("x" * 501)
    proposal_with_overlong_condition = replace(
        proposal,
        mandate=replace(
            proposal.mandate,
            allowed_conditions=(submitted_condition,),
        ),
    )

    issues = validate_draft(proposal_with_overlong_condition, "EN_US", "intake-v1")

    assert [(issue.field, issue.reason_code) for issue in issues] == [
        ("mandate.allowed_conditions", "contains_too_long")
    ]
    assert submitted_condition not in repr(issues)


async def test_invalid_draft_is_saved_without_creating_authority(
    proposal: OperationProposal,
) -> None:
    invalid = OperationProposal(
        route=proposal.route,
        pickup_date=proposal.pickup_date,
        mandate=MandateProposal(
            maximum_amount=Money(Decimal("-1"), "MXN"),
            pickup_window=proposal.mandate.pickup_window,
        ),
    )
    uow = InMemoryUnitOfWork()
    draft = await CreateIntakeDraftService(uow, FixedClock(), FixedIds([DRAFT_ID])).create(
        CreateIntakeDraftCommand("synthetic prompt", "ES_MX", "intake-v1", invalid)
    )

    assert not draft.approval_eligible
    assert uow.operations.values == {}
    assert "synthetic prompt" not in repr(draft)


def test_domain_values_reject_mutability_and_unsafe_local_values(
    proposal: OperationProposal,
) -> None:
    assert proposal.mandate.allowed_conditions == (
        "sealed container",
        "daylight pickup",
    )
    with pytest.raises(FrozenInstanceError):
        proposal.pickup_date = date(2026, 9, 7)  # type: ignore[misc]
    with pytest.raises(InvalidDomainValue, match="finite_decimal_required"):
        Money(amount=Decimal("NaN"), currency="MXN")
    with pytest.raises(InvalidDomainValue, match="tuple_required"):
        MandateProposal(  # type: ignore[arg-type]
            maximum_amount=Money(Decimal("1"), "MXN"),
            pickup_window=PickupWindow(date(2026, 9, 1), date(2026, 9, 2)),
            allowed_conditions=["mutable"],
        )


def test_entities_require_uuid_positive_versions_and_aware_utc(
    proposal: OperationProposal,
) -> None:
    with pytest.raises(InvalidDomainValue, match="aware_utc_required"):
        IntakeDraft(
            id=UUID(int=1),
            source_prompt="synthetic",
            requested_language="EN_US",
            extraction_policy_version="intake-v1",
            proposal=proposal,
            validation_issues=(),
            approval_eligible=True,
            version=1,
            created_at=datetime(2026, 9, 1),
            updated_at=datetime(2026, 9, 1, tzinfo=UTC) + timedelta(),
        )


@pytest.mark.parametrize("bound", ["start_date", "end_date"])
def test_pickup_window_rejects_datetime_subclasses(bound: str) -> None:
    values = {
        "start_date": date(2026, 9, 1),
        "end_date": date(2026, 9, 2),
    }
    values[bound] = datetime(2026, 9, 1, tzinfo=UTC)

    with pytest.raises(InvalidDomainValue, match="date_required"):
        PickupWindow(**values)  # type: ignore[arg-type]


async def test_proposal_and_operation_reject_datetime_pickup_dates(
    proposal: OperationProposal,
) -> None:
    pickup_datetime = datetime(2026, 9, 2, tzinfo=UTC)
    with pytest.raises(InvalidDomainValue, match="date_required"):
        OperationProposal(  # type: ignore[arg-type]
            route=proposal.route,
            pickup_date=pickup_datetime,
            mandate=proposal.mandate,
        )

    uow = InMemoryUnitOfWork()
    draft = await CreateIntakeDraftService(uow, FixedClock(), FixedIds([DRAFT_ID])).create(
        CreateIntakeDraftCommand("synthetic prompt", "EN_US", "intake-v1", proposal)
    )
    operation = await ApproveOperationService(
        uow,
        FixedClock(),
        FixedIds([OPERATION_ID, MANDATE_ID, STATUS_ID, AUDIT_ID]),
    ).approve(
        ApproveOperationCommand(
            draft.id, draft.version, "synthetic-coordinator", CORRELATION_ID
        )
    )

    with pytest.raises(InvalidDomainValue, match="date_required"):
        replace(operation, pickup_date=pickup_datetime)


@pytest.mark.parametrize(
    ("history_factory", "reason"),
    [
        (lambda entry: (entry, entry), "duplicate_entry_id"),
        (
            lambda entry: (replace(entry, operation_id=UUID(int=999)),),
            "operation_id_mismatch",
        ),
        (
            lambda entry: (replace(entry, operation_version=2),),
            "future_operation_version",
        ),
        (
            lambda entry: (
                entry,
                replace(
                    entry,
                    id=UUID(int=1),
                    occurred_at=entry.occurred_at - timedelta(seconds=1),
                ),
            ),
            "ordered_entries_required",
        ),
        (
            lambda entry: (replace(entry, status=OperationStatus.COMMITTED),),
            "must_match_latest_history",
        ),
    ],
)
async def test_operation_rejects_inconsistent_status_history(
    proposal: OperationProposal,
    history_factory: Callable[
        [OperationStatusEntry], tuple[OperationStatusEntry, ...]
    ],
    reason: str,
) -> None:
    uow = InMemoryUnitOfWork()
    draft = await CreateIntakeDraftService(uow, FixedClock(), FixedIds([DRAFT_ID])).create(
        CreateIntakeDraftCommand("synthetic prompt", "EN_US", "intake-v1", proposal)
    )
    operation = await ApproveOperationService(
        uow,
        FixedClock(),
        FixedIds([OPERATION_ID, MANDATE_ID, STATUS_ID, AUDIT_ID]),
    ).approve(
        ApproveOperationCommand(
            draft.id, draft.version, "synthetic-coordinator", CORRELATION_ID
        )
    )
    history = history_factory(operation.status_history[0])

    with pytest.raises(InvalidDomainValue, match=reason):
        replace(operation, status_history=history)
