# Phase 22 requirements — Pass the final P0.1 telephony trial

## Coordination and gate

- Priority: P1 final submission reliability and the terminal P0.1 gate.
- Branch: `phase/22-pass-final-telephony-trial`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Phases 20, 21, 26, and 28, all merged before this claim.
- Conflicts with: none.
- Roadmap gate: one authorized rehearsal must run three literally overlapping outbound PSTN
  sessions, one mandate-safe inbound recovery, and one live human takeover without dropping the
  remote participant or structured context. The final winner must retain a recap visibly labeled
  `SIMULATED`, playable timestamp evidence, and a structured brief; browser voice, text, and the
  private recording must remain ready, and all five submission artifacts must fit the allotted
  time.

Phase 28's merged pull request records a successful authorized sandbox handoff and final hygiene,
but its repository-wide checks predate its last reconciliation with `origin/main`. Phase 22 reruns
the complete gate on its own final integration SHA instead of inheriting that unchecked edge.

## Objective and user-visible outcome

Give the operations coordinator one truthful, timed final rehearsal of the complete minimum
telephony story. The control tower starts the canonical three synthetic carrier calls through
explicit authorized actions, shows independent live outcomes, processes a real inbound recovery,
and lets the coordinator take over one still-live call. It ends with exactly one active winner, a
`SIMULATED` recap, a structured brief, playable agreement-turn evidence, and a correlated audit
trail.

This is an integration and evidence phase. It may fix only the bounded runtime limitation that
currently rejects a second active outbound call or Media Stream. It does not reopen completed
feature phases or broaden the product.

## Included scope

- Replace the FastAPI demo runtime's singleton outbound call/binding and global Media Stream flag
  with an in-process registry bounded to three independent active outbound calls and three streams.
- Preserve exact idempotent replay, provider-call and call-session correlation, one-time stream-token
  claims, per-call status updates, tool/audio isolation, terminal cleanup, and a fail-safe fourth-call
  rejection with no provider I/O.
- Run deterministic concurrency, callback-order, disconnect, handoff-fence, recovery, evidence,
  browser, privacy, and submission checks on a clean canonical fixture.
- Prepare a separately authorized runbook for account restrictions, participants, allowlists,
  disclosure, consent, duration/cost bounds, private recording, retention, cleanup, and fallbacks.
- Execute the credentialed rehearsal only after separate explicit authorization for its calls,
  participants, public ingress, recording, and any temporary provider or deployment configuration.
- Record only redacted outcomes, aggregate timing, safe opaque identifiers, gaps, and cleanup facts.
- Reconcile stale factual claims in the five public submission artifacts only after the evidence is
  observed; do not pre-announce a successful live trial.

## Excluded scope

- New public HTTP operations, request/response fields, application DTOs, generated client behavior,
  migrations, business rules, provider-neutral backend services, or frontend features.
- More than three concurrent demo calls, generalized routing, reconnect/resume hardening,
  production contact-center behavior, high availability, or exhaustive provider-failure coverage.
- SMS, email, external recap delivery, or promotion to `VERIFIED`.
- Real carrier contact, booking, live rates, production identity, production deployment, permanent
  account changes, or unallowlisted callers and destinations.
- Yuno, payments, financial mutations, direct SIP, unrelated infrastructure, or new dependencies.
- Raw audio, transcripts, telephone numbers, signatures, provider payloads, credentials, private
  locators, or participant data in Git, logs, screenshots, or public artifacts.

## Assumptions, risks, and fallback

- Twilio Voice and OpenAI Realtime access, country rules, call-per-second and concurrency limits,
  authorized destinations, HTTPS/WSS ingress, and recording obligations must be reverified from
  current official documentation and the configured accounts before the live run.
- Three authorized participants can overlap long enough to produce observable independent live
  intervals; sequential calls or workflow-only concurrency do not pass.
- The existing durable outbound-attempt store supports multiple idempotency keys and provider call
  identifiers. The known capacity defect is in the FastAPI process runtime, not the database model.
- Provider callbacks may be duplicated or reordered, a participant may disconnect, handoff may
  fail, or playable evidence may be unavailable. No partial outcome is promoted to a pass.
- Browser voice, text, and the private recording remain the demo fallback. They preserve the P0
  story but do not replace the missing PSTN, inbound, overlap, or handoff evidence; the P0.1 gate
  remains explicitly incomplete when any required live outcome fails.

## Acceptance criteria

1. Three fresh authorized outbound requests for the canonical operation use distinct call session
   IDs, destination labels, and idempotency keys; all three become concurrently live and open
   independent signed bidirectional Media Streams. A fourth active request fails safely with zero
   provider I/O.
2. Exact request replay returns its stored call without a duplicate mutation; a changed payload,
   duplicate token claim, mismatched provider callback, or cross-call tool/audio event cannot affect
   another session. Reordered terminal callbacks remain monotonic and durable.
3. Every outbound participant hears the AI disclosure and the accepted no-recording/consent policy.
   The rehearsal records safe start, live, and terminal intervals that prove literal overlap without
   exposing telephone numbers or provider payloads.
4. One signed authorized inbound call correlates fail-closed to exactly one active synthetic
   operation, obtains the required disclosure/consent, completes the driver-delay recovery inside
   the mandate, and durably records the replacement, notification, brief, evidence, and audit facts.
5. During one still-live PSTN call, an explicit coordinator action reaches durable `JOINED` only
   after the verified callback, preserves the remote leg, carries transcript-free structured
   context, and fences all further AI speech and commitment-capable tools.
