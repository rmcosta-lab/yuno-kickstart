# Fase 08 — Implement selection, quotes, and commitments

## Coordination

- Priority: P0 backend negotiation foundation.
- Branch: `phase/08-implement-negotiation-core`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fase 05, merged by pull request #6, and Fase 06, merged by pull request #9, both with their required validation evidence.
- Conflicts with: none.
- Roadmap gate: backend-only tests prove deterministic route and availability filtering, fixed ranking, selection of one to three synthetic carriers, pre-contact escalation when none is eligible, idempotent quote recording, stale-mandate and out-of-mandate rejection, quote comparison, exactly one active winner, superseded history, and atomic retry-safe transitions.

## Objective and terminal outcome

Give Volta a deterministic, provider-neutral negotiation core that turns one approved `READY` operation into auditable carrier sessions, quotes, and one active commitment. The target user remains the operations coordinator, but this phase adds no screen or HTTP implementation. Its terminal observable result is a backend test that selects the canonical one-to-three synthetic carriers, records valid and rejected quotes, deterministically activates the best eligible quote, preserves superseded history, and reloads the same result from PostgreSQL after duplicate and stale retries.

## Included scope

- Frozen carrier, negotiation, call-session, quote, commitment, pre-contact escalation, comparison, and idempotency values under a new provider-neutral `volta.negotiations` package.
- A synthetic carrier catalog injected behind a typed protocol. Exact route coverage plus declared availability determine eligibility; ascending fixed priority and stable carrier ID break ties; at most three carriers are selected.
- Application services for negotiation start, quote recording, quote comparison, and candidate commitment creation. The services, never a model or browser callback, own eligibility and disposition decisions.
- Typed stale-operation, stale-mandate, missing-resource, duplicate/idempotency, invalid-transition, and ineligible-quote exceptions containing only safe identifiers and reason codes.
- Additive operation repository reads and optimistic version transitions, negotiation repositories, and one short unit of work per mutation.
- One reversible Alembic migration and private SQLAlchemy mappings/repositories for negotiation state, selected-session snapshots, quotes, commitments, pre-contact escalations, mutation idempotency, operation status/version changes, and correlated audit events.
- Deterministic in-memory tests plus isolated PostgreSQL tests for round trips, constraints, row-locking, rollback, duplicates, stale versions, and concurrent winner transitions.

## Excluded scope

- FastAPI wiring, Pydantic schema edits, HTTP error translation, authorization, CORS, OpenAPI/Orval regeneration, frontend behavior, or browser testing.
- OpenAI extraction or Realtime behavior, Twilio, Yuno, payment behavior, provider calls, real carriers, real rates, external contacts, deployment, production access, or remote migrations.
- Recording metadata, playable audio, recap delivery, briefs, recovery, notifications, mandate replacement, and post-contact escalation, which remain owned by Fase 14.
- A model-selected carrier, fuzzy route matching, dynamic pricing, asynchronous workers, caches, queues, generic workflow engines, or a production carrier-management interface.
- Changes to mission, technology stack, roadmap, challenge plan, manifests, lockfiles, `.env.example`, Docker Compose, or existing API/generated artifacts.

## Domain and deterministic policy decisions

- `CarrierProfile` uses a stable UUID, synthetic display label, exact normalized route pairs, declared availability, and a positive fixed priority. Duplicate IDs or priorities are rejected when constructing the catalog.
- Starting a negotiation requires the expected operation version, the active mandate version, a browser channel, a printable ASCII idempotency key of 8–128 characters, and a correlation UUID. The string key is preserved exactly so Fase 10 can pass the accepted HTTP `Idempotency-Key` without a lossy conversion. Only a `READY` operation may start. The service snapshots selection rationale and creates one session per selected carrier; zero eligible carriers creates one persisted pre-contact escalation and no session.
- The operation version advances once for every successful logical mutation. The matching status entry and audit event use that new version and are committed atomically. Callers with an older expected version receive `StaleOperationVersion` and make no write.
- Quote recording verifies that the call belongs to the operation's active negotiation, that the supplied carrier matches the selected session, and that the supplied mandate version is still active. A stale mandate raises `StaleMandateVersion` and persists nothing.
- A current-mandate quote is always retained for audit. `MandatePolicy` marks it `ELIGIBLE` or `REJECTED`; rejected terms preserve ordered safe reason codes and can never become a commitment. Expired eligible quotes remain historical but are excluded from comparison.
- Eligible quotes compare by amount ascending, pickup-window start ascending, carrier fixed priority ascending, creation time ascending, then quote UUID. This stable order selects exactly one best current quote without model discretion.
- Candidate commitment creation accepts the selected quote and an opaque `evidence_id` from the accepted application/HTTP boundary. Fase 08 stores only that safe identifier; Fase 14 owns evidence existence, recording metadata, playback, access, retention, and later referential strengthening. Consequently the Fase 08 `Commitment` result is intentionally not sufficient by itself to serialize the existing nested `CommitmentResponse.evidence`; Fase 10 may wire the negotiation state and winner journey, but response-complete evidence/commitment mapping waits for the Fase 14 application contract rather than inventing recording fields.
- Creating a commitment for the current best, unexpired, eligible quote makes it `CANDIDATE`/`ACTIVE`. In the same locked transaction any prior active commitment becomes `SUPERSEDED` with its timestamp and replacement link. A partial or concurrent transition rolls back, and a database constraint permits at most one active commitment per operation.
- Every mutation idempotency record is scoped by operation name plus the exact validated string key and stores a canonical request fingerprint and result identity. Repeating the same logical request returns the stored result without new history; reusing the key with different input raises `IdempotencyConflict`.

