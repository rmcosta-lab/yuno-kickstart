"""Bounded, concurrency-safe mutation limiting for the authorized demo actor."""

from __future__ import annotations

import hashlib
import hmac
import math
import secrets
from collections import OrderedDict, deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from fastapi.security.utils import get_authorization_scheme_param
from starlette.datastructures import Headers
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import Settings
from app.errors import api_error_response
from app.schemas.errors import ApiErrorCode

_REALTIME_CLIENT_SECRET_PATH = "/v1/realtime/client-secrets"
_OUTBOUND_CALL_SUFFIX = "/outbound-calls"


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    """Keep a bounded least-recently-used set of sliding request windows."""

    def __init__(
        self,
        *,
        request_limit: int,
        window_seconds: float,
        max_identities: int,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._request_limit = request_limit
        self._window_seconds = window_seconds
        self._max_identities = max_identities
        self._clock = clock
        self._windows: OrderedDict[bytes, deque[float]] = OrderedDict()
        self._lock = Lock()

    @property
    def identity_count(self) -> int:
        with self._lock:
            return len(self._windows)

    def check(self, identity: bytes) -> RateLimitDecision:
        now = self._clock()
        threshold = now - self._window_seconds
        with self._lock:
            requests = self._windows.get(identity)
            if requests is None:
                self._make_room(threshold)
                requests = deque()
                self._windows[identity] = requests
            else:
                self._windows.move_to_end(identity)

            while requests and requests[0] <= threshold:
                requests.popleft()
            if len(requests) >= self._request_limit:
                retry_after = max(1, math.ceil(self._window_seconds - (now - requests[0])))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)

            requests.append(now)
            return RateLimitDecision(allowed=True)

    def _make_room(self, threshold: float) -> None:
        expired = [
            identity
            for identity, requests in self._windows.items()
            if not requests or requests[-1] <= threshold
        ]
        for identity in expired:
            del self._windows[identity]
        while len(self._windows) >= self._max_identities:
            self._windows.popitem(last=False)


class MutationRateLimitMiddleware:
    """Limit authenticated POST mutations without retaining the bearer token."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        settings: Settings,
        limiter: SlidingWindowRateLimiter,
    ) -> None:
        self.app = app
        self._limiter = limiter
        self._fingerprint_key = secrets.token_bytes(32)
        configured_token = settings.volta_demo_bearer_token.get_secret_value()
        self._configured_fingerprint = (
            self._fingerprint(configured_token) if configured_token else None
        )
        self._realtime_origins = frozenset(settings.cors_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._is_mutation(scope):
            await self.app(scope, receive, send)
            return

        if self._has_invalid_browser_origin(scope):
            # The route dependency owns the 403 response. Do not let an unauthorized
            # browser origin consume the authorized actor's mutation allowance first.
            await self.app(scope, receive, send)
            return

        identity = self._authorized_identity(scope)
        if identity is None:
            await self.app(scope, receive, send)
            return

        decision = self._limiter.check(identity)
        if decision.allowed:
            await self.app(scope, receive, send)
            return

        response = api_error_response(
            Request(scope),
            status_code=429,
            code=ApiErrorCode.RATE_LIMITED,
            message="The configured demo traffic boundary was exceeded.",
        )
        response.headers["Retry-After"] = str(decision.retry_after_seconds)
        await response(scope, receive, send)

    @staticmethod
    def _is_mutation(scope: Scope) -> bool:
        return (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and str(scope.get("path", "")).startswith("/v1/")
        )

    def _authorized_identity(self, scope: Scope) -> bytes | None:
        authorization = Headers(scope=scope).get("authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if scheme.lower() != "bearer" or not credentials or self._configured_fingerprint is None:
            return None
        fingerprint = self._fingerprint(credentials)
        if not hmac.compare_digest(fingerprint, self._configured_fingerprint):
            return None
        return fingerprint

    def _has_invalid_browser_origin(self, scope: Scope) -> bool:
        path = str(scope.get("path", ""))
        if path != _REALTIME_CLIENT_SECRET_PATH and not path.endswith(_OUTBOUND_CALL_SUFFIX):
            return False
        origin = Headers(scope=scope).get("origin")
        return origin is None or origin not in self._realtime_origins

    def _fingerprint(self, token: str) -> bytes:
        return hmac.digest(
            self._fingerprint_key,
            token.encode("utf-8"),
            hashlib.sha256,
        )
