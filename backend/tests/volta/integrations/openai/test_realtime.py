from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from websockets.datastructures import Headers
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK, InvalidStatus
from websockets.frames import Close
from websockets.http11 import Response
from yuno_backend.integrations.openai import OpenAIRealtimeConfig, OpenAIRealtimeGateway
from yuno_backend.volta.realtime import (
    InvalidRealtimeEvent,
    RealtimeAudioDelta,
    RealtimeAuthenticationError,
    RealtimeDisconnectedError,
    RealtimeModelUnavailableError,
    RealtimeProviderError,
    RealtimeRateLimitError,
    RealtimeResponseCancelled,
    RealtimeResponseCompleted,
    RealtimeSessionReady,
    RealtimeSessionRequest,
    RealtimeSpeechStarted,
    RealtimeSpeechStopped,
    RealtimeTimeoutError,
    RealtimeToolCallRequested,
    RealtimeToolDefinition,
    RealtimeToolOutput,
)

API_KEY = "test-api-key-sensitive-marker"
INSTRUCTIONS = "private-instruction-marker Always speak only English."
SAFETY_IDENTIFIER = "privacy_safe_hash"


@dataclass
class FakeSocket:
    messages: list[object]
    sent: list[str] = field(default_factory=list)
    closed: int = 0

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str | bytes:
        if not self.messages:
            await asyncio.Future()
        value = self.messages.pop(0)
        if isinstance(value, BaseException):
            raise value
        assert isinstance(value, str | bytes)
        return value

    async def close(self) -> None:
        self.closed += 1


class CapturingConnector:
    def __init__(self, socket: FakeSocket) -> None:
        self.socket = socket
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, url: str, **kwargs: Any) -> FakeSocket:
        self.calls.append((url, kwargs))
        return self.socket


class BlockingConnector:
    async def __call__(self, url: str, **kwargs: Any) -> FakeSocket:
        await asyncio.Future()


class StatusConnector:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.calls = 0

    async def __call__(self, url: str, **kwargs: Any) -> FakeSocket:
        self.calls += 1
        raise InvalidStatus(Response(self.status_code, "safe", Headers()))


@dataclass
class BlockingCloseSocket(FakeSocket):
    close_attempted: int = 0
    close_cancelled: int = 0

    async def close(self) -> None:
        self.close_attempted += 1
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            self.close_cancelled += 1
            raise


@dataclass
class CancelledOnceCloseSocket(FakeSocket):
    close_attempted: int = 0

    async def close(self) -> None:
        self.close_attempted += 1
        if self.close_attempted == 1:
            raise asyncio.CancelledError
        self.closed += 1


def _json(event_type: str, **values: object) -> str:
    return json.dumps({"type": event_type, **values})


def _session_updated() -> str:
    return _json(
        "session.updated",
        event_id="evt.session",
        session={"id": "sess.safe", "model": "gpt-realtime-2.1"},
    )


def _tool_call(*, call_id: str = "call.safe") -> str:
    return _json(
        "response.output_item.done",
        event_id="evt.tool",
        item={
            "id": "item.tool",
            "type": "function_call",
            "call_id": call_id,
            "name": "lookup_reference",
            "arguments": '{"reference":"SYN-2042"}',
        },
    )


def _request() -> RealtimeSessionRequest:
    return RealtimeSessionRequest(
        instructions=INSTRUCTIONS,
        safety_identifier=SAFETY_IDENTIFIER,
        voice="cedar",
        tools=(
            RealtimeToolDefinition(
                name="lookup_reference",
                description="Read a synthetic reference.",
                parameters={
                    "type": "object",
                    "properties": {"reference": {"type": "string"}},
                    "required": ["reference"],
                    "additionalProperties": False,
                },
            ),
        ),
    )


def _gateway(socket: FakeSocket, **config: Any) -> tuple[OpenAIRealtimeGateway, CapturingConnector]:
    connector = CapturingConnector(socket)
    defaults = {
        "api_key": API_KEY,
        "session_timeout_seconds": 0.05,
        "event_timeout_seconds": 0.05,
        "close_timeout_seconds": 0.05,
    }
    gateway = OpenAIRealtimeGateway(
        OpenAIRealtimeConfig(**(defaults | config)), connector=connector
    )
    return gateway, connector


