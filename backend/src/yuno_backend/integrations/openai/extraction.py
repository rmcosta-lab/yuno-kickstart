"""OpenAI Responses adapter for strict, provider-neutral intake extraction."""

from __future__ import annotations

import asyncio
import json
import re
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from yuno_backend.volta.intake import ExtractionRequest
from yuno_backend.volta.intake.errors import (
    ExtractionAuthenticationError,
    ExtractionError,
    ExtractionModelUnavailableError,
    ExtractionProviderError,
    ExtractionRateLimitError,
    ExtractionTimeoutError,
    InvalidExtractionResponse,
)
from yuno_backend.volta.mandates import (
    MandateProposal,
    Money,
    OperationProposal,
    PickupWindow,
    Route,
)
from yuno_backend.volta.mandates.errors import InvalidDomainValue

__all__ = ["OpenAIExtractionConfig", "OpenAIIntakeExtractor"]

DEFAULT_POLICY_VERSION = "volta-intake-v1"
DEFAULT_POLICY_INSTRUCTIONS = """You extract a proposed drayage operation from coordinator text.
Extract only facts explicitly present in the source request. Represent an absent scalar fact as null
and an absent condition list as an empty list. Never invent a place, date, price, currency, or
condition. Never approve an operation, grant authority, select a carrier, or claim that the proposal
is eligible. Return only the JSON object required by the supplied schema."""
MAX_RESPONSE_TEXT_BYTES = 32_768
MAX_DECIMAL_TEXT_LENGTH = 64
_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

_NULLABLE_STRING: dict[str, Any] = {"type": ["string", "null"], "maxLength": 500}
EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "origin": _NULLABLE_STRING,
        "destination": _NULLABLE_STRING,
        "pickup_date": {
            "type": ["string", "null"],
            "pattern": r"^\d{4}-\d{2}-\d{2}$",
        },
        "pickup_window": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": ["string", "null"],
                    "pattern": r"^\d{4}-\d{2}-\d{2}$",
                },
                "end_date": {
                    "type": ["string", "null"],
                    "pattern": r"^\d{4}-\d{2}-\d{2}$",
                },
            },
            "required": ["start_date", "end_date"],
            "additionalProperties": False,
        },
        "maximum_amount": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": ["string", "null"],
                    "pattern": r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$",
                    "maxLength": MAX_DECIMAL_TEXT_LENGTH,
                },
                "currency": {
                    "type": ["string", "null"],
                    "pattern": "^[A-Z]{3}$",
                },
            },
            "required": ["amount", "currency"],
            "additionalProperties": False,
        },
        "allowed_conditions": {
            "type": "array",
            "items": {"type": "string", "maxLength": 500},
            "maxItems": 25,
        },
        "escalation_conditions": {
            "type": "array",
            "items": {"type": "string", "maxLength": 500},
            "maxItems": 25,
        },
    },
    "required": [
        "origin",
        "destination",
        "pickup_date",
        "pickup_window",
        "maximum_amount",
        "allowed_conditions",
        "escalation_conditions",
    ],
    "additionalProperties": False,
}


async def _default_delay(seconds: float) -> None:
    await asyncio.sleep(seconds)


@dataclass(frozen=True, slots=True)
class OpenAIExtractionConfig:
    api_key: str = field(repr=False)
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-5.6-luna"
    timeout_seconds: float = 30.0
    max_attempts: int = 3
    backoff_seconds: tuple[float, ...] = (0.25, 1.0)
    policy_version: str = DEFAULT_POLICY_VERSION
    policy_instructions: str = field(default=DEFAULT_POLICY_INSTRUCTIONS, repr=False)

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        if not self.base_url.startswith("https://"):
            raise ValueError("OpenAI base URL must use HTTPS")
        if not self.model or not self.policy_version or not self.policy_instructions:
            raise ValueError("model and extraction policy are required")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout must be positive")
        if self.max_attempts < 1:
            raise ValueError("max attempts must be positive")
        if len(self.backoff_seconds) < self.max_attempts - 1:
            raise ValueError("one backoff value is required between attempts")
        if any(value < 0 for value in self.backoff_seconds):
            raise ValueError("backoff values must be non-negative")


