# Phase 19 requirements — Bridge Twilio media through FastAPI

## Objective and user-visible outcome

- Give the operations coordinator one explicit, authorized action that starts a PSTN negotiation for an allowlisted synthetic carrier and exposes a safe normalized call state for the later control-tower work.
- Accept verified Twilio voice and status callbacks plus one secure bidirectional Media Stream, bridge that stream to the existing OpenAI Realtime boundary, and route tool actions through the same typed backend application services used by browser voice.
- Finish with a durable terminal call state and auditable correlation across the operation, call session, provider call, stream, Realtime session, tool calls, and safe disconnect outcome. The API never treats a provider callback or model event as authority to create a commitment.
- Priority: P0.1 telephony integration. Browser voice, deterministic text, and the recorded browser trial remain the fallback.

## Included scope

- Pydantic request/response and safe-error contracts for `POST /v1/operations/{operation_id}/outbound-calls`, backed by the Phase 18 `OutboundCallGateway` and durable idempotency store.
- Verified Twilio voice-flow and call-status ingress under `/v1/telephony/twilio/**`, including disclosure and recording-consent gating before a Media Stream may start.
- An authenticated WebSocket at `/v1/telephony/twilio/media` that accepts only the expected allowlisted provider call/stream binding, enforces size and lifecycle limits, and translates Twilio audio/control frames without logging raw media.
- A bounded bridge between Twilio bidirectional Media Streams and the existing provider-neutral `RealtimeGateway`; audio format conversion is added only when current official contracts prove it necessary.
- Tool-call correlation and delegation to the existing Volta application facade used by the browser path, including safe output return to Realtime with the original call identifier.
- Monotonic, duplicate-safe call status and disconnect handling using Phase 18 provider-neutral values and persistence.
- API tests, WebSocket tests, signature tests, OpenAPI export, Orval regeneration, generated-client verification, frontend typecheck/build, and a separately authorized Twilio sandbox test.

## Excluded scope

- Phase 20 control-tower buttons, live-call UI, frontend state design, browser voice changes, or handwritten TypeScript contracts.
- New mandate, quote, commitment, winner, recovery, or persistence rules inside FastAPI; provider events delegate to typed backend services and cannot bypass deterministic authority.
- Changes to Phase 18 Twilio call-creation URLs, authentication, payload mapping, or provider-neutral rules except a separately coordinated integration correction returned to the Phase 18 owner.
- Real carrier contact, inbound PSTN, direct SIP, SMS, email, production identity, production deployment, number purchase, account or permission changes, recording, or a live call without separate explicit authorization.
- Raw audio, transcript, telephone number, provider payload, authentication material, or private participant data in Git, PostgreSQL projections, logs, errors, fixtures, screenshots, or generated files.
- Yuno, payments, financial mutations, or unrelated infrastructure.

## Coordination, dependency exception, and gate

- Branch: `phase/19-bridge-twilio-media`.
- Workspace: `/private/tmp/yuno-kickstart-phase-19-bridge-twilio-media`.
- Planning directory: `docs/project-specs/2026-08-30-19-bridge-twilio-media/`.
- Owner and team contact: `rmcosta-lab`.
- Tracking Issue: none requested.
- Formal dependencies: Phase 12 is DONE; Phase 18 is ACTIVE at base commit `5600aa9470db4da1c5885fc48eb38a43996f00e1`. Phase 18 formally depended on Phase 17, which was ACTIVE when this claim was created and became DONE through merged PR #25 immediately after publication.
- Owner decision on 2026-08-30: start and implement Phase 19 from Phase 18 without waiting for Phase 17 to become DONE. This explicit decision overrode the ordinary `AGENTS.md`/`start-phase` readiness ordering for this stacked claim and was exercised before PR #25 merged. It did not mark either dependency DONE, edit the roadmap, weaken any gate, or authorize merge, deployment, provider mutation, or participant contact.
- Stacking consequence: Phase 19 consumes unmerged Phase 18 contracts and must preserve their history. Phase 18 must be integrated or otherwise explicitly reconciled before Phase 19 can be independently reviewed and merged; Phase 19 has no separate wait on Phase 17.
- Conflicts: none declared. Refresh remote Phase 18 and overlapping API/specification pull requests before implementation and publication.
- Roadmap gate, unchanged: FastAPI defines and regenerates the telephony contracts, verifies Twilio call-status requests, accepts an allowlisted secure Media Stream, bridges bidirectional audio and events to OpenAI Realtime, delegates tool actions to the same backend services used by the browser, handles disconnects without duplicate commitments, and passes API, WebSocket, signature, redaction, and authorized sandbox tests.

## Assumptions, risks, and fallback

