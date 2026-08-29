# Phase 03 Twilio feasibility harness

This disposable harness exists only to collect the redacted live evidence required by Phase 03. It does not import the product API or backend, call OpenAI, record calls, retain media, or define later application contracts.

## Secret configuration

Set these values only in a local secret store or the authorized temporary host. Never commit them or use a `NEXT_PUBLIC_` prefix:

```text
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_FROM_NUMBER
TWILIO_TO_NUMBER
TWILIO_PUBLIC_BASE_URL=https://canonical-public-host
PHASE03_MAX_STREAM_SECONDS=60
```

The public base must be the exact externally visible HTTPS origin. The harness derives these signed endpoints:

```text
POST https://canonical-public-host/twilio/twiml
POST https://canonical-public-host/twilio/consent
POST https://canonical-public-host/twilio/status
WSS  wss://canonical-public-host/twilio/media
```

Run the server without changing repository manifests:

```bash
uvx --from uvicorn --with fastapi --with twilio --with python-dotenv \
  --with websockets \
  uvicorn scripts.twilio_feasibility.app:create_app --factory \
  --host 127.0.0.1 --port 8000 --ws-max-size 1048576 \
  --env-file .env --no-access-log --log-level warning
```

The Brazilian participant hears the `pt-BR` disclosure before streaming and must press `1`. The server accepts at most one Media Stream, waits for the first inbound media event, sends 25 paced 20-millisecond headerless mu-law frames containing a deterministic 400-hertz tone, and then sends mark `phase03-tone-1`. The call request has a 20-second answer timeout and a 60-second maximum duration. Logs contain event names, timestamps, counts, and process-local aliases only.

## Verification

Run the isolated tests without modifying the lockfile:

```bash
uvx --from pytest --with fastapi --with httpx --with pytest-asyncio --with twilio \
  pytest scripts/twilio_feasibility/test_harness.py
```

After the public hostname is fixed in `TWILIO_PUBLIC_BASE_URL`, verify the exact external status URL and WSS upgrade with the real primary Auth Token but synthetic fields. This sends one valid request, one tampered request, and one empty synthetic WebSocket lifecycle to the disposable harness; it does not contact the Twilio Calls API:

```bash
uvx --from twilio --with python-dotenv --with websockets \
  python -m scripts.twilio_feasibility.preflight_public
```

Do not run `make_call.py` merely to test configuration. It creates a billable external call and has no automatic retry. Run it only after the endpoint is public, exact callback signatures pass, the operator has reviewed the public URLs, participant label, disclosure, recording-disabled behavior, duration, expected charge, and cleanup, and the operator has explicitly authorized that exact call:

```bash
uvx --from twilio --with python-dotenv \
  python -m scripts.twilio_feasibility.make_call \
  --confirm AUTHORIZE_ONE_UNRECORDED_CALL
```
