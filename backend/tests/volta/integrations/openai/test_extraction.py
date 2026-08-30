from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from copy import deepcopy
from datetime import date
from decimal import Decimal

import httpx
import pytest
from yuno_backend.integrations.openai.extraction import (
    DEFAULT_POLICY_INSTRUCTIONS,
    EXTRACTION_SCHEMA,
    MAX_RESPONSE_TEXT_BYTES,
    OpenAIExtractionConfig,
    OpenAIIntakeExtractor,
)
from yuno_backend.volta.intake import (
    ExtractionAuthenticationError,
    ExtractionModelUnavailableError,
    ExtractionProviderError,
    ExtractionRateLimitError,
    ExtractionRequest,
    ExtractionTimeoutError,
    InvalidExtractionResponse,
)

API_KEY = "sk-test-secret-must-never-leak"
SOURCE_PROMPT = "Private synthetic source prompt from Manzanillo with MXN 9000"
POLICY_VERSION = "volta-intake-v1"
REQUEST = ExtractionRequest(SOURCE_PROMPT, "EN_US", POLICY_VERSION)


def extraction_value() -> dict[str, object]:
    return {
        "origin": "Manzanillo",
        "destination": "Guadalajara",
        "cargo_label": "Synthetic 40ft dry container",
        "pickup_date": "2026-09-03",
        "pickup_window": {"start_date": "2026-09-03", "end_date": "2026-09-03"},
        "maximum_amount": {"amount": "9000.00", "currency": "MXN"},
        "allowed_conditions": ["sealed container"],
        "escalation_conditions": ["different pickup day", "higher total rate"],
    }


def completed_response(value: object | None = None) -> dict[str, object]:
    return {
        "id": "resp_safe_123",
        "status": "completed",
        "model": "gpt-5.6-luna-2026-08-01",
        "output": [
            {"type": "reasoning"},
            {
                "type": "message",
                "status": "completed",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(extraction_value() if value is None else value),
                    }
                ],
            },
        ],
    }


