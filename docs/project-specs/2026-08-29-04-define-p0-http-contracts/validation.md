# Fase 04 validation

Implementation and deep-review remediation evidence was recorded on 2026-08-29 from the dedicated Phase 04 branch.

## API and Pydantic contracts

- [x] `uv run ruff check .` passes.
- [x] `uv run pytest` passes.
- [x] Focused API tests cover every request/response family and reject unknown request fields.
- [x] Every Volta operation is under `/v1`, has one explicit unique stable `operation_id`, and declares typed success and route-specific error responses.
- [x] `/health` remains public; every `/v1` route requires the configured bearer dependency.
- [x] Missing authorization maps to `AUTHENTICATION_REQUIRED`; malformed, wrong-scheme, and invalid credentials map to `AUTHENTICATION_INVALID` before delegation, and every `401` includes `WWW-Authenticate: Bearer`.
- [x] Every state-changing `POST` requires a valid `Idempotency-Key`.
- [x] An injected deterministic fake proves same-key/same-request replay and same-key/different-request `409` mapping without claiming durable production idempotency.
- [x] Stale draft and operation versions map to safe `409` responses with only the applicable `current_draft_version` or `current_operation_version` and no internal state leak.
- [x] Validation, not-found, forbidden, mandate/state conflict, rate-limit, unexpected, and not-implemented failures use `ApiErrorResponse` and preserve `X-Request-ID`.
- [x] Unexpected `500` responses preserve the safe body, `X-Request-ID`, allowed-origin CORS, and exposed response headers through the inner ASGI error boundary.
- [x] Default contract handlers return `501 CONTRACT_NOT_IMPLEMENTED` and never fabricate domain success.
- [x] CORS remains credentialed and limited to explicit origins and required headers.
- [x] Operation and audit reads reconstruct current sessions, full quote terms, evidence, active and superseded commitments, recaps, briefs, recoveries, notifications, and escalations.
- [x] JSON versions, money, millisecond offsets, counts, and ranks reject coercion, booleans, negatives, and values above `9_007_199_254_740_991` where the field's narrower bound does not apply.
- [x] The API selects the extraction-policy version server-side and returns it for display/audit; coordinator notifications retain structured before/after recovery decisions and reasons.

## OpenAPI and generated client

- [x] `make generate-openapi` succeeds and updates only the canonical `api/openapi.json` from FastAPI.
- [x] `uv run python api/scripts/export_openapi.py` succeeds and updates only the canonical `api/openapi.json` from FastAPI.
- [x] OpenAPI includes bearer security, required idempotency/version inputs, all accepted success models, safe errors, examples without secrets, and no raw provider schema.
- [x] `make generate` succeeds and updates `frontend/src/lib/api/generated/**` only through Orval.
- [x] Generated functions expose typed bodies, path/query/header parameters, success envelopes, and safe API errors for all 14 stable operation IDs.
- [x] The two authenticated `GET` operations generate queries; all 12 state-changing `POST` operations generate mutations and no POST query key/options.
- [x] Non-2xx fetches throw `ApiHttpError<ApiErrorResponse>` while preserving status, `Headers`, `X-Request-ID`, and `Idempotency-Replayed`; direct behavior checks cover `401`, `409`, `422`, `500`, and `501`.
- [x] `pnpm --dir frontend lint` passes.
- [x] `pnpm --dir frontend typecheck` passes.
- [x] `pnpm --dir frontend build` passes.
- [x] Running the exporter and Orval a second time leaves the 72 hashed source/generated targets byte-identical.
- [x] No generated file was hand-edited and no Python DTO was copied into handwritten TypeScript.

## Security and scope

