"""Safe provider-neutral failures for intake extraction."""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import ClassVar

__all__ = [
    "ExtractionAuthenticationError",
    "ExtractionError",
    "ExtractionModelUnavailableError",
    "ExtractionProviderError",
    "ExtractionRateLimitError",
    "ExtractionTimeoutError",
    "InvalidExtractionResponse",
]

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def _safe_identifier(value: str | None) -> str | None:
    if value is None or _SAFE_IDENTIFIER.fullmatch(value) is None:
        return None
    return value


class ExtractionError(RuntimeError):
    """Base extraction failure containing only allowlisted diagnostic metadata."""

    category: ClassVar[str] = "extraction"

    def __init__(
        self,
        *,
        status_code: int | None = None,
        request_id: str | None = None,
        model_id: str | None = None,
        attempt_count: int = 1,
        duration_ms: int | None = None,
    ) -> None:
        self.status_code = status_code if isinstance(status_code, int) else None
        self.request_id = _safe_identifier(request_id)
        self.model_id = _safe_identifier(model_id)
        self.attempt_count = max(1, attempt_count)
        self.duration_ms = max(0, duration_ms) if duration_ms is not None else None
        super().__init__(self.category)

    @property
    def safe_metadata(self) -> MappingProxyType[str, str | int | None]:
        """Return bounded operational metadata with no prompt or provider payload."""
        return MappingProxyType(
            {
                "category": self.category,
                "status_code": self.status_code,
                "request_id": self.request_id,
                "model_id": self.model_id,
                "attempt_count": self.attempt_count,
                "duration_ms": self.duration_ms,
            }
        )


class ExtractionAuthenticationError(ExtractionError):
    category = "authentication"


class ExtractionModelUnavailableError(ExtractionError):
    category = "model_unavailable"


class ExtractionRateLimitError(ExtractionError):
    category = "rate_limit"


class ExtractionTimeoutError(ExtractionError):
    category = "timeout"


class ExtractionProviderError(ExtractionError):
    category = "provider"


class InvalidExtractionResponse(ExtractionError):
    category = "invalid_response"
