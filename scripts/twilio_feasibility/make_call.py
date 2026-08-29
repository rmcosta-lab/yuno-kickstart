"""Place the single explicitly authorized Phase 03 smoke call."""

from __future__ import annotations

import argparse
import hashlib
import os

from dotenv import load_dotenv
from twilio.rest import Client

from scripts.twilio_feasibility.core import PublicUrls

CONFIRMATION = "AUTHORIZE_ONE_UNRECORDED_CALL"


def _required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != CONFIRMATION:
        raise SystemExit("Exact call confirmation was not provided")

    account_sid = _required("TWILIO_ACCOUNT_SID")
    auth_token = _required("TWILIO_AUTH_TOKEN")
    from_number = _required("TWILIO_FROM_NUMBER")
    to_number = _required("TWILIO_TO_NUMBER")
    urls = PublicUrls.parse(_required("TWILIO_PUBLIC_BASE_URL"))

    client = Client(account_sid, auth_token)
    call = client.calls.create(
        from_=from_number,
        to=to_number,
        url=urls.twiml,
        method="POST",
        status_callback=urls.status,
        status_callback_method="POST",
        status_callback_event=["initiated", "ringing", "answered", "completed"],
        record=False,
        timeout=20,
        time_limit=60,
    )
    safe_call_alias = hashlib.sha256(call.sid.encode()).hexdigest()[:12]
    print(f"call_created alias-{safe_call_alias}")


if __name__ == "__main__":
    main()