async def build_extractor(
    handler: Callable[[httpx.Request], httpx.Response | Awaitable[httpx.Response]],
    *,
    max_attempts: int = 3,
    delay: Callable[[float], Awaitable[None]] | None = None,
) -> tuple[OpenAIIntakeExtractor, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    config = OpenAIExtractionConfig(
        api_key=API_KEY,
        max_attempts=max_attempts,
        backoff_seconds=(0.1, 0.2, 0.3),
    )
    kwargs = {} if delay is None else {"delay": delay}
    return OpenAIIntakeExtractor(client, config, **kwargs), client


def test_configuration_repr_redacts_credentials_and_policy() -> None:
    config = OpenAIExtractionConfig(api_key=API_KEY)

    assert API_KEY not in repr(config)
    assert DEFAULT_POLICY_INSTRUCTIONS not in repr(config)


@pytest.mark.asyncio
async def test_maps_exact_responses_request_and_parses_domain_proposal() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=completed_response(), headers={"x-request-id": "req_123"})

    extractor, client = await build_extractor(handler)
    try:
        proposal = await extractor.extract(REQUEST)
        assert proposal.route.origin == "Manzanillo"
        assert proposal.route.destination == "Guadalajara"
        assert proposal.cargo_label == "Synthetic 40ft dry container"
        assert proposal.pickup_date == date(2026, 9, 3)
        assert proposal.mandate.maximum_amount.amount == Decimal("9000.00")
        assert proposal.mandate.maximum_amount.currency == "MXN"
        assert proposal.mandate.pickup_window.start_date == date(2026, 9, 3)
        assert proposal.mandate.allowed_conditions == ("sealed container",)
        assert proposal.mandate.escalation_conditions == (
            "different pickup day",
            "higher total rate",
        )

        request = captured[0]
        assert request.method == "POST"
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["authorization"] == f"Bearer {API_KEY}"
        assert request.extensions["timeout"] == {
            "connect": 30.0,
            "read": 30.0,
            "write": 30.0,
            "pool": 30.0,
        }
        body = json.loads(request.content)
        assert body == {
            "model": "gpt-5.6-luna",
            "instructions": DEFAULT_POLICY_INSTRUCTIONS,
            "input": SOURCE_PROMPT,
            "store": False,
            "metadata": {
                "integration": "volta_intake",
                "policy_version": POLICY_VERSION,
            },
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "volta_operation_proposal_v1",
                    "strict": True,
                    "schema": EXTRACTION_SCHEMA,
                }
            },
        }
        assert client.is_closed is False
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_reference_date_resolves_relative_dates_without_changing_source_input() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=completed_response())

    extractor, client = await build_extractor(handler)
    request = ExtractionRequest(
        SOURCE_PROMPT,
        "EN_US",
        POLICY_VERSION,
        reference_date=date(2026, 8, 30),
    )
    try:
        await extractor.extract(request)
        body = json.loads(captured[0].content)
        assert body["input"] == SOURCE_PROMPT
        assert body["instructions"] == (
            f"{DEFAULT_POLICY_INSTRUCTIONS}\nReference date (UTC): 2026-08-30."
        )
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_single_pickup_date_becomes_a_one_day_window() -> None:
    value = extraction_value()
    value["pickup_window"] = {"start_date": None, "end_date": None}
    extractor, client = await build_extractor(
        lambda _: httpx.Response(200, json=completed_response(value))
    )
    try:
        proposal = await extractor.extract(REQUEST)
        assert proposal.mandate.pickup_window.start_date == proposal.pickup_date
        assert proposal.mandate.pickup_window.end_date == proposal.pickup_date
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.pop("origin"),
        lambda value: value.update(extra="unexpected"),
        lambda value: value.update(origin=None),
        lambda value: value.update(pickup_date="09/03/2026"),
        lambda value: value["maximum_amount"].update(amount=9000),
        lambda value: value["maximum_amount"].update(amount="NaN"),
        lambda value: value["maximum_amount"].update(currency="mxn"),
        lambda value: value.update(allowed_conditions="sealed"),
    ],
)
@pytest.mark.asyncio
async def test_rejects_missing_extra_incorrectly_typed_and_malformed_output(
    mutate: Callable[[dict[str, object]], object],
) -> None:
    value = deepcopy(extraction_value())
    mutate(value)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=completed_response(value))

    extractor, client = await build_extractor(handler)
    try:
        with pytest.raises(InvalidExtractionResponse) as captured:
            await extractor.extract(REQUEST)
        assert captured.value.attempt_count == 1
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(origin="x" * 501),
        lambda value: value["maximum_amount"].update(amount="1" * 65),
        lambda value: value.update(allowed_conditions=["x" * 501]),
        lambda value: value.update(escalation_conditions=["safe"] * 26),
    ],
)
@pytest.mark.asyncio
async def test_rejects_oversized_extracted_fields(
    mutate: Callable[[dict[str, object]], object],
) -> None:
    value = deepcopy(extraction_value())
    mutate(value)
    extractor, client = await build_extractor(
        lambda _: httpx.Response(200, json=completed_response(value))
    )
    try:
        with pytest.raises(InvalidExtractionResponse):
            await extractor.extract(REQUEST)
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_rejects_oversized_response_text_before_json_parsing() -> None:
    payload = completed_response()
    message = payload["output"][1]
    message["content"][0]["text"] = "x" * (MAX_RESPONSE_TEXT_BYTES + 1)
    extractor, client = await build_extractor(lambda _: httpx.Response(200, json=payload))
    try:
        with pytest.raises(InvalidExtractionResponse):
            await extractor.extract(REQUEST)
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}},
        {"status": "failed", "error": {"message": SOURCE_PROMPT}},
        {"status": "completed", "output": []},
        {"status": "completed", "output": [{"type": "function_call", "name": "unsafe"}]},
        {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}],
        },
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "{}"},
                        {"type": "output_text", "text": "{}"},
                    ],
                }
            ],
        },
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "{}"}],
                },
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "{}"}],
                },
            ],
        },
    ],
)
@pytest.mark.asyncio
async def test_rejects_incomplete_refused_and_ambiguous_response_shapes(
    payload: dict[str, object],
) -> None:
    extractor, client = await build_extractor(lambda _: httpx.Response(200, json=payload))
    try:
        with pytest.raises(InvalidExtractionResponse):
            await extractor.extract(REQUEST)
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    ("status", "body", "error_type"),
    [
        (401, {"error": {"message": SOURCE_PROMPT}}, ExtractionAuthenticationError),
        (403, {"error": {"message": SOURCE_PROMPT}}, ExtractionAuthenticationError),
        (400, {"error": {"code": "model_not_found"}}, ExtractionModelUnavailableError),
        (404, {"error": {"message": SOURCE_PROMPT}}, ExtractionModelUnavailableError),
        (400, {"error": {"message": SOURCE_PROMPT}}, ExtractionProviderError),
    ],
)
@pytest.mark.asyncio
async def test_non_retryable_http_failures_execute_once(
    status: int,
    body: dict[str, object],
    error_type: type[Exception],
) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, json=body, headers={"x-request-id": "req_safe_123"})

    extractor, client = await build_extractor(handler)
    try:
        with pytest.raises(error_type):
            await extractor.extract(REQUEST)
        assert calls == 1
    finally:
        await client.aclose()


