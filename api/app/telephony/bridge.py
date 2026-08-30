"""Single-stream bounded Twilio Media Streams to Realtime bridge."""

import asyncio
import hashlib
import io
import json
import re
import wave
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from yuno_backend.volta.realtime import (
    RealtimeAudioDelta,
    RealtimeSpeechStarted,
    RealtimeToolCallRequested,
    RealtimeToolOutput,
)
from yuno_backend.volta.telephony import HumanHandoffAuthorityError

from app.telephony.media import Pcm24ToMulawConverter, twilio_payload_to_pcm24
from app.telephony.service import MediaBinding, StreamEvidence, TelephonyApplication

MAX_FRAME_BYTES = 16_384
MAX_STREAM_SECONDS = 900
MAX_EVIDENCE_PCM_BYTES = 24_000 * 2 * 30
_CALL_SID = re.compile(r"^CA[0-9a-fA-F]{32}$")
_STREAM_SID = re.compile(r"^MZ[0-9a-fA-F]{32}$")


class MediaProtocolError(ValueError):
    pass


def tool_idempotency_key(binding: MediaBinding, event: RealtimeToolCallRequested) -> str:
    digest = hashlib.sha256(f"{binding.call_session_id}:{event.call_id}".encode()).hexdigest()
    return f"twilio-tool-{digest}"


def _object(message: str) -> dict[str, Any]:
    if len(message.encode()) > MAX_FRAME_BYTES:
        raise MediaProtocolError("frame exceeds the size limit")
    try:
        value = json.loads(message)
    except json.JSONDecodeError as exc:
        raise MediaProtocolError("frame must be JSON") from exc
    if not isinstance(value, dict):
        raise MediaProtocolError("frame must be an object")
    return value


async def _receive_start(
    websocket: WebSocket, application: TelephonyApplication
) -> tuple[MediaBinding, str]:
    connected = _object(await websocket.receive_text())
    if connected != {"event": "connected", "protocol": "Call", "version": "1.0.0"}:
        raise MediaProtocolError("connected must be the first event")
    started = _object(await websocket.receive_text())
    start = started.get("start")
    if started.get("event") != "start" or not isinstance(start, dict):
        raise MediaProtocolError("start must be the second event")
    stream_sid = start.get("streamSid")
    call_sid = start.get("callSid")
    media_format = start.get("mediaFormat")
    parameters = start.get("customParameters")
    account_sid = start.get("accountSid")
    tracks = start.get("tracks")
    if (
        not isinstance(stream_sid, str)
        or _STREAM_SID.fullmatch(stream_sid) is None
        or not isinstance(call_sid, str)
        or _CALL_SID.fullmatch(call_sid) is None
        or started.get("streamSid") != stream_sid
        or started.get("sequenceNumber") != "1"
    ):
        raise MediaProtocolError("start identifiers are invalid")
    if media_format != {"encoding": "audio/x-mulaw", "sampleRate": 8000, "channels": 1}:
        raise MediaProtocolError("media format is unsupported")
    if account_sid != application.twilio_account_sid or tracks != ["inbound"]:
        raise MediaProtocolError("stream account or track is invalid")
    if not isinstance(parameters, dict) or not isinstance(parameters.get("binding"), str):
        raise MediaProtocolError("stream binding is missing")
    binding = await application.binding_for_stream(parameters["binding"], call_sid, stream_sid)
    if binding is None or binding.provider_call_id != call_sid:
        raise MediaProtocolError("stream binding is invalid")
    return binding, stream_sid


