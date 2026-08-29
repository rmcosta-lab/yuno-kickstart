from dataclasses import FrozenInstanceError, replace
from uuid import UUID

import pytest
from yuno_backend.volta.audit import AuditEventRepository
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
        FixedIds([OPERATION_ID, MANDATE_ID, STATUS_ID, AUDIT_ID]),
    ).approve(ApproveOperationCommand(DRAFT_ID, 1, "synthetic-coordinator", CORRELATION_ID))

    assert operation.id == OPERATION_ID
    assert operation.version == operation.source_draft_version == 1
    assert operation.source_draft_id == draft.id
    assert operation.route is proposal.route
    assert operation.mandate.id == MANDATE_ID
    assert operation.mandate.version == 1
    assert operation.mandate.operation_id == operation.id
    assert operation.mandate.approval_actor == "synthetic-coordinator"
    assert operation.mandate.approved_at == operation.created_at == NOW
    assert operation.status.value == "READY"
    assert operation.status_history[0].id == STATUS_ID
    assert operation.status_history[0].occurred_at == NOW
    assert tuple(action.value for action in operation.mandate.authorized_actions) == (
        "NEGOTIATE",
        "COMMIT",
    )
    assert uow.operations.add_calls == uow.commit_calls == 1
    event = uow.audit_events.values[AUDIT_ID]
    assert event.event_type == "OPERATION_APPROVED"
    assert event.correlation_id == CORRELATION_ID
    assert event.metadata == {"draft_version": 1}
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
    command = ApproveOperationCommand(DRAFT_ID, 1, "synthetic-coordinator", CORRELATION_ID)
    if scenario != "missing":
        draft = await _create_valid_draft(uow, proposal)
        uow.commit_calls = 0
        uow.rollback_calls = 0
        if scenario == "stale":
            command = ApproveOperationCommand(
                DRAFT_ID, 2, "synthetic-coordinator", CORRELATION_ID
            )
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
                FixedIds([OPERATION_ID, MANDATE_ID, STATUS_ID, AUDIT_ID]),
            ).approve(command)
            uow.commit_calls = 0
            uow.rollback_calls = 0

    with pytest.raises(error_type) as captured:
        await ApproveOperationService(
            uow,
            FixedClock(),
            FixedIds([UUID(int=900), UUID(int=901), UUID(int=902), UUID(int=903)]),
        ).approve(command)

    assert "synthetic request" not in str(captured.value)
    assert uow.commit_calls == 0
    assert uow.rollback_calls == 1


async def test_audit_failure_rolls_back_operation_status_and_mandate(
    proposal: OperationProposal,
) -> None:
    class FailingAuditRepository:
        values: dict[UUID, object] = {}

        async def add(self, event: object) -> None:
            raise RuntimeError("synthetic audit failure")

        async def list_by_operation(self, operation_id: UUID) -> tuple[()]:
            return ()

    uow = InMemoryUnitOfWork()
    await _create_valid_draft(uow, proposal)
    uow.commit_calls = 0
    uow.rollback_calls = 0
    uow.audit_events = FailingAuditRepository()  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="synthetic audit failure"):
        await ApproveOperationService(
            uow,
            FixedClock(),
            FixedIds([OPERATION_ID, MANDATE_ID, STATUS_ID, AUDIT_ID]),
        ).approve(
            ApproveOperationCommand(
                DRAFT_ID, 1, "synthetic-coordinator", CORRELATION_ID
            )
        )

    assert uow.operations.values == {}
    assert uow.commit_calls == 0
    assert uow.rollback_calls == 1


async def test_repository_failure_rolls_back_without_commit(
    proposal: OperationProposal,
) -> None:
    class FailingDraftRepository:
        values: dict[UUID, IntakeDraft] = {}

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
    assert isinstance(uow.audit_events, AuditEventRepository)
    assert isinstance(uow, OperationUnitOfWork)
    assert isinstance(FixedClock(), Clock)
    assert isinstance(FixedIds([DRAFT_ID]), IdGenerator)


async def test_in_memory_audit_repository_orders_timestamp_ties_by_event_id(
    proposal: OperationProposal,
) -> None:
    uow = InMemoryUnitOfWork()
    await _create_valid_draft(uow, proposal)
    operation = await ApproveOperationService(
        uow,
        FixedClock(),
        FixedIds([OPERATION_ID, MANDATE_ID, STATUS_ID, AUDIT_ID]),
    ).approve(
        ApproveOperationCommand(
            DRAFT_ID, 1, "synthetic-coordinator", CORRELATION_ID
        )
    )
    first = uow.audit_events.values[AUDIT_ID]
    earlier_id = UUID(int=AUDIT_ID.int - 1)
    await uow.audit_events.add(replace(first, event_id=earlier_id))

    events = await uow.audit_events.list_by_operation(operation.id)

    assert tuple(event.event_id for event in events) == (earlier_id, AUDIT_ID)
