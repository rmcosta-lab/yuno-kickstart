# Phase 18 requirements — Implement the Twilio outbound adapter

## Objective and outcome

- Implement the backend-only Twilio outbound-call boundary for Volta's P0.1 path.
- Serve the demo operator by turning one explicitly authorized, allowlisted logical call request into one retry-safe provider call and a provider-neutral result.
- Finish with importable typed contracts and a tested adapter that Phase 19 can wire to FastAPI without importing FastAPI here.
- Priority is P0.1 after the complete browser P0. The owner explicitly authorized planning and isolated implementation to begin before Phase 17 is DONE; integration, review readiness, and merge remain waiting on the recorded Phase 17 gate.

## Scope

Included:

- Provider-neutral outbound-call request, result, lifecycle status, gateway protocol, idempotency record/repository protocol, and safe exception vocabulary under `yuno_backend.volta.telephony`.
- A Twilio adapter under `yuno_backend.integrations.twilio` using an injected `httpx.AsyncClient`, immutable redacted configuration, bounded timeouts, and the official HTTPS call-creation endpoint.
- Explicit authorization metadata, synthetic destination labels resolved through a server-side allowlist, required AI-disclosure and recording-consent policy flags, and rejection before any network request when a precondition fails.
- One persisted application idempotency key and request fingerprint per logical call. Same-key/same-request replay returns the recorded result; same-key/different-request conflicts; uncertain provider outcomes require reconciliation and never create an automatic second call.
- Mapping only the provider call identifier and allowlisted lifecycle states into provider-neutral values. Unknown, duplicate, and out-of-order terminal observations are handled deterministically.
- Mocked tests for request mapping, authentication redaction, retry classification, timeouts, uncertain outcomes, duplicate calls/events, status mapping, cleanup, and failures.
- The smallest backend repository/migration extension required for durable call idempotency, only if the existing persistence boundary cannot safely store the accepted record.

Excluded:

- FastAPI routes, Twilio request-signature verification, callback ingress, TwiML, Media Streams, OpenAI bridging, OpenAPI/Orval generation, frontend controls, browser work, deployment, or public hosting.
- Real phone calls, real carriers, production access, account changes, number purchases, permission changes, recording, or participant contact.
- Persisting or logging full phone numbers, credentials, authorization headers, raw provider payloads, audio, recordings, or transcripts.
- Automatic retry after an ambiguous call-creation outcome; a new logical call under a new key; inbound PSTN, SMS, email, direct SIP, Yuno, or payments.
- Any shared mission, stack, roadmap, or challenge-plan edit. The Phase 17 dependency remains unchanged.

## Coordination and gate

- Branch: `phase/18-implement-twilio-adapter`
- Workspace: `/private/tmp/yuno-kickstart-phase-18-implement-twilio-adapter`
- Planning directory: `docs/project-specs/2026-08-30-18-implement-twilio-adapter/`
- Owner and team contact: `rmcosta-lab`
- Tracking Issue: none requested
- Depends on: Phase 03 is DONE; Phase 17 is ACTIVE and is an explicit temporary prerequisite wait authorized by the owner on 2026-08-30.
- Conflicts with: none
- Roadmap gate, unchanged: A backend provider adapter creates an idempotent outbound call only after explicit human authorization, enforces the destination allowlist, maps provider call identifiers and terminal status, requires disclosure and consent flags, and passes mocked retry, timeout, duplicate-event, redaction, and failure tests without importing FastAPI.
- Publication of this planning claim does not mark Phase 18 READY under the ordinary roadmap state model and does not waive Phase 17 for integration, review, or merge.

## Assumptions, risks, and fallback

- Phase 03's PASS evidence remains the feasibility baseline, but implementation must refresh current official Twilio call-resource, authentication, status, retry, and privacy documentation before fixing mappings.
- Twilio call creation may not provide an application idempotency guarantee. Volta therefore owns the durable logical-operation key and treats every timeout after dispatch as uncertain until reconciled.
- A destination label can map to a private server-side E.164 number without exposing that number through public values, logs, exceptions, fixtures, or representations.
- Provider status delivery is duplicated, eventually consistent, and potentially out of order; terminal transitions must be monotonic and idempotent.
- Risk: early work diverges from Phase 17 or from `main`. Mitigation: keep this phase backend-only, avoid shared contracts, and refresh/reconcile after Phase 17 merges before review.
- Risk: authorization or consent flags become a cosmetic boolean. Mitigation: typed evidence, bounded actor/time data, fail-closed validation, and zero-request tests for every missing precondition.
- Fallback: keep the provider-neutral fake gateway and the browser/text/recorded demo paths. If durable idempotency or current Twilio semantics cannot satisfy the gate, report BLOCKED and do not place a call.

## Acceptance criteria

