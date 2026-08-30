"""Thin API orchestration over Phase 18 telephony and Realtime contracts."""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Request, WebSocket
from yuno_backend.database import DatabaseConfig, create_database_engine, create_session_factory
from yuno_backend.integrations.openai import OpenAIRealtimeConfig, OpenAIRealtimeGateway
from yuno_backend.integrations.twilio import (
    SqlAlchemyTwilioExistingCallResolver,
    SqlAlchemyTwilioHandoffBindingStore,
    TwilioDestinationAllowlist,
    TwilioHandoffStatusCallback,
    TwilioHumanHandoffConfig,
    TwilioHumanHandoffGateway,
    TwilioOutboundCallConfig,
    TwilioOutboundCallGateway,
)
from yuno_backend.volta.persistence import (
    SqlAlchemyHumanHandoffRepository,
    SqlAlchemyOperationUnitOfWork,
    SqlAlchemyOutboundCallAttemptStore,
)
from yuno_backend.volta.realtime import (
    RealtimeGateway,
    RealtimeSessionRequest,
    RealtimeToolCallRequested,
)
from yuno_backend.volta.telephony import (
    AIAuthorityFence,
    HumanHandoff,
    HumanHandoffAudit,
    HumanHandoffCommand,
    HumanHandoffReadiness,
    HumanHandoffService,
    HumanHandoffStatusEvent,
    AcceptInboundCallInput,
    CompleteInboundRecoveryInput,
    FailInboundCallInput,
    InboundCallApplication,
    InboundCallError,
    OutboundCall,
    OutboundCallAuthorizationError,
    OutboundCallGateway,
    OutboundCallIdempotencyConflict,
    OutboundCallRequest,
    OutboundCallStatusEvent,
    RecordInboundConsentInput,
    StartInboundStreamInput,
    apply_status_event,
    outbound_call_request_fingerprint,
)
from yuno_backend.volta.text_slice.demo import create_demo_evidence_storage

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
    inbound: bool = False
    correlation_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class StreamEvidence:
    audio: bytes = field(repr=False)
    audio_start_ms: int
    item_id: str
    event_id: str
    correlation_id: UUID


class TelephonyApplication(Protocol):
    realtime_gateway: RealtimeGateway
    twilio_account_sid: str

    async def create_outbound_call(self, request: OutboundCallRequest) -> OutboundCall: ...

    async def request_handoff(self, command: HumanHandoffCommand) -> HumanHandoff: ...

    async def get_handoff_readiness(self, call_id: UUID) -> HumanHandoffReadiness: ...

    async def get_handoff(self, call_id: UUID, handoff_id: UUID) -> HumanHandoff: ...

    async def observe_handoff(self, event: HumanHandoffStatusEvent) -> HumanHandoff: ...

    async def map_handoff_status_callback(
        self, callback: TwilioHandoffStatusCallback
    ) -> HumanHandoffStatusEvent: ...

    async def ensure_ai_speech_allowed(self, call_id: UUID) -> None: ...

    async def wait_for_ai_authority_revoked(self, call_id: UUID) -> None: ...

    async def binding_for_voice(self, provider_call_id: str) -> MediaBinding | None: ...

    async def accept_inbound_call(
        self, caller_label: str, provider_call_id: str, correlation_id: UUID
    ) -> MediaBinding: ...

    async def record_inbound_consent(
        self, caller_label: str, provider_call_id: str, correlation_id: UUID
    ) -> MediaBinding: ...

    async def binding_for_stream(
        self, stream_token: str, provider_call_id: str, provider_stream_id: str
    ) -> MediaBinding | None: ...

    async def observe_status(self, event: OutboundCallStatusEvent) -> None: ...

    def realtime_session(self, binding: MediaBinding) -> RealtimeSessionRequest: ...

    async def delegate_tool(
        self,
        binding: MediaBinding,
        event: RealtimeToolCallRequested,
        idempotency_key: str,
    ) -> Mapping[str, object]: ...

    async def stream_finished(
        self,
        binding: MediaBinding,
        outcome: str,
        evidence: StreamEvidence | None = None,
    ) -> None: ...

    async def aclose(self) -> None: ...


