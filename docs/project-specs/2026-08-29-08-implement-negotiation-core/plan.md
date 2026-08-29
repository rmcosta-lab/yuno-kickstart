# Fase 08 implementation plan

## Work order

1. **Freeze the provider-neutral negotiation contract**
   - Add the frozen models, commands, safe exceptions, repository ports, service signatures, idempotency fingerprint rule, comparison order, and public exports from `requirements.md`.
   - Extend operation repository/unit-of-work ports additively for ID lookup, version/status transition, negotiation aggregates, idempotency records, and active-winner locking.
   - Prove exact carrier filtering, stable ranking, mandate evaluation, comparison, and exception behavior with in-memory unit tests before persistence work.

2. **Implement selection and pre-contact escalation**
   - Build the injected synthetic catalog and `StartNegotiationService` with `READY`/version/mandate checks and a maximum of three snapshotted sessions.
   - Persist either the selected negotiation plus sessions or one no-eligible-carrier escalation, never both partial outcomes.
   - Add idempotent same-request replay and changed-request conflict tests, plus permutation and zero/one/two/three-carrier coverage.

3. **Implement quotes and deterministic comparison**
   - Record call/carrier-consistent quotes, reject stale mandates without a write, and retain current-mandate out-of-policy quotes as ineligible audit history.
   - Compare only current, eligible, unexpired quotes using the fixed ordering in the requirements.
   - Prove duplicate replay, changed-input conflict, stable reload order, expired quote exclusion, and safe rejection reason ordering.

4. **Implement atomic commitment transitions**
   - Allow only the current deterministic best quote to create a candidate/active commitment and retain the opaque evidence UUID without evidence semantics.
   - Lock the operation and winner scope; supersede any prior active commitment and append status/audit history in the same short transaction.
   - Test initial activation, replacement history, stale and invalid requests, commit failure rollback, and concurrent attempts that leave exactly one active winner.

5. **Extend PostgreSQL persistence and pass the gate**
   - Add one reversible Alembic revision, private tables/mappers/repositories, named constraints, demonstrated indexes, idempotency fingerprint/result storage, and event-specific safe audit schemas.
   - Exercise upgrade/downgrade/re-upgrade, domain round trips, constraints, row locks, duplicates, rollback, and process-restart replay against isolated PostgreSQL.
   - Run focused checks, then `make python-check`; inspect the complete diff, migration SQL, exports, redaction, secrets, scope, and `git diff --check` before handoff.

## Workstreams and ownership

| Workstream | Owner | Paths | Starts after |
| --- | --- | --- | --- |
| Negotiation application contract | Fase 08 backend writer | `backend/src/yuno_backend/volta/negotiations/**` and unit tests | Requirements accepted. |
| Operation/audit extensions | Fase 08 backend writer | `backend/src/yuno_backend/volta/{mandates,audit}/**` and focused tests | Public negotiation commands and event vocabulary fixed. |
| Migration, mappings, repositories, unit of work | Fase 08 backend writer | `backend/migrations/**`, `backend/src/yuno_backend/volta/persistence/**`, persistence tests | Domain values, transaction boundaries, and table relationships fixed. |
| Phase coordination | `rmcosta-lab` | Phase spec directory, path ownership, final evidence | All implementation workstreams complete. |

One backend writer owns all implementation paths because the service, migration, repository, idempotency, and concurrency changes share one transaction contract. Parallel activity, if any, is read-only review; no second writer edits the migration chain, persistence boundary, audit schemas, or public exports.

## Contract and integration checkpoints

- Checkpoint 1: public models, commands, exceptions, ports, construction, returns, comparison order, and opaque evidence boundary match `requirements.md` before database design.
- Checkpoint 2: selection produces deterministic snapshots or one pre-contact escalation and makes no model/provider decision.
- Checkpoint 3: quote recording distinguishes stale mandate from persisted mandate rejection and replays identical idempotent requests exactly.
- Checkpoint 4: schema constraints, operation versioning, row locks, and partial active-winner uniqueness are reviewed before commitment repositories depend on them.
- Checkpoint 5: a PostgreSQL reload returns stable comparison and complete superseded history while concurrent retries preserve one active winner.
- Checkpoint 6: Fase 10 can map the accepted `/v1` shapes to these typed services, and Fase 14 can add evidence/recovery semantics without replacing the Phase 08 boundary.

## Validation sequence

- Run `uv run ruff check .` and focused negotiation unit tests after each contract/service group.
- Start the existing loopback PostgreSQL service only for isolated migration/repository tests; use a disposable test database and synthetic fixtures.
- Apply the migration to head, run persistence and concurrency tests, downgrade one revision, and reapply head.
- Run full `uv run pytest` and `make python-check` from the repository root.
- Run `git diff --check`; inspect the complete diff, migration/index intent, public exports, architecture boundaries, idempotency fingerprints, audit allowlists, and secret/personal-data/provider-term scans.
- Browser, frontend, OpenAPI/Orval, OpenAI, Twilio, Yuno, webhook, Supabase-project, credentialed sandbox, phone, payment, and financial validation are not applicable.

## Shared files and downstream coordination

- No manifest, lockfile, API contract, generated client, mission, stack, roadmap, challenge-plan, `.env.example`, Docker Compose, deployment, or provider change is expected.
- Fases 10, 11, and 14 consume the Phase 08 boundary after merge. They must refresh from `main` and extend it rather than introduce a competing negotiation or persistence path.
- The opaque evidence UUID is the deliberate Phase 08/14 seam. If implementation requires recording metadata or referential evidence enforcement now, pause and coordinate instead of broadening this phase.
- Contract clarification recorded during implementation: application commands preserve the accepted printable-ASCII `Idempotency-Key` string exactly; no UUID conversion is permitted. The Phase 08 commitment remains response-incomplete for the nested evidence object until Fase 14, so downstream integration must not invent evidence fields.
- No shared specification change or temporary prerequisite is known. If one appears, record the wait here, notify affected phase owners, and route a broad decision through `manage-shared-specs`.
- OpenAPI/Orval generation is not run because this phase preserves the accepted contract. Any contract mismatch is a blocker for coordination, not permission to edit generated artifacts.

## Safety boundaries

- Do not deploy, use production access, apply a remote migration, modify a Supabase project, call a provider, dial a participant, create a payment, or perform a financial mutation.
- Do not store or log real contact data, raw prompts, conditions text in audit metadata, evidence references in audit metadata, provider payloads, credentials, private audio, SQL values, or driver errors.
- Do not import FastAPI, Pydantic API schemas, SQLAlchemy, or provider types into negotiation domain/application modules.
- Do not implement recording, recap, brief, recovery, notification, mandate replacement, frontend, API wiring, OpenAI, or telephony behavior.
