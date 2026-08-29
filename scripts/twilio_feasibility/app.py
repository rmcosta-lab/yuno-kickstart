"""FastAPI HTTPS/WSS boundary for the authorized Phase 03 smoke test."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qsl

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from twilio.request_validator import RequestValidator

from scripts.twilio_feasibility.core import (
    PublicUrls,
    SafeAliases,
    consent_twiml,
    disclosure_twiml,
    tone_frames,
)

LOGGER = logging.getLogger("twilio_feasibility")
MARK_NAME = "phase03-tone-1"


@dataclass(frozen=True)
class Settings:
    auth_token: str
    urls: PublicUrls
    max_stream_seconds: int = 60

    @classmethod
    def from_env(cls) -> Settings:
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        public_base_url = os.environ.get("TWILIO_PUBLIC_BASE_URL", "")
        if not auth_token:
            raise RuntimeError("TWILIO_AUTH_TOKEN is required")
        if not public_base_url:
            raise RuntimeError("TWILIO_PUBLIC_BASE_URL is required")
        max_stream_seconds = int(os.environ.get("PHASE03_MAX_STREAM_SECONDS", "60"))
        if not 10 <= max_stream_seconds <= 120:
            raise RuntimeError("PHASE03_MAX_STREAM_SECONDS must be between 10 and 120")
        return cls(
            auth_token=auth_token,
            urls=PublicUrls.parse(public_base_url),
            max_stream_seconds=max_stream_seconds,
        )


def _configure_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    LOGGER.setLevel(logging.INFO)


def _log_event(event: str, **fields: object) -> None:
    LOGGER.info(
        json.dumps(
            {
                "event": event,
                "timestamp": datetime.now(UTC).isoformat(),
                **{key: value for key, value in fields.items() if value is not None},
            },
            sort_keys=True,
        )
    )


def _external_http_url(request: Request, urls: PublicUrls) -> str:
    query = f"?{request.url.query}" if request.url.query else ""
    return f"{urls.base}{request.url.path}{query}"


async def _form_fields(request: Request) -> dict[str, str]:
    body = await request.body()
    return dict(parse_qsl(body.decode("utf-8"), keep_blank_values=True))


def create_app(settings: Settings | None = None) -> FastAPI:
    _configure_logging()
    resolved = settings or Settings.from_env()
    validator = RequestValidator(resolved.auth_token)
    aliases = SafeAliases()
    connection_guard = asyncio.Lock()
    active_media_connection = False
    app = FastAPI(
        title="Phase 03 Twilio feasibility harness",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    async def verified_form(request: Request) -> dict[str, str] | None:
        fields = await _form_fields(request)
        signature = request.headers.get("x-twilio-signature", "")
        valid = validator.validate(
            _external_http_url(request, resolved.urls),
            fields,
            signature,
        )
        if not valid:
            _log_event("signature_rejected", path=request.url.path)
            return None
        return fields

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/twilio/twiml")
    async def twiml(request: Request) -> Response:
        fields = await verified_form(request)
        if fields is None:
            return Response(status_code=403)
        _log_event("twiml_requested", call=aliases.for_value(fields.get("CallSid")))
        return Response(disclosure_twiml(resolved.urls), media_type="application/xml")

    @app.post("/twilio/consent")
    async def consent(request: Request) -> Response:
        fields = await verified_form(request)
        if fields is None:
            return Response(status_code=403)
        affirmed = fields.get("Digits") == "1"
        _log_event(
            "continue_consent",
            call=aliases.for_value(fields.get("CallSid")),
            outcome="affirmed" if affirmed else "declined",
        )
        return Response(
            consent_twiml(resolved.urls, affirmed=affirmed),
            media_type="application/xml",
        )

    @app.post("/twilio/status")
    async def status(request: Request) -> Response:
        fields = await verified_form(request)
        if fields is None:
            return Response(status_code=403)
        _log_event(
            "call_status",
            call=aliases.for_value(fields.get("CallSid")),
            provider_status=fields.get("CallStatus"),
            sequence=fields.get("SequenceNumber"),
        )
        return Response(status_code=200)

    @app.websocket("/twilio/media")
    async def media(websocket: WebSocket) -> None:
        nonlocal active_media_connection
        signature = websocket.headers.get("x-twilio-signature", "")
        if not validator.validate(resolved.urls.media, {}, signature):
            _log_event("media_signature_rejected")
            await websocket.close(code=1008)
            return

        async with connection_guard:
            if active_media_connection:
                _log_event("media_connection_rejected", reason="already_active")
                await websocket.close(code=1013)
                return
            active_media_connection = True

        stream_sid: str | None = None
        stream_alias: str | None = None
        tone_sent = False
        media_frames_received = 0
        try:
            await websocket.accept()
            async with asyncio.timeout(resolved.max_stream_seconds):
                while True:
                    message = await websocket.receive_json()
                    event = message.get("event")
                    if event == "connected":
                        _log_event("media_connected")
                    elif event == "start":
                        stream_sid = message.get("start", {}).get("streamSid")
                        stream_alias = aliases.for_value(stream_sid)
                        _log_event("media_started", stream=stream_alias)
                    elif event == "media":
                        media_frames_received += 1
                        if not tone_sent and stream_sid:
                            for payload in tone_frames():
                                await websocket.send_json(
                                    {
                                        "event": "media",
                                        "streamSid": stream_sid,
                                        "media": {"payload": payload},
                                    }
                                )
                                await asyncio.sleep(0.02)
                            await websocket.send_json(
                                {
                                    "event": "mark",
                                    "streamSid": stream_sid,
                                    "mark": {"name": MARK_NAME},
                                }
                            )
                            tone_sent = True
                            _log_event(
                                "deterministic_tone_sent",
                                stream=stream_alias,
                                frame_count=len(tone_frames()),
                                mark=MARK_NAME,
                            )
                    elif event == "mark":
                        mark_name = message.get("mark", {}).get("name")
                        _log_event(
                            "media_mark_returned",
                            stream=stream_alias,
                            mark=mark_name if mark_name == MARK_NAME else "unexpected",
                        )
                    elif event == "stop":
                        _log_event(
                            "media_stopped",
                            stream=stream_alias,
                            inbound_frame_count=media_frames_received,
                        )
                        break
        except TimeoutError:
            _log_event("media_timeout", stream=stream_alias)
        except WebSocketDisconnect:
            _log_event("media_disconnected", stream=stream_alias)
        finally:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1000)
            async with connection_guard:
                active_media_connection = False
            _log_event("media_cleanup", stream=stream_alias)

    return app