class UnimplementedTelephonyApplication:
    """Fail-closed placeholder until provider adapters are configured."""

    twilio_account_sid = ""
    realtime_gateway: RealtimeGateway

    async def create_outbound_call(self, request: OutboundCallRequest) -> OutboundCall:
        del request
        raise RuntimeError("telephony application is not configured")

    async def request_handoff(self, command: HumanHandoffCommand) -> HumanHandoff:
        del command
        raise RuntimeError("telephony application is not configured")

    async def get_handoff_readiness(self, call_id: UUID) -> HumanHandoffReadiness:
        del call_id
        raise RuntimeError("telephony application is not configured")

    async def get_handoff(self, call_id: UUID, handoff_id: UUID) -> HumanHandoff:
        del call_id, handoff_id
        raise RuntimeError("telephony application is not configured")

    async def observe_handoff(self, event: HumanHandoffStatusEvent) -> HumanHandoff:
        del event
        raise RuntimeError("telephony application is not configured")

    async def map_handoff_status_callback(
        self, callback: TwilioHandoffStatusCallback
    ) -> HumanHandoffStatusEvent:
        del callback
        raise RuntimeError("telephony application is not configured")

    async def ensure_ai_speech_allowed(self, call_id: UUID) -> None:
        del call_id
        raise RuntimeError("telephony application is not configured")

    async def wait_for_ai_authority_revoked(self, call_id: UUID) -> None:
        del call_id
        await asyncio.Event().wait()

    async def binding_for_voice(self, provider_call_id: str) -> MediaBinding | None:
        del provider_call_id
        return None

    async def accept_inbound_call(
        self, caller_label: str, provider_call_id: str, correlation_id: UUID
    ) -> MediaBinding:
        del caller_label, provider_call_id, correlation_id
        raise RuntimeError("telephony application is not configured")

    async def record_inbound_consent(
        self, caller_label: str, provider_call_id: str, correlation_id: UUID
    ) -> MediaBinding:
        del caller_label, provider_call_id, correlation_id
        raise RuntimeError("telephony application is not configured")

    async def binding_for_stream(
        self, stream_token: str, provider_call_id: str, provider_stream_id: str
    ) -> MediaBinding | None:
        del stream_token, provider_call_id, provider_stream_id
        return None

    async def observe_status(self, event: OutboundCallStatusEvent) -> None:
        del event
        raise RuntimeError("telephony application is not configured")

    async def aclose(self) -> None:
        return None


def _get_telephony_application(application: FastAPI) -> TelephonyApplication:
    service = getattr(application.state, "telephony_application", None)
    if service is None:
        from app.openai_client import get_openai_http_client
        from app.volta_text_service import create_volta_text_contract_service

        contracts = getattr(application.state, "contract_service", None)
        if contracts is None:
            contracts = create_volta_text_contract_service(
                application.state.settings,
                http_client=get_openai_http_client(application),
            )
            application.state.contract_service = contracts
        try:
            service = create_live_telephony_application(
                application.state.settings,
                contracts,
                get_openai_http_client(application),
            )
        except (RuntimeError, ValueError):
            service = UnimplementedTelephonyApplication()
        application.state.telephony_application = service
    return service


def get_telephony_application(request: Request) -> TelephonyApplication:
    return _get_telephony_application(request.app)


def get_websocket_telephony_application(websocket: WebSocket) -> TelephonyApplication:
    return _get_telephony_application(websocket.app)


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


class _HandoffStatusMapper(Protocol):
    async def map_status_callback(
        self, callback: TwilioHandoffStatusCallback
    ) -> HumanHandoffStatusEvent: ...


