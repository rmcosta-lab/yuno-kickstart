"""Provider-neutral deterministic recovery scenarios for the P0 demo."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol, runtime_checkable

from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.negotiations.models import QuoteTerms
from yuno_backend.volta.recovery.commands import ReplacementEvidence
from yuno_backend.volta.recovery.models import EscalationContext, RecoveryScenario

__all__ = [
    "DeterministicRecoveryFixtureCatalog",
    "RecoveryFixture",
    "RecoveryFixtureCatalog",
    "RecoveryScenario",
]


@dataclass(frozen=True, slots=True)
class RecoveryFixture:
    scenario: RecoveryScenario
    proposed_terms: QuoteTerms
    decision_reason: str
    evidence: ReplacementEvidence | None
    escalation_context: EscalationContext | None

    def __post_init__(self) -> None:
        if not isinstance(self.scenario, RecoveryScenario):
            raise InvalidDomainValue("scenario", "recovery_scenario_required")
        if not self.decision_reason.strip() or len(self.decision_reason) > 500:
            raise InvalidDomainValue("decision_reason", "bounded_text_required")
        safe = self.scenario is RecoveryScenario.MANDATE_SAFE
        if safe != (self.evidence is not None) or safe == (
            self.escalation_context is not None
        ):
            raise InvalidDomainValue("scenario", "fixture_shape_mismatch")


@runtime_checkable
class RecoveryFixtureCatalog(Protocol):
    def get(self, scenario: RecoveryScenario) -> RecoveryFixture: ...


class DeterministicRecoveryFixtureCatalog:
    """Two bounded scripts; no network/provider state participates in selection."""

    def __init__(self, fixtures: tuple[RecoveryFixture, ...] | None = None) -> None:
        selected = _default_fixtures() if fixtures is None else fixtures
        self._fixtures = {fixture.scenario: fixture for fixture in selected}
        if set(self._fixtures) != set(RecoveryScenario) or len(selected) != len(self._fixtures):
            raise InvalidDomainValue("fixtures", "exactly_one_per_scenario_required")

    def get(self, scenario: RecoveryScenario) -> RecoveryFixture:
        if not isinstance(scenario, RecoveryScenario):
            raise InvalidDomainValue("scenario", "supported_recovery_scenario_required")
        return self._fixtures[scenario]


def _default_fixtures() -> tuple[RecoveryFixture, ...]:
    pickup = date(2026, 9, 3)
    return (
        RecoveryFixture(
            RecoveryScenario.MANDATE_SAFE,
            QuoteTerms(
                Decimal("8750"),
                "MXN",
                pickup,
                pickup,
                ("40ft dry container", "Standard handling"),
            ),
            "MANDATE_SAFE_REPLACEMENT",
            ReplacementEvidence(
                "fixture-recovery-mandate-safe.webm",
                1840,
                "recovery-safe-item",
                "recovery-safe-event",
            ),
            None,
        ),
        RecoveryFixture(
            RecoveryScenario.OUT_OF_MANDATE,
            QuoteTerms(
                Decimal("9500"),
                "MXN",
                pickup,
                pickup,
                ("40ft dry container", "Hazardous surcharge"),
            ),
            "OUT_OF_MANDATE",
            None,
            EscalationContext(
                "The requested replacement exceeds the approved maximum amount.",
                ("Retain the active commitment", "Request coordinator approval"),
                "Review the proposed amount before changing the mandate.",
            ),
        ),
    )
