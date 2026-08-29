"""Credentialed, redacted OpenAI Realtime WebSocket probe for Phase 02."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import sys
import time
import wave
from pathlib import Path
from typing import Any

TOOL_NAME = "check_synthetic_availability"
TOOL_REFERENCE = "SYN-2042"
TRAILING_SILENCE_MS = 1_200
SAFETY_IDENTIFIER = hashlib.sha256(b"phase-02-synthetic-operator").hexdigest()
SAFE_EVENT_TYPES = {
    "session.created",
    "session.updated",
    "input_audio_buffer.speech_started",
    "input_audio_buffer.speech_stopped",
    "input_audio_buffer.committed",
    "conversation.item.added",
    "conversation.item.done",
    "response.created",
    "response.done",
    "response.cancelled",
    "rate_limits.updated",
    "error",
}


class RealtimeFailure(Exception):
    pass


def read_pcm_wav(path: Path) -> bytes:
    with wave.open(str(path), "rb") as audio:
        details = (audio.getnchannels(), audio.getsampwidth(), audio.getframerate())
        if details != (1, 2, 24_000):
            raise RealtimeFailure("audio_format_must_be_mono_pcm16_24khz")
        return audio.readframes(audio.getnframes())


def safe_event(event: dict[str, Any], elapsed_ms: int) -> dict[str, Any] | None:
    event_type = event.get("type")
    if event_type not in SAFE_EVENT_TYPES:
        return None
    result: dict[str, Any] = {"type": event_type, "elapsed_ms": elapsed_ms}
    for field in ("event_id", "item_id", "audio_start_ms", "audio_end_ms"):
        value = event.get(field)
        if isinstance(value, (str, int)):
            result[field] = value
    response = event.get("response")
    if isinstance(response, dict):
        for field in ("id", "status"):
            value = response.get(field)
            if isinstance(value, str):
                result[f"response_{field}"] = value
    if event_type == "rate_limits.updated":
        result["rate_limits"] = [
            {
                key: value
                for key in ("name", "limit", "remaining", "reset_seconds")
                if isinstance((value := limit.get(key)), (str, int, float))
            }
            for limit in event.get("rate_limits", [])
            if isinstance(limit, dict)
        ]
    if event_type == "error":
        error = event.get("error")
        if isinstance(error, dict):
            result["error_code"] = error.get("code") or error.get("type")
    return result


def tool_call(event: dict[str, Any]) -> dict[str, Any] | None:
    if event.get("type") != "response.done":
        return None
    response = event.get("response")
    if not isinstance(response, dict):
        return None
    for item in response.get("output", []):
        if isinstance(item, dict) and item.get("type") == "function_call":
            return item
    return None


def validate_tool_call(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    call_id = item.get("call_id")
    if item.get("name") != TOOL_NAME or not isinstance(call_id, str):
        raise RealtimeFailure("unexpected_tool_call")
    try:
        arguments = json.loads(item.get("arguments", ""))
    except json.JSONDecodeError as error:
        raise RealtimeFailure("invalid_tool_arguments") from error
    if arguments != {"reference": TOOL_REFERENCE}:
        raise RealtimeFailure("invalid_tool_arguments")
    return call_id, arguments


async def run_probe(model: str, audio_path: Path, timeout_seconds: float) -> dict[str, Any]:
    try:
        from websockets.asyncio.client import connect
    except ImportError as error:
        raise RealtimeFailure("missing_websockets_dependency") from error

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RealtimeFailure("authentication")
    audio = read_pcm_wav(audio_path)
    started = time.monotonic()
    events: list[dict[str, Any]] = []
    speech_started = False
    tool_completed = False
    continuation_completed = False
    original_call_id: str | None = None

    async with connect(
        f"wss://api.openai.com/v1/realtime?model={model}",
        additional_headers={
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Safety-Identifier": SAFETY_IDENTIFIER,
        },
        open_timeout=timeout_seconds,
        close_timeout=5,
        max_size=4 * 1024 * 1024,
    ) as websocket:
        await websocket.send(
            json.dumps(
                {
                    "event_id": "phase02_session_update",
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "model": model,
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
                        "instructions": (
                            "Always respond only in English. Speak at a calm, measured, "
                            "conversational pace with natural pauses and a warm tone. Do not "
                            "sound rushed or overly formal. For synthetic reference SYN-2042, "
                            "use the tool before answering."
                        ),
                        "tools": [
                            {
                                "type": "function",
                                "name": TOOL_NAME,
                                "description": "Check a fully synthetic reference.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "reference": {
                                            "type": "string",
                                            "enum": [TOOL_REFERENCE],
                                        }
                                    },
                                    "required": ["reference"],
                                    "additionalProperties": False,
                                },
                            }
                        ],
                        "tool_choice": "auto",
                    },
                }
            )
        )

        session_updated = False
        deadline = time.monotonic() + timeout_seconds
        while not session_updated:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RealtimeFailure("session_update_timeout")
            event = json.loads(await asyncio.wait_for(websocket.recv(), timeout=remaining))
            if event.get("type") == "error":
                raise RealtimeFailure("provider_error")
            retained = safe_event(event, round((time.monotonic() - started) * 1000))
            if retained:
                events.append(retained)
            session_updated = event.get("type") == "session.updated"

        bytes_per_chunk = 4_800  # 100 ms of mono PCM16 at 24 kHz.
        trailing_silence = bytes(48 * TRAILING_SILENCE_MS)
        streamed_audio = audio + trailing_silence
        for offset in range(0, len(streamed_audio), bytes_per_chunk):
            await websocket.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(
                            streamed_audio[offset : offset + bytes_per_chunk]
                        ).decode(),
                    }
                )
            )
            await asyncio.sleep(0.1)

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline and not continuation_completed:
            event = json.loads(
                await asyncio.wait_for(websocket.recv(), timeout=deadline - time.monotonic())
            )
            retained = safe_event(event, round((time.monotonic() - started) * 1000))
            if retained:
                events.append(retained)
            event_type = event.get("type")
            if event_type == "error":
                raise RealtimeFailure("provider_error")
            if event_type == "input_audio_buffer.speech_started":
                speech_started = all(
                    isinstance(event.get(field), expected_type)
                    for field, expected_type in (
                        ("event_id", str),
                        ("item_id", str),
                        ("audio_start_ms", int),
                    )
                )
            call = tool_call(event)
            if call is not None and not tool_completed:
                original_call_id, _ = validate_tool_call(call)
                await websocket.send(
                    json.dumps(
                        {
                            "event_id": "phase02_tool_output",
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": original_call_id,
                                "output": json.dumps(
                                    {"reference": TOOL_REFERENCE, "available": True}
                                ),
                            },
                        }
                    )
                )
                await websocket.send(
                    json.dumps({"event_id": "phase02_continue", "type": "response.create"})
                )
                tool_completed = True
            elif event_type == "response.done" and tool_completed:
                response = event.get("response")
                continuation_completed = (
                    isinstance(response, dict) and response.get("status") == "completed"
                )

    if not speech_started:
        raise RealtimeFailure("missing_speech_started_correlation")
    if not tool_completed or not continuation_completed or original_call_id is None:
        raise RealtimeFailure("incomplete_tool_roundtrip")
    return {
        "status": "passed",
        "probe": "realtime_websocket",
        "model": model,
        "transport": "websocket",
        "latency_ms": round((time.monotonic() - started) * 1000),
        "audio_sha256": hashlib.sha256(audio).hexdigest(),
        "audio_bytes": len(audio),
        "audio_duration_ms": round(len(audio) / 48),
        "trailing_silence_ms": TRAILING_SILENCE_MS,
        "tool_call_id": original_call_id,
        "tool_output_call_id": original_call_id,
        "events": events,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--result", type=Path)
    return parser.parse_args()


def write_result(result: dict[str, Any], path: Path | None) -> None:
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


def safe_failure_category(error: Exception) -> str:
    if isinstance(error, RealtimeFailure):
        return str(error) or "realtime_failure"
    if isinstance(error, TimeoutError):
        return "timeout"
    if isinstance(error, OSError):
        return "network"
    return "provider_or_network"


def main() -> int:
    args = parse_args()
    try:
        result = asyncio.run(run_probe(args.model, args.audio, args.timeout))
    except Exception as error:
        write_result(
            {
                "status": "failed",
                "probe": "realtime_websocket",
                "failure_category": safe_failure_category(error),
            },
            args.result,
        )
        return 1
    write_result(result, args.result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
