# Phase 12 validation

## Planning and coordination

- [x] Phase branch started from the refreshed remote default branch with only the planning files in claim commit `a5853ff0adfaf539fcaa6c536b2597827300242d`.
- [x] Dependencies 10, 11, and 23 remain merged through PRs #15, #11, and #13; no Phase 12 branch/PR predated the claim and the phase declares no conflicts.
- [x] Official OpenAI Realtime WebRTC and client-secret documentation was refreshed before provider mapping changes.
- [x] No shared-spec change, tracking Issue, deployment, production access, provider call, or external mutation entered the phase.

## Backend and OpenAI adapter

- [x] `uv run ruff check .` passes from the repository root, both directly and through `make python-check`/`make check`.
- [x] `uv run pytest` passes from the repository root: 421 passed, 29 skipped, and 2 deselected under the existing credentialed-test marker policy.
- [x] Focused backend tests prove the issuer's exact HTTPS path, authorization/safety headers, narrow session mapping, future expiry/session/model validation, timeout/provider error translation, and caller-owned client lifecycle.
- [x] Architecture tests and import scans prove provider-neutral modules import no FastAPI, Pydantic API schema, `httpx`, or provider payload type; the OpenAI adapter imports no API/frontend module.
- [x] Mocked and adversarial responses prove secrets, safety identifiers, instructions, tool arguments, source prompts, headers, and raw payloads never enter representations, exceptions, or captured logs.
- [x] No credentialed smoke test was run: it was not required by this gate and no separate authorization was requested or inferred.

## API, authorization, origin, rate limit, and cache policy

- [x] Focused API tests pass for `POST /v1/operation-drafts` with configured OpenAI extraction, explicit deterministic fallback, and safe typed provider failures.
- [x] The configured-extraction proof now enters through `POST /v1/operation-drafts`, lets the live service factory select `OpenAIIntakeExtractor`, observes its `httpx.MockTransport` request, and proves provider/source details are redacted on failure.
- [x] `POST /v1/realtime/client-secrets` returns `201` with only the declared response fields and `X-Request-ID`, `Cache-Control: no-store, private, max-age=0`, and `Pragma: no-cache`.
- [x] Missing/invalid bearer returns `401`; missing/untrusted origin returns `403`; both fail before issuer invocation and contain no credential or provider detail.
- [x] Authorized sequential and concurrent requests obey the bounded per-identity limiter; `429` includes `Retry-After` and does not invoke the issuer after rejection.
- [x] Missing and untrusted Realtime origins consistently remain `403`, do not consume the authorized actor's mutation allowance, and cannot change a subsequent allowed request into `429`.
- [x] The safety identifier is a stable lowercase HMAC-SHA256 digest for the synthetic subject, changes with subject/derivation key, and is absent from responses and logs.
- [x] Provider authentication, model, malformed response, timeout, transport, rate-limit, and server failures map to `502 REALTIME_UNAVAILABLE` with the stable safe envelope and no upstream detail.
- [x] No-store headers are present on every route-owned safe error as well as success; tests and review found no standard or ephemeral credential in validation errors, traceback output, structured logs, or representations.
- [x] The route accepts no client model, instructions, tools, voice, VAD, safety identifier, expiry, provider payload, or idempotency key.
- [x] The two server-owned Realtime tool definitions carry every path/body field required by the typed quote and candidate-commitment routes, use closed nested schemas, and preserve the original `call_id` for Phase 13 forwarding.

## OpenAPI, Orval, and frontend compatibility

- [x] API contract tests cover the stable `create_realtime_client_secret` operation ID, response/error schemas, security requirement, headers, and absence of a request body.
- [x] Runtime and OpenAPI agree that a Realtime `401` includes `WWW-Authenticate: Bearer`; focused and repository-wide contract tests freeze that header.
- [x] `make generate` updates `api/openapi.json` and `frontend/src/lib/api/generated/**`; two consecutive post-review runs produced identical hashes (`0636cba...` for OpenAPI and `fb15712...`, `46cb02d...`, `3e4af0e...`, `91cc5c7...` for the affected Orval files).
- [x] Generated artifacts were reviewed and contain no credential value, bearer value, safety identifier, instructions, or handwritten DTO.
- [x] `pnpm --dir frontend lint` passes using the repository-declared pnpm 11.9.0 through an ephemeral `npx` invocation because `pnpm` is not installed on `PATH`.
- [x] `pnpm --dir frontend typecheck` passes under the same pinned pnpm invocation.
- [x] `pnpm --dir frontend build` passes; Next.js 16.3.3 generated all 11 application routes successfully.
- [x] No rendered UI changed, so a browser smoke test is not applicable to this contract-only frontend delta; Phase 13 owns the WebRTC browser journey.

## Final repository gate

- [x] `make python-check` passes: Ruff is clean and pytest reports 421 passed, 29 skipped, and 2 deselected.
- [x] `make frontend-check` passes with the pinned ephemeral pnpm command exported to the Make subprocess.
- [x] `make check` passes with the same environment: Python, lint, typecheck, and production build are green.
- [x] `git diff --check` passes and complete status/diff review contains only Phase 12 planning/implementation, generated artifacts, and the safe configuration inventory change.
- [x] Targeted secret/privacy scans and manual log/error review found no live or committed credential, bearer value, derivation secret/identifier, raw provider payload, source prompt, real participant data, or secret-like value outside explicit synthetic test markers.
- [x] Dependency-wiring and MockTransport evidence demonstrates configured OpenAI extraction plus secure short-lived credential issuance without creating an active browser call; deterministic text mode remains reproducible as fallback.

## Recorded command evidence

- `make generate` twice with identical SHA-256 results for OpenAPI and every affected Orval artifact.
- `make python-check`: 421 passed, 29 skipped, 2 deselected; one external Starlette/httpx deprecation warning.
- `make frontend-check`: ESLint, TypeScript, and Next.js production build passed.
- `make check`: the combined repository gate passed.
- Focused API integration/regression suite after deep-review remediation: 77 passed, including full Realtime tool arguments, invalid-origin/rate-limit ordering, OpenAPI Bearer challenge, route-to-factory OpenAI extraction, safe provider failure, and 32 concurrent first-use calls retaining and closing exactly one shared `httpx.AsyncClient`.
- Backend focused/full workstream evidence: 247 passed, 28 skipped, 2 deselected from `backend/`; provider tests use `httpx.MockTransport` only.
- `git diff --check`, provider-boundary import scans, generated-contract inspection, and targeted credential-pattern scans passed. Expected secret/config names and explicit synthetic test markers remain only where tests or `.env.example` require them.
- Context7 was configured but unauthenticated in this environment; current official OpenAI documentation and installed FastAPI/httpx behavior were used instead.