- [x] `.env.example` contains names or safe empty defaults only; no bearer token or provider credential appears in Git.
- [x] Error and log assertions prove that authorization values, submitted test secrets, raw prompts, participant contact details, stack traces, provider payloads, and recording content do not enter public responses or logs.
- [x] Identifiers, timestamps, money, versions, lifecycle, and disposition fields follow the conventions in `requirements.md`.
- [x] The recap contract can return only simulated delivery for P0 and does not present it as `VERIFIED`.
- [x] P0 contracts expose no phone number, Twilio identifier, Yuno/payment field, PAN, CVV, or live-provider mutation.
- [x] `backend/**`, database migrations, provider adapters, deployment files, and unrelated shared specifications are absent from the diff; the only handwritten frontend changes are the assigned generic fetch boundary, Orval configuration, and minimal health-envelope consumer adaptation.
- [x] No new dependency or manifest/lockfile change entered without a recorded plan update.

## Final repository evidence

- [x] `make check` passes.
- [x] `git diff --check` passes.
- [x] The complete diff, including OpenAPI and Orval output, was reviewed for unrelated changes and generated-name regressions.
- [x] A secret and personal-data review finds no credentials, real participant data, or private audio reference.
- [x] Browser smoke testing at `http://localhost:3000/health` proves a non-blank page, no framework overlay or console errors, a working `Check API` interaction, rendered `Ready` state, and a correlated API `GET /health 200`.
- [x] OpenAI, Twilio, Yuno, database, webhook, and sandbox provider trials are correctly reported as not applicable because this phase performs no provider or persistence integration.

## Recorded command and inspection evidence

- `uv run ruff check .` passed.
- `uv run pytest` passed: 128 tests, with one upstream `StarletteDeprecationWarning` from FastAPI's `TestClient` compatibility shim.
- `make generate` passed twice with Orval 8.26.0.
- `pnpm --dir frontend lint`, `typecheck`, and `build` passed; Next.js 16.3.3 generated 13 static pages.
- `make check` passed the complete Python and frontend gate.
- A SHA-256 comparison before and after the second exporter and Orval run covered 72 targets and retained aggregate hash `f55f8dc8f4ad266dd5c41f59374b4b9b5fa29369f28a4cce4b63c54fa8d213dd`.
- `api/tests/test_generated_client.py` passed seven structural regressions; a direct Node behavior check passed `201`, `401`, `409`, `422`, `500`, and `501` response/error metadata.
- Direct `TestClient` inspection confirmed allowed (`200`) and rejected (`400`) CORS preflights carry `X-Request-ID`, and allowed browser responses expose `X-Request-ID` plus `Idempotency-Replayed`.
- OpenAPI inspection confirmed 15 unique operations total: public `get_health` plus the 14 accepted authenticated `/v1` operations.
- A direct JSON comparison confirmed that `api/openapi.json` exactly matches FastAPI's in-memory schema.
- The branch was refreshed from current `origin/main` `1975649` through local merge commit `d5ae2c6`; canonical fixtures use `EN_US`, while `ES_MX` remains supported.
- Browser verification used the integrated Browser at the configured `http://localhost:3000` CORS origin; the screenshot remained temporary and no browser artifact entered Git.
- `git diff --check`, path-scope inspection, generated-name review, and targeted secret/provider-term scans passed.
- Context7 exposed no callable tools in this session. Current official FastAPI, Pydantic, and Orval documentation was used as the repository-approved fallback.

## Submission revalidation

- On 2026-08-29, `make generate` passed twice without changing the 70 OpenAPI and generated-client artifacts; their aggregate Git-object SHA-256 remained `5589c122421a894f244796ec52dd5daaabb8b97914d3bb7a9dbf7f5a31891235`.
- `make check` passed again: Ruff succeeded, pytest passed all 128 tests with the same upstream `StarletteDeprecationWarning`, ESLint and TypeScript succeeded, and Next.js 16.3.3 built all 13 static pages.
- A fresh integrated-browser smoke test at `http://localhost:3000/health` confirmed the expected title and non-blank content, no framework overlay, no console warnings or errors, a working `Check API` interaction, the final `Ready` state, and a correlated API `GET /health 200`.
- `git diff --check`, path-scope inspection, and targeted secret/provider-term scans passed again. No new deep review was run for submission.
