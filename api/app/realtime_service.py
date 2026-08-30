"""FastAPI-to-core adapter for scoped Realtime credential issuance."""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated

import httpx
from fastapi import Depends, Request
from yuno_backend.integrations.openai import (
    OpenAIRealtimeClientSecretConfig,
    OpenAIRealtimeClientSecretIssuer,
)
from yuno_backend.volta.realtime import (
    RealtimeClientSecretIssuer,
    RealtimeClientSecretRequest,
    RealtimeError,
    RealtimeSessionRequest,
    RealtimeToolDefinition,
)

from app.config import Settings
from app.contract_service import ContractServiceError
from app.openai_client import get_openai_http_client
from app.schemas.errors import ApiErrorCode
from app.schemas.realtime import RealtimeClientSecretResponse

_SESSION_INSTRUCTIONS = """You are Volta, an English-language logistics negotiation assistant.
Use only the supplied tools for operational facts or mutations. Never claim authority outside the
approved mandate, invent a quote, or create a commitment without a validated tool result."""
_UUID_SCHEMA = {"type": "string", "format": "uuid"}
_POSITIVE_VERSION_SCHEMA = {
    "type": "integer",
    "minimum": 1,
    "maximum": 9_007_199_254_740_991,
}
_TOOLS = (
    RealtimeToolDefinition(
        name="record_quote",
        description=(
            "Submit the carrier's quoted terms and concurrency context to the deterministic "
            "application boundary."
        ),
        parameters={
            "type": "object",
            "properties": {
                "call_id": _UUID_SCHEMA,
                "expected_operation_version": _POSITIVE_VERSION_SCHEMA,
                "carrier_id": _UUID_SCHEMA,
                "mandate_version": _POSITIVE_VERSION_SCHEMA,
                "terms": {
                    "type": "object",
                    "properties": {
                        "amount_minor": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 9_007_199_254_740_991,
                        },
                        "currency": {"type": "string", "enum": ["MXN"]},
                        "pickup_window": {
                            "type": "object",
                            "properties": {
                                "start_date": {"type": "string", "format": "date"},
                                "end_date": {"type": "string", "format": "date"},
                            },
                            "required": ["start_date", "end_date"],
                            "additionalProperties": False,
                        },
                        "conditions": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1, "maxLength": 500},
                            "maxItems": 25,
                        },
                    },
                    "required": ["amount_minor", "currency", "pickup_window", "conditions"],
                    "additionalProperties": False,
                },
                "valid_until": {"type": "string", "format": "date-time"},
            },
            "required": [
                "call_id",
                "expected_operation_version",
                "carrier_id",
                "mandate_version",
                "terms",
                "valid_until",
            ],
            "additionalProperties": False,
        },
    ),
    RealtimeToolDefinition(
        name="create_candidate_commitment",
        description="Request a candidate commitment after deterministic mandate validation.",
        parameters={
            "type": "object",
            "properties": {
                "call_id": _UUID_SCHEMA,
                "expected_operation_version": _POSITIVE_VERSION_SCHEMA,
                "quote_id": _UUID_SCHEMA,
                "mandate_version": _POSITIVE_VERSION_SCHEMA,
                "evidence_id": _UUID_SCHEMA,
            },
            "required": [
                "call_id",
                "expected_operation_version",
                "quote_id",
                "mandate_version",
                "evidence_id",
            ],
            "additionalProperties": False,
        },
    ),
)


class RealtimeClientSecretService:
    def __init__(
        self,
        issuer: RealtimeClientSecretIssuer,
        *,
        safety_identifier_key: str,
        subject: str,
        voice: str,
    ) -> None:
        if not safety_identifier_key or not subject:
            raise ValueError("Realtime safety identifier configuration is required")
        self._issuer = issuer
        self._safety_identifier = derive_safety_identifier(
            safety_identifier_key,
            subject,
        )
        self._voice = voice

    async def issue(self) -> RealtimeClientSecretResponse:
        try:
            result = await self._issuer.issue(
                RealtimeClientSecretRequest(
                    session=RealtimeSessionRequest(
                        instructions=_SESSION_INSTRUCTIONS,
                        safety_identifier=self._safety_identifier,
                        tools=_TOOLS,
                        language="en",
                        voice=self._voice,
                        vad="server_vad",
                    )
                )
            )
        except RealtimeError:
            raise ContractServiceError(
                status_code=502,
                code=ApiErrorCode.REALTIME_UNAVAILABLE,
                message="Realtime credential issuance is temporarily unavailable.",
            ) from None
        return RealtimeClientSecretResponse(
            client_secret=result.value,
            expires_at=result.expires_at,
            session_id=result.session_id,
            model=result.model_id,
        )


def derive_safety_identifier(key: str, subject: str) -> str:
    if not key or not subject:
        raise ValueError("safety identifier inputs are required")
    return hmac.new(key.encode(), subject.encode(), hashlib.sha256).hexdigest()


def build_telephony_realtime_session(settings: Settings) -> RealtimeSessionRequest:
    """Reuse browser voice policy while exposing only the non-authoritative quote tool."""

    return RealtimeSessionRequest(
        instructions=_SESSION_INSTRUCTIONS,
        safety_identifier=derive_safety_identifier(
            settings.openai_realtime_safety_identifier_key.get_secret_value(),
            settings.volta_realtime_subject,
        ),
        tools=(_TOOLS[0],),
        language="en",
        voice=settings.volta_realtime_voice,
        vad="server_vad",
    )


def build_realtime_client_secret_service(
    settings: Settings,
    client: httpx.AsyncClient,
) -> RealtimeClientSecretService:
    api_key = settings.openai_api_key.get_secret_value()
    safety_key = settings.openai_realtime_safety_identifier_key.get_secret_value()
    issuer = OpenAIRealtimeClientSecretIssuer(
        client,
        OpenAIRealtimeClientSecretConfig(
            api_key=api_key,
            model=settings.openai_realtime_model,
        ),
    )
    return RealtimeClientSecretService(
        issuer,
        safety_identifier_key=safety_key,
        subject=settings.volta_realtime_subject,
        voice=settings.volta_realtime_voice,
    )


def get_realtime_client_secret_service(request: Request) -> RealtimeClientSecretService:
    service = getattr(request.app.state, "realtime_client_secret_service", None)
    if service is None:
        try:
            service = build_realtime_client_secret_service(
                request.app.state.settings,
                get_openai_http_client(request.app),
            )
        except ValueError:
            raise ContractServiceError(
                status_code=502,
                code=ApiErrorCode.REALTIME_UNAVAILABLE,
                message="Realtime credential issuance is temporarily unavailable.",
            ) from None
        request.app.state.realtime_client_secret_service = service
    return service


RealtimeClientSecretServiceDep = Annotated[
    RealtimeClientSecretService,
    Depends(get_realtime_client_secret_service),
]
