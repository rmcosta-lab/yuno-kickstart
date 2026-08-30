"""Thin API orchestration over Phase 18 telephony and Realtime contracts."""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

import httpx
from fastapi import Request
from yuno_backend.database import DatabaseConfig, create_database_engine, create_session_factory
from yuno_backend.integrations.openai import OpenAIRealtimeConfig, OpenAIRealtimeGateway
from yuno_backend.integrations.twilio import (
    TwilioDestinationAllowlist,
    TwilioOutboundCallConfig,
    TwilioOutboundCallGateway,
)
from yuno_backend.volta.persistence import SqlAlchemyOutboundCallAttemptStore
from yuno_backend.volta.realtime import (
    RealtimeGateway,
    RealtimeSessionRequest,
    RealtimeToolCallRequested,
)
from yuno_backend.volta.telephony import (
    OutboundCall,
    OutboundCallAuthorizationError,
    OutboundCallGateway,
    OutboundCallIdempotencyConflict,
    OutboundCallRequest,
    OutboundCallStatusEvent,
    apply_status_event,
    outbound_call_request_fingerprint,
)

from app.config import Settings
from app.contract_service import ContractService, JsonValue
from app.realtime_service import build_telephony_realtime_session


@dataclass(frozen=True, slots=True)
class MediaBinding:
    operation_id: UUID
    call_session_id: UUID
    provider_call_id: str
    stream_token: str = field(repr=False)
    account_sid: str


class TelephonyApplication(Protocol):
    realtime_gateway: RealtimeGateway
    twilio_account_sid: str

    async def create_outbound_call(self, request: OutboundCallRequest) -> OutboundCall: ...

    async def binding_for_voice(self, provider_call_id: str) -> MediaBinding | None: ...

    async def binding_for_stream(self, stream_token: str) -> MediaBinding | None: ...

    async def observe_status(self, event: OutboundCallStatusEvent) -> None: ...

    def realtime_session(self, binding: MediaBinding) -> RealtimeSessionRequest: ...

    async def delegate_tool(
        self,
        binding: MediaBinding,
        event: RealtimeToolCallRequested,
        idempotency_key: str,
    ) -> Mapping[str, object]: ...

    async def stream_finished(self, binding: MediaBinding, outcome: str) -> None: ...

    async def aclose(self) -> None: ...


class UnimplementedTelephonyApplication:
    """Fail-closed placeholder until provider adapters are configured."""

    twilio_account_sid = ""
    realtime_gateway: RealtimeGateway

    async def create_outbound_call(self, request: OutboundCallRequest) -> OutboundCall:
        del request
        raise RuntimeError("telephony application is not configured")

    async def binding_for_voice(self, provider_call_id: str) -> MediaBinding | None:
        del provider_call_id
        return None

    async def binding_for_stream(self, stream_token: str) -> MediaBinding | None:
        del stream_token
        return None

    async def observe_status(self, event: OutboundCallStatusEvent) -> None:
        del event
        raise RuntimeError("telephony application is not configured")

    async def aclose(self) -> None:
        return None


def get_telephony_application(request: Request) -> TelephonyApplication:
    service = getattr(request.app.state, "telephony_application", None)
    if service is None:
        from app.openai_client import get_openai_http_client
        from app.volta_text_service import create_volta_text_contract_service

        contracts = getattr(request.app.state, "contract_service", None)
        if contracts is None:
            contracts = create_volta_text_contract_service(
                request.app.state.settings,
                http_client=get_openai_http_client(request.app),
            )
            request.app.state.contract_service = contracts
        try:
            service = create_live_telephony_application(
                request.app.state.settings,
                contracts,
                get_openai_http_client(request.app),
            )
        except (RuntimeError, ValueError):
            service = UnimplementedTelephonyApplication()
        request.app.state.telephony_application = service
    return service


class GatewayOutboundCallApplication:
    """Narrow gateway adapter useful when durable orchestration is supplied upstream."""

    def __init__(self, gateway: OutboundCallGateway) -> None:
        self._gateway = gateway

    async def create_outbound_call(self, request: OutboundCallRequest) -> OutboundCall:
        return await self._gateway.create_call(request)


_TELEPHONY_TOOL_OPERATIONS = frozenset({"record_quote"})


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | bool | int | float):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(child) for child in value]
    raise ValueError("tool arguments must be JSON-compatible")


class VoltaToolDelegator:
    """Delegate non-authoritative tools to the browser voice contract facade."""

    def __init__(self, contracts: ContractService) -> None:
        self._contracts = contracts

    async def execute(
        self, event: RealtimeToolCallRequested, idempotency_key: str
    ) -> Mapping[str, object]:
        if event.name not in _TELEPHONY_TOOL_OPERATIONS:
            raise ValueError("Realtime requested an unsupported tool")
        arguments = _json_value(event.arguments)
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be an object")
        call_id = arguments.pop("call_id", None)
        if not isinstance(call_id, str):
            raise ValueError("tool call_id is required")
        payload: dict[str, JsonValue] = {"call_id": call_id, "body": arguments}
        result = await self._contracts.execute(event.name, payload, idempotency_key)
        if not isinstance(result.payload, dict):
            raise ValueError("tool result must be an object")
        return result.payload


