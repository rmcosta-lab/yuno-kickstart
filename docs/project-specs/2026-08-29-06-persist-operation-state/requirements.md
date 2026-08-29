# Fase 06 — Persist operations, mandates, and audit events

## Coordination

- Priority: P0 backend persistence foundation.
- Branch: `phase/06-persist-operation-state`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fase 05, merged by pull request #6 at `fb90cef` with the required validation evidence.
- Conflicts with: none.
- Roadmap gate: versioned migrations and backend repository tests persist and reload the intake source, policy version, operation, immutable mandate, status history, and correlated append-only audit events in PostgreSQL; rollback and duplicate-operation cases preserve a consistent state.

## Objective and terminal outcome

Give later negotiation and API phases a durable PostgreSQL implementation of the Fase 05 repository and unit-of-work contracts. The target user remains the operations coordinator, but this backend-only phase adds no screen or HTTP journey. Its terminal observable result is a PostgreSQL-backed test that creates a draft, approves it once, reloads the same immutable operation and mandate, and shows the initial `READY` history plus a correlated `OPERATION_APPROVED` audit event.

## Included scope

- Alembic as the smallest conventional migration runner compatible with the accepted async SQLAlchemy stack, including one reversible initial Volta migration.
- Private SQLAlchemy tables and explicit domain mappers for intake drafts, operations, immutable mandate versions, operation-status history, and audit events.
- Async PostgreSQL repositories and a short-lived SQLAlchemy unit of work implementing the public Fase 05 protocols without exposing sessions, rows, or ORM models.
- Additive provider-neutral status and audit values required to persist the initial approval transition.
- Database constraints and indexes for UUID identities, positive versions, exact money, aware timestamps, foreign keys, one operation per source draft, one mandate per operation/version, ordered history retrieval, and correlation lookup.
- PostgreSQL-backed repository, migration, rollback, duplicate-approval, round-trip, append-only, and redaction tests using synthetic data.

## Excluded scope

- FastAPI wiring, Pydantic transport models, HTTP status mapping, authorization, CORS, OpenAPI, Orval, frontend behavior, or browser testing.
- Carrier selection, quotes, commitments, recovery, evidence storage, notifications, or later operation transitions owned by Fases 08 and 14.
- OpenAI, Twilio, Yuno, Supabase project configuration, Row Level Security (RLS), provider calls, deployment, production access, remote migrations, and live or financial mutations.
- A generic event store, outbox, database service layer, caching, background workers, or infrastructure beyond the existing local PostgreSQL service.
- Changes to the accepted mission, technology stack, roadmap, or challenge decision.

## Persistence and schema decisions

- Use lowercase `volta_`-prefixed tables in PostgreSQL's existing application schema: `volta_intake_drafts`, `volta_operations`, `volta_mandates`, `volta_operation_status_history`, and `volta_audit_events`.
- Keep application-supplied UUIDs as public identities. Use `timestamptz`, `date`, exact `numeric`, `text`, `boolean`, and PostgreSQL text arrays where they match the frozen domain values; use JSONB only for bounded safe audit metadata and ordered validation issue codes.
- Store every mandate as an immutable row with unique `(operation_id, id)` and `(operation_id, version)` constraints. A deferrable composite foreign key from `volta_operations.(id, active_mandate_id)` to `volta_mandates.(operation_id, id)` keeps the active mandate non-null and tied to the same operation without overwriting prior versions; the cyclic operation/mandate keys are validated at transaction commit.
- Enforce one operation per source draft with a unique foreign key. The repository pre-check remains useful, while the database constraint closes concurrent duplicate-approval races and is translated to the existing safe `OperationAlreadyApproved` exception.
- Persist status changes as insert-only history rows containing operation ID, operation version, status, and occurrence time. Approval creates the initial `READY` row in the same transaction as the operation and mandate.
- Persist audit events as insert-only rows containing event ID, operation ID/version, safe actor kind, event type, occurrence time, correlation ID, and bounded safe metadata. Public repositories expose append/list only; migration-level protection rejects update and delete attempts.
- Index every foreign key not already covered by a unique index and the demonstrated reads: operation history by `(operation_id, occurred_at, id)`, audit pagination by `(operation_id, occurred_at, event_id)`, and audit correlation by `correlation_id`.
- Keep transactions scoped to one application operation. Draft creation is one transaction; approval atomically writes the operation, mandate, initial status, and audit event. No transaction remains open across a provider or network call.
- Migrations own schema evolution and downgrade behavior. Implementation and tests may apply them only to an isolated local/test database; this phase does not apply a remote or production migration.

