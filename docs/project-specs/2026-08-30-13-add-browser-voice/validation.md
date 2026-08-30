# Fase 13 — Validation

Record exact evidence, browser/model versions, and skipped credentialed checks before review.

## Coordination and documentation

- [x] Fases 09 and 12 remain merged with their required validation evidence; no conflicting phase or replacement Fase 13 ref appeared before claim or implementation.
- [x] Current official OpenAI Realtime WebRTC, conversation/tool-output, and interruption contracts are cited in implementation evidence.
- [x] Requirements, plan, ownership, fallback, and exclusions still match the roadmap gate; no shared decision changed.
- [x] `git diff --check` passes and the final status/diff contains only scoped files.

## Deterministic frontend and contract checks

- [x] `pnpm --dir frontend lint` passes.
- [x] `pnpm --dir frontend typecheck` passes.
- [x] `pnpm --dir frontend build` passes.
- [x] `make frontend-check` passes as the frontend-only handoff gate.
- [x] `pnpm --dir frontend test:e2e` passes the credential-free Chromium suite without API/provider mutation, console errors, storage changes, or viewport overflow.
- [x] Generated-model/function conformance is compile-time checked; no Pydantic, OpenAPI, Orval, generated, or API file changed, and backend edits are limited to the user-approved VAD threshold plus exact provider-payload tests.
- [x] Unknown, malformed, oversized, and duplicate tool events perform no extra `/v1` call; one provider call ID reuses one idempotency key, pending result, and safe output.
- [x] `record_quote` and `create_candidate_commitment` map to the exact generated route, request, header, result, and declared safe errors; provider and operational call IDs cannot be confused.
- [x] Tool output is exactly `{ ok: true, data: QuoteResponse | CommitmentResponse }` or `{ ok: false, error: ApiErrorResponse | { code: "TOOL_UNAVAILABLE" } }`; no transport wrapper, `Error.message`, raw response, or exception reaches Realtime.
- [x] Server-owned operation/session/version/quote/evidence context refreshes after every mutation; the model cannot invent identifiers, and candidate commitment remains disabled until a selected quote and attached synthetic evidence exist.
- [x] Stop, failed connect, unmount, and reconnect close the peer/channel, remove listeners, stop all tracks, clear remote audio, discard ephemeral references, and leave no overlapping attempt.
- [x] Source-level parser/dispatcher fixtures and Playwright cover malformed, unknown, duplicate, failed, pending-disconnect, and reconnected events with exact outcomes.
- [x] The text negotiation remains fully usable and no browser code infers mandate validity, carrier selection, quote eligibility, or commitment state.

## Browser smoke test

- [x] Run the deterministic journey with the in-app Browser Playwright API first, then inspect DOM, console, and network through Chrome DevTools.
- [x] Desktop and mobile layouts preserve readable state, usable controls, touch targets, and no page overflow or clipped content.
- [x] Keyboard-only Start, Stop, Reconnect, and text fallback have visible focus and meaningful, non-color status announcements.
- [x] Microphone allow and deny paths, blocked/unavailable playback, explicit Stop, route unmount, clean disconnect, forced disconnect, reconnect with a fresh session, and text fallback are exercised.
- [x] No active microphone indicator or Realtime connection survives teardown; no deliberately induced failure leaks a raw exception or provider payload.
- [x] Console and network inspection show no unexpected runtime error or failed request beyond deliberately induced, sanitized scenarios.

## Separately authorized Realtime evidence

- [x] In a supported browser with synthetic operation data, one live English WebRTC session establishes with natural pacing and remote playback.
- [x] One `record_quote` and one `create_candidate_commitment` tool roundtrip reach the typed BFF operations, return with the original provider call IDs, and refresh visible server-owned state.
- [x] English barge-in produces observed speech-start plus cancellation or truncation and a coherent continuation.
- [x] A forced disconnect or expired session visibly fails and reconnects only after explicit action with a fresh secret. An in-flight mutation settles when possible, triggers authoritative refetch, leaves the old call unresolved until reconciled, blocks another voice mutation, and is never replayed under a new provider call ID.
- [x] Provider/account/model restrictions and any skipped credentialed evidence are reported separately; text fallback remains reproducible.

## Security, privacy, and scope

- [x] The standard OpenAI key is absent from browser source, production bundle, DOM, local/session storage, IndexedDB, cookies, console, and network logs.
- [x] The ephemeral secret is absent from storage, UI, console, screenshots, fixtures, and committed artifacts, and exists only in the no-store response/local memory/required HTTPS authorization exchange.
- [x] Bearers, authorization headers, SDP, raw provider events, tool arguments/results, transcripts, and audio are absent from logs, errors, screenshots, and Git.
- [x] No real participant data, phone number, carrier contact, telephony claim, recording, Yuno/payment behavior, deployment, production access, or financial mutation entered the phase.
- [x] The only dependency change is the approved `@playwright/test` dev dependency and lockfile update; `.env.example`, generated clients, unrelated paths, and shared global specifications are unchanged.

## Recorded evidence — 2026-08-30

