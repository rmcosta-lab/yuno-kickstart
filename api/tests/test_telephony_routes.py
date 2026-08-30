"""Focused Phase 19 outbound-call and Twilio ingress tests."""

import asyncio
import base64
import json
import struct
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from urllib.parse import urlencode
from uuid import UUID

import httpx
import pytest
from app.config import Settings
from app.contract_service import ContractResult, ContractServiceError
from app.main import create_app
from app.schemas.errors import ApiErrorCode
from app.telephony.bridge import bridge_media_stream, tool_idempotency_key
from app.telephony.media import pcm24_to_twilio_payload, twilio_payload_to_pcm24
from app.telephony.service import (
    LiveTelephonyApplication,
    MediaBinding,
    StreamEvidence,
    VoltaToolDelegator,
    _OutboundCallCapacityError,
    create_live_telephony_application,
)
from app.telephony.signatures import twilio_signature
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from yuno_backend.integrations.twilio import TwilioHandoffStatusCallback
from yuno_backend.volta.realtime import (
    RealtimeAudioDelta,
    RealtimeSessionRequest,
    RealtimeSpeechStarted,
    RealtimeToolCallRequested,
    RealtimeToolOutput,
)
from yuno_backend.volta.telephony import (
    HumanHandoff,
    HumanHandoffAuthorityError,
    HumanHandoffCommand,
    HumanHandoffContext,
    HumanHandoffIdempotencyConflict,
    HumanHandoffNotFoundError,
    HumanHandoffReadiness,
    HumanHandoffStatus,
    HumanHandoffStatusEvent,
    InboundCallBinding,
    InboundCorrelationAmbiguous,
    OutboundCall,
    OutboundCallAuthorization,
    OutboundCallAuthorizationError,
    OutboundCallIdempotencyConflict,
    OutboundCallRequest,
    OutboundCallStatus,
    OutboundCallStatusEvent,
    RecordingMode,
)

TOKEN = "synthetic-twilio-token"
ACCOUNT_SID = "AC11111111111111111111111111111111"
CONFERENCE_SID = "CF66666666666666666666666666666666"
COORDINATOR_CALL_SID = "CA77777777777777777777777777777777"
BASE_URL = "https://telephony.example.test"
MEDIA_URL = "wss://telephony.example.test/v1/telephony/twilio/media"
OPERATION_ID = UUID("00000000-0000-4000-8000-000000000002")
CALL_SESSION_ID = UUID("00000000-0000-4000-8000-000000000005")
HANDOFF_ID = UUID("00000000-0000-4000-8000-000000000028")
BINDING = MediaBinding(
    operation_id=OPERATION_ID,
    call_session_id=CALL_SESSION_ID,
    provider_call_id="CA22222222222222222222222222222222",
    stream_token="binding-synthetic-001",
    account_sid=ACCOUNT_SID,
)
INBOUND_CALL_SID = "CA66666666666666666666666666666666"
INBOUND_STREAM_SID = "MZ77777777777777777777777777777777"
INBOUND_CALLER = "+15550003333"
INBOUND_DESTINATION = "+15550004444"
INBOUND_BINDING = MediaBinding(
    operation_id=OPERATION_ID,
    call_session_id=CALL_SESSION_ID,
    provider_call_id=INBOUND_CALL_SID,
    stream_token="binding-inbound-synthetic-001",
    account_sid=ACCOUNT_SID,
    inbound=True,
    correlation_id=UUID("00000000-0000-4000-8000-000000000026"),
)


class FakeRealtimeConnection:
    def __init__(self) -> None:
        self.audio: list[bytes] = []
        self.tool_outputs: list[RealtimeToolOutput] = []
        self.closed = False

    async def send_audio(self, chunk: bytes) -> None:
        self.audio.append(chunk)

    async def truncate_playback(self, truncation: object) -> None:
        del truncation

    async def send_tool_output(self, output: RealtimeToolOutput) -> None:
        self.tool_outputs.append(output)

    async def close(self) -> None:
        self.closed = True

    async def _events(self) -> AsyncIterator[object]:
        yield RealtimeSpeechStarted(event_id="evt-speech", item_id="item-speech", audio_start_ms=20)
        yield RealtimeAudioDelta(
            event_id="evt-audio",
            response_id="response-audio",
            item_id="item-audio",
            content_index=0,
            audio=b"\x00\x00" * 3 * 160,
        )
        yield RealtimeToolCallRequested(
            event_id="evt-tool",
            item_id="item-tool",
            call_id="call-tool-001",
            name="record_quote",
            arguments={"call_id": str(CALL_SESSION_ID), "amount_minor": 880000},
        )
        await asyncio.Event().wait()

    def events(self) -> AsyncIterator[object]:
        return self._events()


class FakeRealtimeGateway:
    def __init__(self) -> None:
        self.connection = FakeRealtimeConnection()
        self.requests: list[RealtimeSessionRequest] = []

    @asynccontextmanager
    async def connect(self, request: RealtimeSessionRequest):  # type: ignore[no-untyped-def]
        self.requests.append(request)
        try:
            yield self.connection
        finally:
            await self.connection.close()


class FakeTelephonyApplication:
    def __init__(self) -> None:
        self.twilio_account_sid = ACCOUNT_SID
        self.realtime_gateway = FakeRealtimeGateway()
        self.outbound_requests: list[OutboundCallRequest] = []
        self.status_events: list[OutboundCallStatusEvent] = []
        self.tool_calls: list[tuple[RealtimeToolCallRequested, str]] = []
        self.finished: list[tuple[MediaBinding, str]] = []
        self.handoff_commands: list[HumanHandoffCommand] = []
        self.handoff_events: list[HumanHandoffStatusEvent] = []
        self.handoff_callbacks: list[TwilioHandoffStatusCallback] = []
        self.handoff_audit: list[tuple[str, UUID, UUID]] = []
        self.handoff_correlation_id: UUID | None = None
        self.authority_revoked = asyncio.Event()
        self.speech_checks = 0
        self.ai_authority_fenced = False
        self.handoff = HumanHandoff(
            handoff_id=HANDOFF_ID,
            call_id=CALL_SESSION_ID,
            coordinator_destination_label="demo-coordinator",
            idempotency_key="handoff-synthetic-001",
            request_fingerprint="a" * 64,
            status=HumanHandoffStatus.CONNECTING,
            requested_at=datetime(2026, 8, 30, 12, 1, tzinfo=UTC),
            status_updated_at=datetime(2026, 8, 30, 12, 1, tzinfo=UTC),
            context=HumanHandoffContext(
                mandate_version=3,
                mandate_facts=("Maximum approved amount is bounded.",),
                eligible_quote_summaries=("Synthetic carrier quote is eligible.",),
                structured_call_brief=("Carrier requested pickup confirmation.",),
                call_status="IN_PROGRESS",
            ),
        )
        self.handoff_readiness = HumanHandoffReadiness(
            call_id=CALL_SESSION_ID,
            call_status_updated_at=datetime(2026, 8, 30, 11, 59, 59, tzinfo=UTC),
            context=self.handoff.context,
        )
        self.finished_evidence: list[StreamEvidence | None] = []
        self.inbound_accepts: list[tuple[str, str, UUID]] = []
        self.inbound_consents: list[str] = []
        self.inbound_consented = False

    async def create_outbound_call(self, request: OutboundCallRequest) -> OutboundCall:
        self.outbound_requests.append(request)
        return OutboundCall(
            call_session_id=request.call_session_id,
            provider_call_id=BINDING.provider_call_id,
            status=OutboundCallStatus.QUEUED,
            created_at=datetime(2026, 8, 30, 12, tzinfo=UTC),
        )

    async def request_handoff(self, command: HumanHandoffCommand) -> HumanHandoff:
        self.handoff_commands.append(command)
        self.handoff_correlation_id = command.correlation_id
        self.ai_authority_fenced = True
        self.authority_revoked.set()
        self.handoff_audit.append(
            ("HANDOFF_REQUESTED", self.handoff.handoff_id, command.correlation_id)
        )
        return self.handoff

    async def get_handoff_readiness(self, call_id: UUID) -> HumanHandoffReadiness:
        if call_id != self.handoff_readiness.call_id:
            raise HumanHandoffNotFoundError(call_id=call_id)
        return self.handoff_readiness

    async def get_handoff(self, call_id: UUID, handoff_id: UUID) -> HumanHandoff:
        if call_id != self.handoff.call_id or handoff_id != self.handoff.handoff_id:
            raise HumanHandoffNotFoundError(call_id=call_id)
        return self.handoff

    async def observe_handoff(self, event: HumanHandoffStatusEvent) -> HumanHandoff:
        self.handoff_events.append(event)
        previous = self.handoff
        if event.provider_event_id not in previous.processed_status_event_ids:
            self.handoff = replace(
                previous,
                status=event.status,
                status_updated_at=max(previous.status_updated_at, event.observed_at),
                last_status_event_id=event.provider_event_id,
                last_status_sequence_number=event.sequence_number,
                processed_status_event_ids=(
                    *previous.processed_status_event_ids,
                    event.provider_event_id,
                ),
            )
            if (
                event.status.is_terminal
                and not previous.status.is_terminal
                and self.handoff_correlation_id is not None
            ):
                self.handoff_audit.append(
                    (
                        f"HANDOFF_{event.status.value}",
                        self.handoff.handoff_id,
                        self.handoff_correlation_id,
                    )
                )
        return self.handoff

    async def map_handoff_status_callback(
        self, callback: TwilioHandoffStatusCallback
    ) -> HumanHandoffStatusEvent:
        self.handoff_callbacks.append(callback)
        joined = callback.participant_call_sid == COORDINATOR_CALL_SID
        return HumanHandoffStatusEvent(
            provider_event_id=callback.provider_event_id,
            handoff_id=HANDOFF_ID,
            call_id=CALL_SESSION_ID,
            status=(HumanHandoffStatus.JOINED if joined else HumanHandoffStatus.CONNECTING),
            sequence_number=callback.sequence_number,
            observed_at=callback.observed_at,
            remote_participant_present=True,
            coordinator_participant_present=joined,
        )

    async def ensure_ai_speech_allowed(self, call_id: UUID) -> None:
        assert call_id == CALL_SESSION_ID
        self.speech_checks += 1
        if self.ai_authority_fenced:
            from yuno_backend.volta.telephony import HumanHandoffAuthorityError

            raise HumanHandoffAuthorityError(call_id=call_id)

    async def wait_for_ai_authority_revoked(self, call_id: UUID) -> None:
        assert call_id == CALL_SESSION_ID
        await self.authority_revoked.wait()

    async def binding_for_voice(self, provider_call_id: str) -> MediaBinding | None:
        return BINDING if provider_call_id == BINDING.provider_call_id else None

    async def accept_inbound_call(
        self, caller_label: str, provider_call_id: str, correlation_id: UUID
    ) -> MediaBinding:
        self.inbound_accepts.append((caller_label, provider_call_id, correlation_id))
        return replace(INBOUND_BINDING, correlation_id=correlation_id)

    async def record_inbound_consent(
        self, caller_label: str, provider_call_id: str, correlation_id: UUID
    ) -> MediaBinding:
        assert caller_label == "synthetic-driver"
        assert provider_call_id == INBOUND_CALL_SID
        if not self.inbound_accepts:
            self.inbound_accepts.append((caller_label, provider_call_id, correlation_id))
        self.inbound_consents.append(provider_call_id)
        self.inbound_consented = True
        correlation_id = (
            self.inbound_accepts[-1][2] if self.inbound_accepts else INBOUND_BINDING.correlation_id
        )
        return replace(INBOUND_BINDING, correlation_id=correlation_id)

    async def binding_for_stream(
        self, stream_token: str, provider_call_id: str, provider_stream_id: str
    ) -> MediaBinding | None:
        if stream_token == INBOUND_BINDING.stream_token:
            if (
                not self.inbound_consented
                or provider_call_id != INBOUND_CALL_SID
                or provider_stream_id != INBOUND_STREAM_SID
            ):
                return None
            correlation_id = (
                self.inbound_accepts[-1][2]
                if self.inbound_accepts
                else INBOUND_BINDING.correlation_id
            )
            return replace(INBOUND_BINDING, correlation_id=correlation_id)
        assert provider_call_id == BINDING.provider_call_id
        assert provider_stream_id == "MZ33333333333333333333333333333333"
        return BINDING if stream_token == BINDING.stream_token else None

    async def observe_status(self, event: OutboundCallStatusEvent) -> None:
        self.status_events.append(event)

    def realtime_session(self, binding: MediaBinding) -> RealtimeSessionRequest:
        assert binding == BINDING or binding.inbound
        return RealtimeSessionRequest(
            instructions="Negotiate only within the approved mandate.",
            safety_identifier="a" * 64,
        )

    async def delegate_tool(
        self,
        binding: MediaBinding,
        event: RealtimeToolCallRequested,
        idempotency_key: str,
    ) -> Mapping[str, object]:
        assert binding == BINDING or binding.inbound
        self.tool_calls.append((event, idempotency_key))
        return {"accepted": True}

    async def stream_finished(
        self,
        binding: MediaBinding,
        outcome: str,
        evidence: StreamEvidence | None = None,
    ) -> None:
        self.finished.append((binding, outcome))
        self.finished_evidence.append(evidence)

    async def aclose(self) -> None:
        return None


