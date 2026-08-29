# Fase 06 validation

Record exact evidence only after executing it. Keep every unexecuted criterion unchecked.

## Migration and schema

- [x] Alembic upgrades an empty isolated PostgreSQL database to the Fase 06 head, downgrades to base, and upgrades to head again without manual changes.
- [x] The committed migration creates only the five accepted lowercase `volta_` tables with named primary-key, foreign-key, unique, check, and append-only protections.
- [x] UUIDs, `timestamptz`, `date`, exact `numeric`, text/arrays, and bounded JSONB match the domain values; money never uses float and timestamps remain aware UTC.
- [x] Every demonstrated foreign key and ordered status/audit read has an explicit supporting index; redundant or speculative indexes are absent.
- [x] Migration downgrade ordering removes dependent protections, indexes, foreign keys, and tables safely in the isolated database.

## Repository round trips

- [x] Intake-draft persistence reloads the exact source prompt, requested language, extraction-policy version, proposal, ordered validation issues, eligibility, version, and timestamps.
- [x] Operation persistence reloads the route, pickup date, immutable active mandate version, exact `Decimal` amount/currency, condition tuples, authorized actions, actor, and approval time.
- [x] Current `READY` status and complete ordered operation-status history survive a new session and contain no ORM-backed mutable state.
- [x] The initial `OPERATION_APPROVED` event reloads with its event ID, operation/version, actor kind, timestamp, correlation ID, and bounded safe metadata.
- [x] Repository methods return frozen provider-neutral values; sessions, SQLAlchemy rows, lazy loaders, driver values, and database exceptions do not cross the public boundary.

## Atomicity, duplicates, and append-only behavior

- [x] Approval commits exactly one operation, mandate version 1, `READY` history row, and correlated audit event in one short transaction.
- [x] Injected mapper, flush, and commit failures roll back every pending approval row and leave the source draft consistently reloadable.
- [x] Sequential duplicate approval raises `OperationAlreadyApproved` and creates no second operation, mandate, history row, or audit event.
- [x] Concurrent approval attempts for one draft are closed by the database uniqueness constraint; one succeeds and one receives the documented safe conflict without leaking SQL or driver details.
- [x] Public audit repositories expose no update/delete operation, and direct PostgreSQL update/delete attempts are rejected by the migration-level append-only protection.
- [x] Broken foreign keys, non-positive versions, invalid status/actor codes, duplicate mandate versions, and inconsistent active-mandate references fail atomically.

## Application contract and architecture

- [x] Public exports match the application contract table in `requirements.md`, including status/audit values, correlation input, repositories, unit of work, and safe persistence exceptions.
- [x] Existing Fase 05 draft creation, approval, mandate enforcement, prompt redaction, immutability, and deterministic in-memory tests continue to pass after the additive contract change.
- [x] `backend/src/yuno_backend/volta/{mandates,audit}/**` imports no FastAPI, Pydantic API schema, SQLAlchemy, asyncpg, provider adapter, or generated transport model.
- [x] Private SQLAlchemy mappings remain under `yuno_backend.volta.persistence`; no ORM table or session is exported from the backend application contract.
- [x] Transaction scope contains no provider/network call, and repository ordering is deterministic for status and audit reads.

## Security and scope

- [x] Database URLs and source prompts are redacted from configuration/domain representations, SQL logs, exceptions, traces, and test failure output.
- [x] Audit metadata tests reject or omit unbounded/raw request values, credentials, authorization headers, provider payloads, participant contacts, and private audio.
- [x] Fixtures contain only synthetic prompts, actors, routes, UUIDs, amounts, and correlations; no credential or real participant data enters Git.
- [x] API, frontend, OpenAPI, generated clients, `.env.example`, Docker Compose, shared specs, deployment, payment/Yuno, and unrelated files remain outside the implementation diff.
- [x] No remote/production migration, Supabase mutation/advisor run, provider call, browser trial, phone call, payment, or financial operation is reported as executed.

## Required commands and final review

- [x] `make postgres-up` starts the existing local PostgreSQL service for isolated test use, or an equivalent isolated PostgreSQL 17 test service is documented.
- [x] `uv run alembic -c backend/alembic.ini upgrade head` passes against the isolated test database.
- [x] `uv run pytest backend/tests/volta/persistence` passes.
- [x] `uv run ruff check .` passes from the repository root.
- [x] `uv run pytest` passes for the complete Python suite.
- [x] `make python-check` passes.
- [x] `git diff --check` passes.
- [x] The complete diff, migration SQL, schema constraints/indexes, public imports, manifest/lockfile pair, redaction behavior, secret scan, and downstream handoff are reviewed.

## External and browser evidence

- [x] Browser testing is explicitly recorded as not applicable because this phase changes no rendered surface.
- [x] OpenAPI/Orval generation is explicitly recorded as not applicable because this phase changes no HTTP contract.
- [x] Provider, Yuno, webhook, Supabase-project, credentialed sandbox, phone, payment, and financial checks are explicitly recorded as not applicable.

## Recorded command and inspection evidence

- `make postgres-up` started the repository's PostgreSQL 17 container; it reported healthy before testing. `make postgres-down` restored the prior zero-service state after validation without removing the named volume.
- `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yuno uv --cache-dir /tmp/yuno-phase6-uv-cache run pytest backend/tests/volta/persistence` passed: 12 tests, zero skips. The fixture created a random loopback-only database, upgraded it, downgraded it, and removed it; the `yuno` database was not migrated.
- A dedicated local database also passed CLI `uv run alembic -c backend/alembic.ini upgrade head`, `downgrade base`, and `upgrade head`. It was downgraded again and removed after inspection.
- `UV_CACHE_DIR=/tmp/yuno-phase6-uv-cache TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yuno make python-check` passed: Ruff reported no findings and the full suite passed 188 tests with zero skips. The one warning is the pre-existing Starlette/httpx compatibility deprecation.
- The first `make python-check` attempt did not execute checks because the sandbox denied the default `~/.cache/uv`; the identical gate passed with the isolated `/tmp` cache above.
- `git diff --check` passed. The complete tracked and untracked path scope, Alembic runner and migration, table/mapper/repository/UoW boundaries, exact constraint and index sets, reversible append-only triggers, manifest/lockfile pair, public exports, and generated-file exclusions were reviewed.
- Targeted secret and sensitive-term scanning found only the pre-existing synthetic database URLs in `backend/tests/test_database.py` and policy prose; no new credential, raw provider payload, PAN/CVV, payment token, or real participant data was introduced.
- Two independent read-only subagent reviews found no remaining PostgreSQL/schema or application-contract blocker after corrections to FK versioning, metadata bounds, local-database safeguards, rollback assertions, and deterministic ordering.
- Browser, OpenAPI/Orval, provider, Yuno, webhook, Supabase-project, credentialed sandbox, phone, payment, and financial checks were not applicable and were not executed.
