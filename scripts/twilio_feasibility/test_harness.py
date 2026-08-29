"""Deterministic tests for the disposable Phase 03 harness."""

from __future__ import annotations

from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from scripts.twilio_feasibility.app import MARK_NAME, Settings, create_app
from scripts.twilio_feasibility.core import (
    DISCLOSURE_LANGUAGE,
    DISCLOSURE_SCRIPT,
    PublicUrls,
    consent_twiml,
    disclosure_twiml,
    tone_frames,
)

TOKEN = "phase03-test-token"
URLS = PublicUrls.parse("https://phase03.example.test")


def _signature(url: str, fields: dict[str, str]) -> str:
    return RequestValidator(TOKEN).compute_signature(url, fields)


def test_public_urls_require_https_and_derive_wss() -> None:
    assert URLS.media == "wss://phase03.example.test/twilio/media"


def test_tone_is_500_milliseconds_of_headerless_mulaw_frames() -> None:
    frames = tone_frames()
    assert len(frames) == 25
    assert all(len(frame) == 216 for frame in frames)


def test_twiml_discloses_before_consent_and_stream() -> None:
    disclosure = disclosure_twiml(URLS)
    consent = consent_twiml(URLS, affirmed=True)
    decline = consent_twiml(URLS, affirmed=False)

    assert DISCLOSURE_SCRIPT in disclosure
    assert f'language="{DISCLOSURE_LANGUAGE}"' in disclosure
    assert "<Stream" not in disclosure
    assert 'input="dtmf"' in disclosure
    assert URLS.media in consent
    assert "<Stream" in consent
    assert "<Hangup" in decline


def test_http_callbacks_require_exact_valid_signature() -> None:
    app = create_app(Settings(auth_token=TOKEN, urls=URLS))
    client = TestClient(app)
    fields = {"CallSid": "CA-test", "CallStatus": "initiated"}
    signature = _signature(URLS.status, fields)

    accepted = client.post(
        "/twilio/status",
        data=fields,
        headers={"x-twilio-signature": signature},
    )
    rejected = client.post(
        "/twilio/status",
        data={**fields, "CallStatus": "completed"},
        headers={"x-twilio-signature": signature},
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 403


def test_media_stream_sends_tone_then_mark_after_inbound_media() -> None:
    app = create_app(Settings(auth_token=TOKEN, urls=URLS, max_stream_seconds=10))
    client = TestClient(app)
    signature = _signature(URLS.media, {})

    with client.websocket_connect(
        "/twilio/media",
        headers={"x-twilio-signature": signature},
    ) as websocket:
        websocket.send_json({"event": "connected"})
        websocket.send_json({"event": "start", "start": {"streamSid": "MZ-test"}})
        websocket.send_json({"event": "media", "media": {"payload": "not-retained"}})
        returned = [websocket.receive_json() for _ in range(26)]
        websocket.send_json({"event": "mark", "mark": {"name": MARK_NAME}})
        websocket.send_json({"event": "stop"})

    assert [message["event"] for message in returned] == ["media"] * 25 + ["mark"]
    assert returned[-1]["mark"]["name"] == MARK_NAME
