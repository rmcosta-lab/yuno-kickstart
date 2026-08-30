# Phase 28 requirements — Transfer a live call to the human coordinator

## Objective and user-visible outcome

- Let the operations coordinator explicitly take over one authorized inbound or outbound PSTN call while seeing the current mandate, quotes, transcript-free structured call context, and normalized call status.
- Preserve the remote participant on the same live conversation, stop AI speech and commitment authority before provider transfer begins, join only the allowlisted coordinator destination, and record the verified outcome in the audit trail.
- Leave failed, timed-out, and duplicate actions in an honest, recoverable safe state. The interface never claims that a coordinator joined until a signed provider event proves it.
- Priority: mandatory P0.1 live-handoff gate. Browser voice, text mode, and the private recorded trial remain fallbacks but do not satisfy the PSTN handoff gate.

## Included scope

- Provider-neutral handoff state, typed commands/results/events, atomic idempotent reservation, AI-authority suspension, durable status, and safe audit records in backend/core.
- A Twilio adapter operation that redirects the existing live remote call into a bounded conference and adds one allowlisted coordinator participant, plus normalized provider errors and timeouts.
- A demo-authorized, origin-checked, rate-limited `POST /v1/calls/{call_id}/handoffs` contract, a read-only readiness snapshot, a read contract for the resulting handoff, and signed Twilio conference/participant status ingress.
- OpenAPI and Orval regeneration followed by a generated-client frontend action that shows the current structured context before confirmation and renders `CONNECTING`, `JOINED`, `FAILED_SAFE`, or `TIMED_OUT_SAFE` truthfully.
- Media-bridge enforcement that stops model output and rejects commitment-producing tool actions once the handoff reservation succeeds; it does not infer human participation from a disconnected AI stream.
- Focused backend, adapter, API, callback, generated-contract, frontend, browser, accessibility, idempotency, timeout, failure, duplicate, and redaction tests.
- One separately authorized Twilio sandbox handoff that proves the remote participant remains connected, the coordinator joins, the AI no longer speaks or commits, and the audit records the accepted outcome.

## Excluded scope

- Hanging up and redialing the remote participant, arbitrary transfer destinations, general contact-center routing, coordinator queues, warm-transfer policy beyond the one fixed demo participant, or more than one active handoff per call.
- Raw transcript display or persistence, new recording behavior, provider payload display, phone-number exposure, production identity, production routing, or unallowlisted callers.
- New mandate, quote, winner, commitment, or recovery rules; a handoff changes conversation authority, not operational authority or the active commitment.
- Automatic AI resumption after a failed or timed-out handoff. A new explicit safe recovery or call termination is required.
- Deployment, provider-account or number mutation, production access, participant contact, recording, or a live call without separate explicit authorization.
- SMS, email, external recap delivery, direct SIP, Yuno, payments, financial mutations, and unrelated infrastructure.

## Coordination and roadmap gate

- Branch: `phase/28-transfer-live-call-to-human` from refreshed `origin/main` at `68cec818cc25f42db8da68cf953ef9a1364b443f`.
- Workspace: `/private/tmp/yuno-kickstart-phase-20-add-outbound-call-controls`.
- Planning directory: `docs/project-specs/2026-08-30-28-transfer-live-call-to-human/`.
- Owner and team contact: `rmcosta-lab`.
- Tracking Issue: none requested.
- Dependency: Phase 20 is DONE through merged PR #34, whose recorded evidence includes `make frontend-check`, focused browser coverage, generated-client use, and privacy review.
- Conflicts: none declared. Refresh open API/backend/frontend/shared-file pull requests and remote phase refs before implementation and publication.
- Roadmap gate, unchanged: during one authorized inbound or outbound PSTN call, an explicit takeover action presents the coordinator with the current mandate, quotes, transcript-free structured context, and call status; joins the coordinator to the same live conversation without disconnecting the remote participant; prevents AI speech or commitment after handoff; records the result in the audit trail; covers failure, timeout, duplicate action, and redaction; and passes one authorized sandbox handoff.