async def _collect(events: AsyncIterator[object], count: int) -> list[object]:
    collected = []
    async for event in events:
        collected.append(event)
        if len(collected) == count:
            break
    return collected


@pytest.mark.asyncio
async def test_exact_headers_session_audio_and_tool_output_mapping() -> None:
    socket = FakeSocket([_json("session.created"), _session_updated(), _tool_call()])
    gateway, connector = _gateway(socket)

    async with gateway.connect(_request()) as connection:
        events = connection.events()
        first = await anext(events)
        tool_call = await anext(events)
        await connection.send_audio(b"\x01\x02")
        await connection.send_tool_output(
            RealtimeToolOutput(
                event_id="evt.output",
                response_event_id="evt.continue",
                call_id="call.safe",
                result={"available": True},
            )
        )

    assert first == RealtimeSessionReady(
        event_id="evt.session", session_id="sess.safe", model_id="gpt-realtime-2.1"
    )
    assert isinstance(tool_call, RealtimeToolCallRequested)
    url, kwargs = connector.calls[0]
    assert url == "wss://api.openai.com/v1/realtime?model=gpt-realtime-2.1"
    assert kwargs == {
        "additional_headers": {
            "Authorization": f"Bearer {API_KEY}",
            "OpenAI-Safety-Identifier": SAFETY_IDENTIFIER,
        },
        "open_timeout": 10.0,
        "close_timeout": 0.05,
        "max_size": 1_048_576,
    }
    session_update, audio_append, tool_output, response_create = map(json.loads, socket.sent)
    assert session_update == {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "instructions": f"{INSTRUCTIONS}\n\nLanguage requirement: respond only in English.",
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcm", "rate": 24_000},
                    "turn_detection": {
                        "type": "server_vad",
                        "create_response": True,
                        "interrupt_response": True,
                    },
                },
                "output": {
                    "format": {"type": "audio/pcm", "rate": 24_000},
                    "voice": "cedar",
                },
            },
            "tools": [
                {
                    "type": "function",
                    "name": "lookup_reference",
                    "description": "Read a synthetic reference.",
                    "parameters": {
                        "type": "object",
                        "properties": {"reference": {"type": "string"}},
                        "required": ["reference"],
                        "additionalProperties": False,
                    },
                }
            ],
            "tool_choice": "auto",
        },
    }
    assert audio_append == {
        "type": "input_audio_buffer.append",
        "audio": base64.b64encode(b"\x01\x02").decode(),
    }
    assert tool_output == {
        "event_id": "evt.output",
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": "call.safe",
            "output": '{"available":true}',
        },
    }
    assert response_create == {
        "event_id": "evt.continue",
        "type": "response.create",
    }
    assert socket.closed == 1


@pytest.mark.asyncio
async def test_maps_typed_events_in_stable_order_and_ignores_unknown_events() -> None:
    audio = b"\x00\x01\x02\x03"
    socket = FakeSocket(
        [
            _session_updated(),
            _json("future.non_application", opaque={"private": "ignored"}),
            _json(
                "input_audio_buffer.speech_started",
                event_id="evt.start",
                item_id="item.user",
                audio_start_ms=20,
            ),
            _json(
                "input_audio_buffer.speech_stopped",
                event_id="evt.stop",
                item_id="item.user",
                audio_end_ms=1_320,
            ),
            _json(
                "response.output_audio.delta",
                event_id="evt.audio",
                response_id="resp.one",
                item_id="item.assistant",
                content_index=0,
                delta=base64.b64encode(audio).decode(),
            ),
            _json(
                "response.output_item.done",
                event_id="evt.tool",
                item={
                    "id": "item.tool",
                    "type": "function_call",
                    "call_id": "call.one",
                    "name": "lookup_reference",
                    "arguments": '{"reference":"SYN-2042"}',
                },
            ),
            _json(
                "response.done",
                event_id="evt.done",
                response={"id": "resp.one", "status": "completed"},
            ),
            _json(
                "response.done",
                event_id="evt.cancelled",
                response={"id": "resp.two", "status": "cancelled"},
            ),
        ]
    )
    gateway, _ = _gateway(socket)

    async with gateway.connect(_request()) as connection:
        events = await _collect(connection.events(), 7)

    assert events == [
        RealtimeSessionReady("evt.session", "sess.safe", "gpt-realtime-2.1"),
        RealtimeSpeechStarted("evt.start", "item.user", 20),
        RealtimeSpeechStopped("evt.stop", "item.user", 1_320),
        RealtimeAudioDelta("evt.audio", "resp.one", "item.assistant", 0, audio),
        RealtimeToolCallRequested(
            "evt.tool",
            "item.tool",
            "call.one",
            "lookup_reference",
            {"reference": "SYN-2042"},
        ),
        RealtimeResponseCompleted("evt.done", "resp.one"),
        RealtimeResponseCancelled("evt.cancelled", "resp.two"),
    ]


