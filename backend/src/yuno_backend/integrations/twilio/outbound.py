"""Bounded Twilio adapter for one explicitly authorized outbound call."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Never, Protocol
from urllib.parse import urlencode

import httpx

from yuno_backend.integrations.twilio.config import (
    TwilioDestinationAllowlist,
    TwilioOutboundCallConfig,
)
from yuno_backend.volta.telephony import (
    InvalidOutboundCallResponseError,
    OutboundCall,
    OutboundCallAllowlistError,
    OutboundCallAttempt,
    OutboundCallAttemptState,
    OutboundCallAttemptStore,
    OutboundCallAuthenticationError,
    OutboundCallAuthorizationError,
    OutboundCallError,
    OutboundCallFailure,
    OutboundCallFailureCategory,
    OutboundCallIdempotencyConflict,
    OutboundCallOutcomeUncertain,
    OutboundCallProviderError,
    OutboundCallRateLimitError,
    OutboundCallRequest,
    OutboundCallStatus,
    OutboundCallTimeoutError,
    OutboundCallUncertainReason,
    OutboundCallUncertainState,
    outbound_call_request_fingerprint,
)

__all__ = ["TwilioOutboundCallGateway", "map_twilio_call_status"]

_CALL_SID = re.compile(r"^CA[0-9a-fA-F]{32}$")
_MAX_RESPONSE_BYTES = 65_536
_STATUS_MAP = {
    "queued": OutboundCallStatus.QUEUED,
    "initiated": OutboundCallStatus.INITIATED,
    "ringing": OutboundCallStatus.RINGING,
    "in-progress": OutboundCallStatus.IN_PROGRESS,
    "completed": OutboundCallStatus.COMPLETED,
    "busy": OutboundCallStatus.BUSY,
    "failed": OutboundCallStatus.FAILED,
    "no-answer": OutboundCallStatus.NO_ANSWER,
    "canceled": OutboundCallStatus.CANCELED,
}


async def _default_delay(seconds: float) -> None:
    await asyncio.sleep(seconds)


class _Clock(Protocol):
    def now(self) -> datetime: ...


def map_twilio_call_status(value: object) -> OutboundCallStatus:
    """Translate the documented Twilio status vocabulary."""

    if not isinstance(value, str) or value not in _STATUS_MAP:
        raise ValueError("unknown Twilio call status")
    return _STATUS_MAP[value]


class TwilioOutboundCallGateway:
    """Create a Twilio Call behind durable application idempotency."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        config: TwilioOutboundCallConfig,
        allowlist: TwilioDestinationAllowlist,
        attempt_store: OutboundCallAttemptStore,
        clock: _Clock,
        *,
        delay: Callable[[float], Awaitable[None]] = _default_delay,
    ) -> None:
        self._client = client
        self._config = config
        self._allowlist = allowlist
        self._attempt_store = attempt_store
        self._clock = clock
        self._delay = delay

    async def create_call(self, request: OutboundCallRequest) -> OutboundCall:
        now = self._clock.now()
        self._validate_authorization(request, now)
        destination = self._allowlist.resolve(request.destination_label)
        if destination is None:
            raise OutboundCallAllowlistError(**self._error_metadata(request))

        request_fingerprint = outbound_call_request_fingerprint(request)
        reservation = await self._attempt_store.reserve(
            OutboundCallAttempt(
                operation_id=request.operation_id,
                idempotency_key=request.idempotency_key,
                request_fingerprint=request_fingerprint,
                state=OutboundCallAttemptState.PENDING,
                result=None,
                uncertainty=None,
                failure=None,
                created_at=now,
                updated_at=now,
            )
        )
        attempt = reservation.attempt
        if attempt.request_fingerprint != request_fingerprint:
            raise OutboundCallIdempotencyConflict(**self._error_metadata(request))
        if not reservation.created:
            return self._replay(attempt, request)

        return await self._dispatch(request, destination, request_fingerprint)

    def _validate_authorization(
        self, request: OutboundCallRequest, now: datetime
    ) -> None:
        age_seconds = (now - request.authorization.authorized_at).total_seconds()
        if (
            age_seconds < 0
            or age_seconds > self._config.authorization_max_age_seconds
            or request.authorization.ai_disclosure_required is not True
        ):
            raise OutboundCallAuthorizationError(**self._error_metadata(request))

    def _replay(
        self, attempt: OutboundCallAttempt, request: OutboundCallRequest
    ) -> OutboundCall:
        if attempt.state is OutboundCallAttemptState.SUCCEEDED and attempt.result is not None:
            return attempt.result
        if attempt.state is OutboundCallAttemptState.FAILED and attempt.failure is not None:
            raise self._failure_error(attempt.failure.category, request)
        raise OutboundCallOutcomeUncertain(**self._error_metadata(request))

    async def _dispatch(
        self,
        request: OutboundCallRequest,
        destination: str,
        request_fingerprint: str,
    ) -> OutboundCall:
        form: list[tuple[str, str]] = [
            ("To", destination),
            ("From", self._config.from_e164),
            ("Url", self._config.instruction_url),
            ("Method", "POST"),
            ("StatusCallback", self._config.status_callback_url),
            ("StatusCallbackMethod", "POST"),
            ("StatusCallbackEvent", "initiated"),
            ("StatusCallbackEvent", "ringing"),
            ("StatusCallbackEvent", "answered"),
            ("StatusCallbackEvent", "completed"),
            ("Record", "false"),
        ]
        encoded_form = urlencode(form).encode("ascii")
        for attempt_number in range(1, self._config.max_attempts + 1):
            try:
                async with self._client.stream(
                    "POST",
                    self._config.create_call_url,
                    auth=httpx.BasicAuth(
                        self._config.api_key_sid, self._config.api_key_secret
                    ),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    content=encoded_form,
                    timeout=httpx.Timeout(self._config.timeout_seconds),
                ) as response:
                    if response.status_code == 429:
                        if attempt_number < self._config.max_attempts:
                            await self._delay(
                                self._config.backoff_seconds[attempt_number - 1]
                            )
                            continue
                        return await self._definitive_failure(
                            request,
                            request_fingerprint,
                            OutboundCallFailureCategory.RATE_LIMIT,
                            response.status_code,
                            retry_after_seconds=_retry_after(response),
                        )
                    if response.status_code >= 500:
                        return await self._uncertain(
                            request,
                            request_fingerprint,
                            OutboundCallUncertainReason.PROVIDER_FAILURE,
                        )
                    if not response.is_success:
                        return await self._definitive_failure(
                            request,
                            request_fingerprint,
                            _failure_category(response.status_code),
                            response.status_code,
                        )
                    try:
                        payload = await _bounded_json(response)
                        result = _parse_call(payload, request, self._clock.now())
                    except (UnicodeError, ValueError):
                        await self._mark_uncertain(
                            request,
                            request_fingerprint,
                            OutboundCallUncertainReason.INVALID_RESPONSE,
                        )
                        raise OutboundCallOutcomeUncertain(
                            **self._error_metadata(request, response)
                        ) from None
                    try:
                        await self._attempt_store.complete(
                            request.idempotency_key,
                            request_fingerprint,
                            result,
                            self._clock.now(),
                        )
                    except Exception:
                        raise OutboundCallOutcomeUncertain(
                            **self._error_metadata(request, response)
                        ) from None
                    return result
            except (httpx.ConnectTimeout, httpx.PoolTimeout):
                if attempt_number < self._config.max_attempts:
                    await self._delay(self._config.backoff_seconds[attempt_number - 1])
                    continue
                return await self._definitive_failure(
                    request,
                    request_fingerprint,
                    OutboundCallFailureCategory.TIMEOUT,
                    None,
                )
            except httpx.ConnectError:
                if attempt_number < self._config.max_attempts:
                    await self._delay(self._config.backoff_seconds[attempt_number - 1])
                    continue
                return await self._definitive_failure(
                    request,
                    request_fingerprint,
                    OutboundCallFailureCategory.CONNECTION,
                    None,
                )
            except httpx.TimeoutException:
                await self._mark_uncertain(
                    request,
                    request_fingerprint,
                    OutboundCallUncertainReason.TIMEOUT,
                )
                raise OutboundCallOutcomeUncertain(**self._error_metadata(request)) from None
            except httpx.RequestError:
                return await self._uncertain(
                    request,
                    request_fingerprint,
                    OutboundCallUncertainReason.CONNECTION_LOST,
                )
        raise AssertionError("bounded Twilio attempt loop did not terminate")

    async def _definitive_failure(
        self,
        request: OutboundCallRequest,
        request_fingerprint: str,
        category: OutboundCallFailureCategory,
        status_code: int | None,
        *,
        retry_after_seconds: int | None = None,
    ) -> Never:
        try:
            await self._attempt_store.fail(
                request.idempotency_key,
                request_fingerprint,
                OutboundCallFailure(
                    category=category,
                    occurred_at=self._clock.now(),
                    status_code=status_code,
                ),
            )
        except Exception:
            raise OutboundCallOutcomeUncertain(**self._error_metadata(request)) from None
        raise self._failure_error(category, request, retry_after_seconds=retry_after_seconds)

    async def _uncertain(
        self,
        request: OutboundCallRequest,
        request_fingerprint: str,
        reason: OutboundCallUncertainReason,
    ) -> Never:
        await self._mark_uncertain(request, request_fingerprint, reason)
        raise OutboundCallOutcomeUncertain(**self._error_metadata(request))

    async def _mark_uncertain(
        self,
        request: OutboundCallRequest,
        request_fingerprint: str,
        reason: OutboundCallUncertainReason,
    ) -> None:
        try:
            await self._attempt_store.mark_uncertain(
                request.idempotency_key,
                request_fingerprint,
                OutboundCallUncertainState(reason=reason, occurred_at=self._clock.now()),
            )
        except Exception:
            raise OutboundCallOutcomeUncertain(**self._error_metadata(request)) from None

    def _failure_error(
        self,
        category: OutboundCallFailureCategory,
        request: OutboundCallRequest,
        *,
        retry_after_seconds: int | None = None,
    ) -> OutboundCallError:
        error_type: type[OutboundCallError]
        if category is OutboundCallFailureCategory.AUTHENTICATION:
            error_type = OutboundCallAuthenticationError
        elif category is OutboundCallFailureCategory.TIMEOUT:
            error_type = OutboundCallTimeoutError
        elif category is OutboundCallFailureCategory.RATE_LIMIT:
            error_type = OutboundCallRateLimitError
        elif category is OutboundCallFailureCategory.INVALID_RESPONSE:
            error_type = InvalidOutboundCallResponseError
        else:
            error_type = OutboundCallProviderError
        return error_type(
            **self._error_metadata(request), retry_after_seconds=retry_after_seconds
        )

    @staticmethod
    def _error_metadata(
        request: OutboundCallRequest, response: httpx.Response | None = None
    ) -> dict[str, object]:
        request_id = response.headers.get("Twilio-Request-Id") if response else None
        return {
            "call_session_id": request.call_session_id,
            "destination_label": request.destination_label,
            "provider_request_id": request_id,
        }