## Assumptions, risks, and fallback

- Current official Twilio documentation permits an in-progress Call to begin new TwiML and exposes conference participant join/leave callbacks. Implementation must refresh the Call resource, `<Conference>`, Participants resource, request-signature, trial/account, regional calling, number, recording, and compliance documentation before fixing provider fields.
- The accepted provider sequence is: atomically reserve the application handoff and revoke AI speech/commitment authority; redirect the existing remote call leg into the server-owned conference; add the allowlisted coordinator participant; accept `JOINED` only from verified durable callback processing.
- Risk: redirecting the remote leg succeeds but dialing the coordinator fails. Mitigation: keep the remote leg in the bounded conference with an explicit `FAILED_SAFE` or `TIMED_OUT_SAFE` application state, keep AI authority revoked, surface a retry/terminate decision, and never fabricate a joined coordinator.
- Risk: a duplicate action or callback creates two coordinators or conflicting state. Mitigation: fingerprinted idempotency, one active handoff constraint, provider event deduplication, monotonic status transitions, and reuse of the same logical operation on uncertain retry.
- Risk: the AI emits speech or executes a commitment tool during transfer. Mitigation: persist the authority fence before provider I/O, gate both bridge output and commitment-capable tools on that fence, and test the race deterministically.
- Risk: a provider callback is forged, reordered, or incomplete. Mitigation: exact signature verification before parsing, provider-call/conference binding, stable event IDs, sequence-aware monotonic processing, and success only after durable delegation.
- Fallback: keep the participant in an explicit safe call state, show the coordinator the context and failure, offer only an explicit retry or termination, and retain browser voice, text, and recorded-demo fallbacks. Fallback evidence is never represented as a successful PSTN handoff.

## Acceptance criteria

1. The control tower shows the active call's normalized status, current immutable mandate, ranked quotes, and bounded structured brief without a raw transcript, provider payload, phone number, or credential before enabling takeover.
2. The takeover action requires demo authorization, allowed origin, a fresh explicit actor/time confirmation, one configured coordinator destination label, a live call-state version, and `Idempotency-Key`; invalid or stale input causes no provider I/O.
3. Backend/core atomically reserves at most one active handoff for the call, persists the request fingerprint, fences AI speech and commitment-capable tools before provider I/O, and appends a safe correlated audit event without importing FastAPI.
4. The Twilio adapter redirects the existing remote call leg to the bounded conference and creates only the allowlisted coordinator participant. Provider URLs, credentials, E.164 values, request fields, and responses stay in the adapter/configuration boundary.
5. A verified join callback advances the handoff to `JOINED`, proves the same remote call is still a participant, records safe provider-neutral evidence, and appends the outcome audit event. The POST response or stream closure alone cannot prove success.
6. Failure or timeout advances monotonically to `FAILED_SAFE` or `TIMED_OUT_SAFE`, leaves the remote leg and AI fence explicit, exposes a safe retry/terminate decision, and never records or renders human participation.
7. A same-request replay returns the durable handoff without a second provider mutation. A changed payload under the same key or another active logical handoff returns a safe conflict. Duplicate/reordered callbacks are accepted at most once without status regression.
8. After reservation, pending Realtime audio output is cleared or dropped, subsequent AI audio is suppressed, and commitment-producing tool actions fail through a safe typed authority error. Read-only context remains available to the coordinator.
9. The readiness read, `POST /v1/calls/{call_id}/handoffs`, the handoff read route, and provider callback ingress enforce their declared auth, validation, idempotency, status, error, signature, and redaction semantics; OpenAPI and Orval are regenerated, not hand-edited.
10. Focused tests, `make check`, generation review, browser console/network/accessibility checks, `git diff --check`, and secret/privacy scans pass. One separately authorized sandbox handoff proves continuity, coordinator join, AI silence/authority revocation, and audit evidence; otherwise the provider portion remains visibly incomplete.

