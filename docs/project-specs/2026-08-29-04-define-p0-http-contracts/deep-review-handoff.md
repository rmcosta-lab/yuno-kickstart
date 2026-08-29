# Phase 04 deep-review handoff

This document preserves the read-only deep-review decision for Phase 04 so work can continue in another Codex session or on another machine.

## Review target and publication state

- Review date: 2026-08-29.
- Branch: `phase/04-define-p0-http-contracts`.
- Reviewed local `HEAD`: `44d80bf924276f66eb93f459b46a34e5d04f73de`.
- The review included every tracked modification and every untracked implementation/generated file in the dedicated Phase 04 worktree.
- The working tree had 86 modified or untracked paths before this handoff file was added.
- Current remote Phase 04 ref: planning commit `8026f6716ea0ed7702f89f8aeb2c797ae975ffcd`.
- Current observed `origin/main`: `1975649b5c2f47a630d2331c18bf2f22ecc14f42`.
- The reviewed local head has merge base `519a3dea97e265b39081c78d35ee270b6f6bd232` with current `origin/main` and therefore needs a refresh before publication.
- No Phase 04 pull request or tracking issue existed when the review completed.
- The implementation bytes, generated files, tests, validation changes, and this handoff are not published. They must be transferred, committed, or otherwise preserved before changing machines.
- No merge verdict applies because there is no published implementation SHA.

## Review outcome

The three review lenses produced a consolidated result of five high-severity, three medium-severity, and one low-severity finding. The review made no code changes.

### High severity

- [ ] **DR-01 — Unexpected `500` responses lose request and CORS headers.**
  - Primary files: `api/app/main.py`, `api/app/middleware/request_context.py`, and `api/app/errors.py`.
  - Evidence: an injected unexpected exception returned the safe `INTERNAL_ERROR` body with `request_id: "err-1"`, but the HTTP response omitted `X-Request-ID`, `Access-Control-Allow-Origin`, and `Access-Control-Expose-Headers`.
  - Cause: FastAPI's catch-all `Exception` handler executes through the outer server-error layer after the user middleware stack has unwound.
  - Correction: translate unexpected exceptions inside an ASGI error boundary that is wrapped by CORS and request-context middleware. Add a test that checks both the safe body and actual response headers for an allowed browser origin.

- [ ] **DR-02 — All 12 state-changing `POST` operations are generated as TanStack queries.**
  - Primary files: `frontend/orval.config.ts` and `frontend/src/lib/api/generated/api.ts`.
  - Evidence: the generated file contains query keys and `useQuery` hooks for all POST operations and no `useMutation`. Mutation query keys omit `Idempotency-Key`.
  - Impact: create, approve, negotiate, quote, commitment, recovery, acknowledgement, and other mutations can execute under query mount, reconnect, refetch, retry, and cache rules rather than only after an explicit user action. Different logical attempts with the same body can alias the same cache entry.
  - Correction: configure Orval so the two GET operations generate queries and all 12 POST operations generate mutations. Add a generated-client structural or behavioral test that rejects POST query hooks.

- [ ] **DR-03 — Generated fetchers cast every HTTP error to the success DTO.**
  - Primary files: `frontend/orval.config.ts` and `frontend/src/lib/api/generated/api.ts`.
  - Evidence: generated fetchers parse the response body without checking `res.ok`; there are no status checks or throws. `includeHttpResponseReturnType` is disabled, so callers also lose status, `X-Request-ID`, and `Idempotency-Replayed`.
  - Impact: `401`, `409`, `422`, `500`, and the default `501 CONTRACT_NOT_IMPLEMENTED` resolve as successful domain data. React Query cannot enter the intended typed error state.
  - Correction: add a shared Orval fetch mutator or equivalent generated transport boundary that parses and throws typed `ApiErrorResponse` values for non-2xx responses while preserving status and response headers. Test representative authentication, stale-state, validation, and not-implemented responses.

