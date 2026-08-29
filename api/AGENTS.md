# API/BFF engineering instructions

This file specializes the root `AGENTS.md` for `api/`. Keep this package a thin FastAPI transport boundary over typed backend application services.

## Ownership and boundaries

- Own HTTP routes, authentication and authorization boundaries, explicit CORS policy, request validation, public response serialization, error mapping, dependency wiring, webhook ingress, and the OpenAPI contract.
- Keep routers thin: accept and validate transport data, call an injected backend service, map its result or error, and return the declared HTTP contract.
- Keep pricing, payment strategy, domain transitions, persistence queries, provider orchestration, and other business rules in `backend/`.
- The API may import typed backend services directly. The backend must never depend on FastAPI.
- Keep provider-specific code out of this package except transport-level webhook verification and delegation.

## HTTP contracts

- Keep `/health` unversioned and place public feature routes under `/v1`.
- Define one HTTP operation per function. Put shared prefixes, tags, and dependencies on `APIRouter` when they apply to the whole router.
- Define every public request, success response, and error response with explicit Pydantic types. Prefer typed return values; use `response_model` when the public schema differs from the internal return type.
- Prefer `Annotated` for request parameters and reusable dependencies. Do not use ellipsis defaults or Pydantic `RootModel` wrappers when ordinary typed annotations express the contract.
- Assign every operation a unique, explicit, stable `operation_id`. Treat renames as contract changes because generated clients depend on them.
- Enforce authentication and authorization through dependencies. Configure credentialed CORS with explicit origins, never `*`.
- Centralize dependency construction and domain-to-HTTP error translation. Do not instantiate provider adapters in routers or expose internal exceptions and provider payloads.
- Treat FastAPI and Pydantic definitions as the source of truth. Never edit `api/openapi.json` manually.

## Yuno webhook ingress

Process `POST /v1/webhooks/yuno` in this order:

1. Read the exact raw request body bytes before any JSON parsing.
2. Read the `x-hmac-signature` header.
3. Verify the Base64 HMAC-SHA256 signature with the configured webhook secret and `hmac.compare_digest`.
4. Reject missing, malformed, or invalid signatures before parsing or delegation.
5. Parse and validate JSON only after successful verification.
6. Delegate the validated event to a backend service for deduplication, persistence, and domain state changes.
7. Return HTTP 200 promptly after successful receipt; do not assume webhook delivery order.

Never log the raw body, signature, webhook secret, or complete webhook payload. Keep webhook transport tests independent from live Yuno services.

## Logging and security

- Use structured logs with the request or correlation ID, HTTP method, route, status code, duration, and safe application identifiers.
- Redact secrets, authorization headers, API keys, card data, CVV, raw payment credentials, signatures, and sensitive payload fields.
- Keep validation and error responses deliberate and stable. Do not leak stack traces, dependency details, or provider responses.

## Tests and OpenAPI artifact

- Test validation failures, declared success and error schemas, authentication and authorization, explicit CORS, dependency overrides and wiring, error translation, and stable operation IDs.
- Test webhook raw-byte preservation, missing or malformed signatures, altered payloads, rejection before JSON parsing or delegation, and delegation after valid verification.
- Use `TestClient`, dependency overrides, fakes, or mocks for transport tests. Put backend business-rule coverage in `backend/tests`.
- After changing a contract, run focused API checks, regenerate `api/openapi.json`, and review its diff before regenerating the frontend client.

## Commands

Run these commands from the repository root:

```bash
make dev-api
uv run ruff check api
uv run pytest api/tests
make generate-openapi
```

`make generate-openapi` writes the canonical generated artifact at `api/openapi.json`.

## Capability routing

MCPs remain development tools; transport tests must stay deterministic and independent from live Yuno services. Follow the [development tooling guide](../docs/development-tooling.md) for setup and official MCP sources.

- **Yuno MCP:** read current webhook documentation and inspect schemas before changing authentication, headers, payload handling, or event contracts. Do not use payment mutation tools for API transport work.

## Required skill routing

Use each skill when its trigger matches the task:

- Use `implement-api-phase` for an isolated API/BFF roadmap workstream.
- Use `fastapi` for routes, Pydantic models, dependencies, response contracts, and current framework conventions.
- Use `context7-mcp` for current third-party library documentation when the root source-routing rule applies; Yuno still uses official Yuno sources first.

## Official references

- [FastAPI response models and OpenAPI schemas](https://fastapi.tiangolo.com/tutorial/response-model/)
- [FastAPI advanced path operation configuration](https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/)
- [Yuno webhook configuration](https://docs.y.uno/docs/webhooks/configure-webhooks)
- [Yuno HMAC webhook signature verification](https://docs.y.uno/docs/webhooks/verify-webhook-signatures-hmac)