class OpenAIIntakeExtractor:
    def __init__(
        self,
        client: httpx.AsyncClient,
        config: OpenAIExtractionConfig,
        *,
        delay: Callable[[float], Awaitable[None]] = _default_delay,
    ) -> None:
        self._client = client
        self._config = config
        self._delay = delay

    async def extract(self, request: ExtractionRequest) -> OperationProposal:
        started = time.monotonic()
        if request.extraction_policy_version != self._config.policy_version:
            raise ExtractionProviderError(
                model_id=self._config.model,
                duration_ms=self._duration_ms(started),
            )

        payload = self._request_payload(request)
        terminal_failure: ExtractionError | None = None
        for attempt in range(1, self._config.max_attempts + 1):
            try:
                response = await self._client.post(
                    f"{self._config.base_url.rstrip('/')}/responses",
                    headers={
                        "Authorization": f"Bearer {self._config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=httpx.Timeout(self._config.timeout_seconds),
                )
                if response.is_error:
                    failure = self._http_failure(response, attempt, started)
                    if self._is_retryable(failure) and attempt < self._config.max_attempts:
                        await self._delay(self._config.backoff_seconds[attempt - 1])
                        continue
                    raise failure
                return self._parse_response(response, attempt, started)
            except httpx.TimeoutException:
                failure = ExtractionTimeoutError(
                    model_id=self._config.model,
                    attempt_count=attempt,
                    duration_ms=self._duration_ms(started),
                )
                if attempt < self._config.max_attempts:
                    await self._delay(self._config.backoff_seconds[attempt - 1])
                    continue
                terminal_failure = failure
                break
            except httpx.TransportError:
                failure = ExtractionProviderError(
                    model_id=self._config.model,
                    attempt_count=attempt,
                    duration_ms=self._duration_ms(started),
                )
                if attempt < self._config.max_attempts:
                    await self._delay(self._config.backoff_seconds[attempt - 1])
                    continue
                terminal_failure = failure
                break
        if terminal_failure is not None:
            raise terminal_failure
        raise AssertionError("bounded extraction loop did not terminate")

    def _request_payload(self, request: ExtractionRequest) -> dict[str, Any]:
        return {
            "model": self._config.model,
            "instructions": self._config.policy_instructions,
            "input": request.source_prompt,
            "store": False,
            "metadata": {
                "integration": "volta_intake",
                "policy_version": self._config.policy_version,
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

    def _http_failure(
        self, response: httpx.Response, attempt: int, started: float
    ) -> ExtractionError:
        status = response.status_code
        request_id = response.headers.get("x-request-id")
        error_code = _provider_error_code(response)
        error_type: type[ExtractionError] = ExtractionProviderError
        if status in {401, 403}:
            error_type = ExtractionAuthenticationError
        elif status == 404 or error_code in {"model_not_found", "model_not_available"}:
            error_type = ExtractionModelUnavailableError
        elif status == 429:
            error_type = ExtractionRateLimitError
        return error_type(
            status_code=status,
            request_id=request_id,
            model_id=self._config.model,
            attempt_count=attempt,
            duration_ms=self._duration_ms(started),
        )

    @staticmethod
    def _is_retryable(error: ExtractionError) -> bool:
        return isinstance(error, ExtractionRateLimitError) or (
            isinstance(error, ExtractionProviderError)
            and error.status_code is not None
            and error.status_code >= 500
        )

    def _parse_response(
        self, response: httpx.Response, attempt: int, started: float
    ) -> OperationProposal:
        request_id = response.headers.get("x-request-id")
        try:
            payload = response.json()
            if (
                not isinstance(payload, dict)
                or payload.get("status") != "completed"
                or payload.get("error") is not None
                or payload.get("incomplete_details") is not None
            ):
                raise ValueError
            text = _extract_output_text(payload)
            if len(text.encode("utf-8")) > MAX_RESPONSE_TEXT_BYTES:
                raise ValueError
            value = json.loads(text)
            return _operation_proposal(value)
        except (InvalidDomainValue, InvalidOperation, UnicodeError, ValueError):
            failure = InvalidExtractionResponse(
                status_code=response.status_code,
                request_id=request_id,
                model_id=_safe_model(payload if "payload" in locals() else None),
                attempt_count=attempt,
                duration_ms=self._duration_ms(started),
            )
        raise failure

    @staticmethod
    def _duration_ms(started: float) -> int:
        return round((time.monotonic() - started) * 1000)


def _provider_error_code(response: httpx.Response) -> str | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("error"), dict):
        return None
    error = payload["error"]
    code = error.get("code") or error.get("type")
    if not isinstance(code, str) or len(code) > 80:
        return None
    return code


def _safe_model(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    model = payload.get("model")
    return model if isinstance(model, str) else None


def _extract_output_text(payload: Mapping[str, Any]) -> str:
    output = payload.get("output")
    if not isinstance(output, list):
        raise ValueError
    texts: list[str] = []
    message_count = 0
    for item in output:
        if not isinstance(item, dict):
            raise ValueError
        if item.get("type") == "reasoning":
            continue
        if item.get("type") != "message":
            raise ValueError
        message_count += 1
        if item.get("status") not in {None, "completed"}:
            raise ValueError
        content = item.get("content")
        if not isinstance(content, list):
            raise ValueError
        for part in content:
            if not isinstance(part, dict):
                raise ValueError
            if part.get("type") == "refusal":
                raise ValueError
            if part.get("type") != "output_text" or not isinstance(part.get("text"), str):
                raise ValueError
            texts.append(part["text"])
    if message_count != 1 or len(texts) != 1:
        raise ValueError
    return texts[0]


def _operation_proposal(value: object) -> OperationProposal:
    root = _object_with_keys(
        value,
        {
            "origin",
            "destination",
            "pickup_date",
            "pickup_window",
            "maximum_amount",
            "allowed_conditions",
            "escalation_conditions",
        },
    )
    window = _object_with_keys(root["pickup_window"], {"start_date", "end_date"})
    maximum = _object_with_keys(root["maximum_amount"], {"amount", "currency"})
    amount = _decimal(maximum["amount"])
    return OperationProposal(
        route=Route(
            origin=_bounded_string(root["origin"]),
            destination=_bounded_string(root["destination"]),
        ),
        pickup_date=_date(root["pickup_date"]),
        mandate=MandateProposal(
            maximum_amount=Money(
                amount=amount,
                currency=_currency(maximum["currency"]),
            ),
            pickup_window=PickupWindow(
                start_date=_date(window["start_date"]),
                end_date=_date(window["end_date"]),
            ),
            allowed_conditions=_conditions(root["allowed_conditions"]),
            escalation_conditions=_conditions(root["escalation_conditions"]),
        ),
    )


def _object_with_keys(value: object, expected: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError
    return value


def _bounded_string(value: object) -> str:
    if not isinstance(value, str) or len(value) > 500:
        raise ValueError
    return value


def _date(value: object) -> date:
    text = _bounded_string(value)
    parsed = date.fromisoformat(text)
    if parsed.isoformat() != text:
        raise ValueError
    return parsed


def _decimal(value: object) -> Decimal:
    if not isinstance(value, str) or len(value) > MAX_DECIMAL_TEXT_LENGTH:
        raise ValueError
    text = value
    if _DECIMAL.fullmatch(text) is None:
        raise ValueError
    amount = Decimal(text)
    if not amount.is_finite():
        raise ValueError
    return amount


def _currency(value: object) -> str:
    currency = _bounded_string(value)
    if re.fullmatch(r"[A-Z]{3}", currency) is None:
        raise ValueError
    return currency


def _conditions(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 25:
        raise ValueError
    return tuple(_bounded_string(item) for item in value)
