# Fase 04 — Define the core P0 HTTP contracts

## Coordination

- Priority: P0 contract foundation.
- Branch: `phase/04-define-p0-http-contracts`.
- Owner: `CaioRuas24010`.
- Tracking Issue: none requested.
- Depends on: none.
- Conflicts with: none.
- Roadmap gate: Pydantic contracts cover the complete P0 browser surface under `/v1`; authorization, idempotency, stale-state, and safe-error semantics have API tests; OpenAPI and Orval generation pass.

## Objective and user-visible outcome

Give frontend, API, and backend implementers one generated, reviewable contract for the complete P0 browser journey before business rules or provider calls are wired. The operations coordinator gains no new working screen in this phase; the terminal observable result is a deterministic OpenAPI document and strict generated TypeScript client that later phases can implement and consume without copying data transfer objects.

## Scope

Included:

- Pydantic request, response, enum, identifier, pagination, and safe-error models for intake, operation approval and retrieval, negotiation start, carrier sessions, quotes, candidate commitments, evidence, simulated recaps, call briefs, inbound recovery simulations, mandate replacement, escalations, notifications, and audit.
- FastAPI contract declarations with stable `operation_id` values, explicit success and error responses, bearer security, required idempotency headers, and version preconditions.
- Central transport behavior needed to prove safe validation, authentication, error translation, and correlation identifiers.
- API contract tests, deterministic `api/openapi.json` export, and Orval output under `frontend/src/lib/api/generated/**`.
- The safe configuration inventory needed for demo authorization, with no secret value committed.

Excluded:

- Backend entities, rules, application services, repositories, migrations, or database access.
- Real extraction, carrier selection, mandate enforcement, quote validation, commitment transitions, recovery, or audit persistence.
- OpenAI Realtime, Twilio, Yuno, browser voice, payment, or any provider call.
- Handwritten frontend types, UI work, deployment, production access, real participant data, and live financial or telephony mutations.
- A claim that any contract-only endpoint completes the Volta journey. Until a later phase wires a service, the endpoint must fail with the safe `CONTRACT_NOT_IMPLEMENTED` response rather than return fabricated success.

## Contract conventions

- `/health` remains public and unversioned. Every Volta operation is under `/v1` and requires `Authorization: Bearer <demo-token>`.
- Every state-changing `POST` requires `Idempotency-Key`, 8–128 printable ASCII characters. Replaying the same key with the same normalized request returns the original status and body and sets `Idempotency-Replayed: true`; reusing it with a different request returns `409 IDEMPOTENCY_KEY_REUSED`.
- Every mutation after an operation exists carries `expected_operation_version` as a positive integer. A mismatch returns `409 STALE_OPERATION_VERSION` with the safe current version. Draft approval carries `expected_draft_version` for the same purpose.
- Every response carries `X-Request-ID`; identifiers are UUIDs; timestamps are timezone-aware UTC RFC 3339 values; dates use ISO 8601; monetary values use non-negative integer minor units and an uppercase ISO currency code. P0 accepts `MXN` only. JSON integer fields reject booleans and numeric strings and do not exceed JavaScript's safe integer maximum, `9_007_199_254_740_991`.
- Server-owned state fields cannot appear in create requests. Unknown request fields are rejected. Response models are explicit and do not expose database or provider payloads.
- P0 browser channels are `BROWSER_TEXT` and `BROWSER_VOICE`; inbound behavior is labeled `INBOUND_SIMULATION`. PSTN and provider identifiers remain for the later telephony contract phase.
- Commitment evidence lifecycle values are `CANDIDATE`, `SIMULATED`, and `VERIFIED`, but no P0 request may set them directly. The recap contract can only produce `SIMULATED`; `VERIFIED` remains reserved for a future accepted delivery provider.
- Commitment disposition is independent of evidence lifecycle and is `ACTIVE` or `SUPERSEDED`.

## HTTP contract gate