def build_client(application: FakeTelephonyApplication | None = None) -> TestClient:
    app = create_app(
        Settings(
            app_env="test",
            volta_demo_bearer_token="synthetic-test-token",
            cors_origins=["http://localhost:3000"],
            twilio_auth_token=TOKEN,
            twilio_account_sid=ACCOUNT_SID,
            twilio_public_base_url=BASE_URL,
            twilio_media_ws_url=MEDIA_URL,
            twilio_inbound_caller_allowlist={"synthetic-driver": INBOUND_CALLER},
            twilio_inbound_destination_e164=INBOUND_DESTINATION,
        )
    )
    if application is not None:
        app.state.telephony_application = application
    return TestClient(app, raise_server_exceptions=False)


def signed_form(path: str, fields: dict[str, str]) -> tuple[dict[str, str], str]:
    return (
        {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Twilio-Signature": twilio_signature(f"{BASE_URL}{path}", fields, TOKEN),
        },
        urlencode(fields),
    )


def outbound_body() -> dict[str, object]:
    return {
        "call_session_id": str(CALL_SESSION_ID),
        "destination_label": "synthetic-carrier-one",
        "authorized_by": "coordinator-demo",
        "authorized_at": "2026-08-30T12:00:00Z",
        "ai_disclosure_required": True,
        "recording_mode": "DISABLED",
        "recording_consent_required": False,
    }


def handoff_body() -> dict[str, object]:
    return {
        "coordinator_destination_label": "demo-coordinator",
        "authorized_by": "coordinator-demo",
        "authorized_at": "2026-08-30T12:00:00Z",
        "expected_call_status_updated_at": "2026-08-30T11:59:59Z",
    }


def media_start(
    *,
    binding: str = BINDING.stream_token,
    call_sid: str = BINDING.provider_call_id,
    stream_sid: str = "MZ33333333333333333333333333333333",
) -> dict[str, object]:
    return {
        "event": "start",
        "sequenceNumber": "1",
        "streamSid": stream_sid,
        "start": {
            "accountSid": ACCOUNT_SID,
            "streamSid": stream_sid,
            "callSid": call_sid,
            "tracks": ["inbound"],
            "mediaFormat": {
                "encoding": "audio/x-mulaw",
                "sampleRate": 8000,
                "channels": 1,
            },
            "customParameters": {"binding": binding},
        },
    }


def send_media_preamble(websocket, *, binding: str = BINDING.stream_token) -> None:  # type: ignore[no-untyped-def]
    websocket.send_json({"event": "connected", "protocol": "Call", "version": "1.0.0"})
    websocket.send_json(media_start(binding=binding))


def receive_until_close(websocket) -> None:  # type: ignore[no-untyped-def]
    for _ in range(5):
        websocket.receive_text()
    raise AssertionError("WebSocket did not close within the bounded test exchange")


def test_outbound_call_requires_bearer_and_maps_provider_neutral_request() -> None:
    application = FakeTelephonyApplication()
    path = f"/v1/operations/{OPERATION_ID}/outbound-calls"
    with build_client(application) as client:
        rejected = client.post(path, json=outbound_body())
        accepted = client.post(
            path,
            headers={
                "Authorization": "Bearer synthetic-test-token",
                "Origin": "http://localhost:3000",
                "Idempotency-Key": "outbound-synthetic-001",
                "X-Request-ID": "outbound-request-001",
            },
            json=outbound_body(),
        )

    assert rejected.status_code == 401
    assert application.outbound_requests and len(application.outbound_requests) == 1
    request = application.outbound_requests[0]
    assert request.operation_id == OPERATION_ID
    assert request.destination_label == "synthetic-carrier-one"
    assert request.authorization.recording_mode.value == "DISABLED"
    assert accepted.status_code == 201
    assert accepted.json()["provider_call_id"] == BINDING.provider_call_id
    assert "synthetic-twilio-token" not in accepted.text


def test_outbound_same_request_replay_is_201_without_marker() -> None:
    application = FakeTelephonyApplication()
    path = f"/v1/operations/{OPERATION_ID}/outbound-calls"
    headers = {
        "Authorization": "Bearer synthetic-test-token",
        "Origin": "http://localhost:3000",
        "Idempotency-Key": "outbound-synthetic-replay-001",
    }
    with build_client(application) as client:
        created = client.post(path, headers=headers, json=outbound_body())
        replayed = client.post(path, headers=headers, json=outbound_body())

    assert created.status_code == replayed.status_code == 201
    assert created.json() == replayed.json()
    assert "replayed" not in replayed.json()
    assert "idempotency-replayed" not in replayed.headers


def test_outbound_capacity_maps_to_existing_state_conflict() -> None:
    class CapacityApplication(FakeTelephonyApplication):
        async def create_outbound_call(self, request: OutboundCallRequest) -> OutboundCall:
            del request
            raise _OutboundCallCapacityError

    path = f"/v1/operations/{OPERATION_ID}/outbound-calls"
    headers = {
        "Authorization": "Bearer synthetic-test-token",
        "Origin": "http://localhost:3000",
        "Idempotency-Key": "outbound-capacity-001",
    }
    with build_client(CapacityApplication()) as client:
        response = client.post(path, headers=headers, json=outbound_body())

    assert response.status_code == 409
    assert response.json()["code"] == ApiErrorCode.STATE_CONFLICT


def test_outbound_origin_rejection_consumes_no_quota_or_gateway_io() -> None:
    application = FakeTelephonyApplication()
    path = f"/v1/operations/{OPERATION_ID}/outbound-calls"
    headers = {
        "Authorization": "Bearer synthetic-test-token",
        "Idempotency-Key": "outbound-origin-rejected-001",
    }
    with build_client(application) as client:
        missing = client.post(path, headers=headers, json=outbound_body())
        invalid = client.post(
            path,
            headers={**headers, "Origin": "https://untrusted.example"},
            json=outbound_body(),
        )
        identity_count = client.app.state.mutation_rate_limiter.identity_count

    assert missing.status_code == invalid.status_code == 403
    assert identity_count == 0
    assert application.outbound_requests == []


def test_outbound_openapi_422_uses_safe_error_envelope() -> None:
    with build_client() as client:
        operation = client.app.openapi()["paths"]["/v1/operations/{operation_id}/outbound-calls"][
            "post"
        ]
    assert operation["responses"]["422"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ApiErrorResponse"
    }


class MissingOperationApplication(FakeTelephonyApplication):
    async def create_outbound_call(self, request: OutboundCallRequest) -> OutboundCall:
        del request
        raise ContractServiceError(
            status_code=404,
            code=ApiErrorCode.RESOURCE_NOT_FOUND,
            message="The operation was not found.",
        )


def test_outbound_preflight_preserves_typed_contract_error() -> None:
    path = f"/v1/operations/{OPERATION_ID}/outbound-calls"
    with build_client(MissingOperationApplication()) as client:
        response = client.post(
            path,
            headers={
                "Authorization": "Bearer synthetic-test-token",
                "Origin": "http://localhost:3000",
                "Idempotency-Key": "outbound-missing-operation-001",
            },
            json=outbound_body(),
        )

    assert response.status_code == 404
    assert response.json()["code"] == "RESOURCE_NOT_FOUND"
    assert response.json()["message"] == "The operation was not found."


