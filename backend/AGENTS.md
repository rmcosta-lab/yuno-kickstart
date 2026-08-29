# Backend/Core engineering instructions

This package owns provider-neutral business rules, application services, persistence abstractions, and server-side integrations. It must remain usable without FastAPI or another transport framework.

## Boundaries and application design

- Keep FastAPI, HTTP request objects, Pydantic API schemas, and transport error handling out of this package.
- Put business rules and use-case orchestration in domain and application services. Keep public service boundaries typed and independently testable.
- Define provider-neutral protocols for payment gateways, repositories, clocks, and other external capabilities. Inject implementations instead of using global clients.
- Keep domain models independent of Yuno payloads, SQLAlchemy sessions, and provider status strings. Translate external values at adapter boundaries.
- Use `Decimal` for monetary values and preserve currency explicitly. Never use binary floating point for payment amounts.

## Persistence and PostgreSQL

- Define repository contracts in the application core and implement database access behind them. Do not expose SQLAlchemy queries or sessions through domain APIs.
- Scope transactions to one application operation. Do not keep a database transaction open while waiting for Yuno or another network provider.
- Persist payment attempts, provider identifiers, idempotency keys, webhook deduplication keys, and state transitions needed for recovery.
- Enforce uniqueness and integrity with database constraints. Add indexes for demonstrated lookup, join, and reconciliation paths.
- Apply durable schema changes through migrations. Keep manual dashboard changes out of the deployment path.
- When Supabase exposes a schema through its Data API, use explicit grants and enable Row Level Security (RLS) with reviewed policies. Keep secret or service-role credentials server-side.
- Use least-privilege database roles and bounded connection pools. Run Supabase security and performance advisors after relevant migrations when Supabase is selected.

## Yuno server-side integration

- Confirm endpoint paths, payloads, enums, authentication, idempotency, and webhook formats against current official Yuno documentation before changing provider code.
- Keep Yuno transport in `integrations/yuno`. The client owns `httpx.AsyncClient`, the environment-specific base URL, `public-api-key` and `private-secret-key` headers, explicit timeouts, connection lifecycle, and transport error translation.
- Keep the gateway responsible for translating provider-neutral application models to Yuno request data transfer objects (DTOs) and Yuno responses back to application models.
- Do not leak Yuno dictionaries, HTTP status codes, headers, or provider exceptions into domain and application services.
- Map transport failures, invalid responses, and provider errors to a small typed exception vocabulary. Include only safe identifiers and diagnostic context.
- Default development and tests to Yuno Sandbox. Keep Sandbox and Production credentials separate.

## Idempotency and retries

- Create and persist one UUID idempotency key before each logical payment mutation. Reuse that key and the same request data when retrying the same uncertain operation.
- Retry timeouts, connection failures, unparseable responses, and retryable provider failures only under the current Yuno rules. Never retry an unclear mutation with a new key.
- Use a new key only for a genuinely new logical attempt. Prevent concurrent provider mutations for the same local attempt.
- Reconcile an uncertain result through the provider retrieval operation before starting another mutation when a retry cannot establish the outcome.
- Make repository writes and webhook handling idempotent even when the provider or caller delivers duplicates.

## Webhook processing and reconciliation

- Accept only normalized events that the API layer has already authenticated and parsed. Raw request handling and HMAC verification remain transport concerns.
- Deduplicate each event with a stable provider event identifier or deterministic deduplication key before applying side effects.
- Do not assume delivery order. Apply valid state transitions transactionally and make repeated processing return the stored result.
- Persist processing timestamps and safe error details so failed events can be retried or inspected.
- Retrieve the current Yuno payment when an event is incomplete, out of order, or inconsistent with local state, then reconcile through an application service.

## Security and observability

- Never collect primary account numbers (PAN) or card verification values (CVV), and never persist or log one-time payment tokens, authentication headers, private keys, database credentials, or full sensitive payloads. Accept a one-time token only at the typed application boundary and pass it directly to the Yuno adapter for the intended operation.
- Keep secrets out of object representations, exceptions, traces, fixtures, and structured log fields.
- Emit structured logs with correlation, merchant order, payment attempt, provider payment, operation, duration, and status identifiers when available.
- Log normalized status and error categories instead of complete Yuno responses or webhook bodies.

## Tests and validation

- Unit-test domain rules and application services with mock gateways, repositories, and clocks. Unit tests must not require a live provider or database.
- Test Yuno mappings, headers, redaction, timeouts, retry decisions, and error translation with `httpx.MockTransport` or an equivalent injected transport.
- Test idempotency persistence, duplicate and out-of-order webhooks, uncertain outcomes, reconciliation, and transaction rollback paths.
- Keep Yuno Sandbox tests separate, explicitly marked, credential-gated, and excluded from the ordinary unit suite.

Run these commands from `backend/` after changes:

```bash
uv run ruff check .
uv run pytest tests
```

## Capability routing

Follow the [development tooling guide](../docs/development-tooling.md) for setup and official MCP sources. MCP access never replaces repository migrations, deterministic tests, or the production Yuno adapter.

- **Yuno MCP:** read current server-side API documentation and inspect provider schemas before changing mappings, authentication, idempotency, retries, or payment behavior. Financial mutations must remain explicit and use Sandbox during development.
- **Supabase MCP:** search current documentation and, when Supabase is selected, inspect development schemas, migrations, logs, generated types, and advisors. Start read-only and project-scoped; database mutations require explicit task scope and durable migrations.

## Required skill routing

Use each skill when its trigger matches the task:

- Use `implement-backend-phase` for an isolated backend/core roadmap workstream.
- Use `supabase` for any Supabase-specific task and check its current changelog and official documentation before implementation.
- Use `supabase-postgres-best-practices` when designing or reviewing schemas, migrations, indexes, query performance, RLS, or database security.
- Use `openai-docs` before changing an optional OpenAI integration. Keep AI adapters provider-specific and outside the domain.
- Use `context7-mcp` for current SQLAlchemy, HTTPX, or other third-party library documentation when the root source-routing rule applies; Yuno still uses official Yuno sources first.

## Official references

- [Yuno authentication and idempotency](https://docs.y.uno/reference/getting-started/authentication)
- [Yuno API environments](https://docs.y.uno/reference/getting-started/api-environments)
- [Yuno checkout session object](https://docs.y.uno/reference/checkout-sessions/the-checkout-session-object)
- [Yuno create checkout session](https://docs.y.uno/reference/checkout-sessions/create-checkout-session)
- [Yuno webhooks overview](https://docs.y.uno/docs/webhooks/index)
- [Supabase Data API security](https://supabase.com/docs/guides/api/securing-your-api)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