async def _bounded_json(response: httpx.Response) -> object:
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            if int(content_length) > _MAX_RESPONSE_BYTES:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError from None
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body.extend(chunk)
        if len(body) > _MAX_RESPONSE_BYTES:
            raise ValueError
    if not body:
        raise ValueError
    return json.loads(body)


def _parse_call(
    payload: object, request: OutboundCallRequest, created_at: datetime
) -> OutboundCall:
    if not isinstance(payload, dict):
        raise ValueError
    sid = payload.get("sid")
    if not isinstance(sid, str) or _CALL_SID.fullmatch(sid) is None:
        raise ValueError
    status = map_twilio_call_status(payload.get("status"))
    return OutboundCall(
        call_session_id=request.call_session_id,
        provider_call_id=sid,
        status=status,
        created_at=created_at,
    )


def _failure_category(status_code: int) -> OutboundCallFailureCategory:
    if status_code == 401:
        return OutboundCallFailureCategory.AUTHENTICATION
    if status_code == 403:
        return OutboundCallFailureCategory.PERMISSION
    if status_code in {400, 405, 409, 415, 422}:
        return OutboundCallFailureCategory.INVALID_REQUEST
    return OutboundCallFailureCategory.PROVIDER_REJECTED


def _retry_after(response: httpx.Response) -> int | None:
    value = response.headers.get("Retry-After")
    try:
        seconds = int(value) if value is not None else None
    except ValueError:
        return None
    return min(seconds, 86_400) if seconds is not None and seconds >= 0 else None