def test_handoff_requires_browser_boundaries_and_maps_typed_command() -> None:
    application = FakeTelephonyApplication()
    path = f"/v1/calls/{CALL_SESSION_ID}/handoffs"
    headers = {
        "Authorization": "Bearer synthetic-test-token",
        "Origin": "http://localhost:3000",
        "Idempotency-Key": "handoff-synthetic-001",
        "X-Request-ID": "handoff-request-001",
    }
    with build_client(application) as client:
        unauthenticated = client.post(path, json=handoff_body())
        missing_origin = client.post(
            path,
            headers={key: value for key, value in headers.items() if key != "Origin"},
            json=handoff_body(),
        )
        accepted = client.post(path, headers=headers, json=handoff_body())

    assert unauthenticated.status_code == 401
    assert missing_origin.status_code == 403
    assert accepted.status_code == 202
    assert len(application.handoff_commands) == 1
    command = application.handoff_commands[0]
    assert command.call_id == CALL_SESSION_ID
    assert command.idempotency_key == "handoff-synthetic-001"
    assert command.coordinator_destination_label == "demo-coordinator"
    assert command.correlation_id.version == 5
    assert accepted.json() == {
        "handoff_id": str(HANDOFF_ID),
        "call_id": str(CALL_SESSION_ID),
        "status": "CONNECTING",
        "requested_at": "2026-08-30T12:01:00Z",
        "status_updated_at": "2026-08-30T12:01:00Z",
        "context": {
            "mandate_version": 3,
            "mandate_facts": ["Maximum approved amount is bounded."],
            "eligible_quote_summaries": ["Synthetic carrier quote is eligible."],
            "structured_call_brief": ["Carrier requested pickup confirmation."],
            "call_status": "IN_PROGRESS",
        },
    }
    for forbidden in (
        "idempotency_key",
        "request_fingerprint",
        "coordinator_destination_label",
        "provider",
        "transcript",
    ):
        assert forbidden not in accepted.text.lower()


def test_handoff_readiness_is_authenticated_bounded_and_read_only() -> None:
    application = FakeTelephonyApplication()
    path = f"/v1/calls/{CALL_SESSION_ID}/handoff-readiness"
    with build_client(application) as client:
        unauthenticated = client.get(path)
        missing_origin = client.get(path, headers={"Authorization": "Bearer synthetic-test-token"})
        found = client.get(
            path,
            headers={
                "Authorization": "Bearer synthetic-test-token",
                "Origin": "http://localhost:3000",
            },
        )

    assert unauthenticated.status_code == 401
    assert missing_origin.status_code == 403
    assert found.status_code == 200
    assert found.json() == {
        "call_id": str(CALL_SESSION_ID),
        "call_status_updated_at": "2026-08-30T11:59:59Z",
        "context": {
            "mandate_version": 3,
            "mandate_facts": ["Maximum approved amount is bounded."],
            "eligible_quote_summaries": ["Synthetic carrier quote is eligible."],
            "structured_call_brief": ["Carrier requested pickup confirmation."],
            "call_status": "IN_PROGRESS",
        },
    }
    assert application.handoff_commands == []
    for forbidden in ("provider", "call_sid", "e164", "transcript", "idempotency_key"):
        assert forbidden not in found.text.lower()


class NonLiveHandoffReadinessApplication(FakeTelephonyApplication):
    async def get_handoff_readiness(self, call_id: UUID) -> HumanHandoffReadiness:
        from yuno_backend.volta.telephony import HumanHandoffCallNotLiveError

        raise HumanHandoffCallNotLiveError(call_id=call_id)


class UnavailableHandoffReadinessApplication(FakeTelephonyApplication):
    async def get_handoff_readiness(self, call_id: UUID) -> HumanHandoffReadiness:
        del call_id
        raise RuntimeError("database password=private participant=private-destination")


def test_handoff_readiness_maps_unknown_and_non_live_calls_safely() -> None:
    headers = {
        "Authorization": "Bearer synthetic-test-token",
        "Origin": "http://localhost:3000",
    }
    missing_id = UUID("00000000-0000-4000-8000-000000000099")
    with build_client(FakeTelephonyApplication()) as client:
        missing = client.get(f"/v1/calls/{missing_id}/handoff-readiness", headers=headers)
    with build_client(NonLiveHandoffReadinessApplication()) as client:
        non_live = client.get(f"/v1/calls/{CALL_SESSION_ID}/handoff-readiness", headers=headers)

    assert missing.status_code == 404
    assert missing.json()["code"] == "RESOURCE_NOT_FOUND"
    assert non_live.status_code == 409
    assert non_live.json()["code"] == "STATE_CONFLICT"


def test_handoff_readiness_maps_durable_failure_to_safe_503() -> None:
    with build_client(UnavailableHandoffReadinessApplication()) as client:
        response = client.get(
            f"/v1/calls/{CALL_SESSION_ID}/handoff-readiness",
            headers={
                "Authorization": "Bearer synthetic-test-token",
                "Origin": "http://localhost:3000",
            },
        )

    assert response.status_code == 503
    assert response.json()["code"] == "TELEPHONY_UNAVAILABLE"
    assert response.json()["message"] == "Telephony is not configured."
    assert "password" not in response.text.lower()
    assert "private-destination" not in response.text


def test_handoff_origin_rejection_consumes_no_rate_limit_quota() -> None:
    application = FakeTelephonyApplication()
    path = f"/v1/calls/{CALL_SESSION_ID}/handoffs"
    with build_client(application) as client:
        response = client.post(
            path,
            headers={
                "Authorization": "Bearer synthetic-test-token",
                "Idempotency-Key": "handoff-origin-rejected-001",
            },
            json=handoff_body(),
        )
        identity_count = client.app.state.mutation_rate_limiter.identity_count

    assert response.status_code == 403
    assert identity_count == 0
    assert application.handoff_commands == []


class ConflictingHandoffApplication(FakeTelephonyApplication):
    async def request_handoff(self, command: HumanHandoffCommand) -> HumanHandoff:
        raise HumanHandoffIdempotencyConflict(call_id=command.call_id)


def test_handoff_maps_idempotency_conflict_without_sensitive_details() -> None:
    path = f"/v1/calls/{CALL_SESSION_ID}/handoffs"
    with build_client(ConflictingHandoffApplication()) as client:
        response = client.post(
            path,
            headers={
                "Authorization": "Bearer synthetic-test-token",
                "Origin": "http://localhost:3000",
                "Idempotency-Key": "handoff-conflicting-001",
            },
            json=handoff_body(),
        )

    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert str(CALL_SESSION_ID) not in response.text


def test_handoff_read_is_bounded_and_has_no_provider_io() -> None:
    application = FakeTelephonyApplication()
    headers = {
        "Authorization": "Bearer synthetic-test-token",
        "Origin": "http://localhost:3000",
    }
    with build_client(application) as client:
        found = client.get(f"/v1/calls/{CALL_SESSION_ID}/handoffs/{HANDOFF_ID}", headers=headers)
        missing = client.get(
            f"/v1/calls/{CALL_SESSION_ID}/handoffs/00000000-0000-4000-8000-000000000099",
            headers=headers,
        )

    assert found.status_code == 200
    assert found.json()["status"] == "CONNECTING"
    assert missing.status_code == 404
    assert missing.json()["code"] == "RESOURCE_NOT_FOUND"


def test_handoff_openapi_contract_is_stable_and_callback_is_private() -> None:
    with build_client() as client:
        schema = client.app.openapi()
    create = schema["paths"]["/v1/calls/{call_id}/handoffs"]["post"]
    read = schema["paths"]["/v1/calls/{call_id}/handoffs/{handoff_id}"]["get"]
    readiness = schema["paths"]["/v1/calls/{call_id}/handoff-readiness"]["get"]
    assert create["operationId"] == "request_human_handoff"
    assert read["operationId"] == "get_human_handoff"
    assert readiness["operationId"] == "get_human_handoff_readiness"
    assert set(create["responses"]) >= {
        "202",
        "401",
        "403",
        "404",
        "409",
        "422",
        "429",
        "502",
        "503",
        "504",
    }
    assert set(read["responses"]) >= {"200", "401", "403", "404"}
    assert set(readiness["responses"]) >= {"200", "401", "403", "404", "409"}
    assert "503" in readiness["responses"]
    assert "/v1/telephony/twilio/handoff-status" not in schema["paths"]


def test_disclosure_and_consent_precede_media_stream() -> None:
    application = FakeTelephonyApplication()
    voice_fields = {"CallSid": BINDING.provider_call_id}
    voice_fields["AccountSid"] = ACCOUNT_SID
    voice_headers, voice_body = signed_form("/v1/telephony/twilio/voice", voice_fields)
    consent_fields = {**voice_fields, "Digits": "1"}
    consent_headers, consent_body = signed_form("/v1/telephony/twilio/consent", consent_fields)
    with build_client(application) as client:
        disclosure = client.post(
            "/v1/telephony/twilio/voice",
            headers=voice_headers,
            content=voice_body,
        )
        consent = client.post(
            "/v1/telephony/twilio/consent",
            headers=consent_headers,
            content=consent_body,
        )

    assert disclosure.status_code == 200
    assert "AI assistant" in disclosure.text
    assert 'timeout="15"' in disclosure.text
    assert "&lt;Stream" not in disclosure.text and "<Stream" not in disclosure.text
    assert MEDIA_URL in consent.text
    assert BINDING.stream_token in consent.text
    assert "synthetic-twilio-token" not in disclosure.text + consent.text


def test_twilio_http_ingress_rejects_missing_and_tampered_signatures() -> None:
    application = FakeTelephonyApplication()
    fields = {"CallSid": BINDING.provider_call_id, "AccountSid": ACCOUNT_SID}
    headers, body = signed_form("/v1/telephony/twilio/voice", fields)
    with build_client(application) as client:
        missing = client.post("/v1/telephony/twilio/voice", content=body)
        tampered = client.post(
            "/v1/telephony/twilio/voice",
            headers=headers,
            content=f"{body}&Digits=1",
        )

    assert missing.status_code == 403
    assert tampered.status_code == 403


def test_twilio_http_ingress_rejects_oversized_form_before_parsing() -> None:
    application = FakeTelephonyApplication()
    with build_client(application) as client:
        response = client.post(
            "/v1/telephony/twilio/voice",
            content=b"Field=" + b"x" * 65_537,
        )
    assert response.status_code == 403


def inbound_fields(**overrides: str) -> dict[str, str]:
    fields = {
        "AccountSid": ACCOUNT_SID,
        "CallSid": INBOUND_CALL_SID,
        "From": INBOUND_CALLER,
        "To": INBOUND_DESTINATION,
    }
    fields.update(overrides)
    return fields