class _LiveHandoffAudit(HumanHandoffAudit):
    """Keep only safe provider-neutral audit evidence in the demo runtime."""

    def __init__(self, clear_pending_audio: Callable[[UUID], Awaitable[None]]) -> None:
        self.events: list[tuple[str, UUID, UUID, str]] = []
        self._clear_pending_audio = clear_pending_audio

    async def handoff_requested(self, handoff: HumanHandoff, command: HumanHandoffCommand) -> None:
        del command
        await self._clear_pending_audio(handoff.call_id)
        self.events.append(
            ("handoff.requested", handoff.call_id, handoff.handoff_id, handoff.status.value)
        )

    async def handoff_outcome(self, handoff: HumanHandoff) -> None:
        self.events.append(
            ("handoff.outcome", handoff.call_id, handoff.handoff_id, handoff.status.value)
        )


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
        inbound_application: InboundCallApplication | None = None,
        engine: object,
    ) -> None:
        self._settings = settings
        self._contracts = contracts
        self._gateway = gateway
        self.realtime_gateway = realtime_gateway
        self._attempt_store = attempt_store
        self._inbound_application = inbound_application
        self.twilio_account_sid = settings.twilio_account_sid.get_secret_value()
        self._engine = engine
        self._binding: MediaBinding | None = None
        self._call: OutboundCall | None = None
        self._stream_claimed = False
        self._stream_consumed = False
        self._idempotency_key: str | None = None
        self._request_fingerprint: str | None = None
        self._lock = asyncio.Lock()
        self._inbound_bindings: dict[str, MediaBinding] = {}
        self._tools = VoltaToolDelegator(contracts)
        self._handoff_service: HumanHandoffService | None = None
        self._handoff_status_mapper: _HandoffStatusMapper | None = None
        self._authority_fence: AIAuthorityFence | None = None
        self._authority_events: dict[UUID, asyncio.Event] = {}

    def configure_handoff(
        self,
        service: HumanHandoffService,
        status_mapper: _HandoffStatusMapper,
        authority_fence: AIAuthorityFence,
        authority_events: dict[UUID, asyncio.Event],
    ) -> None:
        self._handoff_service = service
        self._handoff_status_mapper = status_mapper
        self._authority_fence = authority_fence
        self._authority_events = authority_events

    def _require_handoff_service(self) -> HumanHandoffService:
        if self._handoff_service is None:
            raise RuntimeError("human handoff is not configured")
        return self._handoff_service

    async def request_handoff(self, command: HumanHandoffCommand) -> HumanHandoff:
        return await self._require_handoff_service().request_handoff(command)

    async def get_handoff_readiness(self, call_id: UUID) -> HumanHandoffReadiness:
        return await self._require_handoff_service().get_handoff_readiness(call_id)

    async def get_handoff(self, call_id: UUID, handoff_id: UUID) -> HumanHandoff:
        return await self._require_handoff_service().get_handoff(call_id, handoff_id)

    async def observe_handoff(self, event: HumanHandoffStatusEvent) -> HumanHandoff:
        return await self._require_handoff_service().observe_handoff(event)

    async def map_handoff_status_callback(
        self, callback: TwilioHandoffStatusCallback
    ) -> HumanHandoffStatusEvent:
        if self._handoff_status_mapper is None:
            raise RuntimeError("human handoff callback mapping is not configured")
        return await self._handoff_status_mapper.map_status_callback(callback)

    async def ensure_ai_speech_allowed(self, call_id: UUID) -> None:
        if self._authority_fence is not None:
            await self._authority_fence.ensure_speech_allowed(call_id)

    async def wait_for_ai_authority_revoked(self, call_id: UUID) -> None:
        event = self._authority_events.setdefault(call_id, asyncio.Event())
        await event.wait()

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
                    raise OutboundCallIdempotencyConflict(call_session_id=request.call_session_id)
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

    async def accept_inbound_call(
        self, caller_label: str, provider_call_id: str, correlation_id: UUID
    ) -> MediaBinding:
        if self._inbound_application is None:
            raise RuntimeError("inbound telephony is not configured")
        async with self._lock:
            existing = self._inbound_bindings.get(provider_call_id)
        accepted = await self._inbound_application.accept_inbound_call(
            AcceptInboundCallInput(
                caller_label=caller_label,
                provider_call_id=provider_call_id,
                correlation_id=correlation_id,
            )
        )
        binding_correlation_id = (
            existing.correlation_id
            if existing is not None and existing.correlation_id is not None
            else correlation_id
        )
        binding = MediaBinding(
            operation_id=accepted.operation_id,
            call_session_id=accepted.call_id,
            provider_call_id=accepted.provider_call_id,
            stream_token=accepted.stream_binding,
            account_sid=self.twilio_account_sid,
            inbound=True,
            correlation_id=binding_correlation_id,
        )
        async with self._lock:
            self._inbound_bindings[provider_call_id] = binding
        return binding

    async def record_inbound_consent(
        self, caller_label: str, provider_call_id: str, correlation_id: UUID
    ) -> MediaBinding:
        if self._inbound_application is None:
            raise RuntimeError("inbound telephony is not configured")
        async with self._lock:
            existing = self._inbound_bindings.get(provider_call_id)
        accepted = await self._inbound_application.accept_inbound_call(
            AcceptInboundCallInput(
                caller_label=caller_label,
                provider_call_id=provider_call_id,
                correlation_id=correlation_id,
            )
        )
        binding = MediaBinding(
            operation_id=accepted.operation_id,
            call_session_id=accepted.call_id,
            provider_call_id=accepted.provider_call_id,
            stream_token=accepted.stream_binding,
            account_sid=self.twilio_account_sid,
            inbound=True,
            correlation_id=(
                existing.correlation_id
                if existing is not None and existing.correlation_id is not None
                else correlation_id
            ),
        )
        await self._inbound_application.record_inbound_consent(
            RecordInboundConsentInput(
                provider_call_id=provider_call_id,
                stream_binding=binding.stream_token,
            )
        )
        async with self._lock:
            self._inbound_bindings[provider_call_id] = binding
        return binding

    async def binding_for_stream(
        self, stream_token: str, provider_call_id: str, provider_stream_id: str
    ) -> MediaBinding | None:
        async with self._lock:
            if self._inbound_application is not None:
                try:
                    attempt = await self._inbound_application.start_inbound_stream(
                        StartInboundStreamInput(
                            provider_call_id=provider_call_id,
                            stream_binding=stream_token,
                            provider_stream_id=provider_stream_id,
                        )
                    )
                except InboundCallError:
                    pass
                else:
                    binding = MediaBinding(
                        operation_id=attempt.operation_id,
                        call_session_id=attempt.call_id,
                        provider_call_id=attempt.provider_call_id,
                        stream_token=stream_token,
                        account_sid=self.twilio_account_sid,
                        inbound=True,
                        correlation_id=attempt.correlation_id,
                    )
                    self._inbound_bindings[provider_call_id] = binding
                    return binding
            if (
                self._binding is None
                or not secrets.compare_digest(self._binding.stream_token, stream_token)
                or self._binding.provider_call_id != provider_call_id
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
        if binding.inbound:
            if self._inbound_bindings.get(binding.provider_call_id) != binding:
                raise ValueError("media binding is not active")
            return replace(
                build_telephony_realtime_session(self._settings),
                instructions=(
                    "You are Volta handling an authorized synthetic driver-delay call. "
                    "Listen and acknowledge the update without negotiating, selecting terms, "
                    "or invoking tools. The server applies the fixed recovery deterministically."
                ),
                tools=(),
            )
        if binding != self._binding:
            raise ValueError("media binding is not active")
        return build_telephony_realtime_session(self._settings)

    async def delegate_tool(
        self,
        binding: MediaBinding,
        event: RealtimeToolCallRequested,
        idempotency_key: str,
    ) -> Mapping[str, object]:
        if binding.inbound:
            raise ValueError("inbound Realtime tools are not authorized")
        if binding != self._binding:
            raise ValueError("media binding is not active")
        if self._authority_fence is not None:
            await self._authority_fence.ensure_commitment_allowed(binding.call_session_id)
        return await self._tools.execute(event, idempotency_key)

    async def stream_finished(
        self,
        binding: MediaBinding,
        outcome: str,
        evidence: StreamEvidence | None = None,
    ) -> None:
        if binding.inbound and self._inbound_application is not None:
            if outcome == "COMPLETED" and evidence is not None:
                await self._inbound_application.complete_inbound_recovery(
                    CompleteInboundRecoveryInput(
                        provider_call_id=binding.provider_call_id,
                        post_consent_audio=evidence.audio,
                        audio_start_ms=evidence.audio_start_ms,
                        item_id=evidence.item_id,
                        event_id=evidence.event_id,
                        correlation_id=evidence.correlation_id,
                    )
                )
            else:
                await self._inbound_application.fail_inbound_call(
                    FailInboundCallInput(
                        provider_call_id=binding.provider_call_id,
                        reason_code=outcome,
                    )
                )
        async with self._lock:
            if binding == self._binding:
                self._stream_claimed = False
            if binding.inbound:
                self._inbound_bindings.pop(binding.provider_call_id, None)

    async def aclose(self) -> None:
        dispose = getattr(self._engine, "dispose", None)
        if dispose is not None:
            await dispose()


class _UtcClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class _UuidGenerator:
    def new_id(self) -> UUID:
        return uuid4()


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
    inbound_application = InboundCallApplication(
        lambda: SqlAlchemyOperationUnitOfWork(sessions),
        create_demo_evidence_storage(settings.volta_evidence_storage_path),
        _UtcClock(),
        _UuidGenerator(),
    )
    gateway = TwilioOutboundCallGateway(
        client,
        twilio_config,
        allowlist,
        attempt_store,
        _UtcClock(),
    )
    application = LiveTelephonyApplication(
        settings=settings,
        contracts=contracts,
        gateway=gateway,
        realtime_gateway=realtime,
        attempt_store=attempt_store,
        inbound_application=inbound_application,
        engine=engine,
    )
    authority_events: dict[UUID, asyncio.Event] = {}

    async def clear_pending_audio(call_id: UUID) -> None:
        authority_events.setdefault(call_id, asyncio.Event()).set()

    repository = SqlAlchemyHumanHandoffRepository(
        sessions,
        allowed_destination_labels=frozenset(settings.twilio_destination_allowlist),
    )
    handoff_gateway = TwilioHumanHandoffGateway(
        client,
        TwilioHumanHandoffConfig(
            account_sid=account_sid,
            api_key_sid=settings.twilio_api_key_sid.get_secret_value(),
            api_key_secret=settings.twilio_api_key_secret.get_secret_value(),
            coordinator_caller_id_e164=settings.twilio_from_e164.get_secret_value(),
            status_callback_url=(
                f"{settings.twilio_public_base_url}/v1/telephony/twilio/handoff-status"
            ),
        ),
        allowlist,
        SqlAlchemyTwilioExistingCallResolver(sessions),
        SqlAlchemyTwilioHandoffBindingStore(sessions),
    )
    handoff_service = HumanHandoffService(
        repository,
        handoff_gateway,
        _LiveHandoffAudit(clear_pending_audio),
        _UtcClock(),
        repository,
    )
    application.configure_handoff(
        handoff_service,
        handoff_gateway,
        repository,
        authority_events,
    )
    return application
