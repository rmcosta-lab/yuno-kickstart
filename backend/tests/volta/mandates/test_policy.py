from dataclasses import replace
from datetime import date
from decimal import Decimal
from uuid import UUID

import pytest
from yuno_backend.volta.mandates import (
    CheckMandateCommand,
    Mandate,
    MandateAction,
    MandateConflict,
    Money,
    OperationProposal,
)

from .conftest import MANDATE_ID, NOW, OPERATION_ID


@pytest.fixture
def mandate(proposal: OperationProposal) -> Mandate:
    return Mandate(
        id=MANDATE_ID,
        operation_id=OPERATION_ID,
        version=1,
        maximum_amount=proposal.mandate.maximum_amount,
        pickup_window=proposal.mandate.pickup_window,
        allowed_conditions=proposal.mandate.allowed_conditions,
        escalation_conditions=proposal.mandate.escalation_conditions,
        authorized_actions=(MandateAction.NEGOTIATE, MandateAction.COMMIT),
        approval_actor="synthetic-coordinator",
        approved_at=NOW,
    )


def command(**changes: object) -> CheckMandateCommand:
    values: dict[str, object] = {
        "operation_id": OPERATION_ID,
        "mandate_version": 1,
        "action": MandateAction.COMMIT,
        "proposed_amount": Money(Decimal("1500.00"), "MXN"),
        "proposed_pickup_date": date(2026, 9, 2),
        "proposed_conditions": ("sealed container",),
    }
    values.update(changes)
    return CheckMandateCommand(**values)  # type: ignore[arg-type]


def test_policy_allows_exact_cap_and_inclusive_pickup_boundaries(mandate: Mandate) -> None:
    from yuno_backend.volta.mandates import MandatePolicy

    for pickup_date in (
        mandate.pickup_window.start_date,
        mandate.pickup_window.end_date,
    ):
        decision = MandatePolicy.evaluate(
            mandate,
            command(proposed_pickup_date=pickup_date),
        )
        assert decision.allowed
        assert decision.reason_codes == ()


@pytest.mark.parametrize(
    ("mandate_change", "command_change", "reason"),
    [
        ({"authorized_actions": (MandateAction.NEGOTIATE,)}, {}, "action_not_authorized"),
        ({}, {"operation_id": UUID(int=999)}, "operation_mismatch"),
        ({}, {"mandate_version": 2}, "mandate_version_mismatch"),
        ({}, {"proposed_amount": Money(Decimal("1500.01"), "MXN")}, "amount_exceeds_maximum"),
        ({}, {"proposed_amount": Money(Decimal("1500.00"), "USD")}, "currency_mismatch"),
        ({}, {"proposed_pickup_date": date(2026, 9, 4)}, "pickup_outside_window"),
        ({}, {"proposed_conditions": ("unapproved surcharge",)}, "conditions_not_allowed"),
    ],
)
def test_policy_rejects_each_authority_violation_independently(
    mandate: Mandate,
    mandate_change: dict[str, object],
    command_change: dict[str, object],
    reason: str,
) -> None:
    from yuno_backend.volta.mandates import MandatePolicy

    decision = MandatePolicy.evaluate(replace(mandate, **mandate_change), command(**command_change))
    assert not decision.allowed
    assert decision.reason_codes == (reason,)


def test_combined_reasons_are_stable_and_exception_uses_identical_reasons(
    mandate: Mandate,
) -> None:
    from yuno_backend.volta.mandates import MandatePolicy

    restricted = replace(mandate, authorized_actions=(MandateAction.NEGOTIATE,))
    proposed = command(
        mandate_version=9,
        proposed_amount=Money(Decimal("1500.01"), "USD"),
        proposed_pickup_date=date(2026, 9, 4),
        proposed_conditions=("unapproved surcharge",),
    )
    decision = MandatePolicy.evaluate(restricted, proposed)

    assert decision.reason_codes == (
        "action_not_authorized",
        "mandate_version_mismatch",
        "amount_exceeds_maximum",
        "currency_mismatch",
        "pickup_outside_window",
        "conditions_not_allowed",
    )
    with pytest.raises(MandateConflict) as captured:
        MandatePolicy.require_allowed(restricted, proposed)
    assert captured.value.reason_codes == decision.reason_codes
    assert captured.value.operation_id == OPERATION_ID
