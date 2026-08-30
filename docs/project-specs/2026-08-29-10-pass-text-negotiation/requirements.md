# Fase 10 — Pass the integrated text negotiation slice

## Coordination

- Priority: P0, first cross-layer integration gate.
- Branch: `phase/10-pass-text-negotiation`.
- Owner: `rmcosta-lab`; tracking Issue: none requested.
- Depends on: Fases 06, 07, 08, and 09, merged with their required evidence.
- Conflicts with: none.
- Roadmap gate (preserved): FastAPI routes delegate the accepted intake, operation, negotiation, quote, commitment, and audit-state contracts to typed backend services, and the generated client completes the canonical prompt-to-winner journey in text mode against PostgreSQL; no-eligible-carrier, validation correction, duplicate mutation, stale mandate, and out-of-mandate paths pass API tests, `make generate`, `make check`, and browser console and network inspection.
- Temporary operational wait: Fase 14 must merge before response-complete commitment/evidence serialization and terminal browser prompt-to-winner validation can finish. The roadmap has not yet been formally changed; this wait is recorded here without weakening the gate or making Fase 14 an already-accepted dependency.

## Objective and terminal user outcome

Connect the accepted text-mode frontend, FastAPI contracts, deterministic backend services, and PostgreSQL repositories so an operations coordinator can submit and correct the canonical prompt, explicitly approve its mandate, start one-to-three synthetic carrier sessions, record and compare quotes, reject unsafe terms, and finish with exactly one persisted active winner and an auditable state reload. No fixture, placeholder evidence, or browser decision may stand in for durable application state.

Work independent of Fase 14 may proceed now. The phase remains active and cannot be submitted as complete until the nested `CommitmentResponse.evidence`, commitment history/audit serialization, and final browser winner state are backed by the real Fase 14 evidence contract.

## Included scope

- Replace the generic `UnimplementedContractService` only for `create_operation_draft`, `approve_operation`, `get_operation`, `start_negotiation`, `record_quote`, `create_candidate_commitment`, and `get_operation_audit`; unrelated accepted routes retain honest `501 CONTRACT_NOT_IMPLEMENTED` behavior.
- Construct short-lived SQLAlchemy units of work and delegate intake, approval, selection, quote, comparison, commitment, and read projection behavior to typed backend services. FastAPI owns validation, authorization, error translation, correlation IDs, and serialization only.
- Use the deterministic P0 intake extractor and synthetic carrier catalog; persist all accepted mutations and rebuild operation/negotiation/audit state from PostgreSQL after refresh.
- Remove the Fase 07/09 injected demo boundaries from the live text path while preserving deterministic fallback scenarios as explicitly labeled development/demo fallback, not successful integrated evidence.
- Resolve three integration defects without changing accepted request/response shapes: a memory-only browser demo bearer handoff, truthful end-to-end `Idempotency-Replayed` propagation, and a persisted server-owned `cargo_label` carried from intake proposal through operation serialization.
- Map safe backend errors to the already accepted `ApiErrorResponse` codes and headers; add API, integration, generated-client, and browser coverage for the full gate.
- Integrate Fase 14 later through its typed evidence lookup/projection boundary. Commitment creation must remain unavailable safely until a referenced evidence record can be resolved to every required nested field.

## Excluded scope

- Changing accepted Pydantic shapes, route operation IDs, status codes, generated DTOs by hand, or weakening evidence requirements.
- Inventing recording references, offsets, item/event IDs, lifecycle values, commitment history, or audit artifacts; storing only Fase 08's opaque `evidence_id` is not enough to serialize success.
- Implementing Fase 14 recovery, recap, brief, notification, mandate-replacement, private storage, retention, or playback behavior.
- OpenAI provider extraction, Realtime/WebRTC, Twilio/PSTN, Yuno, payments, live carriers/rates, deployment, production access, remote migrations, or external mutations.
- Production identity or multi-tenancy. The bearer remains an explicit local/demo boundary, not a login system.

## Decisions, assumptions, risks, and fallback

