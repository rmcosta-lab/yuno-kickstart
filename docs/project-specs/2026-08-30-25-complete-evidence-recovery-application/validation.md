# Fase 25 — Validation

## Backend quality

- [x] `cd backend && uv run ruff check .`
- [x] `cd backend && uv run pytest`
- [x] `make python-check`
- [x] `git diff --check`

## Facade and application contracts

- [x] `TextNegotiationApplication` is the single provider-neutral facade for all eight accepted behaviors and imports no FastAPI, Pydantic, HTTP, or provider type.
- [x] All six mutations use canonical fingerprints, atomically persist typed result snapshots, return exact identical replay, reject conflicting reuse, and roll back fully on failure.
- [x] Existing Fase 10 facade behavior and Fase 24 mutation invariants remain green.
- [x] Every accepted response field has a durable backend source; no API memory, direct repository access from FastAPI, or fabricated success fact is required.

## Evidence, recap, brief, and recovery

- [x] Recap call/commitment ownership, exact rendered content, SHA-256 hash, `SIMULATED` disclosure, and timestamp round-trip identically.
- [x] Brief call ownership and ordered `facts`, `objections`, `changes`, and `unresolved_items` round-trip within accepted bounds.
- [x] Safe recovery atomically supersedes one winner, creates one replacement with distinct retrievable agreement evidence, persists one attempt and notification, and leaves exactly one active commitment.
- [x] Missing or empty safe-fixture evidence writes nothing and raises a safe typed exception.
- [x] Bad recovery preserves the active commitment and persists one attempt plus one contextual open escalation without raw transcript/contact/provider data.
- [x] Stale versions, missing/mismatched resources, blocked state, duplicate artifacts, unsupported fixtures, and injected failures preserve prior durable state.

## PostgreSQL, migration, replay, and queries

- [x] Focused suites run with `TEST_DATABASE_URL` against isolated PostgreSQL databases.
- [x] Alembic upgrade, compatible-data downgrade, and re-upgrade pass; incompatible phase-25 data stops downgrade before DDL and preserves the current revision.
- [x] Constraints enforce artifact ownership, complete structured fields, recovery outcome/evidence consistency, and supported idempotency result kinds.
- [x] Concurrent identical requests produce one mutation/result and a replay; conflicting fingerprints produce no partial state.
- [x] Operation projection includes the active escalation and ordered notifications from PostgreSQL.
- [x] Audit pages include bounded artifact histories in stable `(created_at, id, kind)` order with limit 1–100 and deterministic `next_cursor`; `quote_comparison` independently preserves the accepted business ranking with selected/better eligible quotes first.
- [x] Missing/malformed cursors and missing projected evidence fail safely; no collection or query is unbounded.

## Security and scope

- [x] Result snapshots, audit metadata, exceptions, and logs contain no recording bytes/private filesystem path, raw transcript, contact detail, provider payload, submitted secret, or idempotency key.
- [x] No FastAPI/Pydantic/SQLAlchemy session leaks through domain or application contracts.
- [x] No `api/**`, `frontend/**`, OpenAPI, generated client, provider, deployment, shared-spec, manifest, lockfile, `.env.example`, or unrelated file changed.
- [x] Full diff and secret/personal-data review passes.

## Not applicable

- OpenAPI/Orval generation and API route tests: no HTTP contract change.
- Frontend lint/build and browser smoke tests: no frontend change.
- Yuno, OpenAI, Twilio, webhook, or credentialed sandbox tests: no provider integration.
- Supabase advisors: the phase uses isolated local PostgreSQL/SQLAlchemy and adds no Supabase-specific configuration.

## Final gate evidence

- [x] Record exact full and focused command outputs, pass/skip counts, PostgreSQL URL redaction, and migration evidence.
- [x] Record any approved deviation, fallback activation, or unavailable external dependency.

## Recorded evidence — 2026-08-30

- `UV_CACHE_DIR=/private/tmp/uv-cache-phase25 TEST_DATABASE_URL=<redacted-loopback> make python-check`: Ruff passed; pytest reported `486 passed, 2 deselected` with one pre-existing Starlette/httpx deprecation warning.
- `cd backend && UV_CACHE_DIR=/private/tmp/uv-cache-phase25 TEST_DATABASE_URL=<redacted-loopback> uv run pytest tests/volta/persistence -q`: `40 passed` against isolated PostgreSQL databases.
- Adversarial migration order (`test_text_slice.py`, `test_recovery_evidence_repositories.py`, then `test_migrations.py`): `21 passed`; migration tests use their own PostgreSQL database and no longer depend on file order.
- Focused API compatibility (`api/tests/test_volta_text_service.py` and `api/tests/test_volta_text_postgres.py`): `35 passed` with the same pre-existing warning. No API source or contract artifact changed.
- Migration evidence covers upgrade/downgrade/re-upgrade, refusal of unrepresentable legacy upgrade before DDL, refusal of data-bearing downgrade before DDL, preserved revision/schema/data, named constraints, composite keyset indexes, cross-call ownership, recovery/evidence consistency, and exact operation/result-kind mapping.
- Facade evidence covers exact replay of all six mutations, shared-lock concurrency and conflicting fingerprint behavior, injected rollback between domain/audit writes and snapshot/idempotency persistence, stale/missing resources, deterministic safe/bad recovery, default fixture retrieval, exact UTF-8 recap hash, and 10,000/10,001-character bounds.
- Audit and operation reads use bounded keyset queries; audit projection is read in one PostgreSQL `REPEATABLE READ`, read-only transaction. Artifact histories use `(created_at, id, kind)` cursors while quote comparison retains the accepted business ranking.
- The user explicitly approved a 32 MiB durable result-snapshot ceiling. PostgreSQL tests accept a valid multibyte snapshot above 8 MiB and reject a payload above 32 MiB; table metadata and migration use the same `33_554_432`-byte bound.
- Independent read-only contract and PostgreSQL reviews closed their gates after the final corrections. `git diff --check`, import-boundary inspection, changed-path review, and secret/sensitive-data scans passed.
- The two deselected tests require external provider credentials and remain separately marked. No provider, remote database, browser, deployment, production access, or financial/telephony mutation was exercised; no fallback was activated.