@pytest.mark.asyncio
async def test_duplicate_provider_tool_call_is_emitted_once() -> None:
    tool_event = _json(
        "response.output_item.done",
        event_id="evt.tool",
        item={
            "id": "item.tool",
            "type": "function_call",
            "call_id": "call.one",
            "name": "lookup_reference",
            "arguments": '{"reference":"SYN-2042"}',
        },
    )
    socket = FakeSocket(
        [
            _session_updated(),
            tool_event,
            tool_event,
            _json(
                "response.done",
                event_id="evt.done",
                response={"id": "resp.one", "status": "completed"},
            ),
        ]
    )
    gateway, _ = _gateway(socket)
    async with gateway.connect(_request()) as connection:
        events = await _collect(connection.events(), 3)
    assert [type(event) for event in events] == [
        RealtimeSessionReady,
        RealtimeToolCallRequested,
        RealtimeResponseCompleted,
    ]


@pytest.mark.parametrize(
    "message",
    [
        "not-json",
        b"unexpected binary",
        _json(
            "input_audio_buffer.speech_started",
            event_id="evt.start",
            item_id="item.user",
            audio_start_ms=-1,
        ),
        _json(
            "response.output_audio.delta",
            event_id="evt.audio",
            response_id="resp.one",
            item_id="item.one",
            content_index=0,
            delta="%%%",
        ),
        _json(
            "response.output_item.done",
            event_id="evt.tool",
            item={
                "id": "item.tool",
                "type": "function_call",
                "call_id": "call.one",
                "name": "not_allowlisted",
                "arguments": "{}",
            },
        ),
        _json(
            "response.output_item.done",
            event_id="evt.tool",
            item={
                "id": "item.tool",
                "type": "function_call",
                "call_id": "call.one",
                "name": "lookup_reference",
                "arguments": "[]",
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_malformed_mapped_events_fail_closed(message: object) -> None:
    socket = FakeSocket([_session_updated(), message])
    gateway, _ = _gateway(socket)
    async with gateway.connect(_request()) as connection:
        events = connection.events()
        await anext(events)
        with pytest.raises(InvalidRealtimeEvent):
            await anext(events)
        with pytest.raises(RealtimeDisconnectedError):
            await connection.send_audio(b"\x00\x00")


@pytest.mark.asyncio
async def test_deeply_nested_json_fails_with_a_typed_terminal_error() -> None:
    depth = 10_000
    nested = '{"type":"future.event","value":' + "[" * depth + "0" + "]" * depth + "}"
    socket = FakeSocket([_session_updated(), nested])
    gateway, _ = _gateway(socket)
    async with gateway.connect(_request()) as connection:
        events = connection.events()
        await anext(events)
        with pytest.raises(InvalidRealtimeEvent):
            await anext(events)
        with pytest.raises(RealtimeDisconnectedError):
            await connection.send_audio(b"\x00\x00")


@pytest.mark.asyncio
async def test_oversized_message_fails_closed() -> None:
    socket = FakeSocket([_session_updated(), "x" * 1_025])
    gateway, _ = _gateway(socket, max_message_size=1_024)
    async with gateway.connect(_request()) as connection:
        events = connection.events()
        await anext(events)
        with pytest.raises(InvalidRealtimeEvent):
            await anext(events)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("invalid_api_key", RealtimeAuthenticationError),
        ("rate_limit_exceeded", RealtimeRateLimitError),
        ("server_error", RealtimeProviderError),
    ],
)
@pytest.mark.asyncio
async def test_provider_errors_are_safely_translated(code: str, expected: type[Exception]) -> None:
    raw_secret = "provider-message-sensitive-marker"
    socket = FakeSocket(
        [
            _session_updated(),
            _json(
                "error",
                event_id="evt.error",
                error={"type": "server_error", "code": code, "message": raw_secret},
            ),
        ]
    )
    gateway, _ = _gateway(socket)
    async with gateway.connect(_request()) as connection:
        events = connection.events()
        await anext(events)
        with pytest.raises(expected) as caught:
            await anext(events)
        with pytest.raises(RealtimeDisconnectedError):
            await connection.send_audio(b"\x00\x00")
    assert raw_secret not in repr(caught.value)
    assert raw_secret not in str(caught.value)


@pytest.mark.asyncio
async def test_duplicate_tool_output_is_rejected_without_second_send() -> None:
    socket = FakeSocket([_session_updated(), _tool_call(call_id="call.one")])
    gateway, _ = _gateway(socket)
    output = RealtimeToolOutput(
        event_id="evt.output",
        response_event_id="evt.continue",
        call_id="call.one",
        result={"ok": True},
    )
    async with gateway.connect(_request()) as connection:
        events = connection.events()
        await anext(events)
        await anext(events)
        await connection.send_tool_output(output)
        with pytest.raises(ValueError, match="already sent"):
            await connection.send_tool_output(output)
    assert len(socket.sent) == 3


@pytest.mark.asyncio
async def test_tool_output_requires_a_received_provider_call() -> None:
    socket = FakeSocket([_session_updated()])
    gateway, _ = _gateway(socket)
    output = RealtimeToolOutput(
        event_id="evt.output",
        response_event_id="evt.continue",
        call_id="call.unknown",
        result={"ok": True},
    )
    async with gateway.connect(_request()) as connection:
        with pytest.raises(ValueError, match="does not match a received call"):
            await connection.send_tool_output(output)
    assert len(socket.sent) == 1


@pytest.mark.asyncio
async def test_session_and_receive_timeouts_close_the_socket() -> None:
    session_socket = FakeSocket([])
    gateway, _ = _gateway(session_socket, session_timeout_seconds=0.001)
    with pytest.raises(RealtimeTimeoutError):
        async with gateway.connect(_request()):
            pass
    assert session_socket.closed == 1

    event_socket = FakeSocket([_session_updated()])
    gateway, _ = _gateway(event_socket, event_timeout_seconds=0.001)
    async with gateway.connect(_request()) as connection:
        events = connection.events()
        await anext(events)
        with pytest.raises(RealtimeTimeoutError):
            await anext(events)
        with pytest.raises(RealtimeDisconnectedError):
            await connection.send_audio(b"\x00\x00")
    assert event_socket.closed == 1


@pytest.mark.asyncio
async def test_connect_timeout_is_safe_and_does_not_retry() -> None:
    gateway = OpenAIRealtimeGateway(
        OpenAIRealtimeConfig(api_key=API_KEY, connect_timeout_seconds=0.001),
        connector=BlockingConnector(),
    )
    with pytest.raises(RealtimeTimeoutError) as caught:
        async with gateway.connect(_request()):
            pass
    assert caught.value.model_id == "gpt-realtime-2.1"


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (401, RealtimeAuthenticationError),
        (403, RealtimeAuthenticationError),
        (404, RealtimeModelUnavailableError),
        (429, RealtimeRateLimitError),
        (503, RealtimeProviderError),
    ],
)
@pytest.mark.asyncio
async def test_handshake_statuses_are_safely_translated_once(
    status_code: int, expected: type[Exception]
) -> None:
    connector = StatusConnector(status_code)
    gateway = OpenAIRealtimeGateway(
        OpenAIRealtimeConfig(api_key=API_KEY), connector=connector
    )
    with pytest.raises(expected) as caught:
        async with gateway.connect(_request()):
            pass
    assert caught.value.status_code == status_code
    assert connector.calls == 1


