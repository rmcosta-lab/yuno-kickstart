# Fase 15 — Validation

## Planning and eligibility

- [x] Fases 12, 14, 24, and 25 remain merged with their gate evidence recorded.
- [x] No conflicting phase or competing remote `phase/15-expose-evidence-recovery-routes` claim exists.
- [x] The temporary application/query projection checkpoint was resolved by merged Fase 25 pull request #21 before implementation resumed.

## API behavior

- [x] `uv run ruff check api`
- [x] `uv run pytest api/tests`
- [x] Every Fase 15 operation delegates to typed backend behavior in the configured application and no longer returns the default `501`.
- [x] Missing/invalid bearer credentials fail before application delegation; unauthorized actions map to safe `403`.
- [x] Every mutation requires a valid `Idempotency-Key`; identical replay preserves status/body and sets `Idempotency-Replayed: true`; conflicting reuse returns `409 IDEMPOTENCY_KEY_REUSED` without a write.
- [x] Missing operation, call, commitment, evidence, escalation, or notification maps to safe `404 RESOURCE_NOT_FOUND`.
- [x] Stale operation versions return `409 STALE_OPERATION_VERSION` with only the safe current version; mandate and state conflicts use the accepted safe codes.
- [x] Unexpected and persistence failures return `500 INTERNAL_ERROR` with request ID only; logs and responses omit internal exception text.
- [x] Rate limiting and `X-Request-ID` behavior remain unchanged.

## Evidence, recap, and brief

- [x] Evidence retains the private-playable reference, `audio_start_ms`, item ID, event ID, call ownership, version check, and existing reservation/commitment sequence.
- [x] Missing or unreadable evidence fails safely and creates no commitment or fabricated success.
- [x] Recaps are durably represented as `SIMULATED` only and never imply external delivery or `VERIFIED` state.
- [x] Brief responses and audit history contain only bounded structured values from durable backend state, not request-only API memory.
- [x] Identical evidence, recap, and brief retries return their stored identifiers/timestamps without duplicate audit events.

## Recovery and audit

- [x] `MANDATE_SAFE` simulation leaves exactly one active commitment, preserves superseded history, and creates exactly one coordinator notification.
- [x] `OUT_OF_MANDATE` simulation changes no commitment, creates one open escalation, and blocks further recovery until an immutable replacement mandate resolves it.
- [x] Mandate replacement creates and activates version `current + 1`, resolves only the named same-operation escalation, and rolls back fully on missing/foreign/resolved/stale input.
- [x] Explicit escalation persists bounded context and changes no commitment.
- [x] Notification acknowledgement preserves the first actor and aware UTC timestamp; identical retries are read-only and a different actor conflicts.
- [x] Operation and audit responses return durable recap, brief, recovery, escalation, notification, evidence, commitment, quote, and event histories in deterministic order with bounded cursor/limit behavior.
- [x] Audit metadata and projections contain no raw recording path/bytes, transcript, contact detail, provider payload, authorization value, or secret.

## PostgreSQL and transaction safety

- [x] Focused integration tests run with `TEST_DATABASE_URL` against isolated PostgreSQL state.
- [x] Concurrent/replayed mutations do not create duplicate recaps, briefs, recoveries, escalations, notifications, mandate versions, or active commitments.
- [x] Stale-version, ownership mismatch, idempotency conflict, and injected persistence failures preserve the prior operation, commitment, escalation, notification, and audit state.
- [x] The API opens no direct SQLAlchemy session and performs no repository query outside the backend-facing application/service boundary.

## Contract and generated artifacts

- [x] Existing routes, operation IDs, request/response DTOs, statuses, headers, and error schemas remain unchanged.
- [x] `make generate`
- [x] A second `make generate` is clean and `api/openapi.json` plus `frontend/src/lib/api/generated/**` have no diff from `origin/main`.
- [x] No handwritten frontend DTO or generated-file edit is introduced.

## Final repository gate