- Phase 03's PASS dossier and Phase 18's tested adapter are the baseline. Implementation must refresh current official Twilio request-validation, Voice/TwiML, status-callback, bidirectional Media Streams, framing, limits, and disconnect documentation plus current official OpenAI Realtime server-WebSocket documentation.
- The external HTTPS/WSS origin used for signature verification is configured server-side and reconstructed exactly across trusted proxy headers; arbitrary forwarded hosts, schemes, paths, or query strings are rejected.
- Each stream is bound to one already authorized call session through bounded server-issued correlation data. Twilio identifiers are normalized and never used as authorization by themselves.
- Risk: starting from an active Phase 18 causes drift. Mitigation: freeze imports at the recorded base, keep Phase 19 out of Phase 18-owned backend mappings, and reconcile the stack before review.
- Risk: two asynchronous transports race and duplicate tools or commitments. Mitigation: one consumer per stream, bounded queues, original tool-call IDs, durable operation idempotency, terminal monotonic state, and deterministic disconnect cleanup.
- Risk: backpressure, malformed frames, or disconnects leak memory or continue a provider session. Mitigation: strict message and duration limits, bounded queues/timeouts, task-group cancellation, explicit close semantics, and tests for every half-open direction.
- Risk: signature or proxy mistakes admit forged callbacks. Mitigation: exact public URL reconstruction, raw-form verification before parsing, fail-closed configuration, replay-safe event handling, and negative tests for tampering.
- Fallback: keep the Phase 18 fake gateway plus browser voice, text mode, and recorded fallback. If current provider contracts, secure public ingress, or authorized sandbox access cannot satisfy the gate, report the credentialed portion BLOCKED and do not place a call.

## Acceptance criteria

1. `POST /v1/operations/{operation_id}/outbound-calls` requires demo authorization, `Idempotency-Key`, a known call-session identifier, allowlisted destination label, explicit human actor/time evidence, AI-disclosure readiness, and a recording/consent policy; malformed or unauthorized input causes zero provider I/O.
2. The outbound route constructs the exact Phase 18 `OutboundCallRequest`, invokes an injected `OutboundCallGateway`, returns only provider-neutral identifiers/status, replays the same logical request safely, and maps typed authorization, allowlist, conflict, rate-limit, provider, timeout, and uncertain outcomes without leaking provider material.
3. Twilio voice and status HTTP ingress verifies the signature against the exact configured external URL and raw form before typed parsing. Missing, stale, oversized, malformed, or tampered input is rejected; duplicate or out-of-order status events cannot regress a terminal call.
4. Disclosure and applicable explicit recording consent occur before `<Connect><Stream>` is issued. The media URL and custom parameters contain no standard credential, phone number, raw authorization token, or unnecessary participant data.
5. The media WebSocket verifies the upgrade and one expected call/stream binding before accepting media, validates `connected`, `start`, `media`, `mark`, `clear`, and `stop` ordering and bounds, and closes safely on unknown, duplicate, malformed, oversized, timed-out, or unauthorized frames.
6. One bounded bridge forwards accepted Twilio input audio to the existing provider-neutral Realtime connection and maps Realtime output audio back to Twilio with correct ordering, mark/clear behavior, barge-in handling, and backpressure.
7. Realtime tool requests use the same application facade and deterministic services as browser voice. The original `call_id` and one idempotency key survive the roundtrip, and a replay or disconnect cannot create a duplicate quote, commitment, recap, brief, recovery, or escalation.
8. Disconnect from Twilio, OpenAI, application delegation, or server shutdown cancels both directions, closes resources once, records a safe monotonic call-session outcome, and never invents success or erases earlier evidence.
9. Logs and errors contain correlation IDs and allowlisted lifecycle metadata only. Tests and diff review prove that secrets, signatures, authorization headers, phone numbers, raw forms, media, transcripts, and provider payloads are redacted or absent.
10. API and WebSocket tests, `make python-check`, `make generate`, frontend typecheck/build, `git diff --check`, and generated-artifact review pass. A separately authorized sandbox test proves signed status ingress plus bidirectional media and tool delegation; without it the credentialed gate remains explicitly unmet.

## HTTP and WebSocket contract gate

### Public application contract

- `POST /v1/operations/{operation_id}/outbound-calls`
  - Headers: demo bearer authorization and required `Idempotency-Key`.
  - Request: `call_session_id`, `destination_label`, `authorized_by`, `authorized_at`, `ai_disclosure_required=true`, `recording_mode`, and matching `recording_consent_required`. The operation ID comes only from the path; correlation ID comes from trusted request context.
  - Success: `201` for a newly accepted call and `200` for a durable same-request replay, returning `call_session_id`, safe `provider_call_id`, normalized `status`, `created_at`, `status_updated_at`, and `replayed`.
  - Errors: `400` invalid authorization/consent combination, `401` missing demo identity, `403` unknown destination or disallowed origin, `404` operation/call session not found, `409` idempotency or state conflict, `422` schema error, `429` bounded rate limit with safe retry metadata, `502` known provider failure/invalid response, `503` uncertain outcome, and `504` known timeout. Responses use the existing safe error envelope.

