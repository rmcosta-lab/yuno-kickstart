# Fase 05 validation

Record exact evidence only after executing it. Keep every unexecuted criterion unchecked.

## Domain values and draft validation

- [x] Frozen/slotted value and entity tests cover UUID identity, aware UTC timestamps, ordered pickup windows, exact Decimal money, immutable condition tuples, and mutation rejection.
- [x] Source-prompt retention and extraction-policy version tests prove both values survive draft creation while the prompt is absent from `repr`, public exceptions, and loggable failure output.
- [x] Valid canonical English proposals are approval-eligible and retain the accepted policy version.
- [x] Invalid route, pickup order, amount, currency, requested language, conditions, and policy reference produce stable ordered issues without submitted values.
- [x] Draft validation creates no mandate, operation, or authority.

## Application services and repository protocols

- [x] `CreateIntakeDraftService` assigns injected IDs/timestamps, creates draft version 1, saves once, and commits once through deterministic fakes.
- [x] `ApproveOperationService` creates exactly one operation and immutable mandate version 1 from an eligible expected draft version.
- [x] Missing, stale, ineligible, and already-approved drafts raise the documented safe typed exceptions and do not commit partial state.
- [x] Repository, unit-of-work, clock, and ID-generator ports satisfy runtime/static protocol checks without a live database.
- [x] Public modules export exactly the application symbols recorded in `requirements.md` and preserve existing payment exports.

## Mandate enforcement

- [x] An approved in-authority action with the active mandate version, permitted amount/currency/window/conditions is allowed.
- [x] Wrong action authority, stale mandate version, excessive amount, wrong currency, pickup outside the window, and disallowed conditions are rejected independently.
- [x] Combined violations return every safe reason in stable order; `require_allowed` raises `MandateConflict` with the identical reason set.
- [x] Inclusive pickup boundaries and exact Decimal comparisons have focused regression tests.
- [x] Existing mandate and operation versions remain immutable; replacement requires a new object/version and is not implemented as mutation.

## Architecture, security, and scope

- [x] `backend/src/yuno_backend/volta/**` imports no FastAPI, Pydantic API schema, SQLAlchemy, database module, provider adapter, frontend code, or generated contract.
- [x] Tests use synthetic prompts, names, routes, amounts, actors, and identifiers; no credential, real participant data, provider payload, or private recording reference enters Git.
- [x] Existing payment/Yuno/database bootstrap behavior remains unchanged and its tests continue to pass.
- [x] No API, frontend, OpenAPI, generated client, migration, manifest, lockfile, deployment, shared-spec, provider, or unrelated file enters the diff.
- [x] No Yuno, OpenAI, Twilio, database, webhook, browser, sandbox, phone, payment, or financial trial is reported as executed; these are not applicable to this phase.

## Required commands and final review

- [x] `uv run ruff check .` passes from the repository root.
- [x] `uv run pytest backend/tests` passes.
- [x] `uv run pytest` passes for the complete Python suite.
- [x] `make python-check` passes.
- [x] `git diff --check` passes.
- [x] The complete diff, public import surface, test fakes, redaction behavior, and downstream handoff are reviewed.
- [x] The final branch contains only the accepted planning and backend/core implementation scope.

## External and browser evidence

- [x] Browser testing is explicitly recorded as not applicable because this phase changes no rendered surface.
- [x] Provider and credentialed checks are explicitly recorded as not applicable because this phase performs no provider integration or external mutation.

## Recorded command and inspection evidence

- `uv run ruff check .` passed from the repository root.
- `uv run pytest backend/tests` passed: 36 tests.
- `uv run pytest` passed: 156 tests, with one existing `StarletteDeprecationWarning` from FastAPI's `TestClient` compatibility shim.
- `make python-check` passed the complete Python gate with the same 156-test result and warning.
- Focused mandate tests passed: 28 tests covering domain invariants, semantic validation, services, policy enforcement, public exports, and architecture boundaries.
- `git diff --check`, path-scope inspection, forbidden-import scanning, and targeted secret/provider-term review passed.
- Direct source and test review confirmed exact `date` rather than `datetime` pickup values, prompt-redacted representations and safe failures, stable validation and mandate reason ordering, deterministic injected IDs and clock values, runtime-checkable ports, and unchanged payment/Yuno/database bootstrap files.
- Browser testing was not applicable because this phase changes no rendered surface.
- Provider, credentialed, database, webhook, sandbox, phone, payment, and financial trials were not applicable and were not executed.