async def bridge_media_stream(websocket: WebSocket, application: TelephonyApplication) -> None:
    binding, stream_sid = await _receive_start(websocket, application)
    outcome = "DISCONNECTED"
    captured_audio = bytearray()
    evidence_marker: RealtimeSpeechStarted | None = None
    try:
        async with application.realtime_gateway.connect(
            application.realtime_session(binding)
        ) as realtime:

            async def twilio_to_realtime() -> None:
                nonlocal outcome
                last_sequence = 1
                last_chunk = 0
                while True:
                    frame = _object(await websocket.receive_text())
                    event = frame.get("event")
                    if frame.get("streamSid") != stream_sid:
                        raise MediaProtocolError("frame stream identifier is invalid")
                    try:
                        sequence = int(frame.get("sequenceNumber", ""))
                    except (TypeError, ValueError) as exc:
                        raise MediaProtocolError("frame sequence is invalid") from exc
                    if sequence <= last_sequence:
                        raise MediaProtocolError("frame sequence is not monotonic")
                    last_sequence = sequence
                    if event == "stop":
                        stop = frame.get("stop")
                        if (
                            not isinstance(stop, dict)
                            or stop.get("accountSid") != binding.account_sid
                        ):
                            raise MediaProtocolError("stop account is invalid")
                        outcome = "COMPLETED"
                        return
                    if event != "media":
                        raise MediaProtocolError("unexpected stream event")
                    media = frame.get("media")
                    if not isinstance(media, dict) or media.get("track") != "inbound":
                        raise MediaProtocolError("only inbound media is accepted")
                    payload = media.get("payload")
                    try:
                        chunk = int(media.get("chunk", ""))
                    except (TypeError, ValueError) as exc:
                        raise MediaProtocolError("media chunk is invalid") from exc
                    if chunk <= last_chunk:
                        raise MediaProtocolError("media chunk is not monotonic")
                    last_chunk = chunk
                    if not isinstance(payload, str):
                        raise MediaProtocolError("media payload is missing")
                    pcm = twilio_payload_to_pcm24(payload)
                    if binding.inbound and len(captured_audio) < MAX_EVIDENCE_PCM_BYTES:
                        remaining = MAX_EVIDENCE_PCM_BYTES - len(captured_audio)
                        captured_audio.extend(pcm[:remaining])
                    await realtime.send_audio(pcm)

            async def realtime_to_twilio() -> None:
                nonlocal evidence_marker
                converter = Pcm24ToMulawConverter()
                async for event in realtime.events():
                    if isinstance(event, RealtimeAudioDelta):
                        try:
                            await application.ensure_ai_speech_allowed(binding.call_session_id)
                        except HumanHandoffAuthorityError:
                            await websocket.send_json({"event": "clear", "streamSid": stream_sid})
                            continue
                        payload = converter.convert(event.audio)
                        if payload is not None:
                            try:
                                await application.ensure_ai_speech_allowed(
                                    binding.call_session_id
                                )
                            except HumanHandoffAuthorityError:
                                await websocket.send_json(
                                    {"event": "clear", "streamSid": stream_sid}
                                )
                                continue
                            await websocket.send_json(
                                {
                                    "event": "media",
                                    "streamSid": stream_sid,
                                    "media": {"payload": payload},
                                }
                            )
                    elif isinstance(event, RealtimeSpeechStarted):
                        if evidence_marker is None:
                            evidence_marker = event
                        await websocket.send_json({"event": "clear", "streamSid": stream_sid})
                    elif isinstance(event, RealtimeToolCallRequested):
                        key = tool_idempotency_key(binding, event)
                        result = await application.delegate_tool(binding, event, key)
                        await realtime.send_tool_output(
                            RealtimeToolOutput(
                                event_id=f"tool-output-{event.event_id}",
                                response_event_id=f"response-{event.event_id}",
                                call_id=event.call_id,
                                result=result,
                            )
                        )

            async def authority_to_twilio() -> None:
                await application.wait_for_ai_authority_revoked(binding.call_session_id)
                await websocket.send_json({"event": "clear", "streamSid": stream_sid})

            tasks = {
                asyncio.create_task(twilio_to_realtime()),
                asyncio.create_task(realtime_to_twilio()),
                asyncio.create_task(authority_to_twilio()),
            }
            done, pending = await asyncio.wait(
                tasks,
                timeout=MAX_STREAM_SECONDS,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            if not done:
                outcome = "TIMEOUT"
                raise TimeoutError("media stream duration exceeded")
            for task in done:
                task.result()
    except WebSocketDisconnect:
        outcome = "DISCONNECTED"
    finally:
        evidence = None
        if binding.inbound and outcome == "COMPLETED":
            if (
                captured_audio
                and evidence_marker is not None
                and binding.correlation_id is not None
            ):
                buffer = io.BytesIO()
                with wave.open(buffer, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(24_000)
                    wav.writeframes(captured_audio)
                evidence = StreamEvidence(
                    audio=buffer.getvalue(),
                    audio_start_ms=evidence_marker.audio_start_ms,
                    item_id=evidence_marker.item_id,
                    event_id=evidence_marker.event_id,
                    correlation_id=binding.correlation_id,
                )
            else:
                outcome = "INSUFFICIENT_EVIDENCE"
        await application.stream_finished(binding, outcome, evidence)