### Provider ingress contracts

- `POST /v1/telephony/twilio/voice` and the smallest consent continuation required by current Twilio Voice behavior return minimal TwiML only after signature verification and expected-call lookup. These provider routes are not frontend contracts.
- `POST /v1/telephony/twilio/status` verifies raw form input before parsing, delegates a normalized `OutboundCallStatusEvent`, returns `204` only after accepted durable processing, and returns a bounded non-2xx response for invalid signatures or unsafe input according to current provider retry semantics.
- `WS /v1/telephony/twilio/media` is documented outside OpenAPI. It accepts only the verified expected stream, closes with a bounded application code/reason, never exposes internal exceptions, and has explicit limits for frame size, queue depth, idle duration, total duration, and concurrent streams.
- OpenAPI and Orval include only the browser-consumed outbound-call application contract; generated files are never edited manually.

## Application contract gate

- Consume `yuno_backend.volta.telephony.OutboundCallGateway`, `OutboundCallRequest`, `OutboundCallAuthorization`, `OutboundCall`, `OutboundCallStatusEvent`, `RecordingMode`, and their safe typed errors from the Phase 18 base. Construction injects the gateway and durable status application boundary; FastAPI types never cross into backend/core.
- Consume `yuno_backend.volta.realtime.RealtimeGateway`, `RealtimeSessionRequest`, `RealtimeConnection`, typed Realtime events, and `RealtimeToolOutput`; the existing OpenAI adapter remains the sole owner of provider URLs, headers, session payloads, and OpenAI event parsing.
- Add an API-owned orchestration boundary under `api/app/telephony/` with typed internal commands/results for verified voice ingress, normalized status ingress, stream authorization, bridge lifecycle, and tool delegation. It is constructed from injected gateways, the existing Volta application facade, clock, limits, and safe logger.
- The bridge accepts validated Twilio frame values and provider-neutral Realtime events, returns only bounded control/audio frames, and raises safe API-local signature, stream-authorization, protocol, capacity, timeout, provider, and disconnect exceptions. It owns no mandate or commitment rule and no database query.

## Handoffs and terminal result

- Browser/server handoff: Phase 20 will call only the generated outbound-call route. No browser receives Twilio credentials, phone numbers, signatures, raw provider payloads, or OpenAI standard credentials.
- Twilio/server handoff: exact signed HTTPS callbacks and one signed/authorized WSS stream terminate at FastAPI; provider-specific form/frame mapping remains inside the telephony ingress module.
- Server/OpenAI handoff: FastAPI uses the existing provider-neutral Realtime gateway and server-side adapter; standard OpenAI credentials remain server-only.
- Application handoff: every tool action delegates to the same typed Volta facade used by browser voice and returns the original tool-call correlation only after deterministic execution.
- Terminal user-visible result: the later control tower can show a normalized live or terminal outbound-call status. This phase does not add that interface.
- Yuno/payment handoff: none.
- Visual/accessibility: generated types only; no rendered UI changes in this phase.

## One-writer ownership

| Path or resource | Writer | Decision |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-19-bridge-twilio-media/**` | `rmcosta-lab` | Planning and validation evidence, including the owner-authorized stacked-start decision |
| `api/app/telephony/**`, matching routers/schemas/security/wiring | `rmcosta-lab` | HTTP/WebSocket ingress, verification, orchestration, safe errors, and dependency construction |
| `api/tests/**telephony**`, matching contract/security tests | `rmcosta-lab` | Route, signature, WebSocket, bridge, disconnect, idempotency, and redaction coverage |
| `api/openapi.json` | `rmcosta-lab`, generated | Source remains Pydantic models; never edit manually |
| `frontend/src/lib/api/generated/**` | `rmcosta-lab`, generated | Orval output for the outbound-call contract only; never edit manually |
| `api/pyproject.toml` and `uv.lock` | `rmcosta-lab`, paired only if required | Add the official verifier/runtime dependency only after demonstrating need |
| `.env.example` and local configuration docs | `rmcosta-lab`, only if required | Names and safe defaults only; no account identifiers, numbers, origins, or secrets |
| Phase 18 telephony and Twilio adapter paths | none in Phase 19 | Consume the recorded base; coordinate corrections with the Phase 18 owner |
| Existing backend negotiation/recovery/Realtime domain services | none | Consume public typed contracts; do not move rules into FastAPI |
| Frontend UI outside generated artifacts | none | Phase 20 ownership |
| Shared mission, stack, roadmap, and challenge decision | none | No edit; the phase-local exception is recorded without changing dependency declarations |
| Twilio/OpenAI accounts, hosting, numbers, participants, recordings | none | No external mutation, deployment, or contact authorized by phase start |
