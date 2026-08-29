# Fase 04 validation

Implementation evidence was recorded on 2026-08-29 from the dedicated Phase 04 worktree.

## API and Pydantic contracts

- [x] `uv run ruff check .` passes.
- [x] `uv run pytest` passes.
- [x] Focused API tests cover every request/response family and reject unknown request fields.
- [x] Every Volta operation is under `/v1`, has one explicit unique stable `operation_id`, and declares typed success and route-specific error responses.
- [x] `/health` remains public; every `/v1` route requires the configured bearer dependency.
- [x] Missing or invalid authorization is rejected before contract delegation with a safe `401` body.
- [x] Every state-changing `POST` requires a valid `Idempotency-Key`.
- [x] An injected deterministic fake proves same-key/same-request replay and same-key/different-request `409` mapping without claiming durable production idempotency.
- [ ] Stale draft and operation versions map to safe `409` responses with the current version and no internal state leak. Blocker: both stale cases map safely to `409`, and stale operation returns `current_operation_version`; the accepted `ApiErrorResponse` in `requirements.md` defines no `current_draft_version`, so exposing the current draft version requires an explicit contract clarification rather than an implementation guess.
- [x] Validation, not-found, forbidden, mandate/state conflict, rate-limit, unexpected, and not-implemented failures use `ApiErrorResponse` and preserve `X-Request-ID`.
- [x] Default contract handlers return `501 CONTRACT_NOT_IMPLEMENTED` and never fabricate domain success.
- [x] CORS remains credentialed and limited to explicit origins and required headers.

## OpenAPI and generated client

- [ ] `make generate-openapi` succeeds and updates only the canonical `api/openapi.json` from FastAPI. Blocker: `make` is not installed on this Windows host; the exact exporter command below passed.
- [x] `uv run python api/scripts/export_openapi.py` succeeds and updates only the canonical `api/openapi.json` from FastAPI.
- [x] OpenAPI includes bearer security, required idempotency/version inputs, all accepted success models, safe errors, examples without secrets, and no raw provider schema.
- [ ] `make generate` succeeds and updates `frontend/src/lib/api/generated/**` only through Orval. Blocker: `make` is not installed on this Windows host; the exact exporter and Orval commands below passed.
- [x] `corepack pnpm@11.9.0 --dir frontend api:generate` succeeds and updates `frontend/src/lib/api/generated/**` only through Orval.
- [x] Generated functions expose typed bodies, path/query/header parameters, and success values for all 14 stable operation IDs.
- [x] `corepack pnpm@11.9.0 --dir frontend lint` passes.
- [x] `corepack pnpm@11.9.0 --dir frontend typecheck` passes.
- [x] `corepack pnpm@11.9.0 --dir frontend build` passes.
- [x] Running the exporter and Orval a second time leaves `api/openapi.json`, `frontend/orval.config.ts`, and all 67 generated TypeScript files byte-identical.
- [x] No generated file was hand-edited and no Python DTO was copied into handwritten TypeScript.

## Security and scope

- [x] `.env.example` contains names or safe empty defaults only; no bearer token or provider credential appears in Git.
- [x] Error and log tests contain no authorization header, submitted secret, raw prompt, participant contact detail, stack trace, provider payload, or recording content.
- [x] Identifiers, timestamps, money, versions, lifecycle, and disposition fields follow the conventions in `requirements.md`.
- [x] The recap contract can return only simulated delivery for P0 and does not present it as `VERIFIED`.
- [x] P0 contracts expose no phone number, Twilio identifier, Yuno/payment field, PAN, CVV, or live-provider mutation.
- [x] `backend/**`, non-generated frontend UI source, database migrations, provider adapters, deployment files, and unrelated shared specifications are absent from the diff.
- [x] No new dependency or manifest/lockfile change entered without a recorded plan update.

## Final repository evidence

- [ ] `make check` passes. Blocker: `make` is not installed on this Windows host; every exact underlying Python and frontend gate passed separately.
- [x] `git diff --check` passes.
- [x] The complete diff, including OpenAPI and Orval output, was reviewed for unrelated changes and generated-name regressions.
- [x] A secret and personal-data review finds no credentials, real participant data, or private audio reference.
- [x] Browser smoke testing is correctly reported as not applicable because this phase changes no rendered UI.
- [x] OpenAI, Twilio, Yuno, database, webhook, and sandbox provider trials are correctly reported as not applicable because this phase performs no provider or persistence integration.

## Recorded command and inspection evidence

- `uv run ruff check .` passed.
- `uv run pytest` passed: 74 tests, with one upstream `StarletteDeprecationWarning` from FastAPI's `TestClient` compatibility shim.
- `uv run python api/scripts/export_openapi.py` passed.
- `corepack pnpm@11.9.0 --dir frontend api:generate` passed with Orval 8.26.0.
- `corepack pnpm@11.9.0 --dir frontend lint` passed.
- `corepack pnpm@11.9.0 --dir frontend typecheck` passed.
- `corepack pnpm@11.9.0 --dir frontend build` passed with Next.js 16.3.3 and generated 13 static pages.
- A SHA-256 comparison before and after a second exporter and Orval run covered 69 targets: `api/openapi.json`, `frontend/orval.config.ts`, and all 67 generated files; zero hashes changed.
- Direct `TestClient` inspection confirmed allowed (`200`) and rejected (`400`) CORS preflights carry `X-Request-ID`, and allowed browser responses expose `X-Request-ID` plus `Idempotency-Replayed`.
- OpenAPI inspection confirmed 15 unique operations total: public `get_health` plus the 14 accepted authenticated `/v1` operations.
- The branch was refreshed from current `origin/main` at `519a3de` after shared-spec pull request #2 made English authoritative. Canonical contract fixtures use `EN_US`; `ES_MX` remains a supported enum value and the OpenAPI/generated hashes did not change.
- `git diff --check`, path-scope inspection, generated-name review, and targeted secret/provider-term scans passed.
- Context7 was configured but unauthenticated and exposed no callable tools in this session. Current official FastAPI, Pydantic, and Orval documentation was used as the repository-approved fallback.
