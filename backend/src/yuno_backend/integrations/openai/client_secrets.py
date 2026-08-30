"""OpenAI Realtime client-secret issuer."""

from __future__ import annotations

import math
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

import httpx

from yuno_backend.integrations.openai.realtime import (
    DEFAULT_REALTIME_MODEL,
    realtime_session_config,
)
from yuno_backend.volta.realtime.client_secrets import (
    MAX_CLIENT_SECRET_BYTES,
    RealtimeClientSecret,
    RealtimeClientSecretRequest,
)
from yuno_backend.volta.realtime.errors import (
    InvalidRealtimeResponseError,
    RealtimeAuthenticationError,
    RealtimeConnectionError,
    RealtimeError,
    RealtimeModelUnavailableError,
    RealtimeProviderError,
    RealtimeRateLimitError,
    RealtimeTimeoutError,
)

__all__ = ["OpenAIRealtimeClientSecretConfig", "OpenAIRealtimeClientSecretIssuer"]

_OFFICIAL_HOST = "api.openai.com"
_OFFICIAL_PATH = "/v1/realtime/client_secrets"
_DEFAULT_URL = f"https://{_OFFICIAL_HOST}{_OFFICIAL_PATH}"
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_MAX_TIMEOUT_SECONDS = 300
_MAX_RESPONSE_BYTES = 65_536
_MAX_SECRET_TTL_SECONDS = 600
_MAX_CLOCK_SKEW_SECONDS = 60


@dataclass(frozen=True, slots=True)
class OpenAIRealtimeClientSecretConfig:
    """Immutable server-only settings for ephemeral credential issuance."""

    api_key: str = field(repr=False)
    url: str = _DEFAULT_URL
    model: str = DEFAULT_REALTIME_MODEL
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise ValueError("OpenAI API key is required")
        parsed = urlsplit(self.url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != _OFFICIAL_HOST
            or parsed.path != _OFFICIAL_PATH
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("OpenAI client-secret URL must be the official HTTPS endpoint")
        if not isinstance(self.model, str) or _SAFE_IDENTIFIER.fullmatch(self.model) is None:
            raise ValueError("model must be a safe bounded identifier")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, int | float)
            or not math.isfinite(self.timeout_seconds)
            or not 0 < self.timeout_seconds <= _MAX_TIMEOUT_SECONDS
        ):
            raise ValueError("timeout must be positive and at most 300 seconds")


class OpenAIRealtimeClientSecretIssuer:
    """Mint and validate an OpenAI ephemeral credential without owning the client."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        config: OpenAIRealtimeClientSecretConfig,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._client = client
        self._config = config
        self._clock = clock

    async def issue(self, request: RealtimeClientSecretRequest) -> RealtimeClientSecret:
        started = time.monotonic()
        try:
            response = await self._client.post(
                self._config.url,
                headers={
                    "Authorization": f"Bearer {self._config.api_key}",
                    "Content-Type": "application/json",
                    "OpenAI-Safety-Identifier": request.session.safety_identifier,
                },
                json={
                    "session": realtime_session_config(request.session, model=self._config.model)
                },
                timeout=httpx.Timeout(self._config.timeout_seconds),
            )
        except httpx.TimeoutException:
            raise RealtimeTimeoutError(
                model_id=self._config.model, duration_ms=_duration_ms(started)
            ) from None
        except httpx.RequestError:
            raise RealtimeConnectionError(
                model_id=self._config.model, duration_ms=_duration_ms(started)
            ) from None
        except RealtimeError:
            raise
        except Exception:
            raise RealtimeConnectionError(
                model_id=self._config.model, duration_ms=_duration_ms(started)
            ) from None

        if not response.is_success:
            raise _status_error(
                response,
                model_id=self._config.model,
                duration_ms=_duration_ms(started),
            )

        try:
            if len(response.content) > _MAX_RESPONSE_BYTES:
                raise ValueError
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError
            return _parse_secret(
                payload,
                expected_model=self._config.model,
                now=self._clock(),
            )
        except RealtimeError:
            raise
        except Exception:
            raise InvalidRealtimeResponseError(
                model_id=self._config.model, duration_ms=_duration_ms(started)
            ) from None


def _parse_secret(
    payload: Mapping[str, Any], *, expected_model: str, now: float
) -> RealtimeClientSecret:
    value = payload["value"]
    expires_at = payload["expires_at"]
    session = payload["session"]
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value.encode()) > MAX_CLIENT_SECRET_BYTES
        or not isinstance(expires_at, int)
        or isinstance(expires_at, bool)
        or not isinstance(session, dict)
        or session.get("object") != "realtime.session"
        or session.get("type") != "realtime"
        or session.get("model") != expected_model
    ):
        raise ValueError
    session_id = session.get("id")
    if not isinstance(session_id, str):
        raise ValueError
    current_time = math.floor(now)
    if (
        expires_at <= current_time
        or expires_at
        > current_time + _MAX_SECRET_TTL_SECONDS + _MAX_CLOCK_SKEW_SECONDS
    ):
        raise ValueError
    return RealtimeClientSecret(
        value=value,
        expires_at=expires_at,
        session_id=session_id,
        model_id=expected_model,
    )


def _status_error(response: httpx.Response, *, model_id: str, duration_ms: int) -> RealtimeError:
    status_code = response.status_code
    error_code = _provider_error_code(response)
    error_type: type[RealtimeError] = RealtimeProviderError
    if status_code in {401, 403}:
        error_type = RealtimeAuthenticationError
    elif status_code == 404 or error_code in {"model_not_found", "model_not_available"}:
        error_type = RealtimeModelUnavailableError
    elif status_code == 429:
        error_type = RealtimeRateLimitError
    return error_type(model_id=model_id, status_code=status_code, duration_ms=duration_ms)


def _provider_error_code(response: httpx.Response) -> str | None:
    if len(response.content) > _MAX_RESPONSE_BYTES:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return code if isinstance(code, str) else None


def _duration_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1_000))
