# Fase 25 — Complete the evidence and recovery application facade

## Coordination

- Priority: P0 backend prerequisite for Fase 15 and the complete browser recovery journey.
- Branch: `phase/25-complete-evidence-recovery-application`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fases 10 and 24, merged by pull requests #15 and #18 with gate evidence recorded.
- Conflicts with: none.
- Roadmap gate: one provider-neutral backend facade supplies durable recap, brief, recovery, mandate-replacement, escalation, notification-acknowledgement, operation, and audit behavior with atomic fingerprinted idempotency, complete deterministic PostgreSQL projections, rollback, safe errors, no FastAPI import, and no HTTP-contract change.

## Objective and terminal outcome

Extend the existing `TextNegotiationApplication` so Fase 15 can delegate every accepted evidence and recovery operation through one typed backend boundary. The terminal backend-observable result is a complete operation and paged audit projection whose recap, brief, recovery, escalation, notification, commitment, and evidence facts all reload from PostgreSQL, plus exact durable replay for every new mutation.

## Included scope

- Add facade inputs and methods for simulated recap, structured brief, deterministic inbound recovery, mandate replacement, explicit escalation, and notification acknowledgement; extend operation and audit reads.
- Persist recap `call_id`, rendered content, SHA-256 content hash, `SIMULATED` disclosure, and creation time. Persist brief `call_id` and the accepted bounded `facts`, `objections`, `changes`, and `unresolved_items` tuples.
- Persist the recovery scenario, before/after operation versions, decision reason, resulting commitment or escalation, correlation, and creation time needed to reproduce `RecoverySimulationResponse`.
- Own a provider-neutral deterministic fixture catalog for `MANDATE_SAFE` and `OUT_OF_MANDATE`. The safe fixture supplies reconfirmed terms and a private playable evidence reference plus `audio_start_ms`, item ID, and event ID; the bad fixture supplies out-of-mandate terms and bounded escalation context.
- Require a safe replacement to create its new commitment and matching `AgreementEvidence` in the same transaction. Verify that the fixture artifact is retrievable before writing; missing or empty evidence fails without changing operation state.
- Extend post-contact simulation so the bad path persists its call ID and bounded conflict, alternatives, and recommended action. It preserves the active commitment and creates one open escalation.
- Add atomic fingerprinted replay for the six new facade mutations. The operation name, key, normalized request fingerprint, status-independent typed result snapshot, result resource ID, and creation time commit with the mutation. Identical retries return the stored projection and timestamp; conflicting reuse raises the existing safe idempotency error and writes nothing.
- Extend repository ports, SQLAlchemy mappings/queries, and the existing text-mutation idempotency boundary. Add the smallest additive reversible Alembic migration for missing response facts and constraints.
- Return complete bounded projections in deterministic `(created_at, id)` order. Operation reads include the active post-contact escalation and notifications. Audit reads include events, quote comparison, commitment/evidence history, recaps, briefs, recoveries, escalations, and notifications with a stable opaque cursor and limit of 1–100.
- Add deterministic unit and isolated PostgreSQL tests for construction, persistence, replay, ordering, cursor boundaries, missing evidence/resources, stale state, conflicting keys, concurrency, and injected rollback.

## Excluded scope

- FastAPI wiring, Pydantic schema or route changes, HTTP error translation, authorization, CORS, rate limiting, OpenAPI/Orval generation, generated-client changes, frontend behavior, or browser testing.
- Provider calls, live audio capture, real inbound PSTN, notification delivery, OpenAI, Twilio, Yuno, payments, deployment, production access, or remote migration.
- A `VERIFIED` recap, SMS/email delivery, raw transcript storage, recording bytes in PostgreSQL, or reuse of an earlier agreement artifact as evidence for a replacement commitment.
- Mission, technology stack, roadmap, challenge-plan, manifest, lockfile, `.env.example`, Docker Compose, or unrelated changes.

## Application and persistence decisions

