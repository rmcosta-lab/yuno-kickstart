# Fase 25 — Validation

## Backend quality

- [ ] `cd backend && uv run ruff check .`
- [ ] `cd backend && uv run pytest`
- [ ] `make python-check`
- [ ] `git diff --check`

## Facade and application contracts

- [ ] `TextNegotiationApplication` is the single provider-neutral facade for all eight accepted behaviors and imports no FastAPI, Pydantic, HTTP, or provider type.
- [ ] All six mutations use canonical fingerprints, atomically persist typed result snapshots, return exact identical replay, reject conflicting reuse, and roll back fully on failure.
- [ ] Existing Fase 10 facade behavior and Fase 24 mutation invariants remain green.
- [ ] Every accepted response field has a durable backend source; no API memory, direct repository access from FastAPI, or fabricated success fact is required.

## Evidence, recap, brief, and recovery

- [ ] Recap call/commitment ownership, exact rendered content, SHA-256 hash, `SIMULATED` disclosure, and timestamp round-trip identically.
- [ ] Brief call ownership and ordered `facts`, `objections`, `changes`, and `unresolved_items` round-trip within accepted bounds.
- [ ] Safe recovery atomically supersedes one winner, creates one replacement with distinct retrievable agreement evidence, persists one attempt and notification, and leaves exactly one active commitment.
- [ ] Missing or empty safe-fixture evidence writes nothing and raises a safe typed exception.
- [ ] Bad recovery preserves the active commitment and persists one attempt plus one contextual open escalation without raw transcript/contact/provider data.
- [ ] Stale versions, missing/mismatched resources, blocked state, duplicate artifacts, unsupported fixtures, and injected failures preserve prior durable state.

## PostgreSQL, migration, replay, and queries

- [ ] Focused suites run with `TEST_DATABASE_URL` against isolated PostgreSQL databases.
- [ ] Alembic upgrade, compatible-data downgrade, and re-upgrade pass; incompatible phase-25 data stops downgrade before DDL and preserves the current revision.
- [ ] Constraints enforce artifact ownership, complete structured fields, recovery outcome/evidence consistency, and supported idempotency result kinds.
- [ ] Concurrent identical requests produce one mutation/result and a replay; conflicting fingerprints produce no partial state.
- [ ] Operation projection includes the active escalation and ordered notifications from PostgreSQL.
- [ ] Audit pages include events, quotes, commitments/evidence, recaps, briefs, recoveries, escalations, and notifications in stable `(created_at, id)` order with limit 1–100 and deterministic `next_cursor`.
- [ ] Missing/malformed cursors and missing projected evidence fail safely; no collection or query is unbounded.

## Security and scope

- [ ] Result snapshots, audit metadata, exceptions, and logs contain no recording bytes/private filesystem path, raw transcript, contact detail, provider payload, submitted secret, or idempotency key.
- [ ] No FastAPI/Pydantic/SQLAlchemy session leaks through domain or application contracts.
- [ ] No `api/**`, `frontend/**`, OpenAPI, generated client, provider, deployment, shared-spec, manifest, lockfile, `.env.example`, or unrelated file changed.
- [ ] Full diff and secret/personal-data review passes.

## Not applicable

- OpenAPI/Orval generation and API route tests: no HTTP contract change.
- Frontend lint/build and browser smoke tests: no frontend change.
- Yuno, OpenAI, Twilio, webhook, or credentialed sandbox tests: no provider integration.
- Supabase advisors: the phase uses isolated local PostgreSQL/SQLAlchemy and adds no Supabase-specific configuration.

## Final gate evidence

- [ ] Record exact full and focused command outputs, pass/skip counts, PostgreSQL URL redaction, and migration evidence.
- [ ] Record any approved deviation, fallback activation, or unavailable external dependency.
