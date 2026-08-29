# Fase 08 validation

Record exact evidence only after executing it. Keep every unexecuted criterion unchecked.

## Deterministic selection and escalation

- [ ] Exact route coverage and declared availability are the only eligibility predicates; unavailable or uncovered carriers are excluded with stable reason codes.
- [ ] Fixed priority plus stable UUID tie-breaking produces the same order for every input permutation and selects at most three carriers.
- [ ] Canonical fixtures prove zero, one, two, and three eligible-carrier outcomes using only synthetic labels and rates.
- [ ] Zero eligible carriers persists exactly one pre-contact escalation and correlated audit event before any session exists; retry creates no duplicate.
- [ ] A successful start snapshots the selected carriers and rationale, advances the operation from `READY` to `NEGOTIATING`, and commits sessions, status, idempotency, and audit state atomically.

## Quotes, mandate safety, and comparison

- [ ] Quote recording verifies operation, negotiation, call, and carrier relationships and rejects mismatches without a write.
- [ ] A stale operation or mandate version raises the typed stale exception and leaves quotes, versions, idempotency, status, and audit state unchanged.
- [ ] Current-mandate terms outside price, currency, pickup window, conditions, or authority persist as `REJECTED` with deterministic safe reasons and cannot become commitments.
- [ ] Eligible quotes retain exact `Decimal` amount/currency, pickup window, conditions, mandate version, validity, and source session across reloads; money never uses float.
- [ ] Comparison excludes rejected and expired quotes and orders eligible quotes by amount, pickup start, fixed priority, creation time, and UUID exactly as specified.
- [ ] Reusing a quote idempotency key with the same canonical request returns the original quote with no new version/event; changed input raises `IdempotencyConflict`.

## Commitments, concurrency, and retry safety

- [ ] Rejected, expired, wrong-session, missing, stale-mandate, and non-best quotes cannot become commitments.
- [ ] The current deterministic best quote creates one `CANDIDATE`/`ACTIVE` commitment with the opaque evidence UUID and correlated status/audit state.
- [ ] A later valid winner transition atomically marks the prior commitment `SUPERSEDED`, records timestamps/replacement links, and preserves complete ordered history.
- [ ] Database constraints and repository locking permit at most one active commitment per operation under concurrent attempts.
- [ ] Identical commitment retries return the stored result without another winner transition; changed-input key reuse fails safely.
- [ ] Injected mapper, flush, commit, and concurrent conflict failures roll back all pending version, commitment, disposition, status, idempotency, and audit writes.

## Migration and persistence

- [ ] Alembic upgrades an isolated PostgreSQL database to the Phase 08 head, downgrades one revision, and upgrades again without manual changes or loss of the Fase 06 baseline.
- [ ] Private `volta_` tables, named keys/checks/unique constraints, partial active-winner uniqueness, and demonstrated indexes match the accepted relationships and queries.
- [ ] Repositories round-trip only frozen provider-neutral negotiation values; SQLAlchemy rows, sessions, SQL strings, driver exceptions, and lazy state never cross public boundaries.
- [ ] Constraints reject invalid versions/enums, non-finite amounts, broken operation/negotiation/call/carrier/quote relationships, duplicate session selection, and conflicting idempotency records.
- [ ] A process restart can replay an identical mutation and recover the original result identity from durable idempotency state.
- [ ] Operation row locking and expected-version checks are exercised against real PostgreSQL, not inferred from an in-memory double.

## Application contract and architecture

- [ ] Public symbols, construction, typed inputs/outputs, and safe exceptions match the application contract table in `requirements.md`.
- [ ] Existing Fase 05 mandate and Fase 06 persistence/public tests remain passing after additive extensions.
- [ ] Negotiation domain/application modules import no FastAPI, Pydantic API schema, SQLAlchemy, asyncpg, OpenAI, Twilio, Yuno, or generated transport model.
- [ ] Carrier selection, mandate evaluation, quote comparison, and commitment disposition contain no model or browser discretion.
- [ ] The evidence boundary stores only the opaque UUID; recording metadata, playback, access, retention, and recovery behavior remain absent.

## Security and scope

- [ ] Audit metadata is event-specific, bounded, and excludes prompts, contact details, quote conditions text, evidence references, request bodies, provider payloads, credentials, and private audio.
- [ ] Exceptions, representations, logs, traces, SQL configuration, and test failure output expose no secret, database URL, raw prompt, real participant data, or driver detail.
- [ ] Fixtures contain only synthetic carriers, routes, rates, UUIDs, timestamps, correlations, and evidence identifiers.
- [ ] API, frontend, OpenAPI, generated clients, manifests, lockfiles, shared specs, provider code, deployment, and unrelated files remain outside the implementation diff.
- [ ] No remote/production migration, Supabase mutation/advisor run, provider call, browser trial, phone call, payment, or financial operation is reported as executed.

## Required commands and final review

- [ ] `uv run ruff check .` passes from the repository root.
- [ ] `uv run pytest backend/tests/volta/negotiations` passes.
- [ ] `uv run pytest backend/tests/volta/persistence` passes against isolated loopback PostgreSQL.
- [ ] `uv run pytest` passes for the complete Python suite.
- [ ] `make python-check` passes.
- [ ] `git diff --check` passes.
- [ ] The complete diff, migration SQL, constraints/indexes, public exports, idempotency/concurrency behavior, audit allowlists, secret scan, and downstream handoff are reviewed.

## Explicitly not applicable

- [ ] Browser and rendered UI validation are recorded as not applicable because this phase changes no frontend surface.
- [ ] OpenAPI/Orval generation is recorded as not applicable because this phase changes no HTTP contract.
- [ ] OpenAI, Twilio, Yuno, webhook, Supabase-project, credentialed sandbox, phone, payment, financial, and external provider checks are recorded as not applicable and are not executed.