- `TextNegotiationApplication` remains the only transport-free facade; Fase 25 extends it rather than adding a competing API-facing service. Domain services retain mandate and transition authority.
- Facade inputs use UUIDs, versions, bounded tuples/strings, domain money/window values, correlation IDs, and idempotency keys. They import no Pydantic, FastAPI, HTTP status, or API enum.
- The idempotency fingerprint excludes the idempotency key and correlation ID, uses the existing canonical SHA-256 encoding, and includes every behavior-affecting value, including the selected deterministic scenario. The replay snapshot contains only provider-neutral projection fields and no submitted secret or private recording bytes.
- Underlying evidence/recovery services gain idempotency-aware entry points or an equivalent shared transaction helper so domain mutation, audit events, durable result snapshot, and idempotency row commit once. The facade must not perform a mutation and record replay in separate transactions.
- A recap hash is computed server-side from the exact UTF-8 rendered content. The content and hash are immutable; the only channel/disclosure value remains `SIMULATED`.
- Brief arrays preserve caller order, enforce the accepted item/count bounds, and are immutable. Recap and brief ownership is derived from the named call and commitment and is checked before writing.
- The safe recovery fixture represents a new reconfirmation turn. Its evidence belongs to the replacement commitment; copying the superseded commitment's evidence or leaving a placeholder evidence identifier is forbidden.
- Cursor values identify the last `(created_at, id)` boundary without exposing database offsets. Missing or malformed cursors raise a safe typed validation error; page contents and `next_cursor` are stable across identical reads of unchanged data.
- SQLAlchemy sessions and JSON rows never cross repository ports. Constraints enforce complete recap/brief/recovery facts, one-to-one artifact ownership, evidence/commitment ownership, and supported idempotency operation/result kinds.
- Compatible-data downgrade and re-upgrade must pass. If phase-25-only durable facts cannot be represented by the previous schema, downgrade refuses before destructive DDL and preserves the current revision.

## HTTP contract gate

No HTTP contract change is authorized. Fase 25 must be directly adaptable to the accepted Fase 04 operations:

| Existing operation | Accepted success | Backend behavior |
| --- | --- | --- |
| `create_simulated_recap` | `201 WrittenRecapResponse` | Durable recap projection with call, commitment, hash, rendered content, `SIMULATED`, and timestamp. |
| `create_call_brief` | `201 CallBriefResponse` | Durable call-owned structured brief projection. |
| `start_inbound_simulation` | `201 RecoverySimulationResponse` | Deterministic safe replacement plus evidence or bad-path escalation, with all response facts persisted. |
| `replace_mandate` | `201 OperationResponse` | Existing Fase 24 immutable replacement plus the complete operation projection. |
| `create_escalation` | `201 EscalationResponse` | Existing Fase 24 mutation plus durable bounded projection. |
| `acknowledge_notification` | `200 CoordinatorNotificationResponse` | Existing Fase 24 acknowledgement plus exact replay projection. |
| `get_operation` | `200 OperationResponse` | Complete active escalation and notification projection in addition to existing state. |
| `get_operation_audit` | `200 AuditTimelineResponse` | Bounded deterministic artifact histories and cursor without raw/private content leakage. |

Fase 15 remains responsible for bearer authorization, headers, Pydantic conversion, HTTP status/error mapping, and replay headers. `api/openapi.json` and `frontend/src/lib/api/generated/**` remain byte-for-byte unchanged.

## Application contract gate

| Import path | Public symbols | Construction and typed behavior |
| --- | --- | --- |
| `yuno_backend.volta.text_slice` | Extended `TextNegotiationApplication`, existing `OperationUnitOfWorkFactory` | Constructed with the existing extractor, catalog, clock, IDs, evidence storage, policy version, and a deterministic `RecoveryFixtureCatalog`; exposes all eight behaviors through one facade. |
| `yuno_backend.volta.text_slice.models` | `CreateSimulatedRecapInput`, `CreateCallBriefInput`, `StartInboundRecoveryInput`, `ReplaceMandateInput`, `CreateEscalationInput`, `AcknowledgeNotificationInput`, `AuditQuery`, extended `OperationProjection`/`AuditProjection`, artifact/recovery projections, existing `MutationOutcome` | Frozen provider-neutral inputs and complete immutable outputs; mutation methods return `MutationOutcome[T]` with durable replay truth. |
| `yuno_backend.volta.recovery.fixtures` | `RecoveryScenario`, `RecoveryFixture`, `RecoveryFixtureCatalog`, deterministic catalog implementation | Maps only the two accepted scenarios to bounded proposed terms/context and, for the safe path, private evidence metadata; performs no provider or network call. |
| `yuno_backend.volta.evidence` and `.recovery` | Extended recap/brief/recovery models, commands, services, repositories, and safe errors | Services validate ownership/version and commit state, evidence, audit, and replay atomically. Missing evidence, stale state, unsupported scenario, and conflicts use safe typed exceptions. |
| `yuno_backend.volta.idempotency` | Extended `TextMutationIdempotency` and typed durable result snapshot | Supports the six new operation names and exact replay without API/Pydantic values. Existing Fase 10 operation names and behavior remain compatible. |
| `yuno_backend.volta.persistence` | Additive SQLAlchemy repositories, mappers, tables, queries, and `SqlAlchemyOperationUnitOfWork` wiring | Persists every accepted projection fact and returns domain/application values only. |

