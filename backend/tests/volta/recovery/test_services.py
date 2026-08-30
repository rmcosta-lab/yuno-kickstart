from dataclasses import replace as dc_replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from yuno_backend.volta.mandates.errors import MandateConflict
from yuno_backend.volta.mandates.models import Money, OperationStatus, PickupWindow
from yuno_backend.volta.mandates.services import MandatePolicy
from yuno_backend.volta.negotiations.errors import CallSessionNotFound, StaleOperationVersion
from yuno_backend.volta.negotiations.models import CommitmentDisposition
from yuno_backend.volta.recovery.commands import (
    AcknowledgeNotificationCommand,
    CreateEscalationCommand,
    ReplaceMandateCommand,
    ReplacementEvidence,
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
)
from yuno_backend.volta.recovery.models import (
    EscalationContext,
    Notification,
    PostContactEscalation,
    RecoveryDecision,
    RecoveryDecisionState,
    RecoveryOutcome,
    RecoveryScenario,
)
from yuno_backend.volta.recovery.services import (
    AcknowledgeNotificationService,
    CreateEscalationService,
    ReplaceMandateService,
    ResumeAfterEscalationService,
    SimulateInboundRecoveryService,
)

from .conftest import (
    CALL_ID,
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
    proposed = overrides.get("proposed_terms", safe_terms())
    safe = proposed.amount <= Decimal("1500")  # type: ignore[union-attr]
    values: dict[str, object] = {
        "operation_id": OPERATION_ID,
        "expected_operation_version": 2,
        "commitment_id": UUID(int=200),
        "mandate_version": 1,
        "proposed_terms": proposed,
        "correlation_id": UUID(int=900),
        "scenario": RecoveryScenario.MANDATE_SAFE if safe else RecoveryScenario.OUT_OF_MANDATE,
        "decision_reason": "MANDATE_SAFE_REPLACEMENT" if safe else "OUT_OF_MANDATE",
        "evidence": (
            ReplacementEvidence("safe.webm", 100, "item", "event") if safe else None
        ),
        "escalation_context": (
            None
            if safe
            else EscalationContext("Over mandate", ("Keep winner",), "Review mandate")
        ),
    }
    values.update(overrides)
    return SimulateInboundRecoveryCommand(**values)  # type: ignore[arg-type]


def _notification(notification_id: int = 500) -> Notification:
    active = active_commitment()
    state = RecoveryDecisionState(
        operation_version=2,
        operation_status=OperationStatus.COMMITTED,
        active_commitment_id=active.id,
        carrier_id=active.carrier_id,
        agreed_terms=active.agreed_terms,
    )
    return Notification(
        UUID(int=notification_id),
        OPERATION_ID,
        active.id,
        "MANDATE_SAFE_REPLACEMENT",
        operation().created_at,
        operation_version=2,
        recovery_decision=RecoveryDecision(state, state, "MANDATE_SAFE_REPLACEMENT"),
        message="A mandate-safe replacement commitment was activated.",
        correlation_id=UUID(int=notification_id + 1),
    )


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


async def test_replace_mandate_appends_version_resolves_escalation_and_audits() -> None:
    active = active_commitment()
    escalation = PostContactEscalation(
        UUID(int=300),
        OPERATION_ID,
        active.id,
        "OUT_OF_MANDATE",
        2,
        1,
        False,
        UUID(int=301),
        operation().created_at,
    )
    uow = Uow(
        operation(status=OperationStatus.ESCALATED),
        {active.id: active},
        escalations={escalation.id: escalation},
    )
    service = ReplaceMandateService(uow, MandatePolicy(), Clock(), Ids())

    result = await service.replace(
        ReplaceMandateCommand(
            OPERATION_ID,
            2,
            escalation.id,
            Money(Decimal("2000"), "MXN"),
            PickupWindow(date(2026, 9, 1), date(2026, 9, 4)),
            ("sealed",),
            ("weather",),
            "coordinator",
            UUID(int=302),
        )
    )

    assert result.version == 3
    assert result.mandate.version == 2
    assert result.mandate.approval_actor == "coordinator"
    assert uow.post_contact_escalations.values[escalation.id].resolved
    assert {event.event_type for event in uow.audit_events.values.values()} == {
        "MANDATE_REPLACED",
        "ESCALATION_RESOLVED",
    }
    assert all(
        event.actor_kind.value == "COORDINATOR" for event in uow.audit_events.values.values()
    )
    assert uow.commits == 1

    with pytest.raises(EscalationAlreadyResolved):
        await service.replace(
            ReplaceMandateCommand(
                OPERATION_ID,
                3,
                escalation.id,
                result.mandate.maximum_amount,
                result.mandate.pickup_window,
                result.mandate.allowed_conditions,
                result.mandate.escalation_conditions,
                "coordinator",
                UUID(int=303),
            )
        )


async def test_replace_mandate_rolls_back_all_in_memory_writes_on_audit_failure() -> None:
    active = active_commitment()
    escalation = PostContactEscalation(
        UUID(int=350),
        OPERATION_ID,
        active.id,
        "OUT_OF_MANDATE",
        2,
        1,
        False,
        UUID(int=351),
        operation().created_at,
    )
    original = operation(status=OperationStatus.ESCALATED)
    uow = Uow(original, {active.id: active}, escalations={escalation.id: escalation})

    async def fail_audit(_: object) -> None:
        raise RuntimeError("injected audit failure")

    uow.audit_events.add = fail_audit  # type: ignore[method-assign]
    service = ReplaceMandateService(uow, MandatePolicy(), Clock(), Ids())
    with pytest.raises(RuntimeError, match="injected audit failure"):
        await service.replace(
            ReplaceMandateCommand(
                OPERATION_ID,
                2,
                escalation.id,
                Money(Decimal("2000"), "MXN"),
                original.mandate.pickup_window,
                original.mandate.allowed_conditions,
                original.mandate.escalation_conditions,
                "coordinator",
                UUID(int=352),
            )
        )
    assert uow.operations.value == original
    assert uow.post_contact_escalations.values[escalation.id] == escalation
    assert not uow.audit_events.values
    assert uow.commits == 0
    assert uow.rollbacks == 1


async def test_replace_mandate_rejects_missing_foreign_and_stale_without_writes() -> None:
    active = active_commitment()
    original = operation(status=OperationStatus.ESCALATED)
    foreign = PostContactEscalation(
        UUID(int=370),
        UUID(int=999),
        active.id,
        "OUT_OF_MANDATE",
        2,
        1,
        False,
        UUID(int=371),
        original.created_at,
    )
    for escalation_id, escalations, expected_version in (
        (UUID(int=999), {}, 2),
        (foreign.id, {foreign.id: foreign}, 2),
        (foreign.id, {foreign.id: foreign}, 99),
    ):
        uow = Uow(original, {active.id: active}, escalations=escalations)
        with pytest.raises((EscalationNotFound, StaleOperationVersion)):
            await ReplaceMandateService(uow, MandatePolicy(), Clock(), Ids()).replace(
                ReplaceMandateCommand(
                    OPERATION_ID,
                    expected_version,
                    escalation_id,
                    original.mandate.maximum_amount,
                    original.mandate.pickup_window,
                    original.mandate.allowed_conditions,
                    original.mandate.escalation_conditions,
                    "coordinator",
                    UUID(int=372),
                )
            )
        assert uow.operations.value == original
        assert uow.post_contact_escalations.values == escalations
        assert not uow.audit_events.values
        assert uow.commits == 0


async def test_replace_mandate_rejects_invalid_values_without_writes() -> None:
    active = active_commitment()
    escalation = PostContactEscalation(
        UUID(int=380),
        OPERATION_ID,
        active.id,
        "OUT_OF_MANDATE",
        2,
        1,
        False,
        UUID(int=381),
        operation().created_at,
    )
    original = operation(status=OperationStatus.ESCALATED)
    for maximum_amount, pickup_window, allowed_conditions in (
        (Money(Decimal("-1"), "MXN"), original.mandate.pickup_window, ("sealed",)),
        (Money(Decimal("2000"), "USD"), original.mandate.pickup_window, ("sealed",)),
        (
            Money(Decimal("2000"), "MXN"),
            PickupWindow(date(2026, 9, 4), date(2026, 9, 1)),
            ("sealed",),
        ),
        (
            Money(Decimal("2000"), "MXN"),
            original.mandate.pickup_window,
            ("",),
        ),
    ):
        uow = Uow(original, {active.id: active}, escalations={escalation.id: escalation})
        with pytest.raises(MandateConflict):
            await ReplaceMandateService(uow, MandatePolicy(), Clock(), Ids()).replace(
                ReplaceMandateCommand(
                    OPERATION_ID,
                    2,
                    escalation.id,
                    maximum_amount,
                    pickup_window,
                    allowed_conditions,
                    original.mandate.escalation_conditions,
                    "coordinator",
                    UUID(int=382),
                )
            )
        assert uow.operations.value == original
        assert uow.post_contact_escalations.values[escalation.id] == escalation
        assert not uow.audit_events.values
        assert uow.commits == 0


async def test_explicit_escalation_supports_call_without_commitment_and_blocks_duplicate() -> None:
    uow = Uow(operation(status=OperationStatus.NEGOTIATING))
    service = CreateEscalationService(uow, Clock(), Ids())
    command = CreateEscalationCommand(
        CALL_ID,
        2,
        "Carrier cannot honor the pickup window.",
        ("Asked for another slot.",),
        "Coordinator should choose a fallback.",
        UUID(int=400),
    )

    escalation = await service.create(command)

    assert escalation.call_id == CALL_ID
    assert escalation.commitment_id is None
    assert escalation.context is not None
    assert uow.operations.value.status is OperationStatus.ESCALATED
    assert not uow.commitments.values
    with pytest.raises(EscalationContextConflict):
        await service.create(
            CreateEscalationCommand(
                CALL_ID,
                3,
                "Another conflict.",
                (),
                "Review.",
                UUID(int=401),
            )
        )


async def test_explicit_escalation_ignores_active_commitment_from_another_call() -> None:
    active = dc_replace(active_commitment(), call_id=UUID(int=777))
    uow = Uow(operation(status=OperationStatus.NEGOTIATING), {active.id: active})
    escalation = await CreateEscalationService(uow, Clock(), Ids()).create(
        CreateEscalationCommand(
            CALL_ID,
            2,
            "The selected call needs coordinator review.",
            (),
            "Review this call.",
            UUID(int=450),
        )
    )
    assert escalation.commitment_id is None
    assert uow.commitments.values[active.id] == active


async def test_explicit_escalation_rejects_missing_call_and_stale_without_writes() -> None:
    for call_id, expected_version in ((UUID(int=999), 2), (CALL_ID, 99)):
        original = operation(status=OperationStatus.NEGOTIATING)
        uow = Uow(original)
        with pytest.raises((CallSessionNotFound, StaleOperationVersion)):
            await CreateEscalationService(uow, Clock(), Ids()).create(
                CreateEscalationCommand(
                    call_id,
                    expected_version,
                    "Conflict.",
                    (),
                    "Review.",
                    UUID(int=460),
                )
            )
        assert uow.operations.value == original
        assert not uow.post_contact_escalations.values
        assert not uow.audit_events.values
        assert uow.commits == 0


async def test_explicit_escalation_rolls_back_on_audit_failure() -> None:
    original = operation(status=OperationStatus.NEGOTIATING)
    uow = Uow(original)

    async def fail_audit(_: object) -> None:
        raise RuntimeError("injected audit failure")

    uow.audit_events.add = fail_audit  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="injected audit failure"):
        await CreateEscalationService(uow, Clock(), Ids()).create(
            CreateEscalationCommand(
                CALL_ID,
                2,
                "Conflict.",
                (),
                "Review.",
                UUID(int=470),
            )
        )
    assert uow.operations.value == original
    assert not uow.post_contact_escalations.values
    assert not uow.audit_events.values
    assert uow.commits == 0