def test_inbound_voice_validates_all_fields_then_returns_disclosure_gather() -> None:
    application = FakeTelephonyApplication()
    path = "/v1/telephony/twilio/inbound/voice"
    fields = inbound_fields(FutureParameter="future-value")
    headers, body = signed_form(path, fields)
    with build_client(application) as client:
        response = client.post(path, headers=headers, content=body)

    assert response.status_code == 200
    assert "artificial intelligence" in response.text
    assert "recorded for private demo evidence" in response.text
    assert "/v1/telephony/twilio/inbound/consent" in response.text
    assert "<Gather" in response.text
    assert "<Stream" not in response.text
    assert application.inbound_accepts[0][:2] == (
        "synthetic-driver",
        INBOUND_CALL_SID,
    )


def test_inbound_voice_fails_closed_for_signature_origin_and_identity_mismatch() -> None:
    application = FakeTelephonyApplication()
    path = "/v1/telephony/twilio/inbound/voice"
    fields = inbound_fields()
    headers, body = signed_form(path, fields)
    wrong_path_headers, _ = signed_form("/v1/telephony/twilio/voice", fields)
    wrong_destination = inbound_fields(To="+15550005555")
    wrong_destination_headers, wrong_destination_body = signed_form(path, wrong_destination)
    with build_client(application) as client:
        missing = client.post(path, content=body)
        wrong_origin = client.post(path, headers=wrong_path_headers, content=body)
        proxy_spoof = client.post(
            path,
            headers={
                **wrong_path_headers,
                "Forwarded": "proto=https;host=telephony.example.test",
                "X-Forwarded-Host": "telephony.example.test",
            },
            content=body,
        )
        identity_mismatch = client.post(
            path,
            headers=wrong_destination_headers,
            content=wrong_destination_body,
        )

    assert {
        missing.status_code,
        wrong_origin.status_code,
        proxy_spoof.status_code,
        identity_mismatch.status_code,
    } == {403}
    assert application.inbound_accepts == []


def test_inbound_rejection_precedes_live_application_and_storage_construction() -> None:
    path = "/v1/telephony/twilio/inbound/voice"
    with build_client() as client:
        response = client.post(
            path,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            content=urlencode(inbound_fields()),
        )
        constructed = hasattr(client.app.state, "telephony_application")

    assert response.status_code == 403
    assert constructed is False


def test_inbound_voice_rejects_duplicate_fields_after_full_signature_validation() -> None:
    application = FakeTelephonyApplication()
    path = "/v1/telephony/twilio/inbound/voice"
    pairs = list(inbound_fields().items()) + [("CallSid", INBOUND_CALL_SID)]
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Twilio-Signature": twilio_signature(f"{BASE_URL}{path}", pairs, TOKEN),
    }
    with build_client(application) as client:
        response = client.post(path, headers=headers, content=urlencode(pairs))

    assert response.status_code == 403
    assert application.inbound_accepts == []


def test_inbound_unallowlisted_caller_returns_safe_hangup_without_delegation() -> None:
    application = FakeTelephonyApplication()
    path = "/v1/telephony/twilio/inbound/voice"
    fields = inbound_fields(From="+15550006666")
    headers, body = signed_form(path, fields)
    with build_client(application) as client:
        response = client.post(path, headers=headers, content=body)

    assert response.status_code == 200
    assert "<Hangup" in response.text and "<Stream" not in response.text
    assert INBOUND_CALLER not in response.text
    assert application.inbound_accepts == []


class AmbiguousInboundApplication(FakeTelephonyApplication):
    async def accept_inbound_call(
        self, caller_label: str, provider_call_id: str, correlation_id: UUID
    ) -> MediaBinding:
        del caller_label, provider_call_id, correlation_id
        raise InboundCorrelationAmbiguous()


def test_inbound_correlation_failure_returns_only_safe_hangup_twiml() -> None:
    path = "/v1/telephony/twilio/inbound/voice"
    headers, body = signed_form(path, inbound_fields())
    with build_client(AmbiguousInboundApplication()) as client:
        response = client.post(path, headers=headers, content=body)

    assert response.status_code == 200
    assert response.text == "<Response><Hangup /></Response>"
    assert OPERATION_ID.hex not in response.text


def test_inbound_consent_is_durable_before_opaque_stream_instruction() -> None:
    application = FakeTelephonyApplication()
    voice_path = "/v1/telephony/twilio/inbound/voice"
    consent_path = "/v1/telephony/twilio/inbound/consent"
    voice_headers, voice_body = signed_form(voice_path, inbound_fields())
    consent_headers, consent_body = signed_form(consent_path, inbound_fields(Digits="1"))
    with build_client(application) as client:
        voice = client.post(voice_path, headers=voice_headers, content=voice_body)
        consent = client.post(consent_path, headers=consent_headers, content=consent_body)

    assert voice.status_code == consent.status_code == 200
    assert application.inbound_consents == [INBOUND_CALL_SID]
    assert MEDIA_URL in consent.text
    assert INBOUND_BINDING.stream_token in consent.text
    assert "<Connect" in consent.text and "<Stream" in consent.text


def test_inbound_refusal_emits_no_stream_and_does_not_record_consent() -> None:
    application = FakeTelephonyApplication()
    path = "/v1/telephony/twilio/inbound/consent"
    headers, body = signed_form(path, inbound_fields(Digits="2"))
    with build_client(application) as client:
        response = client.post(path, headers=headers, content=body)

    assert response.status_code == 200
    assert "<Hangup" in response.text and "<Stream" not in response.text
    assert application.inbound_consents == []


def test_inbound_provider_routes_remain_outside_openapi() -> None:
    with build_client() as client:
        paths = client.app.openapi()["paths"]
    assert "/v1/telephony/twilio/inbound/voice" not in paths
    assert "/v1/telephony/twilio/inbound/consent" not in paths


@pytest.mark.parametrize(
    ("provider_status", "expected_status"),
    [
        ("initiated", OutboundCallStatus.INITIATED),
        ("ringing", OutboundCallStatus.RINGING),
        ("in-progress", OutboundCallStatus.IN_PROGRESS),
        ("completed", OutboundCallStatus.COMPLETED),
    ],
)
def test_status_is_verified_and_normalized(
    provider_status: str, expected_status: OutboundCallStatus
) -> None:
    application = FakeTelephonyApplication()
    fields = {
        "CallSid": BINDING.provider_call_id,
        "AccountSid": ACCOUNT_SID,
        "CallStatus": provider_status,
        "SequenceNumber": "4",
        "Timestamp": "Sun, 30 Aug 2026 12:05:00 +0000",
    }
    headers, body = signed_form("/v1/telephony/twilio/status", fields)
    with build_client(application) as client:
        response = client.post("/v1/telephony/twilio/status", headers=headers, content=body)

    assert response.status_code == 204
    assert len(application.status_events) == 1
    assert application.status_events[0].status is expected_status


def handoff_callback_fields(*, participant_call_sid: str) -> dict[str, str]:
    return {
        "AccountSid": ACCOUNT_SID,
        "CallSid": participant_call_sid,
        "ConferenceSid": CONFERENCE_SID,
        "StatusCallbackEvent": "participant-join",
        "SequenceNumber": "8",
        "Timestamp": "Sun, 30 Aug 2026 12:05:00 +0000",
    }


def test_handoff_callback_verifies_and_delegates_join_evidence_durably() -> None:
    application = FakeTelephonyApplication()
    fields = handoff_callback_fields(participant_call_sid=COORDINATOR_CALL_SID)
    headers, body = signed_form("/v1/telephony/twilio/handoff-status", fields)
    with build_client(application) as client:
        response = client.post("/v1/telephony/twilio/handoff-status", headers=headers, content=body)

    assert response.status_code == 204
    assert len(application.handoff_callbacks) == 1
    callback = application.handoff_callbacks[0]
    assert callback.account_sid == ACCOUNT_SID
    assert callback.participant_call_sid == COORDINATOR_CALL_SID
    assert len(callback.provider_event_id) == 64
    assert len(application.handoff_events) == 1
    event = application.handoff_events[0]
    assert event.status is HumanHandoffStatus.JOINED
    assert event.remote_participant_present is True
    assert event.coordinator_participant_present is True


def test_fake_provider_handoff_journey_fences_ai_joins_and_refreshes_projection() -> None:
    application = FakeTelephonyApplication()
    browser_headers = {
        "Authorization": "Bearer synthetic-test-token",
        "Origin": "http://localhost:3000",
    }
    post_headers = {
        **browser_headers,
        "Idempotency-Key": "handoff-full-journey-001",
        "X-Request-ID": "handoff-full-journey-request",
    }
    remote_fields = handoff_callback_fields(participant_call_sid=BINDING.provider_call_id)
    remote_headers, remote_body = signed_form("/v1/telephony/twilio/handoff-status", remote_fields)
    coordinator_fields = handoff_callback_fields(participant_call_sid=COORDINATOR_CALL_SID)
    coordinator_fields["SequenceNumber"] = "9"
    coordinator_headers, coordinator_body = signed_form(
        "/v1/telephony/twilio/handoff-status", coordinator_fields
    )

    with build_client(application) as client:
        readiness = client.get(
            f"/v1/calls/{CALL_SESSION_ID}/handoff-readiness",
            headers=browser_headers,
        )
        requested = client.post(
            f"/v1/calls/{CALL_SESSION_ID}/handoffs",
            headers=post_headers,
            json=handoff_body(),
        )
        remote_joined = client.post(
            "/v1/telephony/twilio/handoff-status",
            headers=remote_headers,
            content=remote_body,
        )
        coordinator_joined = client.post(
            "/v1/telephony/twilio/handoff-status",
            headers=coordinator_headers,
            content=coordinator_body,
        )
        refreshed = client.get(
            f"/v1/calls/{CALL_SESSION_ID}/handoffs/{HANDOFF_ID}",
            headers=browser_headers,
        )

    assert readiness.status_code == 200
    assert requested.status_code == 202
    assert remote_joined.status_code == coordinator_joined.status_code == 204
    assert application.ai_authority_fenced
    assert [event.status for event in application.handoff_events] == [
        HumanHandoffStatus.CONNECTING,
        HumanHandoffStatus.JOINED,
    ]
    assert all(event.remote_participant_present for event in application.handoff_events)
    assert application.handoff_events[-1].coordinator_participant_present
    assert refreshed.status_code == 200
    assert refreshed.json()["status"] == "JOINED"
    assert [event[0] for event in application.handoff_audit] == [
        "HANDOFF_REQUESTED",
        "HANDOFF_JOINED",
    ]
    assert application.handoff_audit[0][2] == application.handoff_audit[1][2]
    for forbidden in ("transcript", "e164", "call_sid", "signature", TOKEN):
        assert forbidden not in refreshed.text.lower()