- [ ] **DR-04 — The two read projections cannot reconstruct the P0 control tower after refresh or reconnect.**
  - Primary file: `api/app/schemas/contracts.py`.
  - Evidence: `OperationResponse` exposes only negotiation counts and the active commitment. `AuditTimelineResponse` exposes generic events and price-only comparison rows. Sessions, full quote terms, recaps, briefs, recovery artifacts, and superseded commitment evidence exist only in transient mutation responses.
  - Impact: Phase 09 depends only on Phases 01 and 04 but must render sessions, quote changes, terminal/reconnect states, and comparison. Phase 16 later needs historical evidence and recovery views, while Phase 15 is expected to implement the accepted contract rather than redesign it.
  - Correction: enrich `GET /v1/operations/{operation_id}` with typed current session and quote state, and enrich `GET /v1/operations/{operation_id}/audit` with typed comparison, commitment history/evidence, recaps, briefs, and recovery artifacts. This can be done without increasing the accepted route count.

- [ ] **DR-05 — Stale draft approval cannot return the safe current draft version.**
  - Primary files: `api/app/schemas/errors.py`, `api/app/contract_service.py`, `api/app/errors.py`, and `api/tests/test_contract_routes.py`.
  - Evidence: `ApiErrorResponse` has only `current_operation_version`; the stale-draft test expects `None`, and `validation.md` records the requirement as blocked and unchecked.
  - Impact: the accepted stale-state gate is incomplete and the coordinator cannot recover deterministically from a stale approval response.
  - Correction: clarify the envelope and add `current_draft_version` or a generic current-resource version field. Propagate it through the safe exception, handler, OpenAPI, generated client, and retry-flow tests.

### Medium severity

- [ ] **DR-06 — Integer contracts are coercive and exceed JavaScript's safe range.**
  - Primary file: `api/app/schemas/common.py`.
  - Evidence: request validation accepts `"1"` and `true` as version `1`, `false` as amount `0`, and `9007199254740993`, which TypeScript represents as the rounded value `9007199254740992`.
  - Correction: use strict integer validation and documented upper bounds no greater than `9_007_199_254_740_991` for versions, money, and millisecond offsets. Add coercion and boundary tests.

- [ ] **DR-07 — The browser controls the server extraction-policy version.**
  - Primary file: `api/app/schemas/contracts.py`.
  - Evidence: `CreateOperationDraftRequest` requires `extraction_policy_version`, although the accepted mission and challenge decision say that the API applies the active versioned server policy.
  - Correction: remove policy-version selection from the request and keep the actually applied version in `OperationDraftResponse`. If client selection is intentional, record a separate explicit architecture and authorization decision first.

- [ ] **DR-08 — Coordinator notifications omit required audit facts.**
  - Primary file: `api/app/schemas/contracts.py`.
  - Evidence: `CoordinatorNotificationResponse` has a free-form message, acknowledgement state, and correlation ID, but no operation version, structured before/after decision, or decision reason.
  - Correction: add structured operation-version and recovery-decision facts so acknowledgement and reload preserve an auditable autonomous change.

### Low severity

- [ ] **DR-09 — Malformed authorization is classified as missing authentication.**
  - Primary file: `api/app/security/demo_bearer.py`.
  - Evidence: both an absent header and `Authorization: Basic ...` return `AUTHENTICATION_REQUIRED`; the custom `401` also omits `WWW-Authenticate: Bearer`.
  - Correction: distinguish absent from malformed or wrong-scheme credentials, return `AUTHENTICATION_INVALID` for the latter, include the standard bearer challenge header, and add coverage.

## Recommended correction order