## Domain and application decisions

- Extend the provider-neutral Volta domain with `OperationStatus`, `OperationStatusEntry`, `AuditActorKind`, and `AuditEvent`; no SQLAlchemy type enters these values.
- Add a correlation UUID to `ApproveOperationCommand`. `ApproveOperationService` creates the initial status and audit values before one commit, and rollback removes all four approval writes on any failure.
- Extend `OperationUnitOfWork` additively with an audit repository. Existing in-memory test doubles remain supported after adopting the new public contract.
- Domain-to-row and row-to-domain mapping is explicit and complete. A reload reconstructs exact UUID, `Decimal`, enum, tuple, date, UTC time, prompt-redaction, and immutable mandate semantics rather than returning ORM instances.
- Expected uniqueness conflicts use existing typed domain exceptions. Other database failures are rolled back and translated to a small safe persistence exception vocabulary without SQL, credentials, submitted prompts, or driver messages.

## HTTP contract gate

No HTTP contract changes in this phase. The accepted Fase 04 routes and Pydantic models remain authoritative, `api/openapi.json` and generated frontend files remain untouched, and API contract stubs continue to return their documented behavior. Fase 10 will construct the SQLAlchemy unit of work and map the provider-neutral operation, status, and audit values to the accepted `/v1` responses.

## Application contract gate

Public modules and symbols to add or extend:

| Import path | Public symbols | Contract |
| --- | --- | --- |
| `yuno_backend.volta.mandates.models` | `OperationStatus`, `OperationStatusEntry`; extended `Operation` | Frozen provider-neutral current status and ordered immutable status history; existing operation construction is updated without importing persistence types. |
| `yuno_backend.volta.audit.models` | `AuditActorKind`, `AuditEvent` | Frozen event with UUID identity, operation/version, safe actor/event codes, aware UTC timestamp, correlation UUID, and bounded safe metadata. |
| `yuno_backend.volta.audit.repositories` | `AuditEventRepository` | Async `add(event)` and ordered `list_by_operation(operation_id)` only; no update/delete contract. |
| `yuno_backend.volta.mandates.commands` | extended `ApproveOperationCommand` | Adds the correlation UUID used by approval history and audit evidence. |
| `yuno_backend.volta.mandates.repositories` | extended `OperationUnitOfWork` | Exposes intake-draft, operation, and audit repositories plus commit/rollback while preserving transport independence. |
| `yuno_backend.volta.persistence.repositories` | `SqlAlchemyIntakeDraftRepository`, `SqlAlchemyOperationRepository`, `SqlAlchemyAuditEventRepository` | Constructed with one `AsyncSession`; typed async methods return domain values and raise safe application exceptions. |
| `yuno_backend.volta.persistence.unit_of_work` | `SqlAlchemyOperationUnitOfWork` | Constructed with `async_sessionmaker[AsyncSession]`; one context owns one session/transaction and exposes the repositories above. |
| `yuno_backend.volta.persistence.errors` | `PersistenceConflict`, `PersistenceUnavailable` | Safe persistence exceptions containing only stable reason/resource codes and safe identifiers. |

Private SQLAlchemy tables and mapper functions live under `yuno_backend.volta.persistence` but are not exported. `ApproveOperationService.approve(...) -> Operation` remains the public approval entry point; it now records initial `READY` history and one `OPERATION_APPROVED` audit event with the command's correlation ID in the same commit. Duplicate approval still raises `OperationAlreadyApproved` and leaves no partial rows.

## Security and external handoff

