"""OpenAI Realtime server WebSocket adapter."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import math
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import quote, urlsplit

from websockets.asyncio.client import connect as websocket_connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK, InvalidStatus

from yuno_backend.volta.realtime.errors import (
    InvalidRealtimeEvent,
    RealtimeAuthenticationError,
    RealtimeConnectionError,
    RealtimeDisconnectedError,
    RealtimeError,
    RealtimeModelUnavailableError,
    RealtimeProviderError,
    RealtimeRateLimitError,
    RealtimeTimeoutError,
)
from yuno_backend.volta.realtime.gateway import RealtimeConnection
from yuno_backend.volta.realtime.models import (
    MAX_AUDIO_CHUNK_BYTES,
    RealtimeAudioDelta,
    RealtimeEvent,
    RealtimePlaybackTruncation,
    RealtimeResponseCancelled,
    RealtimeResponseCompleted,
    RealtimeSessionReady,
    RealtimeSessionRequest,
    RealtimeSpeechStarted,
    RealtimeSpeechStopped,
    RealtimeToolCallRequested,
    RealtimeToolOutput,
)

__all__ = ["OpenAIRealtimeConfig", "OpenAIRealtimeGateway"]

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
DEFAULT_REALTIME_MODEL = "gpt-realtime-2.1"
MAX_TRACKED_TOOL_CALLS = 4_096
MAX_TRACKED_AUDIO_ITEMS = 4_096
_OFFICIAL_REALTIME_HOST = "api.openai.com"
_OFFICIAL_REALTIME_PATH = "/v1/realtime"
_ENGLISH_INSTRUCTION = "Language requirement: respond only in English."


class _WebSocket(Protocol):
    async def send(self, message: str) -> None: ...

    async def recv(self) -> str | bytes: ...

    async def close(self) -> None: ...


Connector = Callable[..., Awaitable[_WebSocket]]


async def _default_connector(url: str, **kwargs: Any) -> _WebSocket:
    return await websocket_connect(url, **kwargs)


@dataclass(frozen=True, slots=True)
class OpenAIRealtimeConfig:
    api_key: str = field(repr=False)
    base_url: str = "wss://api.openai.com/v1/realtime"
    model: str = DEFAULT_REALTIME_MODEL
    connect_timeout_seconds: float = 10.0
    session_timeout_seconds: float = 10.0
    event_timeout_seconds: float = 30.0
    close_timeout_seconds: float = 5.0
    max_message_size: int = 1_048_576

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("OpenAI API key is required")
        parsed_base_url = urlsplit(self.base_url)
        if (
            parsed_base_url.scheme != "wss"
            or parsed_base_url.hostname != _OFFICIAL_REALTIME_HOST
            or parsed_base_url.path != _OFFICIAL_REALTIME_PATH
            or parsed_base_url.port is not None
            or parsed_base_url.username is not None
            or parsed_base_url.password is not None
            or parsed_base_url.query
            or parsed_base_url.fragment
        ):
            raise ValueError("OpenAI Realtime base URL must be the official secure endpoint")
        if _SAFE_IDENTIFIER.fullmatch(self.model) is None:
            raise ValueError("model must be a safe bounded identifier")
        deadlines = (
            self.connect_timeout_seconds,
            self.session_timeout_seconds,
            self.event_timeout_seconds,
            self.close_timeout_seconds,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or value <= 0
            or (isinstance(value, float) and not math.isfinite(value))
            for value in deadlines
        ):
            raise ValueError("Realtime deadlines must be positive")
        if not 1_024 <= self.max_message_size <= 16_777_216:
            raise ValueError("max_message_size is outside the safe supported range")


class OpenAIRealtimeGateway:
    """Create one bounded OpenAI server connection per context lifetime."""

    def __init__(
        self,
        config: OpenAIRealtimeConfig,
        *,
        connector: Connector | None = None,
    ) -> None:
        self._config = config
        self._connector = connector or _default_connector

    @asynccontextmanager
    async def connect(self, request: RealtimeSessionRequest) -> AsyncIterator[RealtimeConnection]:
        started = time.monotonic()
        socket: _WebSocket | None = None
        url = f"{self._config.base_url}?model={quote(self._config.model, safe='._-')}"
        try:
            socket = await asyncio.wait_for(
                self._connector(
                    url,
                    additional_headers={
                        "Authorization": f"Bearer {self._config.api_key}",
                        "OpenAI-Safety-Identifier": request.safety_identifier,
                    },
                    open_timeout=self._config.connect_timeout_seconds,
                    close_timeout=self._config.close_timeout_seconds,
                    max_size=self._config.max_message_size,
                ),
                timeout=self._config.connect_timeout_seconds,
            )
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            raise RealtimeTimeoutError(
                model_id=self._config.model, duration_ms=_duration_ms(started)
            ) from None
        except InvalidStatus as exc:
            status = getattr(exc.response, "status_code", None)
            raise _status_error(
                status=status,
                model_id=self._config.model,
                duration_ms=_duration_ms(started),
            ) from None
        except (OSError, ConnectionError):
            raise RealtimeConnectionError(
                model_id=self._config.model, duration_ms=_duration_ms(started)
            ) from None
        except Exception:
            raise RealtimeConnectionError(
                model_id=self._config.model, duration_ms=_duration_ms(started)
            ) from None

        connection = _OpenAIRealtimeConnection(socket, self._config, request)
        try:
            await connection.initialize()
            yield connection
        finally:
            await connection.close()


class _OpenAIRealtimeConnection:
    def __init__(
        self,
        socket: _WebSocket,
        config: OpenAIRealtimeConfig,
        request: RealtimeSessionRequest,
    ) -> None:
        self._socket = socket
        self._config = config
        self._request = request
        self._allowed_tools = frozenset(tool.name for tool in request.tools)
        self._received_audio_items: set[tuple[str, int]] = set()
        self._truncated_audio_items: set[tuple[str, int]] = set()
        self._received_call_ids: set[str] = set()
        self._sent_call_ids: set[str] = set()
        self._ready: RealtimeSessionReady | None = None
        self._closed = False
        self._close_completed = False
        self._events_started = False

    async def initialize(self) -> None:
        await self._send_json(_session_update(self._request))
        started = time.monotonic()
        deadline = started + self._config.session_timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RealtimeTimeoutError(
                    model_id=self._config.model, duration_ms=_duration_ms(started)
                )
            message = await self._receive(
                remaining, started=started
            )
            event = self._parse(message)
            if isinstance(event, RealtimeSessionReady):
                self._ready = event
                return

    async def send_audio(self, chunk: bytes) -> None:
        if self._closed:
            raise RealtimeDisconnectedError(model_id=self._config.model)
        if not isinstance(chunk, bytes) or not 0 < len(chunk) <= MAX_AUDIO_CHUNK_BYTES:
            raise ValueError("audio chunk must be non-empty bounded bytes")
        await self._send_json(
            {
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(chunk).decode("ascii"),
            }
        )

    async def send_tool_output(self, output: RealtimeToolOutput) -> None:
        if self._closed:
            raise RealtimeDisconnectedError(model_id=self._config.model)
        if output.call_id not in self._received_call_ids:
            raise ValueError("tool output does not match a received call")
        if output.call_id in self._sent_call_ids:
            raise ValueError("tool output was already sent for this call")
        self._sent_call_ids.add(output.call_id)
        result = json.dumps(_thaw(output.result), separators=(",", ":"), allow_nan=False)
        item_event = {
            "event_id": output.event_id,
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": output.call_id,
                "output": result,
            },
        }
        response_event = {
            "event_id": output.response_event_id,
            "type": "response.create",
        }
        await self._send_json(item_event)
        await self._send_json(response_event)

    async def truncate_playback(self, truncation: RealtimePlaybackTruncation) -> None:
        if self._closed:
            raise RealtimeDisconnectedError(model_id=self._config.model)
        audio_item = (truncation.item_id, truncation.content_index)
        if audio_item not in self._received_audio_items:
            raise ValueError("playback truncation does not match received audio")
        if audio_item in self._truncated_audio_items:
            raise ValueError("playback was already truncated for this audio item")
        self._truncated_audio_items.add(audio_item)
        await self._send_json(
            {
                "type": "conversation.item.truncate",
                "item_id": truncation.item_id,
                "content_index": truncation.content_index,
                "audio_end_ms": truncation.audio_end_ms,
            }
        )

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        if self._events_started:
            raise RuntimeError("events may only be consumed once")
        self._events_started = True
        if self._ready is not None:
            yield self._ready
        try:
            while not self._closed:
                message = await self._receive(self._config.event_timeout_seconds)
                event = self._parse(message)
                if event is not None:
                    yield event
        except asyncio.CancelledError:
            self._closed = True
            raise
        except RealtimeError:
            self._closed = True
            raise

    async def close(self) -> None:
        if self._close_completed:
            return
        self._closed = True
        try:
            await asyncio.wait_for(
                self._socket.close(), timeout=self._config.close_timeout_seconds
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            # Closing is best effort and must not replace an active application failure.
            self._close_completed = True
        else:
            self._close_completed = True

    async def _send_json(self, event: Mapping[str, Any]) -> None:
        encoded = json.dumps(event, separators=(",", ":"), allow_nan=False)
        if len(encoded.encode()) > self._config.max_message_size:
            raise ValueError("outbound realtime message exceeds the configured limit")
        try:
            await self._socket.send(encoded)
        except asyncio.CancelledError:
            raise
        except (ConnectionClosedOK, ConnectionClosedError) as exc:
            self._closed = True
            raise RealtimeDisconnectedError(
                model_id=self._config.model, close_code=_close_code(exc)
            ) from None
        except Exception:
            self._closed = True
            raise RealtimeDisconnectedError(model_id=self._config.model) from None

    async def _receive(
        self, deadline_seconds: float, *, started: float | None = None
    ) -> str:
        receive_started = time.monotonic() if started is None else started
        try:
            message = await asyncio.wait_for(
                self._socket.recv(), timeout=deadline_seconds
            )
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            raise RealtimeTimeoutError(
                model_id=self._config.model, duration_ms=_duration_ms(receive_started)
            ) from None
        except (ConnectionClosedOK, ConnectionClosedError) as exc:
            self._closed = True
            raise RealtimeDisconnectedError(
                model_id=self._config.model,
                close_code=_close_code(exc),
                duration_ms=_duration_ms(receive_started),
            ) from None
        except Exception:
            self._closed = True
            raise RealtimeDisconnectedError(
                model_id=self._config.model, duration_ms=_duration_ms(receive_started)
            ) from None
        if not isinstance(message, str):
            raise InvalidRealtimeEvent(model_id=self._config.model) from None
        if len(message.encode()) > self._config.max_message_size:
            raise InvalidRealtimeEvent(model_id=self._config.model) from None
        return message

    def _parse(self, message: str) -> RealtimeEvent | None:
        try:
            payload = json.loads(message)
        except (json.JSONDecodeError, RecursionError, UnicodeError, ValueError):
            raise InvalidRealtimeEvent(model_id=self._config.model) from None
        if not isinstance(payload, dict) or not isinstance(payload.get("type"), str):
            raise InvalidRealtimeEvent(model_id=self._config.model) from None
        event_type = payload["type"]
        try:
            if event_type == "session.updated":
                session = _object(payload, "session")
                return RealtimeSessionReady(
                    event_id=_string(payload, "event_id"),
                    session_id=_string(session, "id"),
                    model_id=_optional_string(session, "model") or self._config.model,
                )
            if event_type == "input_audio_buffer.speech_started":
                return RealtimeSpeechStarted(
                    event_id=_string(payload, "event_id"),
                    item_id=_string(payload, "item_id"),
                    audio_start_ms=_integer(payload, "audio_start_ms"),
                )
            if event_type == "input_audio_buffer.speech_stopped":
                return RealtimeSpeechStopped(
                    event_id=_string(payload, "event_id"),
                    item_id=_string(payload, "item_id"),
                    audio_end_ms=_integer(payload, "audio_end_ms"),
                )
            if event_type == "response.output_audio.delta":
                try:
                    audio = base64.b64decode(_string(payload, "delta"), validate=True)
                except (binascii.Error, ValueError):
                    raise ValueError from None
                event = RealtimeAudioDelta(
                    event_id=_string(payload, "event_id"),
                    response_id=_string(payload, "response_id"),
                    item_id=_string(payload, "item_id"),
                    content_index=_integer(payload, "content_index"),
                    audio=audio,
                )
                audio_item = (event.item_id, event.content_index)
                if (
                    audio_item not in self._received_audio_items
                    and len(self._received_audio_items) >= MAX_TRACKED_AUDIO_ITEMS
                ):
                    raise RealtimeProviderError(
                        model_id=self._config.model,
                        event_type=event_type,
                        event_id=event.event_id,
                    )
                self._received_audio_items.add(audio_item)
                return event
            if event_type == "response.output_item.done":
                item = _object(payload, "item")
                if item.get("type") != "function_call":
                    return None
                name = _string(item, "name")
                if name not in self._allowed_tools:
                    raise ValueError
                arguments = json.loads(_string(item, "arguments"))
                if not isinstance(arguments, dict):
                    raise ValueError
                call = RealtimeToolCallRequested(
                    event_id=_string(payload, "event_id"),
                    item_id=_string(item, "id"),
                    call_id=_string(item, "call_id"),
                    name=name,
                    arguments=arguments,
                )
                if call.call_id in self._received_call_ids:
                    return None
                if len(self._received_call_ids) >= MAX_TRACKED_TOOL_CALLS:
                    raise RealtimeProviderError(
                        model_id=self._config.model,
                        event_type=event_type,
                        event_id=call.event_id,
                    )
                self._received_call_ids.add(call.call_id)
                return call
            if event_type == "response.done":
                response = _object(payload, "response")
                status = _string(response, "status")
                if status == "completed":
                    return RealtimeResponseCompleted(
                        event_id=_string(payload, "event_id"),
                        response_id=_string(response, "id"),
                    )
                if status in {"cancelled", "canceled"}:
                    return RealtimeResponseCancelled(
                        event_id=_string(payload, "event_id"),
                        response_id=_string(response, "id"),
                    )
                if status in {"failed", "incomplete"}:
                    raise RealtimeProviderError(
                        model_id=self._config.model,
                        event_type=event_type,
                        event_id=_optional_string(payload, "event_id"),
                    )
                raise ValueError
            if event_type == "error":
                raise _provider_event_error(payload, model_id=self._config.model)
        except RealtimeError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, RecursionError):
            raise InvalidRealtimeEvent(
                model_id=self._config.model,
                event_type=event_type,
                event_id=_optional_string(payload, "event_id"),
            ) from None
        return None


def _session_update(request: RealtimeSessionRequest) -> dict[str, Any]:
    return {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "instructions": f"{request.instructions}\n\n{_ENGLISH_INSTRUCTION}",
            "output_modalities": ["audio"],
            "audio": {
                "input": {
                    "format": {"type": "audio/pcm", "rate": request.audio_format.sample_rate_hz},
                    "turn_detection": {
                        "type": "server_vad",
                        "create_response": True,
                        "interrupt_response": True,
                    },
                },
                "output": {
                    "format": {"type": "audio/pcm", "rate": request.audio_format.sample_rate_hz},
                    "voice": request.voice,
                },
            },
            "tools": [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": _thaw(tool.parameters),
                }
                for tool in request.tools
            ],
            "tool_choice": "auto",
        },
    }


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


def _object(payload: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = payload[key]
    if not isinstance(value, dict):
        raise ValueError
    return value


def _string(payload: Mapping[str, Any], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise ValueError
    return value


def _optional_string(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _integer(payload: Mapping[str, Any], key: str) -> int:
    value = payload[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError
    return value


def _provider_event_error(payload: Mapping[str, Any], *, model_id: str) -> RealtimeError:
    error = payload.get("error")
    error_object = error if isinstance(error, dict) else {}
    code = error_object.get("code")
    error_type = error_object.get("type")
    classifier = code if isinstance(code, str) else error_type
    if not isinstance(classifier, str):
        classifier = ""
    exception_type: type[RealtimeError] = RealtimeProviderError
    if classifier in {"invalid_api_key", "authentication_error"}:
        exception_type = RealtimeAuthenticationError
    elif classifier in {"model_not_found", "model_not_available"}:
        exception_type = RealtimeModelUnavailableError
    elif classifier in {"rate_limit_exceeded", "rate_limit_error"}:
        exception_type = RealtimeRateLimitError
    return exception_type(
        model_id=model_id,
        event_type="error",
        event_id=_optional_string(payload, "event_id"),
    )


def _status_error(*, status: object, model_id: str, duration_ms: int) -> RealtimeError:
    status_code = status if isinstance(status, int) else None
    exception_type: type[RealtimeError] = RealtimeConnectionError
    if status_code in {401, 403}:
        exception_type = RealtimeAuthenticationError
    elif status_code == 404:
        exception_type = RealtimeModelUnavailableError
    elif status_code == 429:
        exception_type = RealtimeRateLimitError
    elif status_code is not None:
        exception_type = RealtimeProviderError
    return exception_type(
        model_id=model_id, status_code=status_code, duration_ms=duration_ms
    )


def _duration_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1_000))


def _close_code(error: ConnectionClosedOK | ConnectionClosedError) -> int | None:
    received = error.rcvd
    return received.code if received is not None else None
