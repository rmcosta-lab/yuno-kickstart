# Fase 24 — Validation

## Backend quality

- [x] `cd backend && uv run ruff check .`
- [x] `cd backend && uv run pytest`
- [x] `make python-check`
- [x] `git diff --check`

## Application contracts

- [x] Public recovery commands, models, services, repositories, results, exceptions, and exports match `requirements.md` and remain independent of FastAPI, Pydantic, SQLAlchemy sessions, and provider payloads.
- [x] Mandate replacement creates immutable version `current + 1`, activates it, resolves only the named same-operation escalation, advances operation state once, and emits safe coordinator audit events.
- [x] Missing, foreign, resolved, stale, or invalid mandate-replacement input rolls back without changing durable state.
- [x] Explicit escalation round-trips bounded structured context and changes no commitment.
- [x] Notification acknowledgement records the first actor and aware UTC timestamp; identical retries are read-only replays and a different actor cannot overwrite them.

## PostgreSQL and migration

- [x] Focused tests run with `TEST_DATABASE_URL` against PostgreSQL.
- [x] Alembic upgrade, compatible-data downgrade, and re-upgrade succeed; a downgrade with phase-24-only data stops before DDL and preserves the current revision.
- [x] Old and new mandate rows round-trip, with only the new mandate referenced as active.
- [x] Escalation context and notification decision/acknowledgement fields round-trip identically.
- [x] Constraints reject partial acknowledgement state, invalid relationships, unsafe bounds, and more than one unresolved escalation per operation.
- [x] Injected failures and stale-version races preserve the previous active mandate, escalation, notification, operation version, commitment history, and audit trail.

## Security and scope

- [x] Audit metadata is event-allowlisted and contains no raw conflict text, attempted-alternative text, recording reference, transcript, contact data, provider payload, or secret.
- [x] Exceptions and logs expose only safe codes, identifiers, versions, and normalized state.
- [x] No FastAPI or Pydantic import appears in backend domain/application modules.
- [x] No `api/**`, `frontend/**`, `api/openapi.json`, generated-client, provider, deployment, manifest, lockfile, shared-spec, or unrelated file changed.
- [x] Full diff review finds no credentials, personal data, remote mutation, or unsupported behavior claim.

## Not applicable

- OpenAPI/Orval generation and API route tests: no HTTP contract change.
- Frontend lint/build and browser smoke tests: no frontend change.
- Yuno, OpenAI, Twilio, webhook, or credentialed sandbox tests: no provider integration.
- Supabase advisors: the phase uses the existing local PostgreSQL/SQLAlchemy boundary and adds no Supabase-specific configuration.

## Final gate evidence

- [x] Record exact command outputs and pass/skip counts.
- [x] Record the focused PostgreSQL command and migration evidence.
- [x] Record any approved deviation, fallback activation, or unavailable external dependency.

## Recorded evidence — 2026-08-30

- `cd backend && uv run ruff check .`: passed with `All checks passed!`.
- `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/yuno uv run pytest tests/volta/recovery tests/volta/persistence/test_recovery_evidence_repositories.py tests/volta/persistence/test_migrations.py -q`: `32 passed` against the healthy local PostgreSQL container; the fixtures created and removed isolated databases.
- `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/yuno uv run pytest -q`: all `288` collected backend tests passed, with `2` tests deselected by the configured suite policy.
- `make python-check`: Ruff passed; pytest reported `431 passed, 32 skipped, 2 deselected` and one pre-existing Starlette `httpx` deprecation warning.
- `git diff --check` and a separate whitespace check of the untracked migration passed.
- `test_upgrade_downgrade_upgrade_is_reversible_and_schema_is_named` exercised head, one-revision downgrade, head re-upgrade, historical downgrade, and final head restoration on an isolated PostgreSQL database.
- The diff is limited to `backend/**` plus this phase-owned validation record. OpenAPI, generated clients, frontend, providers, deployment files, shared specifications, manifests, and lockfiles are unchanged.
- No external provider, credentialed sandbox, remote database, or Supabase-specific dependency was required. A second worktree-local PostgreSQL container was not started because port 5432 was already occupied by the healthy project container; the unused container, network, and empty volume created by that failed attempt were removed.
- Post-review correction: `ReplaceMandateService` now validates all mandate values before writes; the escalation array constraint validates every item; `test_phase24_downgrade_rejects_incompatible_durable_data_before_ddl` proves a phase-24 data-bearing downgrade fails before DDL and leaves the Alembic revision unchanged. Revalidation: focused recovery tests `23 passed`; migration/persistence tests `11 passed`; complete PostgreSQL backend suite `290` collected tests passed with `2` deselected; `make python-check` reported `432 passed, 33 skipped, 2 deselected` and the same pre-existing warning.
- Operational note: downgrade remains schema-reversible on the isolated compatible-data path. It deliberately refuses, rather than deletes, phase-24 audit events, notification context, or explicit escalations without a commitment; an operator must reconcile those facts under an approved retention procedure before retrying the downgrade.