6. Terminal inspection proves exactly one `ACTIVE` winner and historical `SUPERSEDED` decisions,
   creates the replacement winner's idempotent recap as `SIMULATED`, plays the private evidence at
   its `audio_start_ms`, and displays its structured brief and correlated audit trail.
7. `make check`, focused concurrency and telephony tests, generation without a semantic contract
   diff, desktop/mobile browser inspection, secret/privacy scans, and cleanup all pass on the final
   SHA. The five submission artifacts tell the same truthful story in the allotted time.

## HTTP contract gate

No public contract change is planned. The phase reuses:

- `POST /v1/operations/{operation_id}/outbound-calls` three times with the existing body,
  authorization/origin dependencies, one `Idempotency-Key` per logical call, `201` response, and
  declared `401`, `403`, `404`, `409`, `422`, `429`, `500`, `502`, `503`, and `504` errors;
- the existing signed Twilio outbound voice, consent, status, and Media Stream ingress;
- the existing signed inbound voice/consent/media path from Phase 26;
- the existing handoff readiness, creation, lookup, and verified status callback contracts from
  Phase 28; and
- the existing operation, audit, evidence-audio, recap, and brief contracts for terminal
  inspection.

Call creation or an HTTP provider response never proves live success. Status, recovery, and handoff
outcomes come from verified, duplicate-safe durable processing and the resulting projections.
`api/openapi.json` and Orval output must regenerate without semantic change.

## Application contract gate

- Preserve `app.telephony.service.TelephonyApplication`, `LiveTelephonyApplication`, `MediaBinding`,
  `StreamEvidence`, and `create_live_telephony_application`. The factory keeps its existing typed
  `Settings`, `ContractService`, and `httpx.AsyncClient` inputs and constructs the application through
  FastAPI state with the same public methods and return types.
- Preserve the backend `OutboundCallRequest`, `OutboundCall`, `OutboundCallStatusEvent`,
  `OutboundCallAttemptStore`, inbound-recovery, handoff, evidence, recap, brief, operation, and audit
  public symbols and typed exceptions.
- Change only the internal `LiveTelephonyApplication` state from one call to a bounded registry of
  private per-call runtime entries containing the call, binding, idempotency key/fingerprint, and
  stream claim state. Index and resolve entries by the existing safe identifiers; use the existing
  durable store for persistence. A private capacity exception maps to the already-declared `409`
  `STATE_CONFLICT` envelope and does not enter the backend or generated contracts.
- The backend remains the only authority for mandate, recovery, winner, recap, handoff fence, and
  audit transitions. FastAPI verifies and correlates transport events; the browser only presents
  state and initiates explicit actions.

No Yuno browser/server handoff exists in this Nauta phase. The terminal browser result is the
truthful final winner view with `SIMULATED` recap, playable evidence, brief, recovery, handoff, and
audit state.

## Layer, data, AI, security, and experience decisions

- **Frontend:** verification-only by default; use generated hooks and existing controls. Keep
  keyboard access, visible focus, status announcements, duplicate-action prevention, and truthful
  fallback states at desktop and mobile widths.
- **API/BFF:** own the bounded in-process call/stream registry, signed ingress, per-call correlation,
  safe capacity error, dependency wiring, and redacted diagnostics. Do not move domain decisions
  into routers.
- **Backend/core and data:** read-only unless an integration defect proves the accepted durable
  contract is broken. No migration is planned. PostgreSQL remains the terminal source of truth.
- **AI:** each stream receives an independent Realtime session and tool correlation; handoff fences
  the selected call only. Standard OpenAI credentials and raw model/provider events remain private.
- **Security/privacy:** explicit human authorization, allowlists, current calling rules, AI
  disclosure, consent, signed callbacks, bounded duration/cost, private recording, redacted logs,
  deletion/cleanup, and no secret or participant data in Git are release gates.
- **Visual/accessibility:** no redesign. Verify the existing start, live, failure, recovery, handoff,
  evidence, recap, and fallback states remain understandable without color and operable by keyboard.

## One-writer ownership

| Path or resource                                                                              | Writer                           | Rule                                                                                                      |
| --------------------------------------------------------------------------------------------- | -------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `docs/project-specs/2026-08-30-22-pass-final-telephony-trial/**`                              | Phase coordinator                | Sole planning and redacted validation-evidence writer.                                                    |
| `api/app/telephony/service.py`, `api/app/main.py`, `api/app/routers/telephony.py`             | API integration writer           | Bounded runtime only; `bridge.py` changes only for a proven stream-local defect.                          |
| Focused `api/tests/**`                                                                        | API integration writer           | Concurrency, isolation, replay, callback, capacity, and cleanup coverage.                                 |
| `backend/**`, migrations                                                                      | No planned writer                | Verification-only; route a real contract defect back through the coordinator.                             |
| `frontend/**`                                                                                 | No planned writer                | Verification-only; no new UI or handwritten DTO.                                                          |
| `api/openapi.json`, `frontend/src/lib/api/generated/**`                                       | Generation checkpoint owner      | Regenerate only to prove zero semantic contract diff; never hand-edit.                                    |
| `README.md`, `docs/submission/**`, `docs/architecture.md`, `docs/decisions/challenge-plan.md` | Submission reconciliation writer | Update only observed final facts after refreshing other writers; no roadmap/mission/stack change planned. |
| Manifests, lockfiles, `.env.example`                                                          | No planned writer                | No dependency or configuration inventory change expected.                                                 |
| Credentials, allowlists, provider settings, public ingress, participants, private audio       | Authorized operator outside Git  | Separate authorization, least privilege, redaction, retention, and cleanup required.                      |