- Source prompts and approval actors are persisted because the accepted model requires them, but prompts remain excluded from representations, exceptions, SQL logging, test failure values, and structured logs.
- Audit metadata accepts only bounded safe scalar values. It never stores credentials, authorization headers, raw provider payloads, private audio, real contacts, or full request bodies.
- Test fixtures use synthetic prompts, actors, routes, IDs, and amounts. Database URLs remain environment-only and redacted.
- There is no browser/server, Yuno, payment, OpenAI, Twilio, telephony, Supabase, or provider handoff in this phase.

## Acceptance criteria

- Alembic upgrades a clean PostgreSQL test database to the Phase 6 head, downgrades cleanly, and upgrades again without manual schema changes.
- Repository round trips preserve the source prompt, extraction-policy version, validation results, operation, exact mandate values, current status, complete status history, and correlated audit event while retaining immutable/redacted domain behavior.
- Approval atomically persists exactly one operation, mandate version 1, `READY` history row, and `OPERATION_APPROVED` audit event; an injected failure before commit leaves none of them durable.
- Sequential and concurrent approval attempts for one draft cannot create two operations; the database constraint wins the race and callers receive the documented safe conflict.
- Mandate and audit rows cannot be updated through public repositories; PostgreSQL rejects direct update/delete attempts against audit history in the migration test.
- Constraints reject broken foreign keys, non-positive versions, invalid status/actor values, and inconsistent active-mandate references; demonstrated foreign-key and ordered-history reads have explicit indexes.
- Domain modules remain free of FastAPI, Pydantic API, SQLAlchemy, asyncpg, and provider imports; ORM rows and sessions never cross a public application boundary.
- `uv run ruff check .`, `uv run pytest`, PostgreSQL-backed migration/repository tests, `make python-check`, and `git diff --check` pass with no secret or unrelated change.

## Assumptions, risks, and fallback

- Assumption: the merged Fase 05 domain contract and the existing local PostgreSQL 17 service remain the implementation baseline.
- Risk: ORM mappings leak into the domain. Mitigation: private tables, explicit two-way mappers, public architecture tests, and domain-only repository return types.
- Risk: duplicate approval passes the service pre-check under concurrency. Mitigation: database uniqueness plus typed conflict translation inside one short transaction.
- Risk: source prompts or database credentials leak through diagnostics. Mitigation: redacted configuration/domain representations, safe exceptions, disabled SQL value logging, and targeted tests/review.
- Risk: migrations become irreversible or destructive. Mitigation: test upgrade/downgrade/upgrade on an isolated database and review generated SQL and constraints before handoff.
- Fallback: retain the deterministic in-memory Fase 05 repositories and block database/API wiring if PostgreSQL, migration, rollback, or duplicate-consistency evidence fails.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-06-persist-operation-state/**` | `rmcosta-lab` | Phase coordinator owns requirements, plan, and validation evidence. |
| `backend/src/yuno_backend/volta/{mandates,audit,persistence}/**` | Fase 06 backend writer | Sole writer for additive domain contract changes, SQLAlchemy adapters, mappings, and unit of work. |
| `backend/migrations/**`, `backend/alembic.ini` | Fase 06 backend writer | Sole writer for the reversible Volta schema and migration environment. |
| `backend/tests/volta/{mandates,audit,persistence}/**` and database test support | Fase 06 backend writer | Unit and isolated PostgreSQL integration tests; no shared live database. |
| `backend/pyproject.toml` and `uv.lock` | Fase 06 backend writer as one manifest/lockfile pair | Add only the selected Alembic dependency and regenerate the lockfile together. |
| Root `Makefile` | Fase 06 backend writer only if required | Add only narrow migration/test commands needed for reproducible validation; otherwise preserve it. |
| `api/**`, `frontend/**`, `api/openapi.json`, generated clients | No Fase 06 writer | No transport, generated contract, or UI change is authorized. |
| `docs/project-specs/{mission,tech-stack,roadmap}.md`, `docs/decisions/challenge-plan.md` | No Fase 06 writer | No shared decision change is required; route a discovered broad change through `manage-shared-specs`. |
| Existing payment/Yuno adapters, `.env.example`, Docker Compose, deployment files | No Fase 06 writer | Reuse the existing local database configuration without changing provider or deployment scope. |