| Method and route | Stable operation ID | Request | Success | Required semantics |
| --- | --- | --- | --- | --- |
| `POST /v1/operation-drafts` | `create_operation_draft` | `CreateOperationDraftRequest` | `201 OperationDraftResponse` | Apply the active server extraction policy, retain its version with the source prompt, and create no authority. |
| `POST /v1/operations` | `approve_operation` | `ApproveOperationRequest` | `201 OperationResponse` | Approve one draft version and create mandate version 1. |
| `GET /v1/operations/{operation_id}` | `get_operation` | Path UUID | `200 OperationResponse` | Return the reconstructable current aggregate, including sessions and quotes, without raw provider data. |
| `POST /v1/operations/{operation_id}/negotiations` | `start_negotiation` | `StartNegotiationRequest` | `201 NegotiationResponse` | Represent one to three selected sessions or a pre-contact escalation. |
| `POST /v1/calls/{call_id}/quotes` | `record_quote` | `CreateQuoteRequest` | `201 QuoteResponse` | Preserve source call, mandate version, terms, and eligibility result. |
| `POST /v1/calls/{call_id}/evidence` | `attach_commitment_evidence` | `CreateCommitmentEvidenceRequest` | `201 CommitmentEvidenceResponse` | Require private playable reference, `audio_start_ms`, item ID, and event ID. |
| `POST /v1/calls/{call_id}/commitments` | `create_candidate_commitment` | `CreateCommitmentRequest` | `201 CommitmentResponse` | Require quote, mandate, and evidence references; state remains server-owned. |
| `POST /v1/calls/{call_id}/recaps` | `create_simulated_recap` | `CreateSimulatedRecapRequest` | `201 WrittenRecapResponse` | Return channel `SIMULATED` and never imply accepted external delivery. |
| `POST /v1/calls/{call_id}/briefs` | `create_call_brief` | `CreateCallBriefRequest` | `201 CallBriefResponse` | Persist structured facts, objections, changes, and unresolved items. |
| `POST /v1/operations/{operation_id}/inbound-simulations` | `start_inbound_simulation` | `StartInboundSimulationRequest` | `201 RecoverySimulationResponse` | Accept only `MANDATE_SAFE` or `OUT_OF_MANDATE` deterministic scripts. |
| `POST /v1/operations/{operation_id}/mandates` | `replace_mandate` | `ReplaceMandateRequest` | `201 OperationResponse` | Require resolved escalation context and create a new immutable version. |
| `POST /v1/calls/{call_id}/escalations` | `create_escalation` | `CreateEscalationRequest` | `201 EscalationResponse` | Preserve conflict and attempted alternatives without making a commitment. |
| `POST /v1/notifications/{notification_id}/acknowledgements` | `acknowledge_notification` | `AcknowledgeNotificationRequest` | `200 CoordinatorNotificationResponse` | Record coordinator acknowledgement idempotently. |
| `GET /v1/operations/{operation_id}/audit` | `get_operation_audit` | Cursor and limit query | `200 AuditTimelineResponse` | Return ordered safe events, full quote comparison terms, typed artifact histories, and an opaque next cursor. |

Every operation declares the applicable `401`, `403`, `404`, `409`, `422`, `429`, `500`, and `501` responses with `ApiErrorResponse`; non-applicable responses are omitted rather than advertised generically. Contract-only handlers return `501 CONTRACT_NOT_IMPLEMENTED` after authorization and request validation until an integration phase supplies typed application behavior.

## Pydantic model gate

- Intake: requests contain the source prompt and requested language only; responses add the active server-selected extraction policy version, proposed route and pickup date, proposed mandate, validation issues, approval eligibility, draft version, and timestamps.
- Mandate: version, maximum amount in minor units, `MXN`, pickup window, allowed conditions, escalation conditions, approval actor, and approval timestamp.
- Operation: route, synthetic cargo label, status, operation version, active mandate, negotiation summary, current sessions and quotes, active commitment, open escalation, and notifications.
- Carrier and session: synthetic carrier ID/display name, deterministic eligibility and ranking evidence, browser channel, simulated direction, session state, and timestamps. No phone number belongs in P0 responses.
- Quote: call and carrier references, terms, validity window, mandate version, eligibility status, rejection reasons, and creation timestamp.
- Commitment and evidence: quote and carrier references, immutable agreed terms, lifecycle, disposition, replacement link, private recording reference, millisecond turn offset, item ID, and event ID.
- Recap and brief: simulated channel, content hash, safe rendered content, structured facts, objections, changes, unresolved items, and timestamps.
- Recovery, escalation, and notification: fixed scenario, before/after operation versions, structured before/after recovery snapshots and decision reason, attempted alternatives, recommended action, resolution state, acknowledgement state, and correlation ID.
- Audit: append-only event ID, operation version, safe actor kind, event type, timestamp, correlation ID, safe metadata, full quote comparison rows, commitment and evidence history, recaps, briefs, recovery artifacts, escalations, notifications, and an opaque pagination cursor.

## Safe error and authorization semantics

`ApiErrorResponse` contains only `code`, `message`, `request_id`, optional field issues, optional resource ID, optional current operation version, and optional current draft version. Each stale error sets only the applicable safe version. It never includes submitted secrets, raw prompts, authorization headers, stack traces, exception names, provider responses, or full request bodies.

| Status | Codes to test | Meaning |
| --- | --- | --- |
| `401` | `AUTHENTICATION_REQUIRED`, `AUTHENTICATION_INVALID` | Missing or invalid configured demo bearer token. |
| `403` | `ACTION_NOT_AUTHORIZED` | Authenticated demo actor lacks authority for the requested action. |
| `404` | `RESOURCE_NOT_FOUND` | Safe resource absence without internal lookup details. |
| `409` | `STALE_OPERATION_VERSION`, `STALE_DRAFT_VERSION`, `IDEMPOTENCY_KEY_REUSED`, `STATE_CONFLICT`, `MANDATE_CONFLICT` | Retry or transition cannot proceed against current state. |
| `422` | `VALIDATION_ERROR` | Pydantic or semantic field failure; issues identify fields but omit submitted values. |
| `429` | `RATE_LIMITED` | Authorized demo traffic exceeds the configured boundary. |
| `500` | `INTERNAL_ERROR` | Unexpected failure with request ID only. |
| `501` | `CONTRACT_NOT_IMPLEMENTED` | Contract exists but no application service is wired yet. |

