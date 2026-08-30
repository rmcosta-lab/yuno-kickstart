"""Explicitly authorized synthetic OpenAI Realtime trial; excluded by default."""

from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path

import pytest
from yuno_backend.integrations.openai import OpenAIRealtimeConfig, OpenAIRealtimeGateway
from yuno_backend.volta.realtime import (
    RealtimeResponseCompleted,
    RealtimeSessionRequest,
    RealtimeSpeechStarted,
    RealtimeToolCallRequested,
    RealtimeToolDefinition,
    RealtimeToolOutput,
)

pytestmark = pytest.mark.openai_credentialed


@pytest.mark.asyncio
async def test_synthetic_tool_roundtrip_and_speech_evidence_with_explicit_credentials() -> None:
    if os.environ.get("RUN_OPENAI_CREDENTIALED") != "1":
        pytest.skip("set RUN_OPENAI_CREDENTIALED=1 to authorize the synthetic provider test")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY is not available")

    request = RealtimeSessionRequest(
        instructions=(
            "Always speak only English. The user will say the synthetic reference SYN-2042. "
            "Call lookup_reference before answering. Never perform an operational mutation."
        ),
        safety_identifier=hashlib.sha256(b"phase-23-synthetic-operator").hexdigest(),
        voice="cedar",
        tools=(
            RealtimeToolDefinition(
                name="lookup_reference",
                description="Read one harmless synthetic reference.",
                parameters={
                    "type": "object",
                    "properties": {
                        "reference": {"type": "string", "enum": ["SYN-2042"]}
                    },
                    "required": ["reference"],
                    "additionalProperties": False,
                },
            ),
        ),
    )
    # Private synthetic PCM16/24 kHz speech plus trailing silence must be supplied explicitly.
    audio_path = os.environ.get("OPENAI_REALTIME_SYNTHETIC_PCM_PATH")
    if not audio_path:
        pytest.skip("OPENAI_REALTIME_SYNTHETIC_PCM_PATH is not available")
    audio = await asyncio.to_thread(Path(audio_path).read_bytes)
    if not audio or len(audio) > 4_000_000:
        pytest.skip("synthetic PCM artifact is empty or too large")

    evidence: RealtimeSpeechStarted | None = None
    tool_call: RealtimeToolCallRequested | None = None
    completed_after_tool = 0
    gateway = OpenAIRealtimeGateway(
        OpenAIRealtimeConfig(api_key=api_key, event_timeout_seconds=60)
    )
    async with gateway.connect(request) as connection:
        for offset in range(0, len(audio), 4_800):
            await connection.send_audio(audio[offset : offset + 4_800])
            await asyncio.sleep(0.1)
        async for event in connection.events():
            if isinstance(event, RealtimeSpeechStarted):
                evidence = event
            elif isinstance(event, RealtimeToolCallRequested):
                assert event.arguments == {"reference": "SYN-2042"}
                tool_call = event
                await connection.send_tool_output(
                    RealtimeToolOutput(
                        event_id="phase23_tool_output",
                        response_event_id="phase23_continue",
                        call_id=event.call_id,
                        result={"reference": "SYN-2042", "available": True},
                    )
                )
            elif isinstance(event, RealtimeResponseCompleted) and tool_call is not None:
                completed_after_tool += 1
                if completed_after_tool >= 2:
                    break

    assert evidence is not None
    assert evidence.audio_start_ms >= 0
    assert evidence.item_id and evidence.event_id
    assert tool_call is not None
    assert completed_after_tool >= 2