## HTTP contract gate

### Public application routes

- `GET /v1/calls/{call_id}/handoff-readiness`
  - Security: demo bearer authorization and the explicit allowed-origin boundary; no provider I/O.
  - Success: `200 OK` with `call_id`, the durable `call_status_updated_at` concurrency value required by the POST, and the same bounded safe context projection. No provider identifier, destination number, transcript, raw audio reference, signature, or credential is returned.
  - Errors: the standard safe envelope for `401`, `403`, `404`, `409`, `422`, and `503` only.
- `POST /v1/calls/{call_id}/handoffs`
  - Security: demo bearer authorization, explicit allowed origin, rate limit, request correlation, and required `Idempotency-Key`.
  - Request: `coordinator_destination_label`, `authorized_by`, `authorized_at`, and `expected_call_status_updated_at`. The call-session ID comes only from the path; provider identifiers and phone numbers never come from the browser.
  - Success: `202 Accepted` for a new or exact durable replay. Response fields are `handoff_id`, `call_id`, `status`, `requested_at`, `status_updated_at`, and a bounded `context` containing the current mandate version, normalized mandate facts, eligible quote summaries, structured call brief, and call status. Allowed statuses are `CONNECTING`, `JOINED`, `FAILED_SAFE`, and `TIMED_OUT_SAFE`.
  - Errors: the standard safe envelope for `401` unauthenticated, `403` unauthorized action/origin, `404` unknown call or destination, `409` stale call, active-handoff conflict, or idempotency mismatch, `422` malformed input, `429` rate limit, `502` definitive provider failure, `503` unavailable or uncertain provider outcome, and `504` timeout.
- `GET /v1/calls/{call_id}/handoffs/{handoff_id}`
  - Security: the same demo authorization and allowed-origin boundary; no provider I/O.
  - Success: `200 OK` with the same safe handoff projection so the generated client can observe callback-confirmed status.
  - Errors: `401`, `403`, `404`, and the standard safe envelope only.

### Provider ingress

- `POST /v1/telephony/twilio/handoff-status` remains outside the browser contract and generated client. It verifies the exact Twilio signature over raw form values before typed parsing, binds the call/conference/participant to one reserved handoff, and returns `204` only after durable duplicate-safe processing.
- Missing/invalid signature or account/call binding returns `403`; malformed recognized input returns `422`; transient durable-processing failure returns a retryable non-success without exposing internal or provider details.

## Application contract gate

- Add provider-neutral public symbols under `yuno_backend.volta.telephony`: `HumanHandoffCommand`, `HumanHandoffContext`, `HumanHandoffReadiness`, `HumanHandoff`, `HumanHandoffStatus`, `HumanHandoffStatusEvent`, `HumanHandoffService`, `HumanHandoffGateway`, and `HumanHandoffRepository`.
- `HumanHandoffService` is constructed with the handoff repository, provider gateway, existing operation/audit application boundaries, clock, and an AI-authority fence. FastAPI injects the service; no FastAPI/Pydantic/provider payload enters backend/core.
- `request_handoff(command: HumanHandoffCommand) -> HumanHandoff` atomically reserves or replays the logical operation and persists the AI fence before calling the gateway. No database transaction remains open during provider I/O.
- `get_handoff_readiness(call_id: UUID) -> HumanHandoffReadiness` returns the current durable call-status timestamp and bounded context without provider I/O. `get_handoff(call_id: UUID, handoff_id: UUID) -> HumanHandoff` returns the bounded durable projection without provider I/O. `observe_handoff(event: HumanHandoffStatusEvent) -> HumanHandoff` applies verified duplicate-safe monotonic evidence and appends the audit outcome.
- `HumanHandoffGateway.begin_handoff(handoff: HumanHandoff) -> None` receives only provider-neutral identifiers and the server-resolved coordinator destination label. The Twilio implementation owns Call update, conference/participant mapping, authentication, timeouts, and response redaction.
- Typed safe exceptions cover call-not-live/stale state, missing context, unauthorized or unknown destination, active handoff, idempotency conflict, provider authentication/permission/rate limit/failure, timeout, and uncertain outcome. Browser/API errors never include phone numbers, provider identifiers, raw payloads, transcripts, credentials, or participant data.