## Acceptance criteria

- Each new mutation has one facade entry point, one atomic commit, one canonical fingerprint, exact stored replay, conflict detection, and complete rollback on any exception.
- Recap and brief values round-trip every accepted response field; recap content hashes match exact stored content; duplicate ownership and mismatched call/commitment relationships fail safely.
- A mandate-safe fixture replaces exactly one active commitment, supersedes history, persists new agreement evidence owned by the replacement, creates one notification, and returns a fully projectable recovery. Missing fixture evidence leaves all state unchanged.
- An out-of-mandate fixture preserves the commitment, persists one contextual open escalation and recovery attempt, and exposes no raw transcript or contact/provider fact.
- Mandate replacement, explicit escalation, and acknowledgement preserve all Fase 24 invariants while adding atomic facade replay and complete projections.
- Operation and audit projections reload all artifacts from PostgreSQL, order every collection deterministically, enforce the 1–100 page bound, and produce stable cursors.
- Migration upgrade, compatible downgrade, and re-upgrade pass; incompatible downgrade refuses before DDL. Constraints, stale races, idempotency concurrency, and injected failures preserve consistent state.
- `cd backend && uv run ruff check .`, `cd backend && uv run pytest`, focused PostgreSQL tests, `make python-check`, and `git diff --check` pass. Diff review confirms no API/generated/frontend/provider/shared-spec drift, secret, raw recording/transcript, personal data, or FastAPI/Pydantic import.

## Risks and fallback

- Risk: replaying a mutable operation by re-querying current state changes the original response. Mitigation: store and return an immutable typed result snapshot with the idempotency record.
- Risk: safe recovery creates a commitment that cannot satisfy the required evidence projection. Mitigation: require a distinct retrievable fixture artifact and persist its evidence in the same transaction as replacement.
- Risk: extending recap/brief models breaks Fase 14 construction sites. Mitigation: update commands, models, mappers, fakes, repositories, and focused contracts together; do not invent defaults for missing response facts.
- Risk: one aggregate query becomes unbounded or unstable. Mitigation: deterministic `(created_at, id)` ordering, a 1–100 limit, stable cursor tests, and demonstrated indexes only.
- Fallback: retain the merged Fase 10 facade and Fase 24 services unchanged, keep Fase 15 paused at honest `501` operations, and split any unresolved cross-cutting contract decision through `manage-shared-specs`; never add API-owned SQL or fabricate response/evidence facts.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-25-complete-evidence-recovery-application/**` | Fase 25 coordinator (`rmcosta-lab`) | Owns requirements, plan, and validation evidence. |
| `backend/src/yuno_backend/volta/text_slice/**` | Fase 25 backend writer (`rmcosta-lab`) | Sole writer for facade inputs, methods, outputs, pagination, and exports. |
| `backend/src/yuno_backend/volta/{evidence,recovery,idempotency}/**` | Fase 25 backend writer (`rmcosta-lab`) | Smallest additive model/service/fixture/replay extensions required by the facade. |
| `backend/src/yuno_backend/volta/{audit,persistence}/**` | Fase 25 backend writer (`rmcosta-lab`) | Additive ports, ordering queries, mappings, tables, repositories, constraints, and unit-of-work wiring. |
| `backend/migrations/**` | Fase 25 backend writer (`rmcosta-lab`) | Sole writer for one additive reversible migration. |
| `backend/tests/volta/{text_slice,evidence,recovery,idempotency,audit,persistence}/**` | Fase 25 backend writer (`rmcosta-lab`) | Deterministic unit and isolated PostgreSQL coverage. |
| `backend/pyproject.toml`, `uv.lock`, root `Makefile` | No planned writer | Existing dependencies and commands are sufficient; coordinate a discovered need before editing. |
| `api/**`, `frontend/**`, OpenAPI, generated clients | No Fase 25 writer | No transport or browser change is authorized. |
| Shared mission, stack, roadmap, challenge plan, provider/deployment files | No Fase 25 writer | No shared decision is carried; broad discoveries route through `manage-shared-specs`. |