def test_handoff_callback_does_not_infer_join_from_one_participant() -> None:
    application = FakeTelephonyApplication()
    fields = handoff_callback_fields(participant_call_sid=BINDING.provider_call_id)
    headers, body = signed_form("/v1/telephony/twilio/handoff-status", fields)
    with build_client(application) as client:
        response = client.post("/v1/telephony/twilio/handoff-status", headers=headers, content=body)

    assert response.status_code == 204
    assert application.handoff_events[0].status is HumanHandoffStatus.CONNECTING
    assert application.handoff_events[0].coordinator_participant_present is False


def test_handoff_callback_signature_covers_unrecognized_form_parameters() -> None:
    application = FakeTelephonyApplication()
    fields = {
        **handoff_callback_fields(participant_call_sid=COORDINATOR_CALL_SID),
        "ProviderExtra": "signed-value",
    }
    headers, body = signed_form("/v1/telephony/twilio/handoff-status", fields)
    with build_client(application) as client:
        accepted = client.post("/v1/telephony/twilio/handoff-status", headers=headers, content=body)
        tampered = client.post(
            "/v1/telephony/twilio/handoff-status",
            headers=headers,
            content=body.replace("signed-value", "tampered-value"),
        )

    assert accepted.status_code == 204
    assert tampered.status_code == 403
    assert len(application.handoff_events) == 1


class RejectingHandoffBindingApplication(FakeTelephonyApplication):
    async def map_handoff_status_callback(
        self, callback: TwilioHandoffStatusCallback
    ) -> HumanHandoffStatusEvent:
        del callback
        from yuno_backend.volta.telephony import HumanHandoffPermissionError

        raise HumanHandoffPermissionError()


class FailingHandoffPersistenceApplication(FakeTelephonyApplication):
    async def observe_handoff(self, event: HumanHandoffStatusEvent) -> HumanHandoff:
        del event
        raise RuntimeError("synthetic persistence outage")


def test_handoff_callback_fails_closed_for_binding_malformed_and_persistence() -> None:
    fields = handoff_callback_fields(participant_call_sid=COORDINATOR_CALL_SID)
    headers, body = signed_form("/v1/telephony/twilio/handoff-status", fields)
    malformed_fields = {**fields, "SequenceNumber": "not-an-integer"}
    malformed_headers, malformed_body = signed_form(
        "/v1/telephony/twilio/handoff-status", malformed_fields
    )
    with build_client(RejectingHandoffBindingApplication()) as client:
        rejected = client.post("/v1/telephony/twilio/handoff-status", headers=headers, content=body)
    with build_client(FakeTelephonyApplication()) as client:
        malformed = client.post(
            "/v1/telephony/twilio/handoff-status",
            headers=malformed_headers,
            content=malformed_body,
        )
    with build_client(FailingHandoffPersistenceApplication()) as client:
        retryable = client.post(
            "/v1/telephony/twilio/handoff-status", headers=headers, content=body
        )

    assert rejected.status_code == 403
    assert malformed.status_code == 422
    assert retryable.status_code == 503


def test_media_bridge_converts_audio_delegates_tool_and_terminates() -> None:
    application = FakeTelephonyApplication()
    signature = twilio_signature(MEDIA_URL, {}, TOKEN)
    inbound_payload = base64.b64encode(b"\xff" * 160).decode()
    with build_client(application) as client:
        with client.websocket_connect(
            "/v1/telephony/twilio/media",
            headers={"X-Twilio-Signature": signature},
        ) as websocket:
            websocket.send_json({"event": "connected", "protocol": "Call", "version": "1.0.0"})
            websocket.send_json(
                {
                    "event": "start",
                    "sequenceNumber": "1",
                    "streamSid": "MZ33333333333333333333333333333333",
                    "start": {
                        "accountSid": ACCOUNT_SID,
                        "streamSid": "MZ33333333333333333333333333333333",
                        "callSid": BINDING.provider_call_id,
                        "tracks": ["inbound"],
                        "mediaFormat": {
                            "encoding": "audio/x-mulaw",
                            "sampleRate": 8000,
                            "channels": 1,
                        },
                        "customParameters": {"binding": BINDING.stream_token},
                    },
                }
            )
            websocket.send_json(
                {
                    "event": "media",
                    "sequenceNumber": "2",
                    "streamSid": "MZ33333333333333333333333333333333",
                    "media": {
                        "track": "inbound",
                        "chunk": "1",
                        "payload": inbound_payload,
                    },
                }
            )
            clear = websocket.receive_json()
            outbound = websocket.receive_json()
            websocket.send_json(
                {
                    "event": "stop",
                    "sequenceNumber": "3",
                    "streamSid": "MZ33333333333333333333333333333333",
                    "stop": {"accountSid": ACCOUNT_SID},
                }
            )

    assert clear == {"event": "clear", "streamSid": "MZ33333333333333333333333333333333"}
    assert outbound["event"] == "media"
    assert outbound["streamSid"] == "MZ33333333333333333333333333333333"
    assert len(application.realtime_gateway.connection.audio[0]) == 160 * 3 * 2
    assert application.tool_calls[0][0].call_id == "call-tool-001"
    assert application.tool_calls[0][1].startswith("twilio-tool-")
    assert len(application.tool_calls[0][1]) == 76
    assert application.realtime_gateway.connection.tool_outputs[0].call_id == "call-tool-001"
    assert application.finished == [(BINDING, "COMPLETED")]
    assert application.realtime_gateway.connection.closed is True


def test_consented_inbound_media_captures_bounded_playable_evidence_on_stop() -> None:
    application = FakeTelephonyApplication()
    application.inbound_consented = True
    signature = twilio_signature(MEDIA_URL, {}, TOKEN)
    inbound_payload = base64.b64encode(b"\xff" * 160).decode()
    with build_client(application) as client:
        with client.websocket_connect(
            "/v1/telephony/twilio/media",
            headers={"X-Twilio-Signature": signature},
        ) as websocket:
            websocket.send_json({"event": "connected", "protocol": "Call", "version": "1.0.0"})
            websocket.send_json(
                media_start(
                    binding=INBOUND_BINDING.stream_token,
                    call_sid=INBOUND_CALL_SID,
                    stream_sid=INBOUND_STREAM_SID,
                )
            )
            websocket.send_json(
                {
                    "event": "media",
                    "sequenceNumber": "2",
                    "streamSid": INBOUND_STREAM_SID,
                    "media": {
                        "track": "inbound",
                        "chunk": "1",
                        "payload": inbound_payload,
                    },
                }
            )
            websocket.receive_json()
            websocket.receive_json()
            websocket.send_json(
                {
                    "event": "stop",
                    "sequenceNumber": "3",
                    "streamSid": INBOUND_STREAM_SID,
                    "stop": {"accountSid": ACCOUNT_SID},
                }
            )

    assert application.finished[0][1] == "COMPLETED"
    evidence = application.finished_evidence[0]
    assert evidence is not None
    assert evidence.audio.startswith(b"RIFF")
    assert len(evidence.audio) < 2_000_000
    assert evidence.audio_start_ms == 20
    assert evidence.item_id == "item-speech"
    assert evidence.event_id == "evt-speech"


def test_inbound_media_rejects_preconsent_binding_before_realtime_io() -> None:
    application = FakeTelephonyApplication()
    signature = twilio_signature(MEDIA_URL, {}, TOKEN)
    with build_client(application) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(
                "/v1/telephony/twilio/media",
                headers={"X-Twilio-Signature": signature},
            ) as websocket:
                websocket.send_json({"event": "connected", "protocol": "Call", "version": "1.0.0"})
                websocket.send_json(
                    media_start(
                        binding=INBOUND_BINDING.stream_token,
                        call_sid=INBOUND_CALL_SID,
                        stream_sid=INBOUND_STREAM_SID,
                    )
                )
                receive_until_close(websocket)

    assert error.value.code == 1008
    assert application.realtime_gateway.requests == []
    assert application.finished == []


def test_media_websocket_rejects_invalid_signature_before_acceptance() -> None:
    application = FakeTelephonyApplication()
    with build_client(application) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(
                "/v1/telephony/twilio/media",
                headers={"X-Twilio-Signature": "invalid"},
            ):
                pass
    assert error.value.code == 1008


def test_media_websocket_rejects_fourth_reservation_before_realtime_io() -> None:
    application = FakeTelephonyApplication()
    signature = twilio_signature(MEDIA_URL, {}, TOKEN)
    with build_client(application) as client:
        client.app.state.twilio_media_active.update({object(), object(), object()})
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(
                "/v1/telephony/twilio/media",
                headers={"X-Twilio-Signature": signature},
            ):
                pass

    assert error.value.code == 1013
    assert application.realtime_gateway.requests == []


def test_media_websocket_rejects_invalid_binding_and_releases_capacity() -> None:
    application = FakeTelephonyApplication()
    signature = twilio_signature(MEDIA_URL, {}, TOKEN)
    with build_client(application) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(
                "/v1/telephony/twilio/media",
                headers={"X-Twilio-Signature": signature},
            ) as websocket:
                send_media_preamble(websocket, binding="invalid-binding")
                receive_until_close(websocket)
        assert client.app.state.twilio_media_active == set()
    assert error.value.code == 1008
    assert application.finished == []


@pytest.mark.parametrize(
    "bad_frame",
    [
        "not-json",
        "x" * 16_385,
        (
            '{"event":"media","sequenceNumber":"2",'
            '"streamSid":"MZ99999999999999999999999999999999",'
            '"media":{"track":"inbound","chunk":"1","payload":"/w=="}}'
        ),
    ],
)
def test_media_websocket_rejects_malformed_or_mismatched_frames_and_releases(
    bad_frame: str,
) -> None:
    application = FakeTelephonyApplication()
    signature = twilio_signature(MEDIA_URL, {}, TOKEN)
    with build_client(application) as client:
        with pytest.raises(WebSocketDisconnect) as error:
            with client.websocket_connect(
                "/v1/telephony/twilio/media",
                headers={"X-Twilio-Signature": signature},
            ) as websocket:
                send_media_preamble(websocket)
                websocket.send_text(bad_frame)
                receive_until_close(websocket)
        assert client.app.state.twilio_media_active == set()
    assert error.value.code == 1008
    assert application.finished == [(BINDING, "DISCONNECTED")]


