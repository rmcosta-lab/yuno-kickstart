from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest
from yuno_backend.volta.mandates import (
    ApproveOperationCommand,
    ApproveOperationService,
    Clock,
    CreateIntakeDraftCommand,
    CreateIntakeDraftService,
    DraftNotApprovable,
    DraftNotFound,
    DraftValidationIssue,
    IdGenerator,
    IntakeDraft,
    IntakeDraftRepository,
    OperationAlreadyApproved,
    OperationProposal,
    OperationRepository,
    OperationUnitOfWork,
    StaleDraftVersion,
)

from .conftest import (
    DRAFT_ID,
    MANDATE_ID,
    NOW,
    OPERATION_ID,
    FixedClock,
    FixedIds,
    InMemoryUnitOfWork,
)


async def _create_valid_draft(
    uow: InMemoryUnitOfWork,
    proposal: OperationProposal,
):
    return await CreateIntakeDraftService(uow, FixedClock(), FixedIds([DRAFT_ID])).create(
        CreateIntakeDraftCommand("synthetic request", "EN_US", "intake-v1", proposal)
    )


async def test_approval_creates_one_immutable_operation_and_mandate(
    proposal: OperationProposal,
) -> None:
    uow = InMemoryUnitOfWork()
    draft = await _create_valid_draft(uow, proposal)
    uow.commit_calls = 0

    operation = await ApproveOperationService(
        uow,
        FixedClock(),
        FixedIds([OPERATION_ID, MANDATE_ID]),
    ).approve(ApproveOperationCommand(DRAFT_ID, 1, "synthetic-coordinator"))

    assert operation.id == OPERATION_ID
    assert operation.version == operation.source_draft_version == 1
    assert operation.source_draft_id == draft.id
    assert operation.route is proposal.route
    assert operation.mandate.id == MANDATE_ID
    assert operation.mandate.version == 1
    assert operation.mandate.operation_id == operation.id
    assert operation.mandate.approval_actor == "synthetic-coordinator"
    assert operation.mandate.approved_at == operation.created_at == NOW
    assert tuple(action.value for action in operation.mandate.authorized_actions) == (
        "NEGOTIATE",
        "COMMIT",
    )
    assert uow.operations.add_calls == uow.commit_calls == 1
    with pytest.raises(FrozenInstanceError):
        operation.version = 2  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        operation.mandate.version = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    ("scenario", "error_type"),
    [
        ("missing", DraftNotFound),
        ("stale", StaleDraftVersion),
        ("invalid", DraftNotApprovable),
        ("duplicate", OperationAlreadyApproved),
    ],
)
async def test_approval_rejections_are_typed_safe_and_do_not_commit(
    scenario: str,
    error_type: type[Exception],
    proposal: OperationProposal,
) -> None:
    uow = InMemoryUnitOfWork()
    command = ApproveOperationCommand(DRAFT_ID, 1, "synthetic-coordinator")
    if scenario != "missing":
        draft = await _create_valid_draft(uow, proposal)
        uow.commit_calls = 0
        uow.rollback_calls = 0
        if scenario == "stale":
            command = ApproveOperationCommand(DRAFT_ID, 2, "synthetic-coordinator")
        elif scenario == "invalid":
            from dataclasses import replace

            issue_draft = replace(
                draft,
                validation_issues=(DraftValidationIssue("route.origin", "required"),),
                approval_eligible=False,
            )
            uow.intake_drafts.values[DRAFT_ID] = issue_draft
        elif scenario == "duplicate":
            await ApproveOperationService(
                uow,
                FixedClock(),
                FixedIds([OPERATION_ID, MANDATE_ID]),
            ).approve(command)
            uow.commit_calls = 0
            uow.rollback_calls = 0

    with pytest.raises(error_type) as captured:
        await ApproveOperationService(
            uow,
            FixedClock(),
            FixedIds([UUID(int=900), UUID(int=901)]),
        ).approve(command)

    assert "synthetic request" not in str(captured.value)
    assert uow.commit_calls == 0
    assert uow.rollback_calls == 1


async def test_repository_failure_rolls_back_without_commit(
    proposal: OperationProposal,
) -> None:
    class FailingDraftRepository:
        async def get(self, draft_id: UUID) -> IntakeDraft | None:
            return None

        async def add(self, draft: IntakeDraft) -> None:
            raise RuntimeError("synthetic repository failure")

    uow = InMemoryUnitOfWork()
    uow.intake_drafts = FailingDraftRepository()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="synthetic repository failure"):
        await CreateIntakeDraftService(uow, FixedClock(), FixedIds([DRAFT_ID])).create(
            CreateIntakeDraftCommand("synthetic request", "EN_US", "intake-v1", proposal)
        )

    assert uow.commit_calls == 0
    assert uow.rollback_calls == 1


def test_ports_accept_deterministic_test_doubles() -> None:
    uow = InMemoryUnitOfWork()
    assert isinstance(uow.intake_drafts, IntakeDraftRepository)
    assert isinstance(uow.operations, OperationRepository)
    assert isinstance(uow, OperationUnitOfWork)
    assert isinstance(FixedClock(), Clock)
    assert isinstance(FixedIds([DRAFT_ID]), IdGenerator)