## HTTP contract gate

No HTTP contract changes are authorized. Fase 10 will map these services to the existing Fase 04 contracts:

| Route | Accepted request and result | Status and error semantics owned by the existing API contract |
| --- | --- | --- |
| `POST /v1/operations/{operation_id}/negotiations` | `StartNegotiationRequest(expected_operation_version, channel)` plus `Idempotency-Key` -> `NegotiationResponse` with zero-to-three sessions or one pre-contact escalation | `201`; safe `403`, `404`, and `409` responses, including duplicate/stale/invalid state. |
| `POST /v1/calls/{call_id}/quotes` | `CreateQuoteRequest(expected_operation_version, carrier_id, mandate_version, terms, valid_until)` plus `Idempotency-Key` -> `QuoteResponse` with eligibility and ordered rejection reasons | `201`; out-of-mandate terms return a persisted `REJECTED` quote, while missing, stale, or idempotency conflicts map to safe `404`/`409`. |
| `POST /v1/calls/{call_id}/commitments` | `CreateCommitmentRequest(expected_operation_version, quote_id, mandate_version, evidence_id)` plus `Idempotency-Key` -> `CommitmentResponse` | `201`; missing, stale, expired, rejected, non-best, or conflicting requests fail safely without changing the active winner. |
| `GET /v1/operations/{operation_id}` and `GET /v1/operations/{operation_id}/audit` | Existing response models receive the persisted negotiation summary, sessions, quote history, active commitment, pre-contact escalation, comparison, commitment history, and audit events | `200`; existing authorization/not-found semantics remain unchanged. |

`api/openapi.json` and `frontend/src/lib/api/generated/**` remain untouched. Any mismatch discovered in the accepted shapes pauses implementation and is coordinated as a contract decision rather than silently changing generated files.

## Application contract gate

| Import path | Public symbols and construction | Typed behavior |
| --- | --- | --- |
| `yuno_backend.volta.negotiations.models` | `CarrierProfile`, `CarrierSession`, `Negotiation`, `Quote`, `QuoteTerms`, `QuoteEligibility`, `Commitment`, `CommitmentLifecycle`, `CommitmentDisposition`, `PreContactEscalation`, `QuoteComparison` | Frozen provider-neutral values using UUIDs, `Decimal` money, explicit currency, dates, aware UTC timestamps, immutable tuples, and safe codes. |
| `yuno_backend.volta.negotiations.commands` | `StartNegotiationCommand`, `RecordQuoteCommand`, `CreateCommitmentCommand` | Frozen typed inputs containing expected operation/mandate versions, the exact validated printable-ASCII idempotency string, a correlation UUID, and only the fields required by each use case. |
| `yuno_backend.volta.negotiations.repositories` | `CarrierCatalog`, `NegotiationRepository`, `QuoteRepository`, `CommitmentRepository`, `IdempotencyRepository`, and extended `OperationUnitOfWork` | Async ports for exact reads/writes and transaction-scoped winner locking; no SQLAlchemy/session type crosses the boundary. |
| `yuno_backend.volta.negotiations.services` | `StartNegotiationService.start(...) -> Negotiation`, `RecordQuoteService.record(...) -> Quote`, `CreateCommitmentService.create(...) -> Commitment`, `QuoteComparisonService.compare(...) -> QuoteComparison` | Constructed with the typed unit of work, catalog where applicable, `MandatePolicy`, clock, and ID generator; every mutation commits once or rolls back completely. |
| `yuno_backend.volta.negotiations.errors` | `OperationNotFound`, `StaleOperationVersion`, `StaleMandateVersion`, `NegotiationAlreadyStarted`, `CallSessionNotFound`, `CarrierSessionMismatch`, `QuoteNotFound`, `QuoteNotEligible`, `QuoteExpired`, `QuoteNotBestCandidate`, `InvalidNegotiationTransition`, `IdempotencyConflict` | Safe exceptions expose stable codes and UUID/version context only; they contain no SQL, prompt, contact, provider payload, or credential. |
| `yuno_backend.volta.persistence.repositories` and `.unit_of_work` | Additive SQLAlchemy negotiation repositories and the extended `SqlAlchemyOperationUnitOfWork` | Constructed from the existing async session factory; locks and persists one logical mutation transaction and returns only domain values. |

