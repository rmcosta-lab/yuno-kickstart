from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from yuno_backend.volta.realtime import (
    RealtimeClientSecret,
    RealtimeClientSecretIssuer,
    RealtimeClientSecretRequest,
    RealtimeSessionRequest,
)

SAFETY_IDENTIFIER = "a" * 64


def _session() -> RealtimeSessionRequest:
    return RealtimeSessionRequest(
        instructions="private instructions",
        safety_identifier=SAFETY_IDENTIFIER,
    )


def test_client_secret_values_are_frozen_and_sensitive_fields_are_redacted() -> None:
    request = RealtimeClientSecretRequest(session=_session())
    secret = RealtimeClientSecret(
        value="ek_private_ephemeral_value",
        expires_at=2_000_000_060,
        session_id="sess_safe",
        model_id="gpt-realtime-2.1",
    )

    assert "private instructions" not in repr(request)
    assert SAFETY_IDENTIFIER not in repr(request)
    assert secret.value not in repr(secret)
    with pytest.raises(FrozenInstanceError):
        secret.expires_at = 0  # type: ignore[misc]


def test_client_secret_issuer_is_an_async_provider_neutral_protocol() -> None:
    class FakeIssuer:
        async def issue(self, request: RealtimeClientSecretRequest) -> RealtimeClientSecret:
            assert request.session.language == "en"
            return RealtimeClientSecret(
                value="ek_private_ephemeral_value",
                expires_at=2_000_000_060,
                session_id="sess_safe",
                model_id="gpt-realtime-2.1",
            )

    issuer: RealtimeClientSecretIssuer = FakeIssuer()
    assert issuer is not None


@pytest.mark.parametrize(
    "values",
    [
        {
            "value": "",
            "expires_at": 2_000_000_060,
            "session_id": "sess_safe",
            "model_id": "gpt-realtime-2.1",
        },
        {
            "value": "ek_safe",
            "expires_at": 0,
            "session_id": "sess_safe",
            "model_id": "gpt-realtime-2.1",
        },
        {
            "value": "ek_safe",
            "expires_at": 2_000_000_060,
            "session_id": "unsafe value",
            "model_id": "gpt-realtime-2.1",
        },
    ],
)
def test_client_secret_values_reject_invalid_fields(values: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        RealtimeClientSecret(**values)  # type: ignore[arg-type]