## Handoffs and terminal user-visible result

- Browser/API: only generated client types cross the boundary. The browser submits the allowlisted label and explicit authorization, then polls or invalidates the typed handoff projection; it never receives Twilio credentials, E.164 destinations, signatures, or raw callback fields.
- API/backend: FastAPI validates and delegates. Backend/core owns reservation, authority fencing, idempotency, state, context projection, and audit; the API owns HTTP and signed callback transport semantics.
- Backend/Twilio: provider-neutral gateway calls map to Twilio Call update and conference participant creation inside the adapter. Signed callbacks map back to provider-neutral events before application processing.
- Realtime/handoff: the application authority fence stops AI speech and commitment-capable tools before any provider mutation. A transport disconnect is cleanup evidence, not human-join evidence.
- Terminal user-visible result: `JOINED` with the same remote participant still connected, coordinator context visible, AI inactive for speech/commitments, and a correlated audit event; otherwise an explicit safe failure/timeout with no fabricated takeover.
- Yuno/payment handoff: none.

## Visual and accessibility decisions

- Reuse the existing live-session card and control-tower visual language. Add a clearly labeled `Take over live call` confirmation, a concise context panel, processing status, and explicit safe failure actions rather than a new application surface.
- The action is keyboard accessible, has a visible focus state, preserves context while pending, announces status changes through an appropriate live region, prevents duplicate activation, and remains understandable without color.
- Verify desktop and mobile layout, long structured facts, loading, stale-call, failure, timeout, joined, and fallback states. Never render a raw transcript or real destination.

## One-writer ownership

| Path or resource | Writer | Decision |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-28-transfer-live-call-to-human/**` | `rmcosta-lab` | Planning and later validation evidence |
| `backend/src/yuno_backend/volta/telephony/**`, matching audit/application boundaries and tests | `rmcosta-lab` | Provider-neutral handoff state, authority fence, idempotency, service, repository protocol, audit |
| `backend/src/yuno_backend/integrations/twilio/**`, matching adapter tests | `rmcosta-lab` | Call update, conference/participant mapping, timeout, safe provider errors |
| `backend/migrations/**`, persistence models/mappers/repositories/tests | `rmcosta-lab` | Smallest reversible durable handoff and authority-fence change if required |
| `api/app/routers/telephony.py`, telephony schemas/service/signatures/wiring, matching API tests | `rmcosta-lab` | Public routes, verified callback ingress, dependency wiring, safe errors |
| `api/openapi.json` | `rmcosta-lab`, generated | Source remains Pydantic; never edit manually |
| `frontend/src/lib/api/generated/**` | `rmcosta-lab`, generated | Orval output; never edit manually |
| `frontend/src/features/telephony/**`, existing live-session composition, focused browser tests | `rmcosta-lab` | Context, confirmation, generated mutation/read flow, accessible states |
| Python manifests and `uv.lock` | `rmcosta-lab`, paired only if demonstrably required | Refresh overlaps first; no speculative dependency |
| Frontend manifest and `pnpm-lock.yaml` | `rmcosta-lab`, paired only if demonstrably required | Reuse existing primitives and test stack first |
| `.env.example` and minimum setup documentation | `rmcosta-lab`, only if safe configuration names change | Names/safe defaults only; no account, phone, or secret values |
| Mission, tech stack, roadmap, challenge plan | none | No shared decision change required |
| Twilio account, hosting, numbers, participants, recordings | none | No external mutation or contact authorized by phase start |
