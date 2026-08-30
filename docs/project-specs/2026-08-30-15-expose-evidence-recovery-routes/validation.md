# Fase 15 — Validation

## Planning and eligibility

- [ ] Fases 12, 14, and 24 remain merged with their gate evidence recorded.
- [ ] No conflicting phase or competing remote `phase/15-expose-evidence-recovery-routes` claim exists.
- [ ] The temporary application/query projection checkpoint is resolved before implementation proceeds past the integration map.

## API behavior

- [ ] `uv run ruff check api`
- [ ] `uv run pytest api/tests`
- [ ] Every Fase 15 operation delegates to typed backend behavior in the configured application and no longer returns the default `501`.
- [ ] Missing/invalid bearer credentials fail before application delegation; unauthorized actions map to safe `403`.
- [ ] Every mutation requires a valid `Idempotency-Key`; identical replay preserves status/body and sets `Idempotency-Replayed: true`; conflicting reuse returns `409 IDEMPOTENCY_KEY_REUSED` without a write.
- [ ] Missing operation, call, commitment, evidence, escalation, or notification maps to safe `404 RESOURCE_NOT_FOUND`.
- [ ] Stale operation versions return `409 STALE_OPERATION_VERSION` with only the safe current version; mandate and state conflicts use the accepted safe codes.
- [ ] Unexpected and persistence failures return `500 INTERNAL_ERROR` with request ID only; logs and responses omit internal exception text.
- [ ] Rate limiting and `X-Request-ID` behavior remain unchanged.

## Evidence, recap, and brief

- [ ] Evidence retains the private-playable reference, `audio_start_ms`, item ID, event ID, call ownership, version check, and existing reservation/commitment sequence.
- [ ] Missing or unreadable evidence fails safely and creates no commitment or fabricated success.
- [ ] Recaps are durably represented as `SIMULATED` only and never imply external delivery or `VERIFIED` state.
- [ ] Brief responses and audit history contain only bounded structured values from durable backend state, not request-only API memory.
- [ ] Identical evidence, recap, and brief retries return their stored identifiers/timestamps without duplicate audit events.

## Recovery and audit

- [ ] `MANDATE_SAFE` simulation leaves exactly one active commitment, preserves superseded history, and creates exactly one coordinator notification.
- [ ] `OUT_OF_MANDATE` simulation changes no commitment, creates one open escalation, and blocks further recovery until an immutable replacement mandate resolves it.
- [ ] Mandate replacement creates and activates version `current + 1`, resolves only the named same-operation escalation, and rolls back fully on missing/foreign/resolved/stale input.
- [ ] Explicit escalation persists bounded context and changes no commitment.
- [ ] Notification acknowledgement preserves the first actor and aware UTC timestamp; identical retries are read-only and a different actor conflicts.
- [ ] Operation and audit responses return durable recap, brief, recovery, escalation, notification, evidence, commitment, quote, and event histories in deterministic order with bounded cursor/limit behavior.
- [ ] Audit metadata and projections contain no raw recording path/bytes, transcript, contact detail, provider payload, authorization value, or secret.

## PostgreSQL and transaction safety

- [ ] Focused integration tests run with `TEST_DATABASE_URL` against isolated PostgreSQL state.
- [ ] Concurrent/replayed mutations do not create duplicate recaps, briefs, recoveries, escalations, notifications, mandate versions, or active commitments.
- [ ] Stale-version, ownership mismatch, idempotency conflict, and injected persistence failures preserve the prior operation, commitment, escalation, notification, and audit state.
- [ ] The API opens no direct SQLAlchemy session and performs no repository query outside the backend-facing application/service boundary.

## Contract and generated artifacts

- [ ] Existing routes, operation IDs, request/response DTOs, statuses, headers, and error schemas remain unchanged.
- [ ] `make generate`
- [ ] A second `make generate` is clean and `api/openapi.json` plus `frontend/src/lib/api/generated/**` have no diff from `origin/main`.
- [ ] No handwritten frontend DTO or generated-file edit is introduced.

## Final repository gate

- [ ] `make python-check`
- [ ] `git diff --check`
- [ ] Review the complete diff and staged set; only Fase 15 planning/API/test paths are present.
- [ ] Secret and sensitive-data review finds no credential, authorization header, recording content/path, transcript, contact data, provider payload, or unrelated change.
- [ ] Record exact command outputs, pass/skip counts, PostgreSQL evidence, unavailable dependencies, approved deviations, and fallback activation.

## Not applicable

- Frontend lint/build and browser smoke tests: no rendered frontend change.
- Yuno, OpenAI, Twilio, webhook, or credentialed sandbox tests: no provider integration or payment/telephony mutation.
- Supabase advisors and remote migration: the phase uses the existing local PostgreSQL boundary and changes no schema.
- Deployment or production validation: explicitly outside scope.