- The browser receives the demo bearer only from explicit runtime user input or an equivalent non-persisted test harness. It is held in memory, attached through generated-client request options, and never committed, placed in a `NEXT_PUBLIC_` variable, URL, storage, log, error, or screenshot.
- `cargo_label` is server-owned synthetic operational data produced by the deterministic extraction policy, validated as bounded text, persisted with the draft/operation, and serialized from durable state. Missing cargo content creates validation feedback rather than an invented response value.
- Idempotency replay is application truth, not inferred by the API from equal bodies. Additive typed mutation metadata exposes whether the persisted key/fingerprint returned the original result; the adapter sets `Idempotency-Replayed: true` only for that case. Distinct logical attempts use distinct keys.
- Risk: the accepted commitment response requires evidence that Fase 08 deliberately does not own. Mitigation: keep commitment success and terminal winner validation waiting on Fase 14, return a safe state conflict/not-implemented result meanwhile, and never fabricate nested evidence.
- Risk: transport mapping duplicates domain policy. Mitigation: mapping functions convert values only; all selection, mandate, comparison, winner, and idempotency decisions stay in backend services.
- Risk: fallback fixtures look live. Mitigation: development fallback remains visibly `SIMULATED · NO CONTACT`, makes no API/provider mutation, and cannot satisfy the PostgreSQL or browser gate.
- Fallback: if PostgreSQL or Fase 14 is unavailable, retain the deterministic core and labeled injected UI scenarios for diagnosis, report the wait, and leave the integrated gate unchecked.

## Acceptance criteria

- The generated client, with runtime demo authorization, completes draft creation, validation correction, explicit approval, negotiation start, valid and rejected quote recording, commitment creation, operation reload, and audit reload against PostgreSQL without handwritten transport DTOs.
- Refresh/reconnect reconstructs the source-backed operation, immutable mandate, `cargo_label`, sessions, quotes, comparison, exactly one active winner, superseded history where applicable, and correlated safe audit events from durable state.
- Zero eligible carriers returns the accepted pre-contact escalation and creates no session. Out-of-mandate quotes persist as `REJECTED`; stale mandate/version requests make no write and return the accepted safe `409` semantics.
- Same-key/same-request retries return the original status/body and `Idempotency-Replayed: true` after process/database reload, with no duplicate operation, session, quote, commitment, version, or audit event. Changed-payload reuse returns `409 IDEMPOTENCY_KEY_REUSED`.
- Commitment and winner success is validated only after Fase 14 resolves real response-complete evidence. Missing evidence fails safely, leaves the prior winner unchanged, and exposes no placeholder or private recording data.
- Authorization, CORS, validation, not-found, persistence, stale, mandate, state, and unexpected failures map to accepted safe bodies and preserve `X-Request-ID`; secrets, prompts, SQL/driver details, raw payloads, and participant data do not enter logs or responses.
- API tests, PostgreSQL integration tests, `make generate` twice without drift, `make check`, `git diff --check`, and a mobile/desktop browser run pass. Browser inspection shows no console/runtime errors, failed application requests, leaked bearer, or unexpected provider traffic.

## HTTP contract gate

The accepted Fase 04 shapes remain authoritative:

| Method and route | Typed success | Required integrated semantics |
| --- | --- | --- |
| `POST /v1/operation-drafts` | `201 OperationDraftResponse` | `CreateOperationDraftRequest` plus `Idempotency-Key`; deterministic extraction, validation correction, source/policy retention, durable replay. |
| `POST /v1/operations` | `201 OperationResponse` | `ApproveOperationRequest`; one immutable mandate and operation, including durable server-owned `cargo_label`. |
| `GET /v1/operations/{operation_id}` | `200 OperationResponse` | Reconstruct current mandate, negotiation, sessions, quotes, escalation, and active commitment from PostgreSQL. |
| `POST /v1/operations/{operation_id}/negotiations` | `201 NegotiationResponse` | One-to-three deterministic sessions or one pre-contact escalation, with atomic version/audit changes. |
| `POST /v1/calls/{call_id}/quotes` | `201 QuoteResponse` | Persist eligible or `REJECTED` current-mandate quote; stale mandate/state writes nothing. |
| `POST /v1/calls/{call_id}/commitments` | `201 CommitmentResponse` | Atomic winner transition only for the current best quote and only when Fase 14 can resolve complete evidence. |
| `GET /v1/operations/{operation_id}/audit` | `200 AuditTimelineResponse` | Ordered safe events, full comparison, and response-complete commitment history; unrelated recovery collections may remain empty until their owning phase. |

Every route requires the existing bearer contract; every mutation requires the existing printable-ASCII `Idempotency-Key`. Preserve declared `401`, `403`, `404`, `409`, `422`, `429`, `500`, and applicable `501` responses. Map stale draft/operation to the corresponding current safe version; stale mandate and mandate violations to `409 MANDATE_CONFLICT`; idempotency fingerprint reuse to `409 IDEMPOTENCY_KEY_REUSED`; invalid transitions or missing response-complete evidence to safe `409 STATE_CONFLICT` or the still-honest applicable `501`, without altering the accepted envelope.