The existing `MandatePolicy`, operation/audit models, and approval services remain backward compatible. Public package exports are explicit; negotiation domain/application modules import neither FastAPI nor SQLAlchemy.

## Persistence, atomicity, and audit decisions

- Extend the existing migration chain rather than replacing the Fase 06 schema. Use private lowercase `volta_` tables and explicit two-way mappers; the implementation phase fixes exact table/constraint names before code depends on them.
- Store selected carrier label, route, availability, and fixed-rank snapshots with each session so historical rationale is reproducible even if the injected synthetic catalog changes later.
- Use unique constraints for one negotiation start per operation, one session per negotiation/carrier, scoped mutation idempotency, quote/result identities, and one active commitment per operation. Use foreign keys and checks for positive versions, finite exact amounts, valid enum codes, ordered windows, and consistent operation/call/carrier relationships.
- Lock the operation and active-winner scope before version checks and state transitions. Optimistic expected-version checks remain the public stale-write boundary; PostgreSQL uniqueness closes concurrent races.
- Append safe events for negotiation start, pre-contact escalation, quote recorded/rejected, commitment activated, and commitment superseded. Metadata is allowlisted and bounded; no raw request, source prompt, contact detail, evidence reference, conditions text, or provider payload is copied into audit metadata.
- No database transaction remains open across network or provider work. This phase performs no provider work.

## Acceptance criteria

- Exact route/availability filtering and fixed ranking select 1, 2, or 3 eligible synthetic carriers deterministically; zero eligible carriers persists one auditable pre-contact escalation before any call session exists.
- Duplicate negotiation start and quote/commitment retries with the same key and fingerprint return the original result without additional sessions, quotes, version changes, commitments, status entries, or audit events; key reuse with changed input fails safely.
- Current-mandate valid quotes persist as eligible, out-of-mandate quotes persist as rejected with deterministic reason order, and stale-mandate attempts persist nothing.
- Expired, rejected, wrong-session, and non-best quotes cannot become commitments. Quote comparison is stable across process and database reloads.
- Initial and replacement winner transitions preserve complete commitment history while exactly one row is active. Injected and concurrent failures cannot expose two active winners or a partially advanced operation.
- PostgreSQL upgrade, downgrade, and re-upgrade succeed; repositories round-trip every negotiation value; constraints reject broken relationships and invalid values; rollback preserves the prior durable state.
- `uv run ruff check .`, `uv run pytest`, focused PostgreSQL-backed tests, `make python-check`, and `git diff --check` pass. Diff review confirms no secret, personal contact, provider payload, raw evidence detail, unrelated change, API/generated change, or external mutation.

## Assumptions, risks, and fallback

- Assumption: the merged Fase 05 mandate contract and Fase 06 SQLAlchemy/Alembic persistence boundary remain the baseline.
- Risk: Phase 08 overreaches into recovery/evidence. Mitigation: store only the accepted opaque evidence UUID and initial/superseded disposition; defer recording and recovery semantics to Fase 14.
- Risk: concurrent retries create duplicate quotes or winners. Mitigation: canonical fingerprints, scoped uniqueness, operation/winner row locks, expected versions, partial unique active-winner enforcement, and rollback tests.
- Risk: carrier selection becomes nondeterministic. Mitigation: exact route/availability predicates, unique fixed priority, stable UUID tie-break, snapshotted rationale, and permutation tests.
- Risk: new audit data leaks negotiation text or contacts. Mitigation: event-specific allowlists, bounded identifiers/counts/reason codes, synthetic fixtures, and redaction review.
- Fallback: retain deterministic in-memory catalog/repositories and pure comparison/mandate services so Fase 10 can be diagnosed locally; block PostgreSQL/API integration if migration, concurrency, or atomic-winner evidence fails.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-08-implement-negotiation-core/**` | `rmcosta-lab` | Phase coordinator owns requirements, plan, and validation evidence. |
| `backend/src/yuno_backend/volta/negotiations/**` | Fase 08 backend writer | Sole writer for negotiation domain values, ports, services, errors, and exports. |
| `backend/src/yuno_backend/volta/{mandates,audit,persistence}/**` | Fase 08 backend writer | Additive operation/audit/persistence extensions only; preserve Fases 05/06 contracts. |
| `backend/migrations/**` | Fase 08 backend writer | Sole writer for one additive reversible migration and its constraints/indexes. |
| `backend/tests/volta/{negotiations,mandates,audit,persistence}/**` | Fase 08 backend writer | Deterministic unit and isolated PostgreSQL integration tests. |
| `backend/pyproject.toml`, `uv.lock`, root `Makefile` | No planned Fase 08 writer | Existing dependencies and commands are sufficient; treat any discovered need as a coordinated manifest/lockfile decision. |
| `api/**`, `frontend/**`, `api/openapi.json`, generated clients | No Fase 08 writer | No HTTP, generated contract, or UI change is authorized. |
| Shared mission, stack, roadmap, challenge plan, deployment and provider files | No Fase 08 writer | No shared decision is required; route a broad discovery through `manage-shared-specs`. |
