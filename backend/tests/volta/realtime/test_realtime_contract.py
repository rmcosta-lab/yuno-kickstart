from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yuno_backend.volta.realtime as realtime
from yuno_backend.volta.realtime import (
    PcmAudioFormat,
    RealtimeError,
    RealtimeSessionRequest,
    RealtimeToolCallRequested,
    RealtimeToolDefinition,
    RealtimeToolOutput,
)


def _tool() -> RealtimeToolDefinition:
    return RealtimeToolDefinition(
        name="lookup_reference",
        description="Read one synthetic reference.",
        parameters={
            "type": "object",
            "properties": {"reference": {"type": "string"}},
            "required": ["reference"],
            "additionalProperties": False,
        },
    )


def test_public_surface_matches_frozen_phase_contract() -> None:
    assert set(realtime.__all__) == {
        "InvalidRealtimeEvent",
        "PcmAudioFormat",
        "RealtimeAudioDelta",
        "RealtimeAuthenticationError",
        "RealtimeConnection",
        "RealtimeConnectionError",
        "RealtimeDisconnectedError",
        "RealtimeError",
        "RealtimeEvent",
        "RealtimeGateway",
        "RealtimeModelUnavailableError",
        "RealtimeProviderError",
        "RealtimeRateLimitError",
        "RealtimeResponseCancelled",
        "RealtimeResponseCompleted",
        "RealtimeSessionReady",
        "RealtimeSessionRequest",
        "RealtimeSpeechStarted",
        "RealtimeSpeechStopped",
        "RealtimeTimeoutError",
        "RealtimeToolCallRequested",
        "RealtimeToolDefinition",
        "RealtimeToolOutput",
    }


def test_provider_neutral_package_has_no_transport_or_framework_imports() -> None:
    package_root = Path(__file__).parents[3] / "src" / "yuno_backend" / "volta" / "realtime"
    forbidden = {"websockets", "openai", "fastapi", "pydantic", "sqlalchemy", "twilio"}
    imported: list[str] = []
    for source_file in package_root.rglob("*.py"):
        tree = ast.parse(source_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
    assert not [name for name in imported if name.split(".")[0] in forbidden]


def test_sensitive_values_are_redacted_and_nested_json_is_immutable() -> None:
    secret_instruction = "private instruction marker"
    safety_identifier = "safe_operator_hash"
    request = RealtimeSessionRequest(
        instructions=secret_instruction,
        safety_identifier=safety_identifier,
        tools=(_tool(),),
    )
    output = RealtimeToolOutput(
        event_id="evt.output",
        response_event_id="evt.response",
        call_id="call.safe",
        result={"private": {"nested": ["tool-result-marker"]}},
    )
    call = RealtimeToolCallRequested(
        event_id="evt.call",
        item_id="item.call",
        call_id="call.safe",
        name="lookup_reference",
        arguments={"reference": "argument-marker"},
    )

    combined_repr = repr(request) + repr(output) + repr(call) + repr(_tool())
    for marker in (
        secret_instruction,
        safety_identifier,
        "tool-result-marker",
        "argument-marker",
    ):
        assert marker not in combined_repr
    with pytest.raises(TypeError):
        output.result["private"] = None  # type: ignore[index]


@pytest.mark.parametrize(
    ("factory", "match"),
    [
        (lambda: PcmAudioFormat(sample_rate_hz=16_000), "PCM16 mono"),
        (
            lambda: RealtimeSessionRequest(
                instructions="x", safety_identifier="unsafe value"
            ),
            "safety_identifier",
        ),
        (
            lambda: RealtimeSessionRequest(
                instructions="x", safety_identifier="safe", language="pt"  # type: ignore[arg-type]
            ),
            "English",
        ),
        (
            lambda: RealtimeToolOutput(
                event_id="evt",
                response_event_id="evt.response",
                call_id="call",
                result={"x": float("nan")},
            ),
            "JSON-compatible",
        ),
    ],
)
def test_values_reject_unsupported_or_unsafe_data(factory: object, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        factory()  # type: ignore[operator]


def test_exceptions_expose_only_allowlisted_safe_metadata() -> None:
    error = RealtimeError(
        model_id="gpt-realtime-2.1",
        event_type="error",
        event_id="unsafe secret payload",
        request_id="req.safe",
        status_code=503,
        close_code=1006,
        duration_ms=7,
    )
    assert str(error) == "realtime"
    assert error.event_id is None
    assert dict(error.safe_metadata) == {
        "category": "realtime",
        "model_id": "gpt-realtime-2.1",
        "event_type": "error",
        "event_id": None,
        "request_id": "req.safe",
        "status_code": 503,
        "close_code": 1006,
        "duration_ms": 7,
    }