1. One typed request requires operation/call correlation, a caller-supplied idempotency key, explicit human actor and timestamp, an allowlisted destination label, AI-disclosure readiness, recording mode, and the required consent policy.
2. Missing authorization, unknown destination, unsafe configuration, disclosure/consent mismatch, or conflicting idempotency replay fails before network I/O.
3. The adapter sends exactly the current official Twilio call-creation fields and authentication to the exact official HTTPS host, with bounded timeout and no secret-bearing representation.
4. Same-key/same-fingerprint retries and concurrent duplicates create at most one provider call and replay the stored provider-neutral result; a different fingerprint conflicts.
5. Timeouts or connection loss after dispatch produce a typed uncertain outcome and no automatic second mutation. Only documented pre-dispatch failures may be retried under a bounded policy.
6. Provider call identifiers and accepted lifecycle states map to immutable provider-neutral results; duplicate and out-of-order events cannot reverse a terminal state.
7. Mocked tests cover success, provider rejection, authentication failure, rate limiting, timeout, malformed/oversized response, duplicate request/event, unknown status, redaction, and cleanup without a live provider.
8. Backend architecture tests prove the provider-neutral telephony package imports no FastAPI, Pydantic API schema, HTTPX, Twilio SDK, SQLAlchemy model, OpenAI, Yuno, or frontend type.
9. `make python-check`, focused adapter tests, migration checks when applicable, `git diff --check`, and a secret/privacy diff review pass.
10. After Phase 17 merges, the branch refreshes `main`, resolves only genuine integration changes, and re-runs the full deterministic gate before Phase 18 enters review.

## Contract and layer decisions

### HTTP contract gate

Not applicable. Phase 18 adds no `/v1` route, Pydantic request/response, status code, callback verification, WebSocket ingress, OpenAPI document, or generated frontend client. Phase 19 owns those contracts.

### Application contract gate

- `yuno_backend.volta.telephony.models`: immutable `OutboundCallRequest`, `OutboundCall`, `OutboundCallStatus`, `OutboundCallStatusEvent`, and authorization/consent values. Inputs are bounded and provider-neutral; phone numbers and provider payloads are absent.
- `yuno_backend.volta.telephony.gateway.OutboundCallGateway`: `async create_call(request: OutboundCallRequest) -> OutboundCall`.
- `yuno_backend.volta.telephony.repositories.OutboundCallAttemptStore`: atomic `reserve`, `complete`, `mark_uncertain`, and `fail` operations keyed by the logical idempotency key and fingerprint. Each operation owns one short persistence transaction; no database transaction or lock spans the Twilio request. `reserve` returns an immutable `OutboundCallAttemptReservation(attempt, created)` so exactly one caller may dispatch; existing replay, conflict, in-flight, uncertain, and failed records are distinguishable without a transaction-spanning lease. Known rejections persist a bounded `FAILED` category for deterministic replay, while ambiguous timeouts, connection loss, provider failures, and malformed success responses persist `UNCERTAIN` and are never redispatched automatically.
- `yuno_backend.volta.telephony.errors`: safe typed authorization, allowlist, idempotency-conflict, authentication, rate-limit, timeout, uncertain-outcome, invalid-response, and provider errors with allowlisted diagnostics only.
- `yuno_backend.integrations.twilio.outbound.TwilioOutboundCallGateway`: constructed with injected HTTP client, redacted config, allowlist resolver, atomic attempt store, and clock; owns URLs, Basic authentication, form mapping, response/status parsing, and transport-error translation. It reserves and commits `PENDING` before dispatch, performs HTTP outside persistence transactions, then records `SUCCEEDED`, `FAILED`, or `UNCERTAIN` in a second atomic operation.
- Construction and FastAPI dependency wiring remain Phase 19 work. Provider events never invoke mandate, quote, commitment, or recovery rules directly.

### Handoffs and terminal result

- Browser/server handoff: none in this phase. No browser or API code calls the adapter yet.
- Twilio handoff: server-only HTTPS request after all authorization and allowlist checks; only normalized safe output crosses back into application code.
- Yuno/payment handoff: none; explicitly excluded.
- Terminal user-visible result: none yet. The observable phase result is a deterministic backend test suite and importable adapter ready for Phase 19.
- Visual/accessibility: not applicable because no interface changes.

## One-writer ownership

| Path or resource | Writer | Decision |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-18-implement-twilio-adapter/**` | `rmcosta-lab` | Planning and validation evidence |
| `backend/src/yuno_backend/volta/telephony/**` | `rmcosta-lab` | Provider-neutral contracts, idempotency protocol, and safe errors |
| `backend/src/yuno_backend/integrations/twilio/**` | `rmcosta-lab` | Twilio URLs, authentication, payload/status mapping, and error translation |
| `backend/tests/volta/telephony/**` and `backend/tests/volta/integrations/twilio/**` | `rmcosta-lab` | Contract, architecture, mapping, lifecycle, retry, and redaction tests |
| `backend/src/yuno_backend/volta/persistence/**`, `backend/migrations/**` | `rmcosta-lab`, only if required | Smallest durable idempotency extension; no remote migration |
| `backend/pyproject.toml` and `uv.lock` | `rmcosta-lab`, paired only if required | Prefer existing HTTPX; add no dependency without demonstrated need |
| `api/**`, `api/openapi.json`, generated frontend client, `frontend/**` | none | Excluded; Phase 19/20 own later work |
| Shared mission, stack, roadmap, and challenge decision | none | No edit; Phase 17 dependency remains recorded |
| Twilio account, numbers, permissions, hosting, and participants | none | No external mutation or contact authorized |
