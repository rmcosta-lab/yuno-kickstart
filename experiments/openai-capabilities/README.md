# OpenAI capability smoke harness

This isolated harness validates the Phase 02 provider assumptions without importing the Volta
application, changing a manifest, or persisting credentials. It emits only synthetic outputs and a
small allowlist of provider metadata. Raw provider payloads are never written. Generated synthetic
audio is written only under the ignored `private/` directory for the server probe.

## Safety boundary

- Put `OPENAI_API_KEY` in the process environment. Do not pass it as an argument or add it to a
  browser file.
- Use only synthetic speech and the fixture in `probe.py`.
- Keep generated synthetic audio under `private/` (ignored by Git), restrict access to the local
  operator, and delete it after the test window. Do not record an operator's voice.
- Do not export browser network response bodies: the short-lived client secret necessarily crosses
  the local `/token` response but is kept only in a JavaScript variable and is never logged or
  stored.
- Evidence files under `evidence/` are ignored until a human reviews and copies only redacted facts
  into the phase validation report.

## Deterministic checks

From the repository root:

```bash
uv run pytest experiments/openai-capabilities/tests
uv run ruff check experiments/openai-capabilities
```

## Credentialed model and extraction probes

List only the candidate models relevant to this gate:

```bash
uv run --env-file .env python experiments/openai-capabilities/probe.py models \
  --candidate gpt-5.6-luna --candidate gpt-5.6-terra \
  --candidate gpt-realtime-2.1 --candidate gpt-realtime-2.1-mini
```

Run strict extraction with an account-visible model:

```bash
uv run --env-file .env python experiments/openai-capabilities/probe.py extraction \
  --model gpt-5.6-luna --result experiments/openai-capabilities/evidence/extraction.json
```

Failures have stable categories (`authentication`, `model_unavailable`, `rate_limit`, `timeout`,
`network`, `provider`, or `invalid_response`) and a nonzero exit. Diagnostics omit provider message
text because it may echo request content.

## Server WebSocket probe

Generate a private, mono, 24 kHz, 16-bit PCM WAV containing only the synthetic English request. This
avoids recording an operator's voice:

```bash
uv run --env-file .env python experiments/openai-capabilities/synthesize_audio.py \
  --output experiments/openai-capabilities/private/english-synthetic.wav
```

Then run:

```bash
uv run --env-file .env --with 'websockets>=15,<16' \
  python experiments/openai-capabilities/realtime_ws.py \
  --model gpt-realtime-2.1 \
  --audio experiments/openai-capabilities/private/english-synthetic.wav \
  --result experiments/openai-capabilities/evidence/realtime-ws.json
```

The result retains safe event, item, response, and call identifiers, `audio_start_ms`, timings,
rate-limit numbers, and a SHA-256 digest/size/duration that correlates the private audio without
revealing its filename. It does not retain audio, transcripts, credentials, provider errors, or
full events. A successful exit requires a clean session update, VAD speech-start correlation, a
valid tool call, an output with the original `call_id`, and a completed continuation response.

## Browser WebRTC probe

Start the local token/static server and open the printed loopback URL in a supported browser:

```bash
uv run --env-file .env python experiments/openai-capabilities/browser_server.py \
  --model gpt-realtime-2.1
```

Use **Start microphone**, complete an English turn, use **Request synthetic tool** to exercise the
tool roundtrip, and speak while model audio is playing to exercise barge-in. The page has explicit
stop and text-fallback controls. **Download redacted evidence** creates only the safe event matrix;
review it before transferring facts to `validation.md`.

For the shortest operator retest:

1. Click **Start microphone**, allow microphone access, and wait for **Connected**.
2. Say: “Hello. Please answer in English and tell me briefly what you can help with.” Confirm that
   the `cedar` voice sounds calm, conversational, and not rushed.
3. Click **Request synthetic tool** and wait for the English availability response.
4. While that response is playing, say: “Stop. Summarize that in one sentence.” Confirm that the
   audio stops and the model continues coherently in English.
5. Click **Download redacted evidence**, then **Stop and disconnect**. Send the downloaded JSON for
   review; it contains no transcript, audio, or credential.