class DisconnectingWebSocket:
    def __init__(self) -> None:
        self._messages = [
            '{"event":"connected","protocol":"Call","version":"1.0.0"}',
            json.dumps(media_start()),
        ]

    async def receive_text(self) -> str:
        if self._messages:
            return self._messages.pop(0)
        raise WebSocketDisconnect(code=1001)

    async def send_json(self, value: object) -> None:
        del value


async def test_forced_websocket_disconnect_cancels_peer_and_closes_once() -> None:
    application = FakeTelephonyApplication()
    websocket = DisconnectingWebSocket()

    await bridge_media_stream(websocket, application)  # type: ignore[arg-type]

    assert application.realtime_gateway.connection.closed is True
    assert application.finished == [(BINDING, "DISCONNECTED")]


class AuthorityFenceWebSocket:
    def __init__(self) -> None:
        self._messages = [
            json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}),
            json.dumps(media_start()),
        ]
        self.sent: list[dict[str, object]] = []
        self.clear_sent = asyncio.Event()
        self.stop_requested = asyncio.Event()

    async def receive_text(self) -> str:
        if self._messages:
            return self._messages.pop(0)
        await self.stop_requested.wait()
        return json.dumps(
            {
                "event": "stop",
                "sequenceNumber": "2",
                "streamSid": "MZ33333333333333333333333333333333",
                "stop": {"accountSid": ACCOUNT_SID},
            }
        )

    async def send_json(self, value: dict[str, object]) -> None:
        self.sent.append(value)
        if value.get("event") == "clear":
            self.clear_sent.set()


async def test_authority_fence_clears_but_waits_for_explicit_stream_stop() -> None:
    application = FakeTelephonyApplication()
    application.ai_authority_fenced = True
    application.authority_revoked.set()
    websocket = AuthorityFenceWebSocket()

    bridge = asyncio.create_task(
        bridge_media_stream(websocket, application)  # type: ignore[arg-type]
    )
    await websocket.clear_sent.wait()
    assert bridge.done() is False
    websocket.stop_requested.set()
    await bridge

    assert {message["event"] for message in websocket.sent} == {"clear"}
    assert all(message.get("event") != "media" for message in websocket.sent)
    assert application.finished == [(BINDING, "COMPLETED")]


class FenceBetweenConversionAndSendApplication(FakeTelephonyApplication):
    def __init__(self) -> None:
        super().__init__()
        self.second_speech_check = asyncio.Event()

    async def ensure_ai_speech_allowed(self, call_id: UUID) -> None:
        assert call_id == CALL_SESSION_ID
        self.speech_checks += 1
        if self.speech_checks == 2:
            self.second_speech_check.set()
            from yuno_backend.volta.telephony import HumanHandoffAuthorityError

            self.ai_authority_fenced = True
            self.authority_revoked.set()
            raise HumanHandoffAuthorityError(call_id=call_id)


async def test_authority_recheck_blocks_media_when_fence_flips_before_send() -> None:
    application = FenceBetweenConversionAndSendApplication()
    websocket = AuthorityFenceWebSocket()

    bridge = asyncio.create_task(
        bridge_media_stream(websocket, application)  # type: ignore[arg-type]
    )
    await application.second_speech_check.wait()
    assert bridge.done() is False
    websocket.stop_requested.set()
    await bridge

    assert application.speech_checks == 2
    assert all(message.get("event") != "media" for message in websocket.sent)
    assert any(message.get("event") == "clear" for message in websocket.sent)
    assert application.finished == [(BINDING, "COMPLETED")]


class ToolFenceApplication(FakeTelephonyApplication):
    def __init__(self) -> None:
        super().__init__()
        self.tool_fenced = asyncio.Event()

    async def delegate_tool(
        self,
        binding: MediaBinding,
        event: RealtimeToolCallRequested,
        idempotency_key: str,
    ) -> Mapping[str, object]:
        del binding, event, idempotency_key
        self.ai_authority_fenced = True
        self.authority_revoked.set()
        self.tool_fenced.set()
        raise HumanHandoffAuthorityError(call_id=CALL_SESSION_ID)


async def test_tool_authority_denial_clears_without_ending_media_bridge() -> None:
    application = ToolFenceApplication()
    websocket = AuthorityFenceWebSocket()
    bridge = asyncio.create_task(
        bridge_media_stream(websocket, application)  # type: ignore[arg-type]
    )

    await application.tool_fenced.wait()
    await websocket.clear_sent.wait()
    assert bridge.done() is False
    assert application.realtime_gateway.connection.tool_outputs == []
    websocket.stop_requested.set()
    await bridge

    assert any(message.get("event") == "clear" for message in websocket.sent)
    assert application.finished == [(BINDING, "COMPLETED")]


def test_mulaw_conversion_is_bounded_and_preserves_silence_shape() -> None:
    pcm = twilio_payload_to_pcm24(base64.b64encode(b"\xff" * 160).decode())
    assert len(pcm) == 960
    encoded = pcm24_to_twilio_payload(pcm)
    assert len(base64.b64decode(encoded)) == 160
    with pytest.raises(ValueError):
        twilio_payload_to_pcm24("not-base64")


@pytest.mark.parametrize(
    ("mulaw", "sample", "little_endian"),
    [
        (0xFF, 0, b"\x00\x00"),
        (0x80, 32124, b"\x7c\x7d"),
        (0x00, -32124, b"\x84\x82"),
    ],
)
def test_mulaw_known_vectors_and_pcm_little_endian(
    mulaw: int, sample: int, little_endian: bytes
) -> None:
    payload = base64.b64encode(bytes([mulaw])).decode()
    decoded = twilio_payload_to_pcm24(payload)
    assert decoded == little_endian * 3
    pcm = struct.pack("<hhh", sample, sample, sample)
    assert base64.b64decode(pcm24_to_twilio_payload(pcm)) == bytes([mulaw])


@pytest.mark.parametrize(
    "url",
    [
        "wss://user:password@telephony.example.test/v1/telephony/twilio/media",
        "wss://telephony.example.test/v1/telephony/twilio/media#fragment",
        "wss:///v1/telephony/twilio/media",
        "wss://telephony.example.test:8443/v1/telephony/twilio/media",
        "wss://telephony.example.test/another-path",
        "wss://localhost/v1/telephony/twilio/media",
        "wss://127.0.0.1/v1/telephony/twilio/media",
        "wss://[::1]/v1/telephony/twilio/media",
        "wss://singlelabel/v1/telephony/twilio/media",
        "wss://invalid_host.example/v1/telephony/twilio/media",
    ],
)
def test_twilio_media_url_rejects_noncanonical_values(url: str) -> None:
    with pytest.raises(ValueError, match="canonical secure media endpoint"):
        Settings(twilio_media_ws_url=url)


def test_sensitive_allowlist_and_stream_token_are_redacted_from_repr() -> None:
    number = "+15550001111"
    settings = Settings(twilio_destination_allowlist={"synthetic": number})
    assert number not in repr(settings)
    assert "twilio_destination_allowlist" not in settings.model_dump()
    assert BINDING.stream_token not in repr(BINDING)


async def test_live_runtime_validates_realtime_session_configuration_at_construction() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://demo:demo@localhost/demo",
        openai_api_key="synthetic-openai-key",
        twilio_account_sid=ACCOUNT_SID,
        twilio_api_key_sid="SK44444444444444444444444444444444",
        twilio_api_key_secret="synthetic-api-key-secret",
        twilio_from_e164="+15550001111",
        twilio_destination_allowlist={"synthetic": "+15550002222"},
        twilio_public_base_url=BASE_URL,
        twilio_media_ws_url=MEDIA_URL,
        openai_realtime_safety_identifier_key="",
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError, match="safety identifier"):
            create_live_telephony_application(
                settings,
                RuntimeContracts(call_id=CALL_SESSION_ID),  # type: ignore[arg-type]
                client,
            )


class FakeContracts:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object], str | None]] = []

    async def execute(self, operation_id, payload, idempotency_key):  # type: ignore[no-untyped-def]
        self.calls.append((operation_id, payload, idempotency_key))
        return ContractResult({"quote_id": "synthetic-quote"})

    async def get_evidence_audio(self, evidence_id):  # type: ignore[no-untyped-def]
        raise AssertionError(evidence_id)


async def test_tool_delegator_allows_quote_but_rejects_commitment_authority() -> None:
    contracts = FakeContracts()
    delegator = VoltaToolDelegator(contracts)  # type: ignore[arg-type]
    quote = RealtimeToolCallRequested(
        event_id="event-quote",
        item_id="item-quote",
        call_id="call-quote",
        name="record_quote",
        arguments={"call_id": str(CALL_SESSION_ID), "amount_minor": 880000},
    )
    result = await delegator.execute(quote, "twilio-idempotency-quote")
    assert result == {"quote_id": "synthetic-quote"}
    assert contracts.calls[0][0] == "record_quote"
    assert contracts.calls[0][1] == {
        "call_id": str(CALL_SESSION_ID),
        "body": {"amount_minor": 880000},
    }

    commitment = RealtimeToolCallRequested(
        event_id="event-commitment",
        item_id="item-commitment",
        call_id="call-commitment",
        name="create_candidate_commitment",
        arguments={},
    )
    with pytest.raises(ValueError, match="unsupported"):
        await delegator.execute(commitment, "twilio-idempotency-commitment")


def test_duplicate_tool_event_uses_same_bounded_idempotency_key() -> None:
    event = RealtimeToolCallRequested(
        event_id="event-quote-duplicate",
        item_id="item-quote-duplicate",
        call_id="call-quote-duplicate",
        name="record_quote",
        arguments={"call_id": str(CALL_SESSION_ID), "amount_minor": 880000},
    )
    first = tool_idempotency_key(BINDING, event)
    duplicate = tool_idempotency_key(BINDING, event)
    assert first == duplicate
    assert first.startswith("twilio-tool-") and len(first) == 76


