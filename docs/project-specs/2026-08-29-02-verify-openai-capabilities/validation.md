# Phase 02 validation

Keep every criterion unchecked until its redacted evidence is recorded. Raw secrets, authorization headers, full provider payloads, personal data, and private audio must never be committed.

## Implementation status — 2026-08-29

The isolated smoke harness is implemented under `experiments/openai-capabilities/**`. It includes a
strict Responses API extraction probe, account-visible model candidate probe, redacted Realtime
WebSocket probe, loopback-only client-secret server, keyboard-operable WebRTC page, deterministic
text fallback, exact synthetic tool-call validation, safe event capture, and deterministic tests.
No product layer, manifest, lockfile, generated contract, shared specification, or environment
inventory changed.

An ignored local `.env` contains `OPENAI_API_KEY`. On 2026-08-29, the authenticated model-catalog
probe returned HTTP 200 in 752 ms and listed `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`,
`gpt-realtime-2.1`, and `gpt-realtime-2.1-mini`. A strict extraction call through `gpt-5.6-luna`
returned HTTP 200 in 3,320 ms, and a server WebSocket session through `gpt-realtime-2.1` completed
the VAD, tool-call, tool-output, and continuation sequence in 13,025 ms. The private input was
generated with `gpt-4o-mini-tts` and the `cedar` voice, so no operator recording was needed.

The post-change browser WebRTC retest passed under operator control. The operator confirmed English
output and correct behavior with the `cedar` voice and calm, conversational pacing instructions.
Direct review of ignored `phase02-webrtc-redacted.json` found 39 allowlisted events, four correlated
speech turns, three audio truncations, one cancelled response during barge-in, three completed
responses after interruption, three rate-limit updates, and no provider `error` event. Codex browser
control was not required, and the artifact contains no transcript, audio, or credential.

Shared-spec pull request #2 merged into `main` as `8f1685e` on 2026-08-29. The mission, technology
stack, roadmap, and challenge plan now consistently define English, natural pacing, and English
interruption recovery as the authoritative project gate.

## Official contract and account access

