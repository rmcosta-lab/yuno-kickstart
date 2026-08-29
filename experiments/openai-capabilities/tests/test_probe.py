from __future__ import annotations

import importlib.util
import io
import json
import sys
import urllib.error
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[1]


def load_module(filename: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


probe = load_module("probe.py", "phase02_probe")
realtime = load_module("realtime_ws.py", "phase02_realtime")
browser_server = load_module("browser_server.py", "phase02_browser_server")
synthesis = load_module("synthesize_audio.py", "phase02_synthesis")


def test_canonical_extraction_passes_independent_validation() -> None:
    assert probe.validate_extraction(probe.EXPECTED_EXTRACTION.copy()) == []


def test_extraction_rejects_missing_extra_and_invented_values() -> None:
    value = probe.EXPECTED_EXTRACTION.copy()
    del value["phone"]
    value["carrier_name"] = "Invented Carrier"
    value["unexpected"] = True

    assert probe.validate_extraction(value) == [
        "missing_fields:phone",
        "extra_fields:unexpected",
        "unexpected_value:carrier_name",
    ]


def test_output_text_is_found_without_assuming_first_output_item() -> None:
    payload = {
        "output": [
            {"type": "reasoning"},
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps({"ok": True})}],
            },
        ]
    }
    assert probe.extract_output_text(payload) == '{"ok": true}'


def test_tool_call_requires_exact_synthetic_contract_and_preserves_call_id() -> None:
    call_id, arguments = realtime.validate_tool_call(
        {
            "name": realtime.TOOL_NAME,
            "call_id": "call_safe_123",
            "arguments": json.dumps({"reference": realtime.TOOL_REFERENCE}),
        }
    )
    assert call_id == "call_safe_123"
    assert arguments == {"reference": "SYN-2042"}


def test_safe_event_drops_payload_and_provider_message() -> None:
    retained = realtime.safe_event(
        {
            "type": "error",
            "event_id": "event_safe_123",
            "error": {"code": "invalid_value", "message": "sensitive echo"},
            "secret": "must-not-survive",
        },
        42,
    )
    assert retained == {
        "type": "error",
        "elapsed_ms": 42,
        "event_id": "event_safe_123",
        "error_code": "invalid_value",
    }


@pytest.mark.parametrize(
    ("status", "provider_code", "category"),
    [
        (401, "invalid_api_key", "authentication"),
        (400, "model_not_found", "model_unavailable"),
        (429, "rate_limit_exceeded", "rate_limit"),
        (500, "server_error", "provider"),
    ],
)
def test_http_failures_have_stable_redacted_categories(
    status: int, provider_code: str, category: str
) -> None:
    body = json.dumps({"error": {"code": provider_code, "message": "sensitive echo"}}).encode()
    error = urllib.error.HTTPError(
        "https://api.openai.com/v1/responses",
        status,
        "provider text must not survive",
        {"x-request-id": "req_safe_123"},
        io.BytesIO(body),
    )

    with pytest.raises(probe.ProbeFailure) as captured:
        probe._raise_http_failure(error)

    assert captured.value.safe_result() == {
        "status": "failed",
        "failure_category": category,
        "http_status": status,
        "request_id": "req_safe_123",
        "provider_code": provider_code,
    }


def test_timeout_is_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-secret")

    def timeout(*args: object, **kwargs: object) -> None:
        raise TimeoutError

    monkeypatch.setattr(probe.urllib.request, "urlopen", timeout)
    with pytest.raises(probe.ProbeFailure) as captured:
        probe.request_json("GET", "/models")
    assert captured.value.category == "timeout"


def test_unexpected_realtime_exception_does_not_expose_message() -> None:
    error = RuntimeError("provider response containing sensitive echo")
    assert realtime.safe_failure_category(error) == "provider_or_network"


def test_browser_session_requires_english_cedar_and_natural_pacing() -> None:
    session = browser_server.session_config("gpt-realtime-2.1")["session"]
    assert session["audio"]["output"]["voice"] == "cedar"
    assert "Always respond only in English" in session["instructions"]
    assert "calm, measured, conversational pace" in session["instructions"]


def test_synthetic_audio_output_must_stay_private(tmp_path: Path) -> None:
    with pytest.raises(probe.argparse.ArgumentTypeError):
        synthesis.private_output_path(str(tmp_path / "audio.wav"))
