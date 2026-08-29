from __future__ import annotations

import os

import httpx
import pytest
from yuno_backend.integrations.openai import OpenAIExtractionConfig, OpenAIIntakeExtractor
from yuno_backend.volta.intake import ExtractionRequest

pytestmark = pytest.mark.openai_credentialed


@pytest.mark.asyncio
async def test_synthetic_structured_extraction_with_explicit_credentials() -> None:
    if os.environ.get("RUN_OPENAI_CREDENTIALED") != "1":
        pytest.skip("set RUN_OPENAI_CREDENTIALED=1 to authorize the synthetic provider test")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY is not available")

    request = ExtractionRequest(
        source_prompt=(
            "Synthetic demo only: move a sealed container from Demo Manzanillo Port to Demo "
            "Guadalajara Yard on 2026-09-03 for at most MXN 9000. The pickup window starts "
            "on 2026-09-03 and ends on 2026-09-03. Allowed conditions are exactly these "
            "strings: 'sealed container' and 'daylight pickup'. Escalation conditions are "
            "exactly these strings: 'different pickup day', 'higher total rate', and "
            "'conflicting condition'."
        ),
        requested_language="EN_US",
        extraction_policy_version="volta-intake-v1",
    )
    async with httpx.AsyncClient() as client:
        extractor = OpenAIIntakeExtractor(client, OpenAIExtractionConfig(api_key=api_key))
        proposal = await extractor.extract(request)

    assert proposal.route.origin == "Demo Manzanillo Port"
    assert proposal.route.destination == "Demo Guadalajara Yard"
    assert proposal.pickup_date.isoformat() == "2026-09-03"
    assert proposal.mandate.pickup_window.start_date.isoformat() == "2026-09-03"
    assert proposal.mandate.pickup_window.end_date.isoformat() == "2026-09-03"
    assert str(proposal.mandate.maximum_amount.amount) == "9000"
    assert proposal.mandate.maximum_amount.currency == "MXN"
    assert proposal.mandate.allowed_conditions == ("sealed container", "daylight pickup")
    assert proposal.mandate.escalation_conditions == (
        "different pickup day",
        "higher total rate",
        "conflicting condition",
    )