The example authorization value is never emitted into OpenAPI. `.env.example` may add an empty `VOLTA_DEMO_BEARER_TOKEN` name; the real value remains in an ignored local environment or secret store. Credentialed CORS stays limited to explicit origins and permits only the required safe headers.

## Application contract gate

No backend application contract is published or imported in this phase. Pydantic models remain transport DTOs and must not be reused as domain entities. Contract routes expose an injectable test boundary only so API tests can exercise success and error mappings with deterministic fakes. Phases 05, 08, and 14 own backend symbols and typed inputs/outputs; phases 10 and 15 must record their real import paths, construction, return types, and public exceptions before replacing `CONTRACT_NOT_IMPLEMENTED`. No FastAPI type may enter `backend/**`.

## Browser/server and provider handoff

The browser handoff is only the generated Orval client over HTTPS/JSON to this repository's BFF. There is no Yuno handoff and no payment state. There is no OpenAI or Twilio connection in this phase. The terminal result is contract generation and compilation, not a completed user journey; provider and browser-voice handoffs remain gated by their roadmap phases.

## Assumptions, risks, and fallback

- Assumption: the accepted mission, stack, challenge decision, and roadmap remain unchanged during this contract phase.
- Risk: an over-broad aggregate makes generated types hard to consume. Mitigation: small named models, server-owned state, UUID references, and bounded nested summaries.
- Risk: contract stubs appear functional. Mitigation: honest `501 CONTRACT_NOT_IMPLEMENTED` behavior and documentation.
- Risk: later domain work reveals a missing transition. Mitigation: additive schema changes through the owning later API phase; do not weaken current safety or evidence fields.
- Risk: generated files drift. Mitigation: regenerate only from FastAPI, run generation twice, and require the second run to be clean.
- Fallback: deterministic contract fakes and generated client types remain usable by frontend phases even when the database and providers are unavailable.

## Acceptance criteria

- All routes, operation IDs, request/response models, headers, status codes, and safe error schemas above appear in generated OpenAPI.
- API tests prove authentication ordering, safe validation errors, idempotency replay/conflict mapping through an injected fake, stale-version mapping, safe unexpected-error mapping, and stable operation IDs.
- No test or runtime stub fabricates domain success without an injected fake; the default behavior is `501 CONTRACT_NOT_IMPLEMENTED`.
- `make generate` deterministically updates `api/openapi.json` and `frontend/src/lib/api/generated/**`; a second generation produces no diff. The two `GET` operations generate TanStack queries, all twelve `POST` operations generate mutations, and non-2xx responses throw typed API errors that preserve status and safe response headers.
- Generated TypeScript compiles and existing frontend checks pass without handwritten parallel DTOs.
- No backend, provider, database, UI, deployment, or live mutation enters the diff.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-04-define-p0-http-contracts/**` | `CaioRuas24010` | Phase coordinator owns requirements, plan, and validation. |
| `api/app/schemas/**`, contract routers, transport dependencies, and API tests | Fase 04 API writer | Own all Pydantic and FastAPI contract source in this phase. |
| `api/app/main.py`, `.env.example` | Fase 04 API writer | Touch only for router registration, safe auth inventory, CORS, and error handling. |
| `api/openapi.json` | Fase 04 API writer | Generated only; never hand-edit. |
| `frontend/src/lib/api/generated/**` | Fase 04 API writer | Generated through Orval; frontend workers consume but do not edit. |
| `frontend/orval.config.ts`, `frontend/src/lib/api/volta-fetch.ts` | Fase 04 coordinator-assigned Orval writer | Own generator semantics and the typed fetch boundary required by DR-02/DR-03; no UI or parallel DTO enters this path. |
| `frontend/src/components/health-experience.tsx` | Fase 04 coordinator | Adapt the existing health consumer to the generated HTTP response envelope; no visual or behavioral redesign. |
| `pyproject.toml`, `uv.lock`, `frontend/package.json`, `pnpm-lock.yaml` | Fase 04 coordinator if unavoidable | No dependency is expected. Manifest and matching lockfile move together after a plan update. |
| `docs/project-specs/{mission,tech-stack,roadmap}.md`, `docs/decisions/challenge-plan.md` | No Fase 04 writer | No shared-spec change is required. Coordinate separately if that assumption changes. |
| `backend/**`, all other non-generated frontend source | No Fase 04 writer | Explicitly out of scope. |
