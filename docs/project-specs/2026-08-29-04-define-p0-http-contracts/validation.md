# Fase 04 validation

All criteria remain unchecked until implementation evidence is recorded.

## API and Pydantic contracts

- [ ] `uv run ruff check .` passes.
- [ ] `uv run pytest` passes.
- [ ] Focused API tests cover every request/response family and reject unknown request fields.
- [ ] Every Volta operation is under `/v1`, has one explicit unique stable `operation_id`, and declares typed success and route-specific error responses.
- [ ] `/health` remains public; every `/v1` route requires the configured bearer dependency.
- [ ] Missing or invalid authorization is rejected before contract delegation with a safe `401` body.
- [ ] Every state-changing `POST` requires a valid `Idempotency-Key`.
- [ ] An injected deterministic fake proves same-key/same-request replay and same-key/different-request `409` mapping without claiming durable production idempotency.
- [ ] Stale draft and operation versions map to safe `409` responses with the current version and no internal state leak.
- [ ] Validation, not-found, forbidden, mandate/state conflict, rate-limit, unexpected, and not-implemented failures use `ApiErrorResponse` and preserve `X-Request-ID`.
- [ ] Default contract handlers return `501 CONTRACT_NOT_IMPLEMENTED` and never fabricate domain success.
- [ ] CORS remains credentialed and limited to explicit origins and required headers.

## OpenAPI and generated client

- [ ] `make generate-openapi` succeeds and updates only the canonical `api/openapi.json` from FastAPI.
- [ ] OpenAPI includes bearer security, required idempotency/version inputs, all accepted success models, safe errors, examples without secrets, and no raw provider schema.
- [ ] `make generate` succeeds and updates `frontend/src/lib/api/generated/**` only through Orval.
- [ ] Generated functions expose typed bodies, path/query/header parameters, and success values for all 14 stable operation IDs.
- [ ] `pnpm --dir frontend lint` passes.
- [ ] `pnpm --dir frontend typecheck` passes.
- [ ] `pnpm --dir frontend build` passes.
- [ ] Running `make generate` a second time leaves `api/openapi.json` and `frontend/src/lib/api/generated/**` unchanged.
- [ ] No generated file was hand-edited and no Python DTO was copied into handwritten TypeScript.

## Security and scope

- [ ] `.env.example` contains names or safe empty defaults only; no bearer token or provider credential appears in Git.
- [ ] Error and log tests contain no authorization header, submitted secret, raw prompt, participant contact detail, stack trace, provider payload, or recording content.
- [ ] Identifiers, timestamps, money, versions, lifecycle, and disposition fields follow the conventions in `requirements.md`.
- [ ] The recap contract can return only simulated delivery for P0 and does not present it as `VERIFIED`.
- [ ] P0 contracts expose no phone number, Twilio identifier, Yuno/payment field, PAN, CVV, or live-provider mutation.
- [ ] `backend/**`, non-generated frontend UI source, database migrations, provider adapters, deployment files, and unrelated shared specifications are absent from the diff.
- [ ] No new dependency or manifest/lockfile change entered without a recorded plan update.

## Final repository evidence

- [ ] `make check` passes.
- [ ] `git diff --check` passes.
- [ ] The complete diff, including OpenAPI and Orval output, was reviewed for unrelated changes and generated-name regressions.
- [ ] A secret and personal-data review finds no credentials, real participant data, or private audio reference.
- [ ] Browser smoke testing is correctly reported as not applicable because this phase changes no rendered UI.
- [ ] OpenAI, Twilio, Yuno, database, webhook, and sandbox provider trials are correctly reported as not applicable because this phase performs no provider or persistence integration.