@pytest.mark.asyncio
async def test_close_timeout_cancels_close_without_orphaned_task() -> None:
    socket = BlockingCloseSocket([_session_updated()])
    gateway, _ = _gateway(socket, close_timeout_seconds=0.001)
    async with gateway.connect(_request()):
        pass
    assert socket.close_attempted == 1
    assert socket.close_cancelled == 1


@pytest.mark.asyncio
async def test_external_close_cancellation_allows_cleanup_retry() -> None:
    socket = CancelledOnceCloseSocket([_session_updated()])
    gateway, _ = _gateway(socket)
    async with gateway.connect(_request()) as connection:
        with pytest.raises(asyncio.CancelledError):
            await connection.close()
        await connection.close()
    assert socket.close_attempted == 2
    assert socket.closed == 1


@pytest.mark.asyncio
async def test_context_exit_closes_after_application_failure() -> None:
    socket = FakeSocket([_session_updated()])
    gateway, _ = _gateway(socket)
    with pytest.raises(RuntimeError, match="application failure"):
        async with gateway.connect(_request()):
            raise RuntimeError("application failure")
    assert socket.closed == 1


@pytest.mark.asyncio
async def test_explicit_close_is_idempotent_and_stops_writes() -> None:
    socket = FakeSocket([_session_updated()])
    gateway, _ = _gateway(socket)
    async with gateway.connect(_request()) as connection:
        await connection.close()
        await connection.close()
        with pytest.raises(RealtimeDisconnectedError):
            await connection.send_audio(b"\x00\x00")
    assert socket.closed == 1


