"""Verify the exact public callback URL without creating a Twilio call."""

from __future__ import annotations

import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from twilio.request_validator import RequestValidator
from websockets.sync.client import connect

from scripts.twilio_feasibility.core import PublicUrls


def _required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _post(url: str, fields: dict[str, str], signature: str) -> int:
    request = Request(
        url,
        data=urlencode(fields).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Twilio-Signature": signature,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed HTTPS URL
            return response.status
    except HTTPError as error:
        return error.code


def _verify_media_websocket(url: str, signature: str) -> None:
    with connect(
        url,
        additional_headers={"X-Twilio-Signature": signature},
        open_timeout=10,
        close_timeout=10,
    ) as websocket:
        websocket.send('{"event":"connected"}')
        websocket.send('{"event":"stop"}')


def main() -> None:
    load_dotenv()
    urls = PublicUrls.parse(_required("TWILIO_PUBLIC_BASE_URL"))
    validator = RequestValidator(_required("TWILIO_AUTH_TOKEN"))
    valid_fields = {
        "CallSid": "CA00000000000000000000000000000000",
        "CallStatus": "initiated",
        "SequenceNumber": "0",
    }
    signature = validator.compute_signature(urls.status, valid_fields)
    valid_status = _post(urls.status, valid_fields, signature)
    tampered_status = _post(
        urls.status,
        {**valid_fields, "CallStatus": "completed"},
        signature,
    )
    if (valid_status, tampered_status) != (200, 403):
        raise SystemExit(f"public_preflight_failed valid={valid_status} tampered={tampered_status}")
    media_signature = validator.compute_signature(urls.media, {})
    _verify_media_websocket(urls.media, media_signature)
    print("public_preflight_passed valid=200 tampered=403 websocket=accepted")


if __name__ == "__main__":
    main()
