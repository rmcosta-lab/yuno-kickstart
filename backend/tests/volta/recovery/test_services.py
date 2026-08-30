from dataclasses import replace as dc_replace
from decimal import Decimal
from uuid import UUID

import pytest
from yuno_backend.volta.mandates.services import MandatePolicy
from yuno_backend.volta.negotiations.errors import StaleOperationVersion
from yuno_backend.volta.negotiations.models import CommitmentDisposition
from yuno_backend.volta.recovery.commands import (
    ResumeAfterEscalationCommand,
    SimulateInboundRecoveryCommand,
)
from yuno_backend.volta.recovery.errors import (
    CommitmentNotFound,
    EscalationNotFound,
    InvalidCommitmentDisposition,
    MandateVersionNotAdvanced,
    OperationBlockedByEscalation,
)
from yuno_backend.volta.recovery.models import RecoveryOutcome
from yuno_backend.volta.recovery.services import (
    ResumeAfterEscalationService,
    SimulateInboundRecoveryService,
)

from .conftest import (
    OPERATION_ID,
    Clock,
    Ids,
    Uow,
    active_commitment,
    operation,
    original_quote,
    safe_terms,
)


def _recovery_command(**overrides: object) -> SimulateInboundRecoveryCommand:
    values: dict[str, object] = {
        "operation_id": OPERATION_ID,
        "expected_operation_version": 2,
        "commitment_id": UUID(int=200),
        "mandate_version": 1,
        "proposed_terms": safe_terms(),
        "correlation_id": UUID(int=900),
    }
    values.update(overrides)
    return SimulateInboundRecoveryCommand(**values)  # type: ignore[arg-type]


async def test_mandate_safe_attempt_atomically_replaces_and_notifies() -> None:
    active = active_commitment()
    uow = Uow(operation(), {active.id: active}, {original_quote().id: original_quote()})
    service = SimulateInboundRecoveryService(uow, MandatePolicy(), Clock(), Ids())

    attempt = await service.simulate(_recovery_command())

    assert attempt.outcome is RecoveryOutcome.REPLACED
    assert attempt.resulting_commitment_id is not None
    superseded = uow.commitments.values[active.id]
    assert superseded.disposition is CommitmentDisposition.SUPERSEDED
    assert superseded.replaced_by_commitment_id == attempt.resulting_commitment_id
    replacement = uow.commitments.values[attempt.resulting_commitment_id]
    assert replacement.disposition is CommitmentDisposition.ACTIVE
    assert replacement.replaces_commitment_id == active.id
    active_count = sum(
        1
        for item in uow.commitments.values.values()
        if item.disposition is CommitmentDisposition.ACTIVE
    )
    assert active_count == 1
    assert len(uow.notifications.values) == 1
    assert uow.commits == 1
    event_types = {event.event_type for event in uow.audit_events.values.values()}
    assert "RECOVERY_REPLACEMENT_APPLIED" in event_types
    assert "COMMITMENT_SUPERSEDED" in event_types
    assert "COMMITMENT_ACTIVATED" in event_types


async def test_out_of_mandate_attempt_escalates_and_blocks_further_attempts() -> None:
    active = active_commitment()
    uow = Uow(operation(), {active.id: active}, {original_quote().id: original_quote()})
    service = SimulateInboundRecoveryService(uow, MandatePolicy(), Clock(), Ids())

    over_mandate = _recovery_command(proposed_terms=safe_terms(amount=Decimal("999999")))
    attempt = await service.simulate(over_mandate)

    assert attempt.outcome is RecoveryOutcome.ESCALATED
    assert attempt.escalation_id is not None
    assert uow.commitments.values[active.id].disposition is CommitmentDisposition.ACTIVE
    assert len(uow.commitments.values) == 1
    assert len(uow.notifications.values) == 0
    event_types = {event.event_type for event in uow.audit_events.values.values()}
    assert event_types == {"POST_CONTACT_ESCALATED"}

    with pytest.raises(OperationBlockedByEscalation):
        await service.simulate(
            _recovery_command(expected_operation_version=3, correlation_id=UUID(int=901))
        )