- [x] `make python-check`
- [x] `git diff --check`
- [x] Review the complete diff and staged set; only Fase 15 planning/API/test paths are present.
- [x] Secret and sensitive-data review finds no credential, authorization header, recording content/path, transcript, contact data, provider payload, or unrelated change.
- [x] Record exact command outputs, pass/skip counts, PostgreSQL evidence, unavailable dependencies, approved deviations, and fallback activation.

## Not applicable

- Frontend lint/build and browser smoke tests: no rendered frontend change.
- Yuno, OpenAI, Twilio, webhook, or credentialed sandbox tests: no provider integration or payment/telephony mutation.
- Supabase advisors and remote migration: the phase uses the existing local PostgreSQL boundary and changes no schema.
- Deployment or production validation: explicitly outside scope.

## Recorded checkpoint evidence — 2026-08-30

- Remote coordination: the Fase 15 worktree was clean and exactly synchronized with `origin/phase/15-expose-evidence-recovery-routes`; dependencies 12, 14, and 24 were merged with validation recorded; no Fase 15 pull request, competing claim, tracking Issue, or declared conflict existed.
- Baseline `uv run pytest api/tests -q`: passed all collected API tests except one expected skip, with one pre-existing Starlette `httpx` deprecation warning.
- Two independent read-only subagents inspected the API contract and backend application/persistence boundary. Both concluded that the Fase 15 gate cannot be satisfied safely in `api/**` alone.
- Confirmed blockers: missing durable recap/brief/recovery response facts; missing complete operation/audit projection and list queries; missing atomic fingerprinted idempotency/replay for six mutations; incompatible automatic-escalation and recovery-evidence projections; and no backend facade for the required mappings.
- `attach_commitment_evidence` is already integrated with durable replay and remains unchanged. The other dependent operations retain the honest `501 CONTRACT_NOT_IMPLEMENTED` fallback.
- The user approved a supporting backend phase. Specs pull request #19 merged, adding Fase 25 and the dependency from Fase 15; this branch then refreshed from the updated `origin/main`. No implementation, provider call, deployment, production access, remote migration, financial operation, contract change, generated-file edit, or force-push occurred.

## Implementation evidence — 2026-08-30

- Dependency refresh: Fase 25 merged through pull request #21 with `make python-check` reporting 488 passed and 2 provider tests deselected; the Fase 15 worktree contains that merge and has no conflict or phase pull request.
- Focused adapter and route checks: `uv run ruff check api`; `uv run pytest api/tests`; all passed with one credential-independent PostgreSQL test skipped when `TEST_DATABASE_URL` was absent and the existing Starlette/httpx deprecation warning.
- PostgreSQL journey: `TEST_DATABASE_URL=<loopback-test-url> uv run pytest api/tests/test_volta_text_postgres.py -q`; passed against a uniquely named isolated database that was dropped after the test. The journey covered recap, brief, both recovery scenarios, mandate replacement, explicit escalation, notification acknowledgement, durable replay/conflict, different-actor conflict, full audit projection, pagination, malformed cursor, and safe missing evidence.
- Repository Python gate with PostgreSQL enabled: `TEST_DATABASE_URL=<loopback-test-url> make python-check`; Ruff passed and pytest reported 495 passed, 2 credential-gated provider tests deselected, and one pre-existing Starlette/httpx deprecation warning.
- Contract determinism: `make generate` ran twice; `api/openapi.json` and `frontend/src/lib/api/generated/**` remained byte-for-byte unchanged and no frontend DTO was written manually.
- Scope review: implementation changes are limited to the FastAPI application adapter, API tests, and this Fase 15 spec directory. No backend/frontend behavior, schema, migration, manifest, lockfile, provider call, deployment, production access, remote database, financial operation, or shared specification changed.
- Fallback was not activated. The configured PostgreSQL journey returned durable typed results for all eight Fase 15 operations; missing local configuration still fails safely with `500 INTERNAL_ERROR`, and unavailable evidence returns safe `404 RESOURCE_NOT_FOUND` without exposing its reference.
