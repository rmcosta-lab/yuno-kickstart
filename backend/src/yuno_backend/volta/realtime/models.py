"""Immutable provider-neutral values for realtime voice sessions."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

__all__ = [
    "PcmAudioFormat",
    "RealtimeAudioDelta",
    "RealtimeEvent",
    "RealtimePlaybackTruncation",
    "RealtimeResponseCancelled",
    "RealtimeResponseCompleted",
    "RealtimeSessionReady",
    "RealtimeSessionRequest",
    "RealtimeSpeechStarted",
    "RealtimeSpeechStopped",
    "RealtimeToolCallRequested",
    "RealtimeToolDefinition",
    "RealtimeToolOutput",
]

MAX_IDENTIFIER_LENGTH = 128
MAX_INSTRUCTIONS_BYTES = 16_384
MAX_JSON_BYTES = 32_768
MAX_AUDIO_CHUNK_BYTES = 1_048_576
MAX_TOOLS = 32
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_TOOL_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,63}$")
_SAFETY_IDENTIFIER = re.compile(r"^[a-f0-9]{64}$")
type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | tuple[JsonValue, ...] | Mapping[str, JsonValue]


def _identifier(value: object, field_name: str) -> None:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a safe bounded identifier")


def _non_negative(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _safety_identifier(value: object) -> None:
    if not isinstance(value, str) or _SAFETY_IDENTIFIER.fullmatch(value) is None:
        raise ValueError("safety_identifier must be a lowercase SHA-256 digest")


def _freeze_json(value: object, *, field_name: str) -> JsonValue:
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{field_name} must be JSON-compatible") from exc
    if len(encoded.encode()) > MAX_JSON_BYTES:
        raise ValueError(f"{field_name} exceeds the JSON size limit")
    try:
        return _freeze_json_unchecked(value, field_name=field_name)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError(f"{field_name} must be JSON-compatible") from exc


def _freeze_json_unchecked(value: object, *, field_name: str) -> JsonValue:
    if value is None or isinstance(value, str | bool | int | float):
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, JsonValue] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{field_name} keys must be strings")
            frozen[key] = _freeze_json_unchecked(child, field_name=field_name)
        return MappingProxyType(frozen)
    if isinstance(value, list | tuple):
        return tuple(_freeze_json_unchecked(child, field_name=field_name) for child in value)
    raise ValueError(f"{field_name} must be JSON-compatible")


@dataclass(frozen=True, slots=True)
class PcmAudioFormat:
    encoding: Literal["pcm16"] = "pcm16"
    sample_rate_hz: Literal[24000] = 24000
    channels: Literal[1] = 1

    def __post_init__(self) -> None:
        if (self.encoding, self.sample_rate_hz, self.channels) != ("pcm16", 24000, 1):
            raise ValueError("only PCM16 mono at 24 kHz is supported")


@dataclass(frozen=True, slots=True)
class RealtimeToolDefinition:
    name: str
    description: str
    parameters: Mapping[str, JsonValue] = field(repr=False)

    def __post_init__(self) -> None:
        if _TOOL_NAME.fullmatch(self.name) is None:
            raise ValueError("tool name is invalid")
        if not self.description.strip() or len(self.description.encode()) > 1_024:
            raise ValueError("tool description is required and bounded")
        frozen = _freeze_json(self.parameters, field_name="tool parameters")
        if not isinstance(frozen, Mapping):
            raise ValueError("tool parameters must be a JSON object")
        object.__setattr__(self, "parameters", frozen)


@dataclass(frozen=True, slots=True)
class RealtimeSessionRequest:
    instructions: str = field(repr=False)
    safety_identifier: str = field(repr=False)
    tools: tuple[RealtimeToolDefinition, ...] = ()
    language: Literal["en"] = "en"
    voice: str = "marin"
    audio_format: PcmAudioFormat = field(default_factory=PcmAudioFormat)
    vad: Literal["server_vad"] = "server_vad"

    def __post_init__(self) -> None:
        if (
            not self.instructions.strip()
            or len(self.instructions.encode()) > MAX_INSTRUCTIONS_BYTES
        ):
            raise ValueError("instructions are required and bounded")
        _safety_identifier(self.safety_identifier)
        if self.language != "en" or self.vad != "server_vad":
            raise ValueError("only English with server VAD is supported")
        if not self.voice.strip() or len(self.voice) > 64:
            raise ValueError("voice is required and bounded")
        if not isinstance(self.audio_format, PcmAudioFormat):
            raise ValueError("audio_format must be PcmAudioFormat")
        if not isinstance(self.tools, tuple):
            object.__setattr__(self, "tools", tuple(self.tools))
        if not all(isinstance(tool, RealtimeToolDefinition) for tool in self.tools):
            raise ValueError("tools must contain RealtimeToolDefinition values")
        unique_tool_count = len({tool.name for tool in self.tools})
        if len(self.tools) > MAX_TOOLS or unique_tool_count != len(self.tools):
            raise ValueError("tools must be unique and bounded")


@dataclass(frozen=True, slots=True)
class RealtimeToolOutput:
    event_id: str
    response_event_id: str
    call_id: str
    result: Mapping[str, JsonValue] = field(repr=False)

    def __post_init__(self) -> None:
        _identifier(self.event_id, "event_id")
        _identifier(self.response_event_id, "response_event_id")
        _identifier(self.call_id, "call_id")
        frozen = _freeze_json(self.result, field_name="tool result")
        if not isinstance(frozen, Mapping):
            raise ValueError("tool result must be a JSON object")
        object.__setattr__(self, "result", frozen)


@dataclass(frozen=True, slots=True)
class RealtimePlaybackTruncation:
    item_id: str
    content_index: int
    audio_end_ms: int

    def __post_init__(self) -> None:
        _identifier(self.item_id, "item_id")
        _non_negative(self.content_index, "content_index")
        _non_negative(self.audio_end_ms, "audio_end_ms")


@dataclass(frozen=True, slots=True)
class RealtimeSessionReady:
    event_id: str
    session_id: str
    model_id: str
    type: Literal["session_ready"] = field(init=False, default="session_ready")

    def __post_init__(self) -> None:
        _identifier(self.event_id, "event_id")
        _identifier(self.session_id, "session_id")
        _identifier(self.model_id, "model_id")


@dataclass(frozen=True, slots=True)
class RealtimeSpeechStarted:
    event_id: str
    item_id: str
    audio_start_ms: int
    type: Literal["speech_started"] = field(init=False, default="speech_started")

    def __post_init__(self) -> None:
        _identifier(self.event_id, "event_id")
        _identifier(self.item_id, "item_id")
        _non_negative(self.audio_start_ms, "audio_start_ms")


@dataclass(frozen=True, slots=True)
class RealtimeSpeechStopped:
    event_id: str
    item_id: str
    audio_end_ms: int
    type: Literal["speech_stopped"] = field(init=False, default="speech_stopped")

    def __post_init__(self) -> None:
        _identifier(self.event_id, "event_id")
        _identifier(self.item_id, "item_id")
        _non_negative(self.audio_end_ms, "audio_end_ms")


@dataclass(frozen=True, slots=True)
class RealtimeAudioDelta:
    event_id: str
    response_id: str
    item_id: str
    content_index: int
    audio: bytes = field(repr=False)
    type: Literal["audio_delta"] = field(init=False, default="audio_delta")

    def __post_init__(self) -> None:
        for name in ("event_id", "response_id", "item_id"):
            _identifier(getattr(self, name), name)
        _non_negative(self.content_index, "content_index")
        if not isinstance(self.audio, bytes) or not 0 < len(self.audio) <= MAX_AUDIO_CHUNK_BYTES:
            raise ValueError("audio must be non-empty bounded bytes")


@dataclass(frozen=True, slots=True)
class RealtimeToolCallRequested:
    event_id: str
    item_id: str
    call_id: str
    name: str
    arguments: Mapping[str, JsonValue] = field(repr=False)
    type: Literal["tool_call_requested"] = field(init=False, default="tool_call_requested")

    def __post_init__(self) -> None:
        for name in ("event_id", "item_id", "call_id"):
            _identifier(getattr(self, name), name)
        if _TOOL_NAME.fullmatch(self.name) is None:
            raise ValueError("tool name is invalid")
        frozen = _freeze_json(self.arguments, field_name="tool arguments")
        if not isinstance(frozen, Mapping):
            raise ValueError("tool arguments must be a JSON object")
        object.__setattr__(self, "arguments", frozen)


@dataclass(frozen=True, slots=True)
class RealtimeResponseCompleted:
    event_id: str
    response_id: str
    type: Literal["response_completed"] = field(init=False, default="response_completed")

    def __post_init__(self) -> None:
        _identifier(self.event_id, "event_id")
        _identifier(self.response_id, "response_id")


@dataclass(frozen=True, slots=True)
class RealtimeResponseCancelled:
    event_id: str
    response_id: str
    type: Literal["response_cancelled"] = field(init=False, default="response_cancelled")

    def __post_init__(self) -> None:
        _identifier(self.event_id, "event_id")
        _identifier(self.response_id, "response_id")


type RealtimeEvent = (
    RealtimeSessionReady
    | RealtimeSpeechStarted
    | RealtimeSpeechStopped
    | RealtimeAudioDelta
    | RealtimeToolCallRequested
    | RealtimeResponseCompleted
    | RealtimeResponseCancelled
)
