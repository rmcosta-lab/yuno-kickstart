# Fase 06 implementation plan

## Work order

1. **Freeze the additive persistence contract**
   - Add provider-neutral operation-status and audit values, the correlation input, audit repository port, safe persistence exceptions, and the extended unit-of-work boundary from `requirements.md`.
   - Update Fase 05 services and deterministic fakes so approval constructs one initial status entry and audit event before committing.
   - Keep domain constructors, exceptions, and public exports independent of SQLAlchemy and PostgreSQL.

2. **Introduce the migration runner and reversible schema**
   - Add Alembic to `backend/pyproject.toml`, regenerate `uv.lock`, and configure its async SQLAlchemy environment under `backend/` without logging credentials or bound values.
   - Create the five lowercase `volta_` tables, named constraints, foreign-key indexes, ordered-history indexes, and append-only audit protection defined in the requirements.
   - Review upgrade and downgrade SQL before exercising both directions against an isolated PostgreSQL database.

3. **Implement explicit mappings and repositories**
   - Map every frozen draft, proposal, operation, mandate, status, and audit value to private rows and back without returning ORM objects.
   - Implement the three repositories over one injected `AsyncSession`, including deterministic ordered reads and database-backed duplicate protection.
   - Test UUID, exact `Decimal`, tuple/array, JSONB safe metadata, `date`, `timestamptz`, enum-code, and prompt-redaction round trips near each mapper.

4. **Implement atomic transaction ownership**
   - Build `SqlAlchemyOperationUnitOfWork` around one async session and short transaction per application operation.
   - Prove successful draft creation and approval commits, while mapper, constraint, and injected commit failures roll back all pending rows.
   - Translate the one-operation-per-draft race into `OperationAlreadyApproved`; translate other expected database failures into the accepted safe persistence exceptions.

5. **Pass the PostgreSQL persistence gate**
   - Exercise clean upgrade, downgrade, and re-upgrade; repository round trips; direct audit mutation rejection; missing-foreign-key and invalid-value constraints; and sequential/concurrent duplicate approval.
   - Run focused backend checks during iteration, then the complete `make python-check` gate.
   - Review schema/index intent, diff scope, generated lockfile, redaction, secrets, migrations, public exports, and `git diff --check` before handoff.

## Workstreams and ownership

| Workstream | Owner | Paths | Starts after |
| --- | --- | --- | --- |
| Provider-neutral status/audit contract | Fase 06 backend writer | `backend/src/yuno_backend/volta/{mandates,audit}/**` and matching tests | Requirements accepted. |
| Migration runner and schema | Fase 06 backend writer | `backend/alembic.ini`, `backend/migrations/**`, `backend/pyproject.toml`, `uv.lock` | Contract and schema names fixed. |
| SQLAlchemy tables and mappers | Fase 06 backend writer | `backend/src/yuno_backend/volta/persistence/{tables,mappers}.py` and focused tests | Migration columns and constraints fixed. |
| Repositories and unit of work | Fase 06 backend writer | `backend/src/yuno_backend/volta/persistence/{repositories,unit_of_work,errors}.py` and integration tests | Mappers and public ports fixed. |
| Phase coordination | `rmcosta-lab` | Phase spec directory, path ownership, final validation evidence | All implementation workstreams complete. |

One backend writer owns every implementation path because mappings, schema, repositories, and transaction tests share one contract. Parallel work is limited to read-only review; no second writer edits the manifest/lockfile pair, migration chain, or shared domain modules.

## Contract and integration checkpoints

- Checkpoint 1: public status/audit values, repository methods, unit-of-work construction, correlation input, return types, and safe exceptions match `requirements.md` before ORM work begins.
- Checkpoint 2: table names, types, constraints, indexes, immutable-history behavior, and downgrade sequence are reviewed before repositories depend on them.
- Checkpoint 3: mapper round trips reconstruct only domain objects and pass redaction/immutability tests before services use the SQLAlchemy unit of work.
- Checkpoint 4: approval writes operation, mandate, initial status, and audit evidence in one transaction; rollback and database uniqueness close partial-write and duplicate races.
- Checkpoint 5: Fases 08 and 14 can extend the repositories/history additively, and Fase 10 can construct the unit of work without importing SQLAlchemy types into API schemas.

## Validation sequence

- Start the existing local PostgreSQL service only for isolated migration/repository tests; use synthetic data and a dedicated test database or schema.
- Apply Alembic to head, run persistence tests, downgrade to base, and reapply head to prove reversibility and reproducibility.
- Run `uv run ruff check .`, focused backend tests, the full `uv run pytest`, and `make python-check`.
- Inspect the migration and indexes, run `git diff --check`, review the full diff and lockfile, and scan for database URLs, credentials, raw real prompts, provider data, and unrelated paths.
- Browser, OpenAPI/Orval, provider, Yuno, webhook, Supabase advisor, and credentialed sandbox validation are not applicable to this backend-only plain-PostgreSQL phase.

## Shared files and downstream coordination

- The backend manifest and root lockfile are one writer-owned pair because Alembic is the selected migration runner. No other dependency change is expected.
- No shared mission, technology-stack, roadmap, challenge-plan, OpenAPI, generated-client, `.env.example`, Docker Compose, or deployment change is expected.
- Fases 08, 10, and 14 consume this persistence boundary after merge. They must refresh and extend existing migrations/repositories rather than introducing competing persistence paths.
- If implementation reveals a broad database or hosting decision, pause only affected integration work, notify downstream owners, and route it through `manage-shared-specs`; do not silently broaden this phase.
- No temporary prerequisite is known. If one appears, record the wait here rather than weakening the gate.

## Safety boundaries

- Do not deploy, use production access, apply a remote migration, modify a Supabase project, call a provider, dial a participant, create a payment, or perform any financial mutation.
- Do not log or commit database credentials, raw real prompts, participant data, provider payloads, or private recordings.
- Do not expose SQLAlchemy rows, sessions, SQL strings, driver exceptions, or database configuration through the domain or API boundary.
- Do not implement carrier, negotiation, commitment, recovery, evidence, notification, frontend, or transport behavior in this phase.
