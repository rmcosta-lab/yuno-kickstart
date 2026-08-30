# Phase 12 validation

## Planning and coordination

- [ ] Phase branch started from the refreshed remote default branch with only the planning files in the claim commit.
- [ ] Dependencies 10, 11, and 23 remain merged with gate evidence; no Phase 12 branch/PR predated the claim and no declared conflict became active.
- [ ] Official OpenAI Realtime WebRTC and client-secret documentation is refreshed before provider mapping changes.
- [ ] No shared-spec change, tracking Issue, deployment, production access, provider call, or external mutation entered the phase.

## Backend and OpenAI adapter

- [ ] `uv run ruff check .` passes from the repository root.
- [ ] `uv run pytest` passes from the repository root with credentialed provider tests excluded by their existing marker policy.
- [ ] Focused backend tests prove the issuer's exact HTTPS path, authorization/safety headers, narrow session mapping, future expiry/session/model validation, timeout/provider error translation, and caller-owned client lifecycle.
- [ ] Provider-neutral modules import no FastAPI, Pydantic API schema, `httpx`, or provider payload type; the OpenAI adapter imports no API/frontend module.
- [ ] Mocked and adversarial responses prove secrets, safety identifiers, instructions, tool arguments, source prompts, headers, and raw payloads never enter representations, exceptions, or captured logs.
- [ ] Any separately authorized credentialed smoke test is synthetic, explicitly marked, reported separately, and retains no secret, raw response, or session artifact; otherwise record it as not run and not required by the gate.

## API, authorization, origin, rate limit, and cache policy

- [ ] Focused API tests pass for `POST /v1/operation-drafts` with configured OpenAI extraction, explicit deterministic fallback, and safe typed provider failures.
- [ ] `POST /v1/realtime/client-secrets` returns `201` with only the declared response fields and `X-Request-ID`, `Cache-Control: no-store, private, max-age=0`, and `Pragma: no-cache`.
- [ ] Missing/invalid bearer returns `401`; missing/untrusted origin returns `403`; both fail before issuer invocation and contain no credential or provider detail.
- [ ] Authorized sequential and concurrent requests obey the bounded per-identity limiter; `429` includes `Retry-After` and does not invoke the issuer after rejection.
- [ ] The safety identifier is a stable lowercase HMAC-SHA256 digest for the synthetic subject, changes with subject/derivation key, and is absent from responses and logs.
- [ ] Provider authentication, model, malformed response, timeout, transport, rate-limit, and server failures map to `502 REALTIME_UNAVAILABLE` with the stable safe envelope and no upstream detail.
- [ ] No-store headers are present on every route-owned safe error as well as success; the standard or ephemeral key never appears in validation errors, traceback output, structured logs, or test failure representations.
- [ ] The route accepts no client model, instructions, tools, voice, VAD, safety identifier, expiry, provider payload, or idempotency key.

## OpenAPI, Orval, and frontend compatibility

- [ ] API contract tests cover the stable `create_realtime_client_secret` operation ID, response/error schemas, security requirement, headers, and absence of a request body.
- [ ] `make generate` updates `api/openapi.json` and `frontend/src/lib/api/generated/**`; a second run produces no diff.
- [ ] Generated artifacts are reviewed and contain no standard key, ephemeral value, bearer token, safety identifier, instructions, or handwritten DTO.
- [ ] `pnpm --dir frontend lint` passes.
- [ ] `pnpm --dir frontend typecheck` passes.
- [ ] `pnpm --dir frontend build` passes.
- [ ] No rendered UI changed, so a browser smoke test is not applicable to this contract-only frontend delta; Phase 13 owns the WebRTC browser journey.

## Final repository gate

- [ ] `make python-check` passes.
- [ ] `make frontend-check` passes.
- [ ] `make check` passes.
- [ ] `git diff --check` passes and the complete diff contains only Phase 12 planning/implementation, generated artifacts, and any pre-recorded safe configuration inventory change.
- [ ] Targeted secret/privacy scans and manual log/error review find no `OPENAI_API_KEY`, ephemeral credential, bearer value, safety derivation key/identifier, raw provider payload, prompt, instruction text, or real participant data.
- [ ] The terminal evidence demonstrates live configured extraction plus a securely issued short-lived credential without creating an active browser call; deterministic text mode remains reproducible as fallback.
