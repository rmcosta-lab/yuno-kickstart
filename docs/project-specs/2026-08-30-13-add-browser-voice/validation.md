# Fase 13 — Validation

Record exact evidence, browser/model versions, and skipped credentialed checks before review.

## Coordination and documentation

- [ ] Fases 09 and 12 remain merged with their required validation evidence; no conflicting phase or replacement Fase 13 ref appeared before claim or implementation.
- [ ] Current official OpenAI Realtime WebRTC, conversation/tool-output, and interruption contracts are cited in implementation evidence.
- [ ] Requirements, plan, ownership, fallback, and exclusions still match the roadmap gate; any shared decision change used its owning workflow.
- [ ] `git diff --check` passes and the final status/diff contains only scoped files.

## Deterministic frontend and contract checks

- [ ] `pnpm --dir frontend lint` passes.
- [ ] `pnpm --dir frontend typecheck` passes.
- [ ] `pnpm --dir frontend build` passes.
- [ ] `make frontend-check` passes as the frontend-only handoff gate.
- [ ] Generated-model/function conformance is compile-time checked; no Pydantic, OpenAPI, Orval, generated, API, or backend file changed.
- [ ] Unknown, malformed, oversized, and duplicate tool events perform no extra `/v1` call; one provider call ID reuses one idempotency key, pending result, and safe output.
- [ ] `record_quote` and `create_candidate_commitment` map to the exact generated route, request, header, result, and declared safe errors; provider and operational call IDs cannot be confused.
- [ ] Tool output is exactly `{ ok: true, data: QuoteResponse | CommitmentResponse }` or `{ ok: false, error: ApiErrorResponse | { code: "TOOL_UNAVAILABLE" } }`; no transport wrapper, `Error.message`, raw response, or exception reaches Realtime.
- [ ] Server-owned operation/session/version/quote/evidence context refreshes after every mutation; the model cannot invent identifiers, and candidate commitment remains disabled until a selected quote and attached synthetic evidence exist.
- [ ] Stop, failed connect, unmount, and reconnect close the peer/channel, remove listeners, stop all tracks, clear remote audio, discard ephemeral references, and leave no overlapping attempt.
- [ ] Source-level parser/dispatcher fixtures and deterministic browser scenario controls cover malformed, unknown, duplicate, failed, pending-disconnect, and reconnected events; exact manual outcomes are recorded because the package has no test command.
- [ ] The text negotiation remains fully usable and no browser code infers mandate validity, carrier selection, quote eligibility, or commitment state.

## Browser smoke test

- [ ] Run the user journey with Playwright first, then inspect DOM, console, and network through Chrome DevTools.
- [ ] Desktop and mobile layouts preserve readable state, usable controls, touch targets, and no page overflow or clipped content.
- [ ] Keyboard-only Start, Stop, Reconnect, and text fallback have visible focus and meaningful, non-color status announcements.
- [ ] Microphone allow and deny paths, blocked/unavailable playback, explicit Stop, route unmount, clean disconnect, forced disconnect, reconnect with a fresh session, and text fallback are exercised.
- [ ] No active microphone indicator or Realtime connection survives teardown; no deliberately induced failure leaks a raw exception or provider payload.
- [ ] Console and network inspection show no unexpected runtime error or failed request beyond deliberately induced, sanitized scenarios.

## Separately authorized Realtime evidence

- [ ] In a supported browser with synthetic operation data, one live English WebRTC session establishes with natural pacing and remote playback.
- [ ] One `record_quote` and one `create_candidate_commitment` tool roundtrip reach the typed BFF operations, return with the original provider call IDs, and refresh visible server-owned state.
- [ ] English barge-in produces observed speech-start plus cancellation or truncation and a coherent continuation.
- [ ] A forced disconnect or expired session visibly fails and reconnects only after explicit action with a fresh secret. An in-flight mutation settles when possible, triggers authoritative refetch, leaves the old call unresolved until reconciled, blocks another voice mutation, and is never replayed under a new provider call ID.
- [ ] Provider/account/model restrictions and any skipped credentialed evidence are reported separately; text fallback remains reproducible.

## Security, privacy, and scope

- [ ] The standard OpenAI key is absent from browser source, production bundle, DOM, local/session storage, IndexedDB, cookies, console, and network logs.
- [ ] The ephemeral secret is absent from storage, UI, console, screenshots, fixtures, and committed artifacts, and exists only in the no-store response/local memory/required HTTPS authorization exchange.
- [ ] Bearers, authorization headers, SDP, raw provider events, tool arguments/results, transcripts, and audio are absent from logs, errors, screenshots, and Git.
- [ ] No real participant data, phone number, carrier contact, telephony claim, recording, Yuno/payment behavior, deployment, production access, or financial mutation entered the phase.
- [ ] `frontend/package.json`, `pnpm-lock.yaml`, `.env.example`, shared project specs, and unrelated paths are unchanged unless an explicit plan revision records the reason and owner.
