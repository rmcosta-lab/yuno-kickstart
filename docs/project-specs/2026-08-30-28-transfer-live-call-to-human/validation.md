# Phase 28 validation — Transfer a live call to the human coordinator

## Planning and coordination

- [ ] Requirements, contracts, ownership, exclusions, risks, and fallback still match the Phase 28 roadmap gate on refreshed `origin/main`.
- [ ] Phase 20 remains DONE through merged PR #34 with its gate evidence recorded.
- [ ] Remote Phase 28 branch/PR state, conflicts, and overlapping telephony/API/frontend/shared-file pull requests are refreshed before implementation and publication.
- [ ] Only the phase specification and approved backend/API/frontend/generated/migration/configuration paths enter the phase.

## Current official provider evidence

- [ ] Current Twilio Call update documentation confirms the accepted way to change an in-progress call to server-owned TwiML without ending the remote leg.
- [ ] Current Twilio `<Conference>` and Participants documentation confirms participant creation, join/leave events, status callback ownership, call-per-second/account limits, and failure semantics used by the phase.
- [ ] Current Twilio request-signature, trial/account, regional calling, phone-number, recording, disclosure, consent, and applicable compliance constraints are recorded before implementation.
- [ ] Provider fields used by the adapter are frozen from official documentation; assumptions and unavailable sandbox capabilities are reported explicitly.

## Backend/core authority and persistence

- [ ] Public provider-neutral commands, context, handoff values/statuses/events, gateway, repository, service, and safe errors match `requirements.md` and import no FastAPI/Pydantic/provider payload.
- [ ] One transaction validates the live call/version, reserves or replays the logical handoff, persists the fingerprint and AI fence, and appends the requested audit event before provider I/O; no transaction stays open across the network call.
- [ ] Same-request replay is durable and side-effect free; changed payload, stale call, missing context, unknown destination, and another active handoff fail safely with zero provider I/O.
- [ ] Callback event IDs deduplicate durably; reordered events do not regress terminal state; `JOINED`, `FAILED_SAFE`, and `TIMED_OUT_SAFE` audit outcomes correlate to the request.
- [ ] Reservation races with pending AI audio and commitment-capable tools are deterministic: output is dropped/cleared and mutations fail with a safe authority error after the fence.
- [ ] Persistence round trips, constraints, rollback, retry, and migration review preserve a consistent safe state.

## Twilio adapter

- [ ] The adapter updates only the expected live remote Call into the bounded conference and creates only the allowlisted coordinator participant.
- [ ] Twilio URLs, credentials, E.164 values, Call/Conference/Participant identifiers, form fields, TwiML, HTTP responses, and provider exceptions remain inside the adapter/configuration boundary.
- [ ] Injected-transport tests cover accepted redirect/add-participant behavior, authentication/permission/rate limit, definitive failure, timeout, connection loss, invalid response, and uncertain outcome.
- [ ] Exact same-request retry cannot add a second coordinator; ambiguous outcomes remain explicit and are not retried with a new logical identity.
- [ ] Logs, errors, representations, fixtures, and snapshots redact credentials, phone numbers, provider payloads, and private participant data.

## Public API and verified callback ingress

- [ ] `POST /v1/calls/{call_id}/handoffs` enforces demo auth, explicit origin, rate limit, correlation, current call status, fresh human authorization, allowlisted label, and `Idempotency-Key` before provider I/O.
- [ ] `202` new/replay and safe `401`, `403`, `404`, `409`, `422`, `429`, `502`, `503`, and `504` semantics match `requirements.md` without leaking provider or participant data.
- [ ] `GET /v1/calls/{call_id}/handoffs/{handoff_id}` returns the bounded durable projection without provider I/O and exposes only declared safe errors.
- [ ] The context projection includes current mandate version/facts, eligible quote summaries, structured brief, and normalized call status, but no raw transcript, raw audio reference, provider payload, E.164 number, signature, or credential.
- [ ] Twilio handoff callbacks verify exact signatures and expected account/call/conference/participant binding before typed parsing and delegation.
- [ ] Missing/tampered/ambiguous callback input fails closed; duplicate valid callbacks return success only after durable duplicate-safe processing; retryable persistence failure returns non-success.
- [ ] Stable operation IDs and declared Pydantic schemas/errors pass focused API contract tests.

