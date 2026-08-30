# Fase 13 — Plan

One frontend writer owns this isolated workstream. No API or backend writer is required.

## Task groups in dependency order

1. **Freeze provider and generated-route mappings**
   - Refresh current official OpenAI Realtime WebRTC, conversations/tool output, and interruption documentation before implementation.
   - Inventory the merged Fase 12 client-secret result and generated quote/commitment functions; name provider correlation `call_id` and operational carrier-session `call_id` distinctly.
   - Freeze the source and refresh rules for server-owned operational/session/version/quote/evidence context. The commitment trial requires a selected quote and synthetic evidence attached through the existing typed route; if the fixed session cannot receive safe current context, stop and coordinate the API owner.
   - Freeze allowlisted event names, bounded runtime guards, the exact tool success/error envelope, safe `ApiHttpError` extraction, idempotency and uncertain-mutation behavior, and the exact `function_call_output` then `response.create` ordering before component work.

2. **Build guarded tool dispatch**
   - Implement pure event parsing and discriminated tool argument validation for `record_quote` and `create_candidate_commitment`.
   - Dispatch only through generated client functions and map typed BFF success or safe failure to the frozen `{ ok, data | error }` envelope.
   - Keep one idempotency key, pending promise, and result per provider call ID at the feature-session boundary so duplicate delivery never invokes a second logical mutation.
   - On disconnect during a mutation, let the request settle when possible, mark the old voice call unresolved, refetch authoritative operation state, and block another voice mutation until reconciliation completes; never abort and replay under a new call ID.

3. **Build the native WebRTC lifecycle**
   - Request microphone access from an explicit user action, mint one fresh ephemeral secret, exchange SDP, attach remote audio, and open the Realtime data channel.
   - Model one active connection generation and idempotent cleanup for peers, channel, tracks, listeners, audio sink, and ephemeral references while uncertain mutation state remains available for reconciliation.
   - Implement text input; observe and render documented speech-start, cancel, and truncate events; preserve coherent continuation; and send explicit cancel/truncate events only when current official WebRTC documentation requires client action.

4. **Integrate the smallest voice leaf**
   - Add explicit Start, Stop, Reconnect, and text-fallback controls to the existing negotiation experience while keeping App Router pages as Server Components.
   - Supply and refresh bounded server-owned tool context after safe tool completion. Reuse the existing negotiation evidence handoff for the commitment precondition and render only server-owned quote and commitment outcomes.
   - Preserve the existing text journey and label browser voice as a simulator rather than telephony or carrier contact.

5. **Finish failure, accessibility, and responsive states**
   - Distinguish permission, playback, credential, SDP, provider, tool, timeout, and disconnect states with safe recovery actions.
   - Verify keyboard order, visible focus, restrained live announcements, non-color cues, reduced-motion behavior, touch targets, and mobile/desktop layout.
   - Ensure Stop, route unmount, connect failure, and reconnect leave no active microphone or overlapping connection.

6. **Verify and review the complete gate**
   - Add source-level fixtures for the pure parser/dispatcher seams and expose deterministic browser scenarios for malformed, unknown, duplicate, failed, pending-disconnect, and reconnected events without a provider credential; automate those scenarios with the phase-owned Playwright harness.
   - Run `make frontend-check`, followed by the Playwright-first and Chrome-DevTools-second browser flow required by `frontend/AGENTS.md`.
   - Run the separately authorized credentialed English WebRTC, natural-pacing, barge-in, reconnect, and two-tool roundtrip trial with synthetic data.
   - Review source, bundle, storage, DOM, console, network, screenshots, diff, and status for secrets, raw content, generated drift, unexpected dependencies, and unrelated changes.

7. **Calibrate server-owned VAD after the human trial**
   - Preserve `server_vad`, `create_response`, and `interrupt_response`; trial `0.7`, record its failed human noise check, then raise the provider activation threshold to `0.85` for the next calibration pass.
   - Keep the change inside the OpenAI adapter and its exact-payload tests; do not change the browser, HTTP contract, provider-neutral request, persistence, or generated client.
   - Run the focused backend tests and `make python-check`, restart the local API, then repeat one intentional barge-in and one ambient-noise observation before closing the quality finding.

## Contracts, generation, and checkpoints

- Contract decisions and call-ID semantics precede parallel implementation. The Fase 12 Pydantic/OpenAPI/Orval output is authoritative.
- No API contract change and no `make generate` run are planned. A missing route, field, tool schema, or safe-error semantic stops frontend work for coordination with the owning API phase; generated files are never hand-edited.
- The WebRTC lifecycle and tool dispatcher may be implemented independently after the mapping is frozen, but one frontend writer owns their integration paths.
- The integration checkpoint proves a server result reaches both Realtime with the original provider call ID and the negotiation UI through refreshed server state, without a browser-owned commitment transition.
- Tests and deterministic guards stay beside the changed behavior. The durable verification follow-up adds only `@playwright/test`, a Chromium project for credential-free checks, and a separately gated Realtime project.

## Ownership, shared files, and authority

- The one-writer matrix in `requirements.md` is authoritative for feature, route, shared component, manifest/lockfile, generated, and shared-spec paths.
- The phase coordinator owns the explicitly requested durable Playwright addition under `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/playwright.config.ts`, and `frontend/tests/e2e/**`. `@playwright/test` is the only new dependency; deterministic checks remain credential-free, while provider use is isolated behind `RUN_OPENAI_CREDENTIALED=1`. No mission, tech-stack, roadmap, challenge-plan, generated-client, or `.env.example` edit is required.
- After the human trial exposed ambient-noise false positives, the user explicitly approved one support change owned by the coordinator: `backend/src/yuno_backend/integrations/openai/realtime.py` plus the two exact provider-payload tests. The threshold is fixed server-side; no API, persistence, generated-client, or shared-stack decision changes.
- No temporary wait exists: Fases 09 and 12 are merged with gate evidence, Fase 13 has no conflicts, and no remote branch or pull request represented it at claim time.
- This plan authorizes no deployment, production access, real participant or carrier contact, PSTN call, recording retention, Yuno/payment operation, live financial mutation, or unrelated remote change.
