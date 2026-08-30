# Browser voice end-to-end tests

The default suite is credential-free and safe for continuous integration:

```bash
pnpm test:e2e
```

Install the pinned Chromium build once when the Playwright cache is empty:

```bash
pnpm test:e2e:install
```

The separately authorized Realtime suite creates only synthetic local Volta
operations and uses the server-side OpenAI configuration from the repository
root `.env`. It is skipped unless provider use is explicitly enabled. Export
only the browser-test inputs below; never expose `OPENAI_API_KEY` to the
frontend process.

```bash
RUN_OPENAI_CREDENTIALED=1 \
VOLTA_DEMO_BEARER_TOKEN='<same local demo bearer configured in ../.env>' \
OPENAI_REALTIME_SYNTHETIC_WAV_PATH='/absolute/private/synthetic.wav' \
VOLTA_REALTIME_EVIDENCE_REFERENCE='phase13/private-synthetic.wav' \
VOLTA_REALTIME_EVIDENCE_AUDIO_START_MS='4200' \
VOLTA_REALTIME_EVIDENCE_ITEM_ID='synthetic-item-001' \
VOLTA_REALTIME_EVIDENCE_EVENT_ID='synthetic-event-001' \
pnpm test:e2e:realtime
```

The evidence reference must already resolve beneath
`<Python tempfile.gettempdir()>/yuno-volta-text-evidence` (on macOS this is
usually under `/var/folders`, not `/tmp`); audio remains private and outside
Git. The credentialed project disables Playwright screenshots, traces, and
video so a failed provider trial cannot retain bearer, SDP, audio, transcript,
or tool payloads. The demo bearer input is also cleared immediately after
connection.

`PLAYWRIGHT_BASE_URL`, `PLAYWRIGHT_API_URL`, and
`PLAYWRIGHT_SKIP_WEB_SERVER=1` may target already-running local services. The
qualitative natural-pacing judgment remains a separately recorded human check;
these tests assert connection, typed tool roundtrips, call-ID correlation,
single-mutation behavior, reconciliation, and explicit fresh-session reconnect.