- [x] On 2026-08-29, refreshed [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Realtime overview](https://developers.openai.com/api/docs/guides/realtime), [GPT-Realtime-2.1](https://developers.openai.com/api/docs/models/gpt-realtime-2.1), [WebRTC and client secrets](https://developers.openai.com/api/docs/guides/realtime-webrtc), [WebSocket](https://developers.openai.com/api/docs/guides/realtime-websocket), [tool outputs and interruptions](https://developers.openai.com/api/docs/guides/realtime-conversations), [voice activity detection](https://developers.openai.com/api/docs/guides/realtime-vad), [Text to speech](https://developers.openai.com/api/docs/guides/text-to-speech), and [Responses create](https://developers.openai.com/api/reference/resources/responses/methods/create).
- [x] The authenticated `/v1/models` catalog lists all five candidates above, and actual extraction and Realtime calls succeeded with `gpt-5.6-luna` and `gpt-realtime-2.1`.
- [x] Safe observed limits and latency are recorded: extraction had 4,999 of 5,000 requests and 2,000,000 of 2,000,000 tokens remaining; Realtime had 197,496 of 200,000 tokens remaining. No quota, spend, or region blocker appeared. The probes do not expose an account-tier label.
- [x] Direct inspection and the harness use current GA `/v1/responses`, `/v1/realtime/client_secrets`, `/v1/realtime/calls`, and `/v1/realtime?model=...` shapes with no obsolete beta header.

## Structured extraction

- [x] A credentialed Responses API probe returned the canonical synthetic English intake as the strict JSON Schema through `gpt-5.6-luna` (HTTP 200, 3,320 ms).
- [x] `uv run pytest experiments/openai-capabilities/tests` independently rejects missing/extra fields and invented or incorrect values; the schema fixes price, currency, window, and explicit null fields.
- [x] Thirteen deterministic tests cover redacted authentication, unavailable-model, rate-limit, timeout, provider, unexpected-event, invalid-output, unsafe-tool, English session, natural-voice, and private-output paths; manual no-key model and WebSocket invocations returned safe `authentication` results with exit 1.
- [x] Selected extraction model: `gpt-5.6-luna`. Deterministic fallback: the isolated browser harness keeps an operator-copyable English text note available after connection failure or teardown.

## Realtime server WebSocket

- [x] A credentialed server WebSocket session reached `gpt-realtime-2.1`, completed the required roundtrip, and closed cleanly in 13,025 ms.
- [x] Synthetic English audio input succeeded and the English-only output session completed with safe terminal event evidence. Voice configuration is `cedar` with calm, conversational pacing instructions; human assessment of language and naturalness remains part of the browser retest.
- [x] `input_audio_buffer.speech_started` recorded `audio_start_ms: 20` with correlated item and event IDs. The ignored private PCM16/24 kHz WAV is represented in evidence only by SHA-256, byte count, and duration.
- [x] Timeout, provider `error`, disconnect, and rate-limit paths are safely categorized or allowlisted without logging a standard or ephemeral credential. The first run timed out until 1,200 ms of trailing silence was added for deterministic server VAD turn closure.

## Realtime browser WebRTC

- [x] Direct source review confirms the server exchanges the standard key for a narrowly scoped client secret; the browser keeps only that short-lived value in a local variable. The successful WebRTC session and redacted artifact contain no standard key, client secret, storage write, authorization value, screenshot, or raw network payload.
- [x] The operator confirmed that a supported browser established the current GA WebRTC call with microphone and audio playback, then used the explicit teardown control.
- [x] The operator confirmed English speech and correct behavior with the adjusted `cedar` voice and pace. Four correlated speech turns and completed post-interruption responses reproduce coherent continuation.
- [x] Three `conversation.item.truncated` events reproduce barge-in. One active response ended as `cancelled`, and later responses reached `completed`.
- [x] Direct source and local failure-path inspection confirm microphone denial and connection failures produce textual status while preserving the English deterministic text fallback; no-key `/token` returned a redacted `503`.
- [x] Direct HTML/CSS/JavaScript review confirms native keyboard-operable controls, textual live status, labeled inputs, and status communication that does not depend on color alone.

## Tool-call roundtrip

- [x] In the server WebSocket probe, the model emitted the fixed synthetic tool call with schema-valid `{"reference":"SYN-2042"}` arguments.
- [x] The harness returned `function_call_output` with the original `call_id`, requested continuation, and received a completed follow-up response with the same call correlation.
- [x] Deterministic tests prove invalid or non-canonical tool arguments are rejected before the harmless local synthetic lookup; the harness has no product-state mutation.

## Security and evidence handling

- [x] Direct fixture review confirms only synthetic references, locations, windows, rates, and null carrier/contact fields.
- [x] Repository diff and pattern review found no API key, client secret, authorization value, raw provider payload, private audio, or personal data; logs retain only an allowlist of safe metadata.
- [x] A fully synthetic 266,444-byte WAV was generated under ignored `experiments/openai-capabilities/private/`, used only for the server probe, and deleted on 2026-08-29 before handoff. No operator recording was created.
- [x] This report leaves every unexecuted credentialed/browser item unchecked and does not treat the implemented fallback or documented capability as account evidence.

## Repository checks

- [x] `uv run ruff check .` — passed on 2026-08-29.
- [x] `uv run pytest` — 15 passed with one existing Starlette deprecation warning after the English/voice changes; `uv run pytest experiments/openai-capabilities/tests` — 13 passed.
- [x] `pnpm lint` from `frontend/` — not applicable; no `frontend/**` file changed.
- [x] `pnpm build` from `frontend/` — not applicable; no `frontend/**` file changed.
- [x] `git diff --check` — passed after merging current `origin/main`; the Phase 02 delta contains only the authorized phase directory and `experiments/openai-capabilities/**`.
- [x] Final secret/privacy and diff review passed after browser evidence review and the shared-spec merge. Credentialed JSON artifacts remain ignored and unstaged; the synthetic WAV has been deleted.

Additional local smoke evidence: `node --check experiments/openai-capabilities/web/app.js` passed;
the loopback server returned `200` with all primary controls, `/token` returned a redacted `503`
without a key, and a token request without the harness header returned `403`. The reviewed browser
artifact contains only allowlisted event metadata and the operator supplied the English/naturalness
assessment that redacted events intentionally omit.

After merging current `origin/main`, `make check` repeated Ruff and all 15 Python tests successfully,
then stopped because `pnpm` is unavailable on `PATH`. No Phase 02 file exists under `frontend/**`,
and the merged Phase 01 frontend baseline is outside this phase delta, so frontend lint/build remain
not applicable rather than reported as passed.

## Gate decision

- [x] **PASS:** every roadmap capability is backed by current official documentation and credentialed evidence, limits and fallbacks are recorded, and the English gate is authoritative after shared-spec merge `8f1685e`. Phases 11 and 13 may depend on the merged Phase 02 result.
- [ ] **BLOCKED:** no account, quota, environment, privacy, provider-contract, browser, or shared-spec blocker remains.