class RuntimeContracts(FakeContracts):
    def __init__(self, call_id: UUID | None, *additional_call_ids: UUID) -> None:
        super().__init__()
        self.call_ids = (() if call_id is None else (call_id, *additional_call_ids))

    async def execute(self, operation_id, payload, idempotency_key):  # type: ignore[no-untyped-def]
        self.calls.append((operation_id, payload, idempotency_key))
        if operation_id == "get_operation":
            sessions = [{"call_id": str(call_id)} for call_id in self.call_ids]
            return ContractResult({"operation_id": str(OPERATION_ID), "sessions": sessions})
        return ContractResult({"quote_id": "synthetic-quote"})


class RuntimeGateway:
    def __init__(self) -> None:
        self.requests: list[OutboundCallRequest] = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def create_call(self, request: OutboundCallRequest) -> OutboundCall:
        self.requests.append(request)
        provider_call_id = f"CA{len(self.requests):032d}"
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0)
            return OutboundCall(
                call_session_id=request.call_session_id,
                provider_call_id=provider_call_id,
                status=OutboundCallStatus.QUEUED,
                created_at=datetime(2026, 8, 30, 12, tzinfo=UTC),
            )
        finally:
            self.in_flight -= 1


class RuntimeAttemptStore:
    def __init__(self) -> None:
        self.completions: list[tuple[object, ...]] = []

    async def complete(self, *values: object) -> None:
        self.completions.append(values)


class RuntimeEngine:
    async def dispose(self) -> None:
        return None


class RuntimeInboundApplication:
    def __init__(self) -> None:
        self.accepted: list[object] = []
        self.consented: list[object] = []
        self.started: list[object] = []
        self.completed: list[object] = []
        self.failed: list[object] = []
        self.binding = InboundCallBinding(
            attempt_id=UUID("00000000-0000-4000-8000-000000000061"),
            operation_id=OPERATION_ID,
            commitment_id=UUID("00000000-0000-4000-8000-000000000062"),
            call_id=CALL_SESSION_ID,
            provider_call_id=INBOUND_CALL_SID,
            stream_binding=INBOUND_BINDING.stream_token,
            expires_at=datetime(2026, 8, 30, 12, tzinfo=UTC) + timedelta(minutes=5),
        )

    async def accept_inbound_call(self, command):  # type: ignore[no-untyped-def]
        self.accepted.append(command)
        return self.binding

    async def record_inbound_consent(self, command):  # type: ignore[no-untyped-def]
        self.consented.append(command)
        return self.binding

    async def start_inbound_stream(self, command):  # type: ignore[no-untyped-def]
        self.started.append(command)
        return SimpleNamespace(
            operation_id=OPERATION_ID,
            call_id=CALL_SESSION_ID,
            provider_call_id=INBOUND_CALL_SID,
            correlation_id=UUID("00000000-0000-4000-8000-000000000026"),
        )

    async def complete_inbound_recovery(self, command):  # type: ignore[no-untyped-def]
        self.completed.append(command)
        return object()

    async def fail_inbound_call(self, command):  # type: ignore[no-untyped-def]
        self.failed.append(command)
        return object()


def runtime_request(
    *,
    call_session_id: UUID = CALL_SESSION_ID,
    idempotency_key: str = "runtime-outbound-001",
    destination_label: str = "synthetic-carrier-one",
) -> OutboundCallRequest:
    return OutboundCallRequest(
        operation_id=OPERATION_ID,
        call_session_id=call_session_id,
        correlation_id=UUID("00000000-0000-4000-8000-000000000015"),
        idempotency_key=idempotency_key,
        destination_label=destination_label,
        authorization=OutboundCallAuthorization(
            actor_id="coordinator-demo",
            authorized_at=datetime(2026, 8, 30, 12, tzinfo=UTC),
            recording_mode=RecordingMode.DISABLED,
        ),
    )


async def test_live_runtime_validates_call_membership_before_provider_io() -> None:
    contracts = RuntimeContracts(call_id=None)
    gateway = RuntimeGateway()
    runtime = LiveTelephonyApplication(
        settings=Settings(twilio_account_sid=ACCOUNT_SID),
        contracts=contracts,  # type: ignore[arg-type]
        gateway=gateway,
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=RuntimeAttemptStore(),  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )

    with pytest.raises(OutboundCallAuthorizationError):
        await runtime.create_outbound_call(runtime_request())
    assert gateway.requests == []


async def test_live_runtime_claims_stream_once_and_persists_terminal_status() -> None:
    contracts = RuntimeContracts(call_id=CALL_SESSION_ID)
    gateway = RuntimeGateway()
    store = RuntimeAttemptStore()
    runtime = LiveTelephonyApplication(
        settings=Settings(twilio_account_sid=ACCOUNT_SID),
        contracts=contracts,  # type: ignore[arg-type]
        gateway=gateway,
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=store,  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )
    first = await runtime.create_outbound_call(runtime_request())
    replay = await runtime.create_outbound_call(runtime_request())
    assert replay == first
    assert len(gateway.requests) == 1
    conflicting = replace(runtime_request(), destination_label="synthetic-carrier-two")
    with pytest.raises(OutboundCallIdempotencyConflict):
        await runtime.create_outbound_call(conflicting)
    assert len(gateway.requests) == 1
    binding = await runtime.binding_for_voice(first.provider_call_id)
    assert binding is not None
    assert (
        await runtime.binding_for_stream(
            binding.stream_token,
            binding.provider_call_id,
            "MZ33333333333333333333333333333333",
        )
        == binding
    )
    assert (
        await runtime.binding_for_stream(
            binding.stream_token,
            binding.provider_call_id,
            "MZ33333333333333333333333333333333",
        )
        is None
    )
    await runtime.stream_finished(binding, "COMPLETED")
    assert (
        await runtime.binding_for_stream(
            binding.stream_token,
            binding.provider_call_id,
            "MZ33333333333333333333333333333333",
        )
        is None
    )

    event = OutboundCallStatusEvent(
        provider_event_id="status-event-1",
        provider_call_id=first.provider_call_id,
        status=OutboundCallStatus.COMPLETED,
        sequence_number=1,
        observed_at=datetime(2026, 8, 30, 12, 5, tzinfo=UTC),
    )
    await runtime.observe_status(event)
    await runtime.observe_status(event)
    await runtime.observe_status(
        OutboundCallStatusEvent(
            provider_event_id="status-event-2",
            provider_call_id=first.provider_call_id,
            status=OutboundCallStatus.RINGING,
            sequence_number=2,
            observed_at=datetime(2026, 8, 30, 12, 6, tzinfo=UTC),
        )
    )
    assert len(store.completions) == 3
    assert all(
        completion[2].status is OutboundCallStatus.COMPLETED for completion in store.completions
    )
    with pytest.raises(ValueError, match="not active"):
        runtime.realtime_session(binding)
    matching_tool = RealtimeToolCallRequested(
        event_id="event-after-terminal",
        item_id="item-after-terminal",
        call_id="provider-tool-after-terminal",
        name="record_quote",
        arguments={"call_id": str(CALL_SESSION_ID), "amount_minor": 880000},
    )
    with pytest.raises(ValueError, match="not active"):
        await runtime.delegate_tool(binding, matching_tool, "twilio-tool-after-terminal")


async def test_live_runtime_local_handoff_event_fails_closed_before_durable_fence() -> None:
    class PermissiveAuthorityFence:
        def __init__(self) -> None:
            self.speech_checks = 0
            self.commitment_checks = 0

        async def ensure_speech_allowed(self, call_id: UUID) -> None:
            del call_id
            self.speech_checks += 1

        async def ensure_commitment_allowed(self, call_id: UUID) -> None:
            del call_id
            self.commitment_checks += 1

    contracts = RuntimeContracts(call_id=CALL_SESSION_ID)
    fence = PermissiveAuthorityFence()
    authority_event = asyncio.Event()
    authority_event.set()
    runtime = LiveTelephonyApplication(
        settings=Settings(twilio_account_sid=ACCOUNT_SID),
        contracts=contracts,  # type: ignore[arg-type]
        gateway=RuntimeGateway(),
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=RuntimeAttemptStore(),  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )
    runtime.configure_handoff(
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        fence,  # type: ignore[arg-type]
        {CALL_SESSION_ID: authority_event},
    )
    call = await runtime.create_outbound_call(runtime_request())
    binding = await runtime.binding_for_voice(call.provider_call_id)
    assert binding is not None
    tool = RealtimeToolCallRequested(
        event_id="event-local-fence",
        item_id="item-local-fence",
        call_id="provider-tool-local-fence",
        name="record_quote",
        arguments={"call_id": str(CALL_SESSION_ID), "amount_minor": 880000},
    )
    contract_calls_before_tool = len(contracts.calls)

    with pytest.raises(HumanHandoffAuthorityError):
        await runtime.ensure_ai_speech_allowed(CALL_SESSION_ID)
    with pytest.raises(HumanHandoffAuthorityError):
        await runtime.delegate_tool(binding, tool, "twilio-tool-local-fence")

    assert fence.speech_checks == 0
    assert fence.commitment_checks == 0
    assert len(contracts.calls) == contract_calls_before_tool


async def test_live_runtime_coalesces_concurrent_exact_replay() -> None:
    gateway = RuntimeGateway()
    runtime = LiveTelephonyApplication(
        settings=Settings(twilio_account_sid=ACCOUNT_SID),
        contracts=RuntimeContracts(call_id=CALL_SESSION_ID),  # type: ignore[arg-type]
        gateway=gateway,
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=RuntimeAttemptStore(),  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )

    first, replay = await asyncio.gather(
        runtime.create_outbound_call(runtime_request()),
        runtime.create_outbound_call(runtime_request()),
    )

    assert first == replay
    assert len(gateway.requests) == 1


async def test_live_runtime_shields_pending_provider_mutation_from_client_cancellation() -> None:
    class BlockingGateway(RuntimeGateway):
        def __init__(self) -> None:
            super().__init__()
            self.started = asyncio.Event()
            self.release = asyncio.Event()

        async def create_call(self, request: OutboundCallRequest) -> OutboundCall:
            self.started.set()
            await self.release.wait()
            return await super().create_call(request)

    gateway = BlockingGateway()
    runtime = LiveTelephonyApplication(
        settings=Settings(twilio_account_sid=ACCOUNT_SID),
        contracts=RuntimeContracts(call_id=CALL_SESSION_ID),  # type: ignore[arg-type]
        gateway=gateway,
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=RuntimeAttemptStore(),  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )
    request = runtime_request()
    abandoned = asyncio.create_task(runtime.create_outbound_call(request))
    await gateway.started.wait()
    abandoned.cancel()
    with pytest.raises(asyncio.CancelledError):
        await abandoned

    replay = asyncio.create_task(runtime.create_outbound_call(request))
    gateway.release.set()
    call = await replay

    assert call.call_session_id == CALL_SESSION_ID
    assert len(gateway.requests) == 1