- Branch coordination: refreshed `origin`; Fase 09 PR #7 and Fase 12 PR #16 are merged with completed validation, and no open Fase 13 pull request or declared conflict was found.
- Official contracts reviewed: [Realtime calls WebRTC connection](https://developers.openai.com/api/reference/typescript/resources/realtime/subresources/calls/methods/create) and [Realtime client events](https://developers.openai.com/api/reference/resources/realtime/client-events). The implementation sends function output with the provider's original `call_id`, then requests the next response; interruption status follows the documented speech/truncation events.
- Frontend gate: `make frontend-check` passed and executed ESLint with zero warnings, `tsc --noEmit`, and a successful Next.js 16.3.3 production build of all routes.
- Durable browser automation: Playwright 1.62.1 Chromium passed `2/2` credential-free tests. The suite keyboard-opens the fallback, verifies all eight exact diagnostic results, rejects unexpected mutation/provider/WebSocket requests and console/runtime errors, detects diagnostic storage changes, and checks 390 × 844 horizontal fit. `test:e2e:realtime` exits with `2 skipped` unless the explicit credentialed flags are present.
- Browser: Chrome 152.0.0.0 on macOS. The production build ran at `http://127.0.0.1:3013/sessions`. Desktop measured 1728 × 906 with 1713 px document width; mobile measured 390 × 844 with 375 px document width. Neither viewport overflowed horizontally.
- All eight local diagnostics passed: malformed and unknown made 0 calls; duplicate reused one pending safe result and made 1 call; failed reduced to `TOOL_UNAVAILABLE` and made 1 call; refreshed operation v8 context was sent after the tool output and before `response.create`, allowing the next quote; an expired credential and a stalled SDP exchange terminated safely; pending disconnect blocked a new call without replay; reconnected accepted a new call only after reconciliation without replay.
- Chrome DevTools reported no console messages. The diagnostic interaction added no XHR, API, provider, or WebSocket request; the observed fetches were successful same-origin Next.js route prefetches only.
- Source/diff review confirmed the voice secret remains memory-only, no storage/logging/recording API is used, and no API, generated client, environment inventory, or shared global specification changed. Backend changes are limited to the documented VAD calibration and exact provider-payload tests; the manifest and lockfile changed only for the phase-owned Playwright dev dependency.
- Credentialed Chromium used the explicitly authorized real server-side OpenAI key, a 6.78-second English synthetic WAV, fake microphone permission, and synthetic local operations. The private artifact was copied with mode `0600` beneath the actual Python `tempfile.gettempdir()` evidence root; no audio or credential entered Git or a Playwright artifact.
- The isolated quote-and-commitment scenario passed `1/1`: OpenAI Realtime invoked exactly one `record_quote` and one `create_candidate_commitment`, both BFF mutations returned `201`, visible server state refreshed, and the safe outputs reused the two original provider call IDs. The forced-disconnect scenario passed in the full project run: one delayed quote settled once, the channel error entered reconciliation, a new mutation stayed blocked, reconnect minted a second client secret, and explicit Stop left one recorded quote with no replay.
- Provider nondeterminism remains visible rather than hidden: a later combined rerun passed the forced-disconnect scenario but timed out because the model did not issue `create_candidate_commitment` within 60 seconds after evidence attachment. The same scenario had already passed in isolation; the overall `test:e2e:realtime` command is therefore not claimed as consistently green.
- Browser validation at `http://localhost:3000/sessions` confirmed page identity, nonblank content, no framework overlay, no console warning/error, visible keyboard focus on the fallback control, Space-key activation, the `LOCAL · NO NETWORK` label, and `PASS · malformed JSON rejected · 0 calls`. The user directly confirmed the keyboard-only controls and non-color announcements, permission-denied and playback-blocked handling, teardown, disconnect, reconnect, fallback, and cleanup paths as validated.
- Human-assisted Chrome validation at `http://localhost:3000/comparison` established a live English WebRTC session with audible natural-paced playback. While the model was speaking, the user interrupted it with a new English question and confirmed that playback stopped and the model produced a coherent follow-up response. The same operation retained its eligible synthetic quote after an explicit server-state reload; no console warning or error was observed.
- The same human-assisted trial confirmed that explicit Stop released the Chrome microphone indicator and ended further responses. It also exposed that ordinary ambient noise could trigger interruption as if the user had spoken, motivating calibration of the server-owned Realtime policy rather than a browser override.
- The first user-approved calibration fixed `server_vad.threshold` at `0.7`, following the official guidance that a higher threshold requires louder input and may perform better in noisy environments. Exact provider-payload assertions passed in `64` focused adapter tests; `make python-check` then passed Ruff plus `421 passed, 29 skipped, 2 deselected`, and the restarted API returned `{"status":"ok"}`. The human retest still produced a false interruption from ambient noise, so `0.7` is explicitly rejected. The threshold was raised to `0.85`, which the user accepted as the correct final calibration without requiring further testing.
- The user explicitly confirmed the three remaining browser-smoke groups as validated: keyboard-only controls and non-color announcements; permission, playback, teardown, disconnect, reconnect, and fallback paths; and absence of a surviving microphone/Realtime connection or leaked raw failure.
- Deep-review remediation revalidation passed `make check` (`421 passed, 29 skipped, 2 deselected`, Ruff, ESLint, TypeScript, and Next.js build), `pnpm --dir frontend test:e2e` (`2/2`), and `git diff --check`. The integrated Browser at `http://localhost:3000/sessions` confirmed the correct page, nonblank rendered content, no framework overlay or console warning/error, and `PASS` results for both refreshed-context ordering and credential-expiry/stalled-SDP guards.
