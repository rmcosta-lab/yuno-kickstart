# Fase 08 validation

Record exact evidence only after executing it. Keep every unexecuted criterion unchecked.

## Deterministic selection and escalation

- [x] Exact route coverage and declared availability are the only eligibility predicates; unavailable or uncovered carriers are excluded with stable reason codes.
- [x] Fixed priority plus stable UUID tie-breaking produces the same order for every input permutation and selects at most three carriers.
- [x] Canonical fixtures prove zero, one, two, and three eligible-carrier outcomes using only synthetic labels and rates.
- [x] Zero eligible carriers persists exactly one pre-contact escalation and correlated audit event before any session exists; retry creates no duplicate.
- [x] A successful start snapshots the selected carriers and rationale, advances the operation from `READY` to `NEGOTIATING`, and commits sessions, status, idempotency, and audit state atomically.

## Quotes, mandate safety, and comparison

- [x] Quote recording verifies operation, negotiation, call, and carrier relationships and rejects mismatches without a write.
- [x] A stale operation or mandate version raises the typed stale exception and leaves quotes, versions, idempotency, status, and audit state unchanged.
- [x] Current-mandate terms outside price, currency, pickup window, conditions, or authority persist as `REJECTED` with deterministic safe reasons and cannot become commitments.
- [x] Eligible quotes retain exact `Decimal` amount/currency, pickup window, conditions, mandate version, validity, and source session across reloads; money never uses float.
- [x] Comparison excludes rejected and expired quotes and orders eligible quotes by amount, pickup start, fixed priority, creation time, and UUID exactly as specified.
- [x] Reusing a quote idempotency key with the same canonical request returns the original quote with no new version/event; changed input raises `IdempotencyConflict`.
- [x] Application commands and durable records preserve printable ASCII idempotency keys of 8–128 characters exactly as accepted by the HTTP contract; no UUID coercion or lossy normalization occurs.

## Commitments, concurrency, and retry safety

- [x] Rejected, expired, wrong-session, missing, stale-mandate, and non-best quotes cannot become commitments.
- [x] The current deterministic best quote creates one `CANDIDATE`/`ACTIVE` commitment with the opaque evidence UUID and correlated status/audit state.
- [x] A later valid winner transition atomically marks the prior commitment `SUPERSEDED`, records timestamps/replacement links, and preserves complete ordered history.
- [x] Database constraints and repository locking permit at most one active commitment per operation under concurrent attempts.
- [x] Identical commitment retries return the stored result without another winner transition; changed-input key reuse fails safely.
- [x] Injected mapper, flush, commit, and concurrent conflict failures roll back all pending version, commitment, disposition, status, idempotency, and audit writes.

## Migration and persistence

- [x] Alembic upgrades an isolated PostgreSQL database to the Phase 08 head, downgrades one revision, and upgrades again without manual changes or loss of the Fase 06 baseline.
- [x] Private `volta_` tables, named keys/checks/unique constraints, partial active-winner uniqueness, and demonstrated indexes match the accepted relationships and queries.
- [x] Repositories round-trip only frozen provider-neutral negotiation values; SQLAlchemy rows, sessions, SQL strings, driver exceptions, and lazy state never cross public boundaries.
- [x] Constraints reject invalid versions/enums, non-finite amounts, broken operation/negotiation/call/carrier/quote relationships, duplicate session selection, and conflicting idempotency records.
- [x] A process restart can replay an identical mutation and recover the original result identity from durable idempotency state.
- [x] Operation row locking and expected-version checks are exercised against real PostgreSQL, not inferred from an in-memory double.

## Application contract and architecture

- [x] Public symbols, construction, typed inputs/outputs, and safe exceptions match the application contract table in `requirements.md`.
- [x] Existing Fase 05 mandate and Fase 06 persistence/public tests remain passing after additive extensions.
- [x] Negotiation domain/application modules import no FastAPI, Pydantic API schema, SQLAlchemy, asyncpg, OpenAI, Twilio, Yuno, or generated transport model.
- [x] Carrier selection, mandate evaluation, quote comparison, and commitment disposition contain no model or browser discretion.
- [x] The evidence boundary stores only the opaque UUID; recording metadata, playback, access, retention, and recovery behavior remain absent.
- [x] The handoff explicitly records that nested `CommitmentResponse.evidence` serialization remains incomplete until Fase 14; no placeholder recording fields are invented in backend or API code.

## Security and scope

- [x] Audit metadata is event-specific, bounded, and excludes prompts, contact details, quote conditions text, evidence references, request bodies, provider payloads, credentials, and private audio.
- [x] Exceptions, representations, logs, traces, SQL configuration, and test failure output expose no secret, database URL, raw prompt, real participant data, or driver detail.
- [x] Fixtures contain only synthetic carriers, routes, rates, UUIDs, timestamps, correlations, and evidence identifiers.
- [x] API, frontend, OpenAPI, generated clients, manifests, lockfiles, shared specs, provider code, deployment, and unrelated files remain outside the implementation diff.
- [x] No remote/production migration, Supabase mutation/advisor run, provider call, browser trial, phone call, payment, or financial operation is reported as executed.

## Required commands and final review

- [x] `uv run ruff check .` passes from the repository root.
- [x] `uv run pytest backend/tests/volta/negotiations` passes.
- [x] `uv run pytest backend/tests/volta/persistence` passes against isolated loopback PostgreSQL.
- [x] `uv run pytest` passes for the complete Python suite.
- [x] `make python-check` passes.
- [x] `git diff --check` passes.
- [x] The complete diff, migration SQL, constraints/indexes, public exports, idempotency/concurrency behavior, audit allowlists, secret scan, and downstream handoff are reviewed.

## Explicitly not applicable

- [x] Browser and rendered UI validation are recorded as not applicable because this phase changes no frontend surface.
- [x] OpenAPI/Orval generation is recorded as not applicable because this phase changes no HTTP contract.
- [x] OpenAI, Twilio, Yuno, webhook, Supabase-project, credentialed sandbox, phone, payment, financial, and external provider checks are recorded as not applicable and are not executed.

## Executed evidence

- Focused negotiation and persistence suite: `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yuno UV_CACHE_DIR=/tmp/yuno-phase8-uv-cache uv run pytest backend/tests/volta/negotiations backend/tests/volta/persistence -q` passed all 44 tests.
- Complete required Python gate: `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yuno UV_CACHE_DIR=/tmp/yuno-phase8-uv-cache make python-check` passed Ruff and all 220 tests; one pre-existing Starlette/httpx deprecation warning was emitted.
- Migration cycle on isolated loopback database `yuno_phase8_final_validation`: upgrade to `20260829_08`, downgrade to `20260829_06`, verification of the five Fase 06 baseline tables and revision, and re-upgrade to `20260829_08` all passed. The temporary database was dropped afterward.
- Final independent read-only contract review and PostgreSQL best-practices review both returned `PASS` after their findings were corrected.
- `git diff --check`, untracked-file whitespace inspection, architecture-boundary inspection, changed-path scope review, and secret-pattern scan passed.
- Browser/UI and OpenAPI/Orval checks were not applicable because no frontend or HTTP contract changed. Provider, Supabase-project, credentialed sandbox, phone, payment, financial, and production checks were not applicable and were not executed.
- Fase 14 remains responsible for evidence metadata and nested `CommitmentResponse.evidence`; Fase 08 persists only the opaque `evidence_id` UUID.