async def test_live_runtime_reserves_capacity_across_four_concurrent_requests() -> None:
    call_ids = tuple(
        UUID(f"00000000-0000-4000-8000-{index:012d}") for index in range(71, 75)
    )
    gateway = RuntimeGateway()
    runtime = LiveTelephonyApplication(
        settings=Settings(twilio_account_sid=ACCOUNT_SID),
        contracts=RuntimeContracts(call_ids[0], *call_ids[1:]),  # type: ignore[arg-type]
        gateway=gateway,
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=RuntimeAttemptStore(),  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )
    requests = [
        runtime_request(
            call_session_id=call_id,
            idempotency_key=f"runtime-capacity-{index}",
            destination_label=f"synthetic-carrier-{index}",
        )
        for index, call_id in enumerate(call_ids, start=1)
    ]

    outcomes = await asyncio.gather(
        *(runtime.create_outbound_call(item) for item in requests),
        return_exceptions=True,
    )

    assert sum(isinstance(item, OutboundCall) for item in outcomes) == 3
    assert sum(isinstance(item, _OutboundCallCapacityError) for item in outcomes) == 1
    assert len(gateway.requests) == 3
    assert gateway.max_in_flight == 3


async def test_live_runtime_isolates_three_calls_and_releases_terminal_capacity() -> None:
    call_ids = (
        CALL_SESSION_ID,
        UUID("00000000-0000-4000-8000-000000000006"),
        UUID("00000000-0000-4000-8000-000000000007"),
        UUID("00000000-0000-4000-8000-000000000008"),
    )
    contracts = RuntimeContracts(call_ids[0], *call_ids[1:])
    gateway = RuntimeGateway()
    store = RuntimeAttemptStore()
    runtime = LiveTelephonyApplication(
        settings=Settings(twilio_account_sid=ACCOUNT_SID),
        contracts=contracts,  # type: ignore[arg-type]
        gateway=gateway,
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=store,  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )
    requests = [
        runtime_request(
            call_session_id=call_id,
            idempotency_key=f"runtime-outbound-00{index}",
            destination_label=f"synthetic-carrier-{index}",
        )
        for index, call_id in enumerate(call_ids, start=1)
    ]

    calls = await asyncio.gather(*(runtime.create_outbound_call(item) for item in requests[:3]))
    assert len(gateway.requests) == 3
    assert gateway.max_in_flight == 3
    with pytest.raises(_OutboundCallCapacityError):
        await runtime.create_outbound_call(requests[3])
    assert len(gateway.requests) == 3

    bindings = [await runtime.binding_for_voice(call.provider_call_id) for call in calls]
    assert all(binding is not None for binding in bindings)
    claimed = await asyncio.gather(
        *(
            runtime.binding_for_stream(
                binding.stream_token,
                binding.provider_call_id,
                f"MZ{index:032d}",
            )
            for index, binding in enumerate(bindings, start=1)
            if binding is not None
        )
    )
    assert claimed == bindings
    assert (
        await runtime.binding_for_stream(
            bindings[0].stream_token,  # type: ignore[union-attr]
            calls[1].provider_call_id,
            "MZ00000000000000000000000000000002",
        )
        is None
    )
    cross_call_tool = RealtimeToolCallRequested(
        event_id="event-cross-call",
        item_id="item-cross-call",
        call_id="provider-tool-call-cross-call",
        name="record_quote",
        arguments={"call_id": str(call_ids[1]), "amount_minor": 880000},
    )
    contract_call_count = len(contracts.calls)
    with pytest.raises(ValueError, match="does not match"):
        await runtime.delegate_tool(
            bindings[0],  # type: ignore[arg-type]
            cross_call_tool,
            "twilio-tool-cross-call",
        )
    assert len(contracts.calls) == contract_call_count

    terminal = OutboundCallStatusEvent(
        provider_event_id="status-terminal-first",
        provider_call_id=calls[0].provider_call_id,
        status=OutboundCallStatus.COMPLETED,
        sequence_number=1,
        observed_at=datetime(2026, 8, 30, 12, 5, tzinfo=UTC),
    )
    await runtime.observe_status(terminal)
    fourth = await runtime.create_outbound_call(requests[3])
    assert fourth.call_session_id == call_ids[3]
    assert len(gateway.requests) == 4

    replay = await runtime.create_outbound_call(requests[0])
    assert replay.provider_call_id == calls[0].provider_call_id
    assert replay.status is OutboundCallStatus.COMPLETED
    assert len(gateway.requests) == 4
    assert store.completions[0][0] == requests[0].idempotency_key


async def test_live_runtime_maps_inbound_lifecycle_to_provider_neutral_backend() -> None:
    inbound = RuntimeInboundApplication()
    runtime = LiveTelephonyApplication(
        settings=Settings(
            twilio_account_sid=ACCOUNT_SID,
            openai_realtime_safety_identifier_key="synthetic-safety-key",
        ),
        contracts=RuntimeContracts(call_id=CALL_SESSION_ID),  # type: ignore[arg-type]
        gateway=RuntimeGateway(),
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=RuntimeAttemptStore(),  # type: ignore[arg-type]
        inbound_application=inbound,  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )
    correlation_id = UUID("00000000-0000-4000-8000-000000000026")
    accepted = await runtime.accept_inbound_call(
        "synthetic-driver", INBOUND_CALL_SID, correlation_id
    )
    consented = await runtime.record_inbound_consent(
        "synthetic-driver", INBOUND_CALL_SID, correlation_id
    )
    started = await runtime.binding_for_stream(
        consented.stream_token, INBOUND_CALL_SID, INBOUND_STREAM_SID
    )
    evidence = StreamEvidence(
        audio=b"RIFF\x04\x00\x00\x00WAVE",
        audio_start_ms=20,
        item_id="item-evidence",
        event_id="event-evidence",
        correlation_id=correlation_id,
    )
    assert started == accepted
    assert started is not None
    assert runtime.realtime_session(started).tools == ()
    await runtime.stream_finished(started, "COMPLETED", evidence)
    replayed_consent = await runtime.record_inbound_consent(
        "synthetic-driver", INBOUND_CALL_SID, correlation_id
    )
    assert (
        await runtime.binding_for_stream(
            replayed_consent.stream_token, INBOUND_CALL_SID, INBOUND_STREAM_SID
        )
        is None
    )

    assert inbound.accepted[0].caller_label == "synthetic-driver"  # type: ignore[attr-defined]
    assert inbound.accepted[0].provider_call_id == INBOUND_CALL_SID  # type: ignore[attr-defined]
    assert inbound.consented[0].stream_binding == INBOUND_BINDING.stream_token  # type: ignore[attr-defined]
    assert inbound.started[0].provider_stream_id == INBOUND_STREAM_SID  # type: ignore[attr-defined]
    assert inbound.completed[0].post_consent_audio == b"RIFF\x04\x00\x00\x00WAVE"  # type: ignore[attr-defined]
    assert inbound.completed[0].correlation_id == correlation_id  # type: ignore[attr-defined]
    assert inbound.failed == []


async def test_late_inbound_accept_preserves_claimed_canonical_binding() -> None:
    class RacingInboundApplication(RuntimeInboundApplication):
        def __init__(self) -> None:
            super().__init__()
            self.first_accept_started = asyncio.Event()
            self.release_first_accept = asyncio.Event()
            self.accept_count = 0

        async def accept_inbound_call(self, command):  # type: ignore[no-untyped-def]
            self.accept_count += 1
            if self.accept_count == 1:
                self.first_accept_started.set()
                await self.release_first_accept.wait()
            self.accepted.append(command)
            return self.binding

    inbound = RacingInboundApplication()
    runtime = LiveTelephonyApplication(
        settings=Settings(twilio_account_sid=ACCOUNT_SID),
        contracts=RuntimeContracts(call_id=CALL_SESSION_ID),  # type: ignore[arg-type]
        gateway=RuntimeGateway(),
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=RuntimeAttemptStore(),  # type: ignore[arg-type]
        inbound_application=inbound,  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )
    old_correlation = UUID("00000000-0000-4000-8000-000000000081")
    canonical_correlation = UUID("00000000-0000-4000-8000-000000000082")
    late_accept = asyncio.create_task(
        runtime.accept_inbound_call(
            "synthetic-driver", INBOUND_CALL_SID, old_correlation
        )
    )
    await inbound.first_accept_started.wait()
    consented = await runtime.record_inbound_consent(
        "synthetic-driver", INBOUND_CALL_SID, canonical_correlation
    )
    claimed = await runtime.binding_for_stream(
        consented.stream_token, INBOUND_CALL_SID, INBOUND_STREAM_SID
    )
    assert claimed == consented

    inbound.release_first_accept.set()
    late_binding = await late_accept

    assert late_binding == consented
    assert late_binding.correlation_id == canonical_correlation
    assert (
        await runtime.binding_for_stream(
            consented.stream_token, INBOUND_CALL_SID, INBOUND_STREAM_SID
        )
        is None
    )


async def test_live_runtime_reconstructs_consented_binding_after_process_restart() -> None:
    inbound = RuntimeInboundApplication()
    runtime = LiveTelephonyApplication(
        settings=Settings(twilio_account_sid=ACCOUNT_SID),
        contracts=RuntimeContracts(call_id=CALL_SESSION_ID),  # type: ignore[arg-type]
        gateway=RuntimeGateway(),
        realtime_gateway=FakeRealtimeGateway(),
        attempt_store=RuntimeAttemptStore(),  # type: ignore[arg-type]
        inbound_application=inbound,  # type: ignore[arg-type]
        engine=RuntimeEngine(),
    )

    reconstructed = await runtime.binding_for_stream(
        INBOUND_BINDING.stream_token, INBOUND_CALL_SID, INBOUND_STREAM_SID
    )

    assert reconstructed is not None
    assert reconstructed.inbound is True
    assert reconstructed.operation_id == OPERATION_ID
    assert reconstructed.call_session_id == CALL_SESSION_ID
    assert reconstructed.provider_call_id == INBOUND_CALL_SID
    assert reconstructed.correlation_id == UUID(
        "00000000-0000-4000-8000-000000000026"
    )
    assert inbound.started[0].stream_binding == INBOUND_BINDING.stream_token  # type: ignore[attr-defined]