## Typed application contract gate

- Existing use-case imports remain authoritative: `yuno_backend.volta.mandates.services.{CreateIntakeDraftService,ApproveOperationService}`, `yuno_backend.volta.negotiations.services.{StartNegotiationService,RecordQuoteService,CreateCommitmentService,QuoteComparisonService}`, their command models, and `yuno_backend.volta.persistence.unit_of_work.SqlAlchemyOperationUnitOfWork` constructed from the configured `async_sessionmaker` plus injected extractor, catalog, clock, and ID generator.
- Add an integration-facing backend boundary under `yuno_backend.volta.text_slice` exporting `TextNegotiationApplication`, typed read projections, and `MutationOutcome[T]`. Construction accepts factories/ports, never FastAPI or Pydantic types; methods use UUIDs/domain commands and return domain projections plus truthful replay metadata. Public exceptions remain the existing mandate, negotiation, and safe persistence exceptions.
- `app.volta_text_service.VoltaTextContractService` implements the existing `ContractService.execute(operation_id, payload, idempotency_key) -> ContractResult`, translates Pydantic JSON values to backend inputs and backend results to the accepted response models, and maps only allowlisted public exceptions to `ContractServiceError`. Dependency construction is centralized, not performed in routers.
- Fase 14 must provide a provider-neutral evidence resolver/projection consumed by `TextNegotiationApplication`; until it exists, no commitment or audit projection may synthesize `CommitmentEvidenceResponse`.

## Browser/server handoff and layer decisions

- Frontend: use only generated Orval functions/hooks and their request options; replace injected success sources with live reads/mutations, invalidate/refetch operation state after mutations, preserve explicit loading/error/retry states, and never calculate eligibility or winner state.
- API/BFF: keep the accepted routers thin, authenticate before delegation, translate safe errors centrally, and set replay/request headers from typed application metadata.
- Backend/core and data: own extraction validation, `cargo_label`, idempotency, PostgreSQL transactions/projections, carrier selection, quote policy, comparison, and winner transitions. Add only the migration required to persist the missing cargo field; no API schema is changed.
- AI/provider/Yuno/payment: no live handoff in this phase. Text mode uses deterministic extraction and synthetic carriers only.
- Security/accessibility/visual: synthetic data only; bearer stays memory-only; no sensitive logging. Preserve keyboard-operable explicit approval/mutations, labeled errors and status announcements, non-color state cues, visible focus, and responsive session/comparison layouts.
- Terminal handoff: browser HTTPS/JSON -> generated client -> authenticated FastAPI -> typed backend services -> PostgreSQL. The terminal visible result is one durable active candidate winner with complete real evidence, never a booking or `VERIFIED` external delivery.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-10-pass-text-negotiation/**` | Fase 10 coordinator (`rmcosta-lab`) | Sole writer for requirements, plan, validation, and temporary wait. |
| `api/app/**`, `api/tests/**` | Fase 10 API writer | Service adapter, dependency wiring, projections/serialization, safe error mapping, and API integration tests; no domain policy. |
| `backend/src/yuno_backend/volta/text_slice/**`, necessary additive mandate/negotiation/persistence files, matching tests, and one migration | Fase 10 backend writer | Integration projections, replay metadata, and durable `cargo_label`; preserve Fase 14 evidence ownership. |
| `frontend/src/app/(control-tower)/{intake,mandate,sessions,comparison}/**`, `frontend/src/features/negotiation/**`, and narrow auth/live-data modules | Fase 10 frontend writer | Live generated-client wiring, runtime bearer handoff, and rendered journey; no generated-file edits or business rules. |
| `api/openapi.json`, `frontend/src/lib/api/generated/**` | Fase 10 API/generated writer | Regenerate only with `make generate`; expected to remain semantically unchanged and never hand-edit. |
| `backend/migrations/**` | Fase 10 backend writer | One additive reversible cargo-label migration; coordinate against Fase 14 before overlapping migration work. |
| `.env.example`, manifests and lockfiles, root `Makefile` | Fase 10 coordinator only if unavoidable | One writer per paired artifact; no dependency is expected and no browser bearer value may be added. |
| Shared mission, stack, roadmap, challenge plan | No Fase 10 writer | The Fase 14 wait is not yet formalized in the roadmap; use `manage-shared-specs` separately if approved. |
| Fase 14 evidence/recovery paths and private storage | No Fase 10 writer | Consume the later typed contract after merge; do not preempt or placeholder it. |