1. Preserve the current dirty worktree before moving machines. Do not assume the remote Phase 04 branch contains the implementation.
2. Refresh from current `origin/main` only after the implementation has a recoverable snapshot; do not discard or overwrite the dirty worktree.
3. Resolve the contract decisions first: DR-04, DR-05, DR-07, and DR-08.
4. Fix strict numeric transport validation in DR-06 and regenerate the Python/OpenAPI fixtures as needed.
5. Fix the server middleware/error boundary in DR-01 and the bearer taxonomy in DR-09.
6. Fix the generated browser transport and React Query semantics in DR-02 and DR-03.
7. Update API tests and generated-client tests before regeneration.
8. Run OpenAPI and Orval generation twice and require byte-identical output on the second run.
9. Complete every validation checkbox, review the full generated diff, and only then use `deep-review` again against a published commit SHA.

## Required regression coverage

- Unexpected `500` responses preserve safe bodies, `X-Request-ID`, allowed-origin CORS, and exposed headers.
- All POST hooks are mutations and do not execute before an explicit mutation call.
- Generated requests reject typed API errors for at least `401`, `409`, `422`, `500`, and `501`.
- The browser can observe `X-Request-ID` and `Idempotency-Replayed` where declared.
- Same body with different idempotency keys does not alias a query cache entry.
- Operation and audit reads reconstruct session, quote, evidence, recap, brief, recovery, notification, escalation, and superseded-commitment state required by the downstream screens.
- Stale draft and stale operation responses both expose the applicable safe current version.
- Numeric strings, booleans, negative values, and values above the JavaScript-safe bound are rejected for integer contract fields.
- The active extraction-policy version is selected server-side and returned for display/audit.
- Notification acknowledgement preserves structured before/after recovery evidence.
- Missing and malformed bearer credentials map to their distinct accepted error codes.

## Checks completed by the review

- `uv run ruff check .` passed.
- `uv run pytest` passed: 74 tests, with one upstream Starlette `TestClient` deprecation warning.
- `corepack pnpm@11.9.0 --dir frontend lint` passed.
- `corepack pnpm@11.9.0 --dir frontend typecheck` passed.
- `corepack pnpm@11.9.0 --dir frontend build` passed with 13 static pages.
- `git diff --check` passed.
- The in-memory FastAPI OpenAPI document exactly matched `api/openapi.json`.
- Focused reproductions confirmed the unexpected-error header loss, malformed-auth taxonomy, Pydantic integer coercion, JavaScript precision loss, POST query generation, and non-2xx success casting.

The review did not rerun generation because it was read-only and generation writes files. `make` was unavailable on the Windows host. The existing phase validation records successful direct exporter and Orval commands plus deterministic second-run hashes, but DR-02 through DR-08 require regeneration after correction.

`corepack pnpm@11.9.0 --dir frontend format:check` reported 54 repository-wide files, largely because of the existing Windows CRLF/baseline formatting state. This was not classified as a Phase 04 implementation finding, but the next session should avoid introducing additional formatting drift.

## Continuation commands

Run from the repository root after safely restoring the complete dirty worktree:

```powershell
git status --short
git rev-parse HEAD
git fetch origin
git rev-parse origin/main
git ls-remote origin refs/heads/phase/04-define-p0-http-contracts
uv run ruff check .
uv run pytest
uv run python api/scripts/export_openapi.py
corepack pnpm@11.9.0 --dir frontend api:generate
corepack pnpm@11.9.0 --dir frontend lint
corepack pnpm@11.9.0 --dir frontend typecheck
corepack pnpm@11.9.0 --dir frontend build
git diff --check
git status --short
```

Do not run generation until the source contracts and Orval transport decisions are updated. Review every generated change rather than editing generated files manually.

## Suggested continuation prompt

> Continue Phase 04 from `docs/project-specs/2026-08-29-04-define-p0-http-contracts/deep-review-handoff.md`. Preserve the restored dirty worktree, refresh coordination state, implement DR-01 through DR-09 in the recorded order, regenerate OpenAPI and Orval output, complete the validation document, and run the full Phase 04 check matrix. Do not publish or merge until a new read-only deep review is run against the exact published implementation SHA.