## OpenAPI, Orval, and frontend

- [ ] API contract tests pass before `make generate`; `api/openapi.json` and `frontend/src/lib/api/generated/**` are generated only from accepted Pydantic/OpenAPI sources and fully reviewed.
- [ ] The frontend uses only generated hooks/types and an injected test boundary; no handwritten duplicate HTTP DTO or provider field is added.
- [ ] The live-session interface presents current mandate, quotes, structured brief, and normalized call status before an explicit `Take over live call` confirmation.
- [ ] Processing, `JOINED`, stale, `FAILED_SAFE`, `TIMED_OUT_SAFE`, duplicate-disabled, retry/terminate, and browser/text fallback states are truthful and preserve context.
- [ ] Keyboard activation, visible focus, status announcements, disabled-state semantics, color-independent meaning, long content, and mobile/desktop layout pass focused tests and browser review.
- [ ] Browser console and network inspection show no runtime error, raw transcript, real number, provider payload, signature, credential, or duplicate request.

## Cross-layer and security behavior

- [ ] The fake-provider journey preserves the remote leg, confirms coordinator join through a verified callback, fences AI speech/commitments, refreshes the generated projection, and appends the correlated audit outcome.
- [ ] Redirect-success/participant-failure, timeout, stale version, duplicate action/callback, callback reorder/tampering, and AI audio/tool races end in declared safe states without fabricated participation.
- [ ] FastAPI remains a thin transport boundary; backend owns authority/state/audit; Twilio mapping stays in the adapter; React owns presentation and explicit user action only.
- [ ] No raw audio/transcript, E.164 destination, credential, signature, authorization header, provider payload, private participant data, or standard OpenAI secret enters Git, public responses, logs, errors, screenshots, or generated artifacts.

## Required deterministic commands

- [ ] `uv run ruff check .` passes for the affected Python workspace.
- [ ] `uv run pytest` passes for affected backend/API tests.
- [ ] `make python-check` passes from the repository root.
- [ ] `make generate` passes; the complete OpenAPI/Orval diff is reviewed.
- [ ] `pnpm lint` passes from `frontend/`.
- [ ] `pnpm build` passes from `frontend/`.
- [ ] `make check` passes from the repository root.
- [ ] Focused frontend interaction/browser tests pass against the supported dev or production server.
- [ ] Desktop and mobile browser smoke plus console/network inspection pass.
- [ ] `git diff --check`, complete tracked/untracked review, and secret/privacy/phone/transcript/audio/provider-payload scans pass.

## Authorized sandbox handoff

- [ ] Separate explicit authorization records the synthetic remote and coordinator labels, destination countries, origin class, public HTTPS/WSS endpoints, account restrictions, disclosure/consent/recording behavior, expected cost/duration, evidence retained, deletion/cleanup, and abort plan.
- [ ] One authorized sandbox call proves the remote participant remains connected while the allowlisted coordinator joins the same conversation.
- [ ] The trial proves AI speech stops, commitment-capable tools remain fenced, signed callbacks persist exactly once, the UI shows `JOINED`, and the correlated audit outcome is durable.
- [ ] Handoff latency, participant continuity, provider restrictions, failures, redacted evidence, and endpoint cleanup are reported separately from deterministic tests.

## Explicitly not authorized by phase start

- [x] No deployment, production access, provider account/number/permission change, real-carrier contact, unapproved PSTN call, recording, Yuno operation, payment, financial mutation, or unrelated remote mutation is authorized.

## Planning references reviewed on 2026-08-30

- [Twilio Call resource](https://www.twilio.com/docs/voice/api/call-resource): an in-progress call can begin new TwiML through a Call update.
- [Twilio `<Conference>`](https://www.twilio.com/docs/voice/twiml/conference): conference start/end and participant join/leave callbacks provide asynchronous evidence; the first participant owns the callback configuration.
- [Twilio Conference Participants resource](https://www.twilio.com/docs/voice/api/conference-participant-resource): creating a participant initiates an outbound call into an active conference and is subject to account call-per-second limits.
- These references guide planning only. Implementation must refresh them and the signature/account/regional/number/recording sources before code or a sandbox trial.