@pytest.mark.parametrize("status", [429, 500, 503])
@pytest.mark.asyncio
async def test_retryable_http_failures_are_sequential_and_bounded(status: int) -> None:
    calls = 0
    active = 0
    max_active = 0
    delays: list[float] = []

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal active, calls, max_active
        calls += 1
        active += 1
        max_active = max(max_active, active)
        active -= 1
        return httpx.Response(status, json={"error": {"message": SOURCE_PROMPT}})

    async def delay(value: float) -> None:
        delays.append(value)

    extractor, client = await build_extractor(handler, delay=delay)
    expected = ExtractionRateLimitError if status == 429 else ExtractionProviderError
    try:
        with pytest.raises(expected) as captured:
            await extractor.extract(REQUEST)
        assert calls == 3
        assert max_active == 1
        assert delays == [0.1, 0.2]
        assert captured.value.attempt_count == 3
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    ("transport_error", "error_type"),
    [
        (httpx.ReadTimeout("sensitive timeout"), ExtractionTimeoutError),
        (httpx.ConnectError("sensitive network"), ExtractionProviderError),
    ],
)
@pytest.mark.asyncio
async def test_transport_failures_retry_to_limit_without_leaking_messages(
    transport_error: httpx.TransportError,
    error_type: type[Exception],
) -> None:
    calls = 0
    delays: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise transport_error

    async def delay(value: float) -> None:
        delays.append(value)

    extractor, client = await build_extractor(handler, delay=delay)
    try:
        with pytest.raises(error_type) as captured:
            await extractor.extract(REQUEST)
        assert calls == 3
        assert delays == [0.1, 0.2]
        assert "sensitive" not in str(captured.value)
        assert "sensitive" not in repr(captured.value)
        assert captured.value.__cause__ is None
        assert captured.value.__context__ is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_errors_metadata_and_logs_are_redacted(caplog: pytest.LogCaptureFixture) -> None:
    extracted_value = "Manzanillo"
    provider_policy_echo = DEFAULT_POLICY_INSTRUCTIONS

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={
                "error": {
                    "message": f"{API_KEY} {SOURCE_PROMPT} {provider_policy_echo} {extracted_value}"
                }
            },
            headers={
                "x-request-id": f"unsafe {API_KEY}",
                "authorization": f"Bearer {API_KEY}",
            },
        )

    extractor, client = await build_extractor(handler)
    try:
        with pytest.raises(ExtractionAuthenticationError) as captured:
            await extractor.extract(REQUEST)
        diagnostic = " ".join(
            [str(captured.value), repr(captured.value), repr(dict(captured.value.safe_metadata))]
        )
        logs = caplog.text
        for forbidden in (
            API_KEY,
            f"Bearer {API_KEY}",
            SOURCE_PROMPT,
            provider_policy_echo,
            extracted_value,
        ):
            assert forbidden not in diagnostic
            assert forbidden not in logs
        assert captured.value.request_id is None
        assert captured.value.safe_metadata["category"] == "authentication"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_invalid_response_sanitizes_provider_model_metadata() -> None:
    payload = completed_response({})
    payload["model"] = f"unsafe model {API_KEY}"
    extractor, client = await build_extractor(lambda _: httpx.Response(200, json=payload))
    try:
        with pytest.raises(InvalidExtractionResponse) as captured:
            await extractor.extract(REQUEST)
        assert captured.value.model_id is None
        assert API_KEY not in repr(dict(captured.value.safe_metadata))
        assert captured.value.__cause__ is None
        assert captured.value.__context__ is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_policy_version_mismatch_does_not_call_provider() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=completed_response())

    extractor, client = await build_extractor(handler)
    try:
        with pytest.raises(ExtractionProviderError):
            await extractor.extract(ExtractionRequest("synthetic", "EN_US", "wrong-policy"))
        assert calls == 0
    finally:
        await client.aclose()
