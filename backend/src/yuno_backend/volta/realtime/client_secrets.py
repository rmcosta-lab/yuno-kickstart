"""Provider-neutral client-secret issuance contracts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from yuno_backend.volta.realtime.models import RealtimeSessionRequest

__all__ = [
    "RealtimeClientSecret",
    "RealtimeClientSecretIssuer",
    "RealtimeClientSecretRequest",
]

MAX_CLIENT_SECRET_BYTES = 4_096
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


def _safe_identifier(value: object, field_name: str) -> None:
    if not isinstance(value, str) or _SAFE_IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a safe bounded identifier")


@dataclass(frozen=True, slots=True)
class RealtimeClientSecretRequest:
    """One accepted, server-controlled Realtime session configuration."""

    session: RealtimeSessionRequest = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.session, RealtimeSessionRequest):
            raise ValueError("session must be RealtimeSessionRequest")


@dataclass(frozen=True, slots=True)
class RealtimeClientSecret:
    """Safe session metadata plus a representation-redacted ephemeral value."""

    value: str = field(repr=False)
    expires_at: int
    session_id: str
    model_id: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or not self.value.strip()
            or len(self.value.encode()) > MAX_CLIENT_SECRET_BYTES
        ):
            raise ValueError("client secret must be non-empty bounded text")
        if (
            not isinstance(self.expires_at, int)
            or isinstance(self.expires_at, bool)
            or self.expires_at <= 0
        ):
            raise ValueError("expires_at must be a positive Unix timestamp")
        _safe_identifier(self.session_id, "session_id")
        _safe_identifier(self.model_id, "model_id")


class RealtimeClientSecretIssuer(Protocol):
    """Mint one ephemeral credential for an accepted session."""

    async def issue(self, request: RealtimeClientSecretRequest) -> RealtimeClientSecret: ...
