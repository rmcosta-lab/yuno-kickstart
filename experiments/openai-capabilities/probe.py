"""Redacted Responses API and model-access probes for Phase 02."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Never

API_BASE = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 45.0

SYNTHETIC_INTAKE = (
    "Fully synthetic request SYN-2042. A container move is needed from Demo North Port to "
    "Fictional South Yard. Pickup is between 2026-09-02T13:00:00Z and "
    "2026-09-02T15:00:00Z. Target rate: 875 USD. No carrier or phone number was provided."
)

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reference": {"type": "string"},
        "origin": {"type": "string"},
        "destination": {"type": "string"},
        "pickup_window_start": {"type": "string"},
        "pickup_window_end": {"type": "string"},
        "target_rate": {"type": "number"},
        "currency": {"type": "string"},
        "carrier_name": {"type": ["string", "null"]},
        "phone": {"type": ["string", "null"]},
    },
    "required": [
        "reference",
        "origin",
        "destination",
        "pickup_window_start",
        "pickup_window_end",
        "target_rate",
        "currency",
        "carrier_name",
        "phone",
    ],
    "additionalProperties": False,
}

EXPECTED_EXTRACTION: dict[str, Any] = {
    "reference": "SYN-2042",
    "origin": "Demo North Port",
    "destination": "Fictional South Yard",
    "pickup_window_start": "2026-09-02T13:00:00Z",
    "pickup_window_end": "2026-09-02T15:00:00Z",
    "target_rate": 875,
    "currency": "USD",
    "carrier_name": None,
    "phone": None,
}

SAFE_RATE_LIMIT_HEADERS = (
    "x-ratelimit-limit-requests",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-reset-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-tokens",
)


@dataclass(frozen=True)
class SafeHttpMetadata:
    status: int
    request_id: str | None
    rate_limits: dict[str, str]


class ProbeFailure(Exception):
    """A provider failure containing only pre-redacted fields."""

    def __init__(
        self,
        category: str,
        *,
        status: int | None = None,
        request_id: str | None = None,
        provider_code: str | None = None,
    ) -> None:
        super().__init__(category)
        self.category = category
        self.status = status
        self.request_id = request_id
        self.provider_code = provider_code

    def safe_result(self) -> dict[str, Any]:
        return {
            "status": "failed",
            "failure_category": self.category,
            "http_status": self.status,
            "request_id": self.request_id,
            "provider_code": self.provider_code,
        }


def _require_api_key() -> str:
    value = os.environ.get("OPENAI_API_KEY")
    if not value:
        raise ProbeFailure("authentication")
    return value


def _safe_headers(headers: Any) -> SafeHttpMetadata:
    status = int(getattr(headers, "status", 200))
    rate_limits = {
        name: value
        for name in SAFE_RATE_LIMIT_HEADERS
        if (value := headers.headers.get(name)) is not None
    }
    return SafeHttpMetadata(
        status=status,
        request_id=headers.headers.get("x-request-id"),
        rate_limits=rate_limits,
    )


def _error_code(raw: bytes) -> str | None:
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return None
    code = error.get("code") or error.get("type")
    return code if isinstance(code, str) and len(code) <= 80 else None


def _raise_http_failure(error: urllib.error.HTTPError) -> Never:
    status = error.code
    provider_code = _error_code(error.read())
    category = "provider"
    if status in (401, 403):
        category = "authentication"
    elif status == 404 or provider_code in {"model_not_found", "model_not_available"}:
        category = "model_unavailable"
    elif status == 429:
        category = "rate_limit"
    raise ProbeFailure(
        category,
        status=status,
        request_id=error.headers.get("x-request-id"),
        provider_code=provider_code,
    )


def request_json(
    method: str,
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[dict[str, Any], SafeHttpMetadata]:
    body = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {_require_api_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            metadata = _safe_headers(response)
            raw = response.read()
    except urllib.error.HTTPError as error:
        _raise_http_failure(error)
    except TimeoutError as error:
        raise ProbeFailure("timeout") from error
    except urllib.error.URLError as error:
        reason = error.reason
        category = "timeout" if isinstance(reason, TimeoutError) else "network"
        raise ProbeFailure(category) from error
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProbeFailure("invalid_response", status=metadata.status) from error
    if not isinstance(parsed, dict):
        raise ProbeFailure("invalid_response", status=metadata.status)
    return parsed, metadata


def extract_output_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    return text
    raise ProbeFailure("invalid_response")


def validate_extraction(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["output_not_object"]
    errors: list[str] = []
    expected_keys = set(EXPECTED_EXTRACTION)
    actual_keys = set(value)
    if missing := sorted(expected_keys - actual_keys):
        errors.append(f"missing_fields:{','.join(missing)}")
    if extra := sorted(actual_keys - expected_keys):
        errors.append(f"extra_fields:{','.join(extra)}")
    for key, expected in EXPECTED_EXTRACTION.items():
        if key in value and value[key] != expected:
            errors.append(f"unexpected_value:{key}")
    return errors


def probe_models(candidates: list[str], timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    response, metadata = request_json("GET", "/models", timeout=timeout)
    visible = {
        item.get("id")
        for item in response.get("data", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    return {
        "status": "passed",
        "probe": "model_catalog",
        "latency_ms": round((time.monotonic() - started) * 1000),
        "candidates": {candidate: candidate in visible for candidate in candidates},
        **asdict(metadata),
    }


def probe_extraction(model: str, timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    response, metadata = request_json(
        "POST",
        "/responses",
        timeout=timeout,
        payload={
            "model": model,
            "store": False,
            "input": [
                {
                    "role": "developer",
                    "content": "Extract only explicit facts. Use null for missing information.",
                },
                {"role": "user", "content": SYNTHETIC_INTAKE},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "synthetic_drayage_intake",
                    "strict": True,
                    "schema": EXTRACTION_SCHEMA,
                }
            },
        },
    )
    try:
        parsed = json.loads(extract_output_text(response))
    except json.JSONDecodeError as error:
        raise ProbeFailure(
            "invalid_response", status=metadata.status, request_id=metadata.request_id
        ) from error
    validation_errors = validate_extraction(parsed)
    if validation_errors:
        raise ProbeFailure(
            "invalid_response", status=metadata.status, request_id=metadata.request_id
        )
    return {
        "status": "passed",
        "probe": "structured_extraction",
        "model": response.get("model", model),
        "latency_ms": round((time.monotonic() - started) * 1000),
        "output": parsed,
        **asdict(metadata),
    }


def emit(result: dict[str, Any], destination: Path | None) -> None:
    serialized = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    models = subparsers.add_parser("models")
    models.add_argument("--candidate", action="append", required=True)
    extraction = subparsers.add_parser("extraction")
    extraction.add_argument("--model", required=True)
    for command in (models, extraction):
        command.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
        command.add_argument("--result", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "models":
            result = probe_models(args.candidate, args.timeout)
        else:
            result = probe_extraction(args.model, args.timeout)
    except ProbeFailure as error:
        emit(error.safe_result(), args.result)
        return 1
    emit(result, args.result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
