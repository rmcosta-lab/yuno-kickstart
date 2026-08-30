from datetime import UTC, datetime
from uuid import UUID

import pytest
from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.recovery.models import (
    EscalationContext,
    Notification,
    PostContactEscalation,
    RecoveryAttempt,
    RecoveryOutcome,
    RecoveryScenario,
)

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


def test_recovery_attempt_replaced_requires_resulting_commitment_only() -> None:
    attempt = RecoveryAttempt(
        UUID(int=1),
        UUID(int=2),
        UUID(int=3),
        RecoveryScenario.MANDATE_SAFE,
        1,
        2,
        "MANDATE_SAFE_REPLACEMENT",
        RecoveryOutcome.REPLACED,
        UUID(int=4),
        None,
        UUID(int=5),
        NOW,
        UUID(int=6),
    )
    assert attempt.resulting_commitment_id == UUID(int=4)
    with pytest.raises(InvalidDomainValue):
        RecoveryAttempt(
            UUID(int=1),
            UUID(int=2),
            UUID(int=3),
            RecoveryScenario.MANDATE_SAFE,
            1,
            2,
            "MANDATE_SAFE_REPLACEMENT",
            RecoveryOutcome.REPLACED,
            None,
            None,
            UUID(int=5),
            NOW,
            UUID(int=7),
        )
    with pytest.raises(InvalidDomainValue):
        RecoveryAttempt(
            UUID(int=1),
            UUID(int=2),
            UUID(int=3),
            RecoveryScenario.MANDATE_SAFE,
            1,
            2,
            "MANDATE_SAFE_REPLACEMENT",
            RecoveryOutcome.REPLACED,
            UUID(int=4),
            UUID(int=6),
            UUID(int=5),
            NOW,
        )


def test_recovery_attempt_escalated_requires_escalation_only() -> None:
    attempt = RecoveryAttempt(
        UUID(int=1),
        UUID(int=2),
        UUID(int=3),
        RecoveryScenario.OUT_OF_MANDATE,
        1,
        2,
        "OUT_OF_MANDATE",
        RecoveryOutcome.ESCALATED,
        None,
        UUID(int=4),
        UUID(int=5),
        NOW,
    )
    assert attempt.escalation_id == UUID(int=4)
    with pytest.raises(InvalidDomainValue):
        RecoveryAttempt(
            UUID(int=1),
            UUID(int=2),
            UUID(int=3),
            RecoveryScenario.OUT_OF_MANDATE,
            1,
            2,
            "OUT_OF_MANDATE",
            RecoveryOutcome.ESCALATED,
            None,
            None,
            UUID(int=5),
            NOW,
        )


def test_post_contact_escalation_resolved_state_must_match_resolved_at() -> None:
    unresolved = PostContactEscalation(
        UUID(int=1), UUID(int=2), UUID(int=3), "OUT_OF_MANDATE", 1, 1, False, UUID(int=4), NOW
    )
    assert unresolved.resolved_at is None
    resolved = PostContactEscalation(
        UUID(int=1), UUID(int=2), UUID(int=3), "OUT_OF_MANDATE", 1, 1, True, UUID(int=4), NOW, NOW
    )
    assert resolved.resolved_at == NOW
    with pytest.raises(InvalidDomainValue):
        PostContactEscalation(
            UUID(int=1), UUID(int=2), UUID(int=3), "OUT_OF_MANDATE", 1, 1, True, UUID(int=4), NOW
        )
    with pytest.raises(InvalidDomainValue):
        PostContactEscalation(
            UUID(int=1),
            UUID(int=2),
            UUID(int=3),
            "OUT_OF_MANDATE",
            1,
            1,
            False,
            UUID(int=4),
            NOW,
            NOW,
        )


def test_notification_requires_safe_reason_code() -> None:
    notification = Notification(
        UUID(int=1), UUID(int=2), UUID(int=3), "MANDATE_SAFE_REPLACEMENT", NOW
    )
    assert notification.reason_code == "MANDATE_SAFE_REPLACEMENT"
    with pytest.raises(InvalidDomainValue):
        Notification(UUID(int=1), UUID(int=2), UUID(int=3), "", NOW)


def test_escalation_context_is_bounded_and_notification_ack_is_all_or_none() -> None:
    context = EscalationContext("capacity conflict", ("later pickup",), "human review")
    assert context.attempted_alternatives == ("later pickup",)
    with pytest.raises(InvalidDomainValue):
        EscalationContext("x", tuple("a" for _ in range(26)), "review")
    with pytest.raises(InvalidDomainValue):
        PostContactEscalation(
            UUID(int=1),
            UUID(int=2),
            None,
            "EXPLICIT_COORDINATOR_ESCALATION",
            1,
            1,
            False,
            UUID(int=4),
            NOW,
            call_id=UUID(int=5),
        )
    with pytest.raises(InvalidDomainValue):
        Notification(
            UUID(int=1),
            UUID(int=2),
            UUID(int=3),
            "MANDATE_SAFE_REPLACEMENT",
            NOW,
            operation_version=1,
        )
    with pytest.raises(InvalidDomainValue):
        Notification(
            UUID(int=1),
            UUID(int=2),
            UUID(int=3),
            "MANDATE_SAFE_REPLACEMENT",
            NOW,
            acknowledged_by="coordinator",
        )