async def test_notification_acknowledgement_is_idempotent_and_actor_is_immutable() -> None:
    active = active_commitment()
    uow = Uow(operation(), {active.id: active})
    notification = _notification()
    uow.notifications.values[notification.id] = notification
    service = AcknowledgeNotificationService(uow, Clock(), Ids())
    command = AcknowledgeNotificationCommand(notification.id, 2, "coordinator", UUID(int=501))

    acknowledged = await service.acknowledge(command)
    replay = await service.acknowledge(command)

    assert acknowledged == replay
    assert acknowledged.acknowledged_by == "coordinator"
    assert acknowledged.acknowledged_at == Clock().now()
    assert acknowledged.operation_version == 2
    assert uow.operations.value.version == 3
    assert len(uow.audit_events.values) == 1
    with pytest.raises(NotificationAlreadyAcknowledged):
        await service.acknowledge(
            AcknowledgeNotificationCommand(notification.id, 3, "other", UUID(int=502))
        )
    with pytest.raises(NotificationNotFound):
        await service.acknowledge(
            AcknowledgeNotificationCommand(UUID(int=999), 3, "coordinator", UUID(int=503))
        )


async def test_notification_acknowledgement_rejects_stale_before_first_write() -> None:
    active = active_commitment()
    original = operation()
    notification = _notification(550)
    uow = Uow(original, {active.id: active})
    uow.notifications.values[notification.id] = notification
    with pytest.raises(StaleOperationVersion):
        await AcknowledgeNotificationService(uow, Clock(), Ids()).acknowledge(
            AcknowledgeNotificationCommand(
                notification.id, 99, "coordinator", UUID(int=551)
            )
        )
    assert uow.operations.value == original
    assert uow.notifications.values[notification.id] == notification
    assert not uow.audit_events.values
    assert uow.commits == 0
