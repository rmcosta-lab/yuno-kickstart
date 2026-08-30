from __future__ import annotations

import ast
import json
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from yuno_backend.integrations.openai import (
    OpenAIRealtimeClientSecretConfig,
    OpenAIRealtimeClientSecretIssuer,
)
from yuno_backend.volta.realtime import (
    InvalidRealtimeResponseError,
    RealtimeAuthenticationError,
    RealtimeClientSecretRequest,
    RealtimeConnectionError,
    RealtimeModelUnavailableError,
    RealtimeProviderError,
    RealtimeRateLimitError,
    RealtimeSessionRequest,
    RealtimeTimeoutError,
    RealtimeToolDefinition,
)

API_KEY = "sk-standard-private-marker"
EPHEMERAL_SECRET = "ek_ephemeral_private_marker"
SAFETY_IDENTIFIER = "a" * 64
NOW = 2_000_000_000.0


def _request() -> RealtimeClientSecretRequest:
    return RealtimeClientSecretRequest(
        session=RealtimeSessionRequest(
            instructions="private instruction marker",
            safety_identifier=SAFETY_IDENTIFIER,
            tools=(
                RealtimeToolDefinition(
                    name="lookup_reference",
                    description="Read one synthetic reference.",
                    parameters={
                        "type": "object",
                        "properties": {"reference": {"type": "string"}},
                        "required": ["reference"],
                        "additionalProperties": False,
                    },
                ),
            ),
        )
    )


def _response(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "value": EPHEMERAL_SECRET,
        "expires_at": int(NOW) + 60,
        "session": {
            "id": "sess_safe",
            "object": "realtime.session",
            "type": "realtime",
            "model": "gpt-realtime-2.1",
        },
    }
    payload.update(overrides)
    return payload


def _issuer(
    handler: Callable[[httpx.Request], httpx.Response],
    **config: object,
) -> tuple[OpenAIRealtimeClientSecretIssuer, httpx.AsyncClient]:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    issuer = OpenAIRealtimeClientSecretIssuer(
        client,
        OpenAIRealtimeClientSecretConfig(api_key=API_KEY, **config),  # type: ignore[arg-type]
        clock=lambda: NOW,
    )
    return issuer, client


def test_config_is_immutable_redacted_and_rejects_non_official_urls() -> None:
    config = OpenAIRealtimeClientSecretConfig(api_key=API_KEY)
    assert API_KEY not in repr(config)
    with pytest.raises(ValueError, match="official HTTPS"):
        OpenAIRealtimeClientSecretConfig(
            api_key=API_KEY,
            url="https://example.invalid/v1/realtime/client_secrets",
        )


def test_openai_adapter_does_not_import_api_or_frontend_modules() -> None:
    source = (
        Path(__file__).parents[4]
        / "src"
        / "yuno_backend"
        / "integrations"
        / "openai"
        / "client_secrets.py"
    )
    imported: list[str] = []
    for node in ast.walk(ast.parse(source.read_text())):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not [name for name in imported if name.split(".")[0] in {"api", "frontend"}]


