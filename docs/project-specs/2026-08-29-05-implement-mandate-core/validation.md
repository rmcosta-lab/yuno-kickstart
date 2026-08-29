# Fase 05 validation

Record exact evidence only after executing it. Keep every unexecuted criterion unchecked.

## Domain values and draft validation

- [ ] Frozen/slotted value and entity tests cover UUID identity, aware UTC timestamps, ordered pickup windows, exact Decimal money, immutable condition tuples, and mutation rejection.
- [ ] Source-prompt retention and extraction-policy version tests prove both values survive draft creation while the prompt is absent from `repr`, public exceptions, and loggable failure output.
- [ ] Valid canonical English proposals are approval-eligible and retain the accepted policy version.
- [ ] Invalid route, pickup order, amount, currency, requested language, conditions, and policy reference produce stable ordered issues without submitted values.
- [ ] Draft validation creates no mandate, operation, or authority.

## Application services and repository protocols

- [ ] `CreateIntakeDraftService` assigns injected IDs/timestamps, creates draft version 1, saves once, and commits once through deterministic fakes.
- [ ] `ApproveOperationService` creates exactly one operation and immutable mandate version 1 from an eligible expected draft version.
- [ ] Missing, stale, ineligible, and already-approved drafts raise the documented safe typed exceptions and do not commit partial state.
- [ ] Repository, unit-of-work, clock, and ID-generator ports satisfy runtime/static protocol checks without a live database.
- [ ] Public modules export exactly the application symbols recorded in `requirements.md` and preserve existing payment exports.

## Mandate enforcement

- [ ] An approved in-authority action with the active mandate version, permitted amount/currency/window/conditions is allowed.
- [ ] Wrong action authority, stale mandate version, excessive amount, wrong currency, pickup outside the window, and disallowed conditions are rejected independently.
- [ ] Combined violations return every safe reason in stable order; `require_allowed` raises `MandateConflict` with the identical reason set.
- [ ] Inclusive pickup boundaries and exact Decimal comparisons have focused regression tests.
- [ ] Existing mandate and operation versions remain immutable; replacement requires a new object/version and is not implemented as mutation.

## Architecture, security, and scope

- [ ] `backend/src/yuno_backend/volta/**` imports no FastAPI, Pydantic API schema, SQLAlchemy, database module, provider adapter, frontend code, or generated contract.
- [ ] Tests use synthetic prompts, names, routes, amounts, actors, and identifiers; no credential, real participant data, provider payload, or private recording reference enters Git.
- [ ] Existing payment/Yuno/database bootstrap behavior remains unchanged and its tests continue to pass.
- [ ] No API, frontend, OpenAPI, generated client, migration, manifest, lockfile, deployment, shared-spec, provider, or unrelated file enters the diff.
- [ ] No Yuno, OpenAI, Twilio, database, webhook, browser, sandbox, phone, payment, or financial trial is reported as executed; these are not applicable to this phase.

## Required commands and final review

- [ ] `uv run ruff check .` passes from the repository root.
- [ ] `uv run pytest backend/tests` passes.
- [ ] `uv run pytest` passes for the complete Python suite.
- [ ] `make python-check` passes.
- [ ] `git diff --check` passes.
- [ ] The complete diff, public import surface, test fakes, redaction behavior, and downstream handoff are reviewed.
- [ ] The final branch contains only the accepted planning and backend/core implementation scope.

## External and browser evidence

- [ ] Browser testing is explicitly recorded as not applicable because this phase changes no rendered surface.
- [ ] Provider and credentialed checks are explicitly recorded as not applicable because this phase performs no provider integration or external mutation.