async def test_simulate_rejects_missing_or_superseded_commitment() -> None:
    active = active_commitment()
    uow = Uow(operation(), {active.id: active}, {original_quote().id: original_quote()})
    service = SimulateInboundRecoveryService(uow, MandatePolicy(), Clock(), Ids())

    with pytest.raises(CommitmentNotFound):
        await service.simulate(_recovery_command(commitment_id=UUID(int=999)))

    uow.commitments.values[active.id] = dc_replace(
        active,
        disposition=CommitmentDisposition.SUPERSEDED,
        replaced_by_commitment_id=UUID(int=777),
        superseded_at=operation().created_at,
    )
    with pytest.raises(InvalidCommitmentDisposition):
        await service.simulate(_recovery_command())


async def test_simulate_rejects_stale_operation_version_and_writes_nothing() -> None:
    active = active_commitment()
    uow = Uow(operation(), {active.id: active}, {original_quote().id: original_quote()})
    service = SimulateInboundRecoveryService(uow, MandatePolicy(), Clock(), Ids())

    with pytest.raises(StaleOperationVersion):
        await service.simulate(_recovery_command(expected_operation_version=99))
    assert len(uow.commitments.values) == 1
    assert uow.commits == 0


async def test_resume_requires_strictly_greater_mandate_version_and_mutates_no_commitment() -> None:
    active = active_commitment()
    uow = Uow(operation(), {active.id: active}, {original_quote().id: original_quote()})
    service = SimulateInboundRecoveryService(uow, MandatePolicy(), Clock(), Ids())
    escalated = await service.simulate(
        _recovery_command(proposed_terms=safe_terms(amount=Decimal("999999")))
    )

    resume_service = ResumeAfterEscalationService(uow, Clock(), Ids())
    with pytest.raises(MandateVersionNotAdvanced):
        await resume_service.resume(
            ResumeAfterEscalationCommand(OPERATION_ID, 3, escalated.escalation_id, 1, UUID(int=910))
        )
    with pytest.raises(MandateVersionNotAdvanced):
        await resume_service.resume(
            ResumeAfterEscalationCommand(OPERATION_ID, 3, escalated.escalation_id, 0, UUID(int=911))
        )

    resolved = await resume_service.resume(
        ResumeAfterEscalationCommand(OPERATION_ID, 3, escalated.escalation_id, 2, UUID(int=912))
    )
    assert resolved.resolved is True
    assert uow.commitments.values[active.id].disposition is CommitmentDisposition.ACTIVE
    assert len(uow.commitments.values) == 1

    unblocked = await service.simulate(
        _recovery_command(expected_operation_version=4, correlation_id=UUID(int=913))
    )
    assert unblocked.outcome is RecoveryOutcome.REPLACED


async def test_resume_rejects_unknown_escalation_and_is_idempotent_once_resolved() -> None:
    active = active_commitment()
    uow = Uow(operation(), {active.id: active}, {original_quote().id: original_quote()})
    service = SimulateInboundRecoveryService(uow, MandatePolicy(), Clock(), Ids())
    escalated = await service.simulate(
        _recovery_command(proposed_terms=safe_terms(amount=Decimal("999999")))
    )
    resume_service = ResumeAfterEscalationService(uow, Clock(), Ids())

    with pytest.raises(EscalationNotFound):
        await resume_service.resume(
            ResumeAfterEscalationCommand(OPERATION_ID, 3, UUID(int=999), 2, UUID(int=920))
        )

    resolved = await resume_service.resume(
        ResumeAfterEscalationCommand(OPERATION_ID, 3, escalated.escalation_id, 2, UUID(int=921))
    )
    replay = await resume_service.resume(
        ResumeAfterEscalationCommand(OPERATION_ID, 4, escalated.escalation_id, 3, UUID(int=922))
    )
    assert replay == resolved
