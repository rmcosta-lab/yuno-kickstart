from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal

import pytest
from yuno_backend.volta.intake import (
    DeterministicIntakeExtractor,
    ExtractionRequest,
    IntakeExtractor,
)
from yuno_backend.volta.mandates import (
    MandateProposal,
    Money,
    OperationProposal,
    PickupWindow,
    Route,
)


def proposal() -> OperationProposal:
    return OperationProposal(
        route=Route("Synthetic Port", "Synthetic Yard"),
        pickup_date=date(2026, 9, 3),
        mandate=MandateProposal(
            maximum_amount=Money(Decimal("9000"), "MXN"),
            pickup_window=PickupWindow(date(2026, 9, 3), date(2026, 9, 3)),
            escalation_conditions=("different pickup day", "higher total rate"),
        ),
    )


@pytest.mark.asyncio
async def test_fixed_deterministic_extractor_implements_protocol() -> None:
    expected = proposal()
    extractor: IntakeExtractor = DeterministicIntakeExtractor(expected)
    request = ExtractionRequest("submitted secret", "EN_US", "volta-intake-v1")

    assert await extractor.extract(request) is expected
    assert "submitted secret" not in repr(request)
    with pytest.raises(FrozenInstanceError):
        request.requested_language = "ES_MX"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_mapping_deterministic_extractor_receives_typed_request() -> None:
    expected = proposal()
    seen: list[ExtractionRequest] = []

    def mapping(request: ExtractionRequest) -> OperationProposal:
        seen.append(request)
        return expected

    extractor = DeterministicIntakeExtractor(mapping=mapping)
    request = ExtractionRequest("synthetic", "EN_US", "volta-intake-v1")

    assert await extractor.extract(request) == expected
    assert seen == [request]


def test_deterministic_extractor_requires_exactly_one_source() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        DeterministicIntakeExtractor()
    with pytest.raises(ValueError, match="exactly one"):
        DeterministicIntakeExtractor(proposal(), mapping=lambda _: proposal())


def test_provider_neutral_modules_have_no_transport_or_framework_imports() -> None:
    from pathlib import Path

    package = Path(__file__).parents[3] / "src/yuno_backend/volta/intake"
    source = "\n".join(path.read_text() for path in package.glob("*.py"))
    for forbidden in ("httpx", "fastapi", "pydantic", "sqlalchemy", "frontend", "api."):
        assert forbidden not in source.lower()
