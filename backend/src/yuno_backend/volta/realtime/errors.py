"""Safe provider-neutral failures for realtime sessions."""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import ClassVar

__all__ = [
    "InvalidRealtimeEvent",
    "RealtimeAuthenticationError",
    "RealtimeConnectionError",
    "RealtimeDisconnectedError",
    "RealtimeError",
    "RealtimeModelUnavailableError",
    "RealtimeProviderError",
    "RealtimeRateLimitError",
    "RealtimeTimeoutError",
]

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def _safe_identifier(value: object) -> str | None:
    return value if isinstance(value, str) and _SAFE_IDENTIFIER.fullmatch(value) else None


class RealtimeError(RuntimeError):
    """Base failure whose message and metadata cannot contain realtime content."""

    category: ClassVar[str] = "realtime"

    def __init__(
        self,
        *,
        model_id: str | None = None,
        event_type: str | None = None,
        event_id: str | None = None,
        request_id: str | None = None,
        status_code: int | None = None,
        close_code: int | None = None,
        duration_ms: int | None = None,
    ) -> None:
        self.model_id = _safe_identifier(model_id)
        self.event_type = _safe_identifier(event_type)
        self.event_id = _safe_identifier(event_id)
        self.request_id = _safe_identifier(request_id)
        self.status_code = status_code if isinstance(status_code, int) else None
        self.close_code = close_code if isinstance(close_code, int) else None
        self.duration_ms = max(0, duration_ms) if isinstance(duration_ms, int) else None
        super().__init__(self.category)

    @property
    def safe_metadata(self) -> MappingProxyType[str, str | int | None]:
        return MappingProxyType(
            {
                "category": self.category,
                "model_id": self.model_id,
                "event_type": self.event_type,
                "event_id": self.event_id,
                "request_id": self.request_id,
                "status_code": self.status_code,
                "close_code": self.close_code,
                "duration_ms": self.duration_ms,
            }
        )


class RealtimeAuthenticationError(RealtimeError):
    category = "authentication"


class RealtimeModelUnavailableError(RealtimeError):
    category = "model_unavailable"


class RealtimeRateLimitError(RealtimeError):
    category = "rate_limit"


class RealtimeConnectionError(RealtimeError):
    category = "connection"


class RealtimeTimeoutError(RealtimeError):
    category = "timeout"


class RealtimeDisconnectedError(RealtimeError):
    category = "disconnected"


class InvalidRealtimeEvent(RealtimeError):
    category = "invalid_event"


class RealtimeProviderError(RealtimeError):
    category = "provider"
