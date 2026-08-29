# Fase 06 validation

Record exact evidence only after executing it. Keep every unexecuted criterion unchecked.

## Migration and schema

- [ ] Alembic upgrades an empty isolated PostgreSQL database to the Fase 06 head, downgrades to base, and upgrades to head again without manual changes.
- [ ] The committed migration creates only the five accepted lowercase `volta_` tables with named primary-key, foreign-key, unique, check, and append-only protections.
- [ ] UUIDs, `timestamptz`, `date`, exact `numeric`, text/arrays, and bounded JSONB match the domain values; money never uses float and timestamps remain aware UTC.
- [ ] Every demonstrated foreign key and ordered status/audit read has an explicit supporting index; redundant or speculative indexes are absent.
- [ ] Migration downgrade ordering removes dependent protections, indexes, foreign keys, and tables safely in the isolated database.

## Repository round trips

- [ ] Intake-draft persistence reloads the exact source prompt, requested language, extraction-policy version, proposal, ordered validation issues, eligibility, version, and timestamps.
- [ ] Operation persistence reloads the route, pickup date, immutable active mandate version, exact `Decimal` amount/currency, condition tuples, authorized actions, actor, and approval time.
- [ ] Current `READY` status and complete ordered operation-status history survive a new session and contain no ORM-backed mutable state.
- [ ] The initial `OPERATION_APPROVED` event reloads with its event ID, operation/version, actor kind, timestamp, correlation ID, and bounded safe metadata.
- [ ] Repository methods return frozen provider-neutral values; sessions, SQLAlchemy rows, lazy loaders, driver values, and database exceptions do not cross the public boundary.

## Atomicity, duplicates, and append-only behavior

- [ ] Approval commits exactly one operation, mandate version 1, `READY` history row, and correlated audit event in one short transaction.
- [ ] Injected mapper, flush, and commit failures roll back every pending approval row and leave the source draft consistently reloadable.
- [ ] Sequential duplicate approval raises `OperationAlreadyApproved` and creates no second operation, mandate, history row, or audit event.
- [ ] Concurrent approval attempts for one draft are closed by the database uniqueness constraint; one succeeds and one receives the documented safe conflict without leaking SQL or driver details.
- [ ] Public audit repositories expose no update/delete operation, and direct PostgreSQL update/delete attempts are rejected by the migration-level append-only protection.
- [ ] Broken foreign keys, non-positive versions, invalid status/actor codes, duplicate mandate versions, and inconsistent active-mandate references fail atomically.

## Application contract and architecture

- [ ] Public exports match the application contract table in `requirements.md`, including status/audit values, correlation input, repositories, unit of work, and safe persistence exceptions.
- [ ] Existing Fase 05 draft creation, approval, mandate enforcement, prompt redaction, immutability, and deterministic in-memory tests continue to pass after the additive contract change.
- [ ] `backend/src/yuno_backend/volta/{mandates,audit}/**` imports no FastAPI, Pydantic API schema, SQLAlchemy, asyncpg, provider adapter, or generated transport model.
- [ ] Private SQLAlchemy mappings remain under `yuno_backend.volta.persistence`; no ORM table or session is exported from the backend application contract.
- [ ] Transaction scope contains no provider/network call, and repository ordering is deterministic for status and audit reads.

## Security and scope

- [ ] Database URLs and source prompts are redacted from configuration/domain representations, SQL logs, exceptions, traces, and test failure output.
- [ ] Audit metadata tests reject or omit unbounded/raw request values, credentials, authorization headers, provider payloads, participant contacts, and private audio.
- [ ] Fixtures contain only synthetic prompts, actors, routes, UUIDs, amounts, and correlations; no credential or real participant data enters Git.
- [ ] API, frontend, OpenAPI, generated clients, `.env.example`, Docker Compose, shared specs, deployment, payment/Yuno, and unrelated files remain outside the implementation diff.
- [ ] No remote/production migration, Supabase mutation/advisor run, provider call, browser trial, phone call, payment, or financial operation is reported as executed.

## Required commands and final review

- [ ] `make postgres-up` starts the existing local PostgreSQL service for isolated test use, or an equivalent isolated PostgreSQL 17 test service is documented.
- [ ] `uv run alembic -c backend/alembic.ini upgrade head` passes against the isolated test database.
- [ ] `uv run pytest backend/tests/volta/persistence` passes.
- [ ] `uv run ruff check .` passes from the repository root.
- [ ] `uv run pytest` passes for the complete Python suite.
- [ ] `make python-check` passes.
- [ ] `git diff --check` passes.
- [ ] The complete diff, migration SQL, schema constraints/indexes, public imports, manifest/lockfile pair, redaction behavior, secret scan, and downstream handoff are reviewed.

## External and browser evidence

- [ ] Browser testing is explicitly recorded as not applicable because this phase changes no rendered surface.
- [ ] OpenAPI/Orval generation is explicitly recorded as not applicable because this phase changes no HTTP contract.
- [ ] Provider, Yuno, webhook, Supabase-project, credentialed sandbox, phone, payment, and financial checks are explicitly recorded as not applicable.