class LiveTelephonyApplication:
    """One-call runtime composed from existing provider-neutral adapters."""

    def __init__(
        self,
        *,
        settings: Settings,
        contracts: ContractService,
        gateway: OutboundCallGateway,
        realtime_gateway: RealtimeGateway,
        attempt_store: SqlAlchemyOutboundCallAttemptStore,
        engine: object,
    ) -> None:
        self._settings = settings
        self._contracts = contracts
        self._gateway = gateway
        self.realtime_gateway = realtime_gateway
        self._attempt_store = attempt_store
        self.twilio_account_sid = settings.twilio_account_sid.get_secret_value()
        self._engine = engine
        self._binding: MediaBinding | None = None
        self._call: OutboundCall | None = None
        self._stream_claimed = False
        self._stream_consumed = False
        self._idempotency_key: str | None = None
        self._request_fingerprint: str | None = None
        self._lock = asyncio.Lock()
        self._tools = VoltaToolDelegator(contracts)

    async def create_outbound_call(self, request: OutboundCallRequest) -> OutboundCall:
        operation = await self._contracts.execute(
            "get_operation", {"operation_id": str(request.operation_id)}, None
        )
        if not isinstance(operation.payload, dict):
            raise ValueError("operation lookup returned an invalid result")
        sessions = operation.payload.get("sessions")
        if not isinstance(sessions, list) or not any(
            isinstance(item, dict) and item.get("call_id") == str(request.call_session_id)
            for item in sessions
        ):
            raise OutboundCallAuthorizationError(call_session_id=request.call_session_id)
        request_fingerprint = outbound_call_request_fingerprint(request)
        async with self._lock:
            active_call_exists = (
                self._binding is not None
                and self._call is not None
                and not self._call.status.is_terminal
            )
            if active_call_exists:
                if request.idempotency_key == self._idempotency_key:
                    if request_fingerprint == self._request_fingerprint:
                        assert self._call is not None
                        return self._call
                    raise OutboundCallIdempotencyConflict(
                        call_session_id=request.call_session_id
                    )
                raise OutboundCallAuthorizationError(call_session_id=request.call_session_id)
            call = await self._gateway.create_call(request)
            self._call = call
            self._idempotency_key = request.idempotency_key
            self._request_fingerprint = request_fingerprint
            self._binding = MediaBinding(
                operation_id=request.operation_id,
                call_session_id=request.call_session_id,
                provider_call_id=call.provider_call_id,
                stream_token=secrets.token_urlsafe(32),
                account_sid=self.twilio_account_sid,
            )
            self._stream_claimed = False
            self._stream_consumed = False
            return call

    async def binding_for_voice(self, provider_call_id: str) -> MediaBinding | None:
        async with self._lock:
            if self._binding is None or self._binding.provider_call_id != provider_call_id:
                return None
            return self._binding

    async def binding_for_stream(self, stream_token: str) -> MediaBinding | None:
        async with self._lock:
            if (
                self._binding is None
                or not secrets.compare_digest(self._binding.stream_token, stream_token)
                or self._stream_claimed
                or self._stream_consumed
            ):
                return None
            self._stream_claimed = True
            self._stream_consumed = True
            return self._binding

    async def observe_status(self, event: OutboundCallStatusEvent) -> None:
        async with self._lock:
            if self._call is None or self._call.provider_call_id != event.provider_call_id:
                raise ValueError("status callback does not match the active call")
            updated = apply_status_event(self._call, event)
            if self._idempotency_key is None or self._request_fingerprint is None:
                raise RuntimeError("outbound attempt persistence cursor is missing")
            await self._attempt_store.complete(
                self._idempotency_key,
                self._request_fingerprint,
                updated,
                event.observed_at,
            )
            self._call = updated

    def realtime_session(self, binding: MediaBinding) -> RealtimeSessionRequest:
        if binding != self._binding:
            raise ValueError("media binding is not active")
        return build_telephony_realtime_session(self._settings)

    async def delegate_tool(
        self,
        binding: MediaBinding,
        event: RealtimeToolCallRequested,
        idempotency_key: str,
    ) -> Mapping[str, object]:
        if binding != self._binding:
            raise ValueError("media binding is not active")
        return await self._tools.execute(event, idempotency_key)

    async def stream_finished(self, binding: MediaBinding, outcome: str) -> None:
        del outcome
        async with self._lock:
            if binding == self._binding:
                self._stream_claimed = False

    async def aclose(self) -> None:
        dispose = getattr(self._engine, "dispose", None)
        if dispose is not None:
            await dispose()


class _UtcClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def create_live_telephony_application(
    settings: Settings,
    contracts: ContractService,
    client: httpx.AsyncClient,
) -> LiveTelephonyApplication:
    database_url = settings.database_url.get_secret_value()
    if not database_url:
        raise RuntimeError("database configuration is required")
    account_sid = settings.twilio_account_sid.get_secret_value()
    twilio_config = TwilioOutboundCallConfig(
        account_sid=account_sid,
        api_key_sid=settings.twilio_api_key_sid.get_secret_value(),
        api_key_secret=settings.twilio_api_key_secret.get_secret_value(),
        from_e164=settings.twilio_from_e164.get_secret_value(),
        instruction_url=f"{settings.twilio_public_base_url}/v1/telephony/twilio/voice",
        status_callback_url=f"{settings.twilio_public_base_url}/v1/telephony/twilio/status",
    )
    allowlist = TwilioDestinationAllowlist(settings.twilio_destination_allowlist)
    realtime = OpenAIRealtimeGateway(
        OpenAIRealtimeConfig(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.openai_realtime_model,
        )
    )
    build_telephony_realtime_session(settings)
    engine = create_database_engine(DatabaseConfig(url=database_url))
    sessions = create_session_factory(engine)
    attempt_store = SqlAlchemyOutboundCallAttemptStore(sessions)
    gateway = TwilioOutboundCallGateway(
        client,
        twilio_config,
        allowlist,
        attempt_store,
        _UtcClock(),
    )
    return LiveTelephonyApplication(
        settings=settings,
        contracts=contracts,
        gateway=gateway,
        realtime_gateway=realtime,
        attempt_store=attempt_store,
        engine=engine,
    )