@pytest.mark.parametrize(
    "closed",
    [
        ConnectionClosedOK(
            Close(1000, "safe close"), Close(1000, "safe close"), True
        ),
        ConnectionClosedError(None, None),
    ],
)
@pytest.mark.asyncio
async def test_clean_and_unclean_disconnect_are_terminal(closed: BaseException) -> None:
    socket = FakeSocket([_session_updated(), closed])
    gateway, _ = _gateway(socket)
    async with gateway.connect(_request()) as connection:
        events = connection.events()
        await anext(events)
        with pytest.raises(RealtimeDisconnectedError):
            await anext(events)
    assert socket.closed == 1


@pytest.mark.asyncio
async def test_receive_cancellation_propagates_and_context_closes() -> None:
    socket = FakeSocket([_session_updated()])
    gateway, _ = _gateway(socket, event_timeout_seconds=10)
    async with gateway.connect(_request()) as connection:
        events = connection.events()
        await anext(events)
        task = asyncio.create_task(anext(events))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert socket.closed == 1


def test_config_and_failures_do_not_expose_secret_content() -> None:
    config = OpenAIRealtimeConfig(api_key=API_KEY)
    assert API_KEY not in repr(config)
    assert INSTRUCTIONS not in repr(_request())
    assert SAFETY_IDENTIFIER not in repr(_request())
    with pytest.raises(ValueError) as caught:
        OpenAIRealtimeConfig(api_key=API_KEY, base_url="ws://unsafe.invalid")
    combined = repr(caught.value) + str(caught.value)
    for secret in (API_KEY, INSTRUCTIONS, SAFETY_IDENTIFIER):
        assert secret not in combined


@pytest.mark.parametrize(
    "base_url",
    [
        "wss://example.com/v1/realtime",
        "wss://user@api.openai.com/v1/realtime",
        "wss://api.openai.com:443/v1/realtime",
        "wss://api.openai.com/v1/realtime?existing=value",
        "wss://api.openai.com/v1/realtime#fragment",
        "wss://api.openai.com/v1/realtime/extra",
    ],
)
def test_config_rejects_non_official_or_ambiguous_destinations(base_url: str) -> None:
    with pytest.raises(ValueError, match="official secure endpoint"):
        OpenAIRealtimeConfig(api_key=API_KEY, base_url=base_url)


@pytest.mark.asyncio
async def test_session_mapping_enforces_the_declared_english_language() -> None:
    socket = FakeSocket([_session_updated()])
    gateway, _ = _gateway(socket)
    request = RealtimeSessionRequest(
        instructions="Responda somente em português.",
        safety_identifier=SAFETY_IDENTIFIER,
    )
    async with gateway.connect(request):
        pass
    session_update = json.loads(socket.sent[0])
    assert session_update["session"]["instructions"] == (
        "Responda somente em português.\n\n"
        "Language requirement: respond only in English."
    )