@pytest.mark.asyncio
async def test_posts_exact_narrow_session_and_keeps_client_caller_owned() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=_response())

    issuer, client = _issuer(handler)
    try:
        result = await issuer.issue(_request())

        assert result.value == EPHEMERAL_SECRET
        assert result.expires_at == int(NOW) + 60
        assert result.session_id == "sess_safe"
        assert result.model_id == "gpt-realtime-2.1"
        assert EPHEMERAL_SECRET not in repr(result)
        request = captured[0]
        assert request.method == "POST"
        assert str(request.url) == "https://api.openai.com/v1/realtime/client_secrets"
        assert request.headers["authorization"] == f"Bearer {API_KEY}"
        assert request.headers["openai-safety-identifier"] == SAFETY_IDENTIFIER
        assert request.extensions["timeout"] == {
            "connect": 10.0,
            "read": 10.0,
            "write": 10.0,
            "pool": 10.0,
        }
        assert json.loads(request.content) == {
            "session": {
                "type": "realtime",
                "model": "gpt-realtime-2.1",
                "instructions": (
                    "private instruction marker\n\nLanguage requirement: respond only in English."
                ),
                "output_modalities": ["audio"],
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "turn_detection": {
                            "type": "server_vad",
                            "create_response": True,
                            "interrupt_response": True,
                        },
                    },
                    "output": {
                        "format": {"type": "audio/pcm", "rate": 24000},
                        "voice": "marin",
                    },
                },
                "tools": [
                    {
                        "type": "function",
                        "name": "lookup_reference",
                        "description": "Read one synthetic reference.",
                        "parameters": {
                            "type": "object",
                            "properties": {"reference": {"type": "string"}},
                            "required": ["reference"],
                            "additionalProperties": False,
                        },
                    }
                ],
                "tool_choice": "auto",
            }
        }
        assert client.is_closed is False
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, RealtimeAuthenticationError),
        (403, RealtimeAuthenticationError),
        (404, RealtimeModelUnavailableError),
        (429, RealtimeRateLimitError),
        (500, RealtimeProviderError),
    ],
)
@pytest.mark.asyncio
async def test_translates_provider_status_without_response_details(
    status: int, error_type: type[Exception]
) -> None:
    issuer, client = _issuer(
        lambda _: httpx.Response(
            status,
            json={"error": {"message": EPHEMERAL_SECRET, "api_key": API_KEY}},
        )
    )
    try:
        with pytest.raises(error_type) as caught:
            await issuer.issue(_request())
        rendered = repr(caught.value) + str(caught.value)
        assert EPHEMERAL_SECRET not in rendered
        assert API_KEY not in rendered
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_maps_provider_model_code_without_exposing_error_body() -> None:
    issuer, client = _issuer(
        lambda _: httpx.Response(
            400,
            json={
                "error": {
                    "code": "model_not_found",
                    "message": EPHEMERAL_SECRET,
                }
            },
        )
    )
    try:
        with pytest.raises(RealtimeModelUnavailableError) as caught:
            await issuer.issue(_request())
        assert EPHEMERAL_SECRET not in (repr(caught.value) + str(caught.value))
    finally:
        await client.aclose()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        _response(value=""),
        _response(value="x" * 4_097),
        _response(expires_at=int(NOW)),
        _response(expires_at=int(NOW) + 601),
        _response(session={"id": "sess_safe", "type": "transcription"}),
        _response(
            session={
                "id": "sess_safe",
                "object": "realtime.session",
                "type": "realtime",
                "model": "wrong-model",
            }
        ),
        _response(
            session={
                "id": "unsafe session value",
                "object": "realtime.session",
                "type": "realtime",
                "model": "gpt-realtime-2.1",
            }
        ),
    ],
)
@pytest.mark.asyncio
async def test_rejects_adversarial_responses_without_leaking_payload(
    payload: dict[str, object], caplog: pytest.LogCaptureFixture
) -> None:
    issuer, client = _issuer(lambda _: httpx.Response(200, json=payload))
    try:
        with pytest.raises(InvalidRealtimeResponseError) as caught:
            await issuer.issue(_request())
        rendered = repr(caught.value) + str(caught.value) + caplog.text
        assert EPHEMERAL_SECRET not in rendered
        assert API_KEY not in rendered
        assert "private instruction marker" not in rendered
        assert SAFETY_IDENTIFIER not in rendered
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_translates_timeout_and_transport_failures() -> None:
    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("private timeout detail")

    issuer, client = _issuer(timeout)
    try:
        with pytest.raises(RealtimeTimeoutError):
            await issuer.issue(_request())
    finally:
        await client.aclose()

    def transport(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private transport detail", request=request)

    issuer, client = _issuer(transport)
    try:
        with pytest.raises(RealtimeConnectionError):
            await issuer.issue(_request())
    finally:
        await client.aclose()
