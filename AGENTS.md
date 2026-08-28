# AGENTS.md — Yuno × Nauta Hackathon

> Engineering instructions for Codex.
>
> **Primary objective:** ship a working, polished hackathon demo quickly while keeping the frontend, HTTP API, and backend/domain clearly separated.
>
> **Default principle:** keep logical boundaries strong and operational complexity low. Do not turn the hackathon into a microservices/infrastructure project.

---

## 1. Mission and operating mode

Build the project as three logical application layers:

1. **Frontend**
   - Next.js + TypeScript.
   - Owns presentation, browser state, forms, and user interaction.
   - Communicates only with our FastAPI API.
   - Uses Yuno's Web SDK only for browser-side payment UI/tokenization when required.

2. **API / BFF**
   - FastAPI + Pydantic + OpenAPI.
   - Owns HTTP contracts, validation, authentication/authorization boundaries, error mapping, webhook ingress, and request orchestration.
   - Must remain thin.
   - Must not contain domain/business rules.

3. **Backend / Core**
   - Plain Python domain/application code.
   - Owns business rules, application services, database access abstractions, Yuno server-side integration, AI integration, and external adapters.
   - Must not depend on FastAPI.

For the hackathon, **do not introduce an unnecessary network hop between the FastAPI layer and the Python core**. The API may import the backend package directly. Preserve the boundary in code so it can be split into a separate service later if needed.

```text
┌──────────────────────────────────────┐
│ Browser / Next.js                    │
│ TypeScript + shadcn/ui + TanStack    │
└──────────────────┬───────────────────┘
                   │ HTTPS / JSON
                   │ generated OpenAPI client
                   ▼
┌──────────────────────────────────────┐
│ FastAPI API / BFF                    │
│ Pydantic + OpenAPI                   │
│ auth + validation + webhooks         │
└──────────────────┬───────────────────┘
                   │ typed Python calls
                   ▼
┌──────────────────────────────────────┐
│ Backend / Core                      │
│ domain + services + repositories     │
│ integrations + AI                   │
└───────┬───────────────────┬──────────┘
        │                   │
        ▼                   ▼
 PostgreSQL/Supabase       Yuno API
                              │
                              ▼
                         Payment providers

Optional:
Backend/Core ──> OpenAI API / Agents SDK
```

---

## 2. Non-negotiable engineering rules

### Architecture

- Keep business logic out of FastAPI routers.
- The backend/core package must not import FastAPI.
- The frontend must never call Yuno's private/server APIs directly.
- The frontend must never receive or store `YUNO_PRIVATE_SECRET_KEY`.
- Do not duplicate API DTOs manually in TypeScript when they can be generated from OpenAPI.
- External providers must be hidden behind adapters/protocols.
- Prefer a vertical slice that works end-to-end over broad unfinished architecture.
- Avoid Kafka, Kubernetes, service mesh, event sourcing, Celery, or extra microservices unless the challenge creates a concrete need.
- Redis is **optional** and should only be added for a demonstrated need such as cache, rate limiting, short-lived distributed state, or background work.

### Code quality

- Python: type hints on public functions and service boundaries.
- TypeScript: strict mode.
- Pydantic models for every external API request/response contract we expose.
- Use structured logging.
- Never log secrets, card data, CVV, authentication headers, or full sensitive payloads.
- Keep functions small and testable.
- Prefer composition over global state.
- Add dependencies only when they remove more complexity than they create.

### Definition of done

A task is not complete until relevant checks pass.

At minimum:

```bash
# Python
uv run ruff check .
uv run pytest

# Frontend
pnpm lint
pnpm build
```

For rendered UI changes, also perform a browser smoke test and inspect console/runtime errors.

---

## 3. Repository layout

Use a monorepo with independently understandable modules:

```text
/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env.example
├── .codex/
│   └── config.toml
├── docker-compose.yml
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── decisions/
│
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   └── src/
│       ├── app/
│       ├── components/
│       │   └── ui/
│       ├── features/
│       ├── hooks/
│       └── lib/
│           ├── api/
│           │   └── generated/
│           └── yuno/
│
├── api/
│   ├── pyproject.toml
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── routers/
│       ├── schemas/
│       ├── dependencies/
│       ├── middleware/
│       └── errors/
│
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   └── rules/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── integrations/
│   │   │   ├── yuno/
│   │   │   └── openai/
│   │   ├── db/
│   │   └── ai/
│   └── tests/
│
└── infra/
    ├── sql/
    └── scripts/
```

Do not create empty architecture folders merely to look sophisticated. Create a folder when the first real module belonging to it exists.

---

## 4. Default technology stack

### Frontend

Use:

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query
- React Hook Form
- Zod
- Orval for OpenAPI → TypeScript client generation
- pnpm

Rules:

- Use Server Components by default where appropriate.
- Add `"use client"` only where browser state/interactivity is actually required.
- Use TanStack Query for remote server state.
- Do not add Redux unless there is a concrete cross-application state problem that cannot be handled cleanly otherwise.
- Prefer shadcn/ui primitives instead of creating a bespoke design system during the hackathon.
- The frontend calls only our API/BFF, except for the Yuno browser SDK flow documented below.

### API / BFF

Use:

- Python 3.12+
- FastAPI
- Pydantic
- Uvicorn
- `httpx`
- structured logging (`structlog` or equivalent)
- `uv`
- Ruff
- pytest

The API owns:

- HTTP routes
- input/output schemas
- auth boundaries
- CORS
- error translation
- webhook ingress
- dependency wiring
- OpenAPI contract

The API does **not** own:

- pricing/risk/business decisions
- payment strategy
- domain state transitions
- database query details
- provider-specific logic beyond transport-level webhook verification/delegation

### Backend / Core

Use:

- Python 3.12+
- SQLAlchemy 2.x
- PostgreSQL
- Supabase when managed Postgres/auth/storage makes the demo faster
- `httpx.AsyncClient` for server-side HTTP integrations
- pytest
- Ruff
- `uv`

Optional AI:

- OpenAI API
- OpenAI Agents SDK only when the problem truly requires tools/agent loops/handoffs
- Prefer structured outputs and deterministic code before adding multi-agent orchestration

### Deployment

Default:

- Frontend: Vercel
- Database: Supabase/PostgreSQL
- API: choose a Python-compatible deployment target based on what is fastest/reliable for the event
- Keep deployment provider-specific code out of the domain layer

---

## 5. API contract between frontend and backend

The FastAPI OpenAPI document is the source of truth for browser/server contracts.

Target flow:

```text
Pydantic response/request models
          │
          ▼
FastAPI /openapi.json
          │
          ▼
Orval
          │
          ▼
generated TypeScript client
          │
          ▼
TanStack Query hooks
          │
          ▼
React components
```

Suggested frontend command:

```json
{
  "scripts": {
    "api:generate": "orval --config orval.config.ts"
  }
}
```

Rules:

- Never hand-copy Python API schemas into TypeScript.
- Do not edit generated API files manually.
- When an API contract changes:
  1. change the Pydantic schema,
  2. run API tests,
  3. regenerate the TypeScript client,
  4. fix compile errors in the frontend,
  5. run frontend build.

Version our routes under `/v1`.

Initial API surface may include:

```text
GET  /health

POST /v1/customers
POST /v1/checkout/sessions

GET  /v1/payments/{payment_id}
POST /v1/payments/{payment_id}/refund

POST /v1/webhooks/yuno
```

Only add challenge-specific endpoints after the challenge is known.

---

## 6. Yuno integration — source-of-truth policy

Yuno changes over time. **Never guess endpoint payloads, enum values, SDK methods, authentication behavior, or webhook formats.**

Before implementing or modifying a Yuno integration:

1. Prefer the official Yuno MCP `documentation.read` tool when available.
2. Read the official index:
   - `https://docs.y.uno/llms.txt`
3. Read the relevant official Yuno page.
4. Yuno publishes machine-readable Markdown: append `.md` to a Yuno Docs URL when useful.
5. Prefer Yuno official documentation over blog posts, old examples, or memory.

The MCP is a **Codex development tool**. Production application code should still integrate with Yuno's official API/SDK through our application adapter.

---

## 7. Configure Yuno MCP for Codex

Yuno currently provides an official local MCP package:

```text
@yuno-payments/yuno-mcp
```

It exposes tools including customer creation/retrieval, checkout sessions, payment creation/retrieval/refunds/cancel/capture, subscriptions, recipients, installment plans, and `documentation.read`.

Create a project-scoped Codex MCP configuration:

```toml
# .codex/config.toml
#
# Do NOT commit credentials here.
# env_vars tells Codex to forward variables already present
# in the local environment to the MCP process.

[mcp_servers.yuno]
command = "npx"
args = ["-y", "@yuno-payments/yuno-mcp@latest"]
env_vars = [
  "YUNO_ACCOUNT_CODE",
  "YUNO_PUBLIC_API_KEY",
  "YUNO_PRIVATE_SECRET_KEY",
  "YUNO_COUNTRY_CODE",
  "YUNO_CURRENCY",
]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 60
```

Before using it, export the variables locally.

Example only:

```bash
export YUNO_ACCOUNT_CODE="..."
export YUNO_PUBLIC_API_KEY="..."
export YUNO_PRIVATE_SECRET_KEY="..."
export YUNO_COUNTRY_CODE="BR"
export YUNO_CURRENCY="BRL"
```

Then verify:

```bash
codex mcp list
```

### MCP rule

Use the Yuno MCP primarily for:

- reading current Yuno documentation,
- validating an integration approach,
- inspecting current tool schemas,
- sandbox experimentation when appropriate.

Do not make an autonomous payment/refund/cancel call merely because the MCP exposes the tool. Financial state-changing actions must be explicit, intended, and use sandbox during development.

For a hackathon, prefer the **local MCP**. A remotely hosted Yuno MCP also exists, but it adds remote authentication/session/network considerations that are not needed by default for rapid prototyping.

---

## 8. Yuno credentials and environments

Yuno server-side API requests require:

```text
public-api-key
private-secret-key
```

The private secret is server-side only.

Use sandbox until explicitly ready for production:

```text
Sandbox:    https://api-sandbox.y.uno
Production: https://api.y.uno
```

Suggested `.env.example`:

```dotenv
# Application
APP_ENV=development
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Database
DATABASE_URL=

# Yuno - server
YUNO_BASE_URL=https://api-sandbox.y.uno
YUNO_ACCOUNT_CODE=
YUNO_ACCOUNT_ID=
YUNO_PUBLIC_API_KEY=
YUNO_PRIVATE_SECRET_KEY=
YUNO_COUNTRY_CODE=BR
YUNO_CURRENCY=BRL

# Yuno - browser
# Public key is intentionally public; private key must NEVER use NEXT_PUBLIC_.
NEXT_PUBLIC_YUNO_PUBLIC_API_KEY=

# Yuno webhook
YUNO_WEBHOOK_HMAC_SECRET=

# Optional AI
OPENAI_API_KEY=
```

Rules:

- `.env` is gitignored.
- `.env.example` contains names only, never live secrets.
- Never create `NEXT_PUBLIC_YUNO_PRIVATE_SECRET_KEY`.
- Redact `public-api-key`, `private-secret-key`, auth headers, and secrets from logs.
- Sandbox and production credentials must remain separate.

---

## 9. Recommended Yuno web payment architecture

For a web demo, default to Yuno's **Full Checkout Web SDK** unless the challenge requires a different flow.

Install:

```bash
pnpm add @yuno-payments/sdk-web
```

Use the `SDK_CHECKOUT` workflow.

### End-to-end flow

```text
1. Browser
   │
   │ POST /v1/checkout/sessions
   ▼
2. Our FastAPI API
   │
   ▼
3. Backend/Core CheckoutService
   │
   ├── ensure/create Yuno customer
   │
   └── YunoGateway.create_checkout_session(...)
   ▼
4. Yuno API
   │
   └── returns checkout_session
   ▼
5. Browser initializes Yuno Web SDK
   │
   └── uses public API key + checkout session
   ▼
6. Yuno SDK renders/tokenizes payment data
   │
   └── callback returns one-time token
   ▼
7. Browser sends token to OUR API
   ▼
8. Backend/Core creates payment server-side in Yuno
   ▼
9. Browser receives immediate result for UX
   │
   └── source of truth continues via webhook
   ▼
10. Yuno webhook -> POST /v1/webhooks/yuno
    └── verify HMAC -> persist/process event -> update local payment state
```

### Important checkout-session rules

For `SDK_CHECKOUT`:

- create the checkout session server-side,
- one payment is supported per checkout session,
- a checkout session expires after five hours,
- treat a checkout session as tied to a payment attempt,
- do not build a custom raw-card collection form when the Yuno SDK can tokenize/handle sensitive payment data.

A typical checkout-session request includes fields such as:

```json
{
  "account_id": "<uuid>",
  "merchant_order_id": "order-001",
  "payment_description": "Hackathon order",
  "country": "BR",
  "customer_id": "<uuid>",
  "amount": {
    "currency": "BRL",
    "value": 100
  },
  "callback_url": "https://example.test/payment/callback",
  "workflow": "SDK_CHECKOUT"
}
```

**Important:** this example is architectural guidance, not a permanent schema contract. Before coding, read the current Yuno API reference/MCP schema and adapt to the exact challenge/account configuration.

---

## 10. Yuno adapter boundary

The domain layer must not know about HTTP headers, Yuno endpoint URLs, or `httpx`.

Define an application-facing protocol, for example:

```python
from typing import Protocol

class PaymentGateway(Protocol):
    async def create_customer(self, request): ...
    async def create_checkout_session(self, request): ...
    async def create_payment(self, request): ...
    async def retrieve_payment(self, payment_id: str): ...
    async def refund_payment(self, request): ...
```

Implement:

```text
PaymentGateway
├── YunoPaymentGateway       # real sandbox/production adapter
└── MockPaymentGateway       # tests/local fallback only
```

Suggested Yuno module:

```text
backend/src/integrations/yuno/
├── client.py
├── gateway.py
├── schemas.py
├── errors.py
└── auth.py
```

`client.py` owns:

- `httpx.AsyncClient`
- base URL
- Yuno headers
- timeout
- HTTP error translation
- idempotency headers

`gateway.py` translates between domain/application models and Yuno models.

Do not leak Yuno-specific response dictionaries throughout the application.

---

## 11. Idempotency

Payment mutations must be designed for retries.

When Yuno requires/supports `X-Idempotency-Key`:

- use a UUID,
- generate one key per **logical operation**,
- persist the key with the local payment/refund attempt,
- reuse the same key if retrying the same uncertain operation,
- use a new key for a genuinely new logical operation,
- do not blindly create a new key after a timeout if the previous request may have succeeded,
- do not issue concurrent duplicate mutations for the same logical attempt.

Suggested local model:

```text
payment_attempts
- id
- order_id
- yuno_payment_id
- yuno_checkout_session_id
- idempotency_key
- status
- created_at
- updated_at
```

Network retries must preserve the same idempotency key for the same logical Yuno call.

---

## 12. Webhooks

Create:

```text
POST /v1/webhooks/yuno
```

### Required processing order

```text
HTTP request
  │
  ├─ read RAW request body bytes
  │
  ├─ read x-hmac-signature
  │
  ├─ verify HMAC-SHA256
  │
  ├─ reject invalid signatures
  │
  ├─ parse JSON only after signature validation
  │
  ├─ deduplicate/idempotently process event
  │
  ├─ persist/update state
  │
  └─ return HTTP 200 quickly
```

When HMAC is enabled, Yuno signs the payload with HMAC-SHA256 and sends the signature in:

```text
x-hmac-signature
```

Verify against the **raw request body before parsing JSON**.

In Python, use constant-time comparison such as `hmac.compare_digest`.

Yuno expects HTTP 200 as receipt confirmation and may retry an unconfirmed webhook up to seven attempts, with later retries extending through 96 hours. Therefore webhook processing must be idempotent.

Suggested table:

```text
webhook_events
- id
- provider
- event_key / dedup_key
- event_type
- event_version
- payload JSONB
- received_at
- processed_at
- processing_error
```

Do not assume webhook delivery order.

Do not use the browser's final callback as the durable source of payment truth. Persist/reconcile server-side payment state using webhooks and, where necessary, Yuno payment retrieval.

---

## 13. Minimal database model

Start small.

```text
customers
- id
- merchant_customer_id
- yuno_customer_id
- created_at
- updated_at

orders
- id
- merchant_order_id
- amount
- currency
- status
- created_at
- updated_at

payment_attempts
- id
- order_id
- yuno_payment_id
- yuno_checkout_session_id
- idempotency_key
- status
- provider_status
- created_at
- updated_at

webhook_events
- id
- provider
- event_type
- dedup_key
- payload JSONB
- received_at
- processed_at
```

Only add tables required by the actual challenge.

If Supabase is used:

- enable RLS on exposed schemas,
- never expose the service role/secret key to the browser,
- use explicit authorization policies,
- use migrations rather than manual production-only edits.

---

## 14. Security rules

### Payment data

- Never store PAN or CVV.
- Never log card data.
- Prefer Yuno Web SDK tokenization so sensitive payment information does not transit our own backend.
- Keep private API credentials server-side.
- HTTPS for non-local environments.
- Explicit CORS origins; do not use permissive wildcard CORS together with credentials.
- Validate all inbound payloads.
- Verify webhook signatures.
- Sanitize/redact structured logs.
- Use sandbox credentials in development and demo preparation unless production is explicitly required.

### Secrets

Never commit:

```text
.env
YUNO_PRIVATE_SECRET_KEY
YUNO_WEBHOOK_HMAC_SECRET
OPENAI_API_KEY
DATABASE_PASSWORD
service-role / administrative database keys
```

---

## 15. Codex plugins / skills to use

Prefer **official/current plugins** over copying random community skills into the repository.

### Priority 1 — Build Web Apps

Install/use OpenAI's **Build Web Apps** plugin.

Relevant included skills:

- `frontend-app-builder`
- `frontend-testing-debugging`
- `react-best-practices`
- `shadcn-best-practices`
- `supabase-best-practices`

The plugin also includes Stripe guidance; **ignore Stripe-specific guidance for this project** because Yuno is our payment orchestration layer.

Use this plugin for:

- creating/refining the Next.js UI,
- shadcn composition,
- React/Next.js quality,
- browser validation,
- Supabase/Postgres patterns.

### Priority 2 — GitHub

Use/install the official GitHub plugin when repository, issues, PRs, CI, or review workflows are needed.

### Priority 3 — Vercel / Next.js

If available in the current Codex Plugin Directory, use the Vercel-oriented skills for:

- Next.js App Router best practices,
- Vercel deployment/preview workflows,
- browser/dev-server verification.

### Priority 4 — Supabase

Use the official Supabase capability/skill if Supabase is selected.

Key principles:

- check current docs/changelog,
- enable RLS where appropriate,
- never expose administrative/service-role keys in the browser,
- verify migrations/queries after applying them.

### Priority 5 — Yuno

Do **not** depend on an unofficial generic payment skill.

Instead:

1. configure the official Yuno MCP,
2. use `documentation.read`,
3. use `https://docs.y.uno/llms.txt`,
4. keep this AGENTS.md as project-specific Yuno integration guidance.

If the challenge later benefits from an agent that actively performs Yuno operations at runtime, evaluate Yuno's official TypeScript **Agent Toolkit** (`@yuno-payments/agent-toolkit`) separately. Do not introduce it for a standard checkout flow.

### Plugin discovery note

OpenAI's current official curated examples live in:

```text
https://github.com/openai/plugins
```

The old `openai/skills` repository is deprecated; do not make it the primary installation source.

Use the Codex Plugin Directory (`/plugins` in supported Codex surfaces) to find/install current plugins instead of hard-coding potentially stale marketplace installation commands.

---

## 16. Codex working rules

Before editing:

1. Read this `AGENTS.md`.
2. Inspect the existing repository before proposing new structure.
3. Check installed plugins/skills and MCP servers.
4. If touching Yuno, query current Yuno docs/MCP before implementation.
5. If touching an unfamiliar dependency, verify its current official docs rather than guessing.
6. Make the smallest coherent change that completes a vertical slice.

After editing:

1. run relevant unit tests,
2. run Ruff/Python checks,
3. regenerate OpenAPI client if contract changed,
4. run TypeScript/lint/build,
5. browser-test rendered frontend changes,
6. review `git diff`,
7. ensure no secrets were created or logged,
8. update README/architecture notes only when behavior or setup changed.

Do not silently change architecture conventions in this file. If a challenge-specific requirement makes a rule inappropriate, document the decision in `docs/decisions/`.

---

## 17. Recommended nested AGENTS.md files

Once the initial project exists, create smaller scoped instructions.

### `frontend/AGENTS.md`

```markdown
# Frontend instructions

- Stack: Next.js App Router, TypeScript, Tailwind, shadcn/ui, TanStack Query.
- Use generated OpenAPI clients for our server API.
- Do not call Yuno private REST APIs from the browser.
- Yuno Web SDK is allowed for browser payment UI/tokenization.
- Never expose server secrets.
- Prefer Server Components unless client interactivity is needed.
- Validate rendered changes in a browser.
```

### `api/AGENTS.md`

```markdown
# API instructions

- FastAPI is a thin HTTP/BFF layer.
- Routers contain no business rules.
- Use explicit Pydantic request/response models.
- Keep OpenAPI accurate.
- Delegate application behavior to backend services.
- For Yuno webhooks, verify HMAC against raw bytes before JSON parsing.
```

### `backend/AGENTS.md`

```markdown
# Backend instructions

- Plain Python; never import FastAPI.
- Business logic lives in services/domain.
- DB access belongs behind repositories.
- Yuno belongs behind an adapter/protocol.
- Use async httpx for provider calls.
- Persist idempotency keys for mutable payment operations.
- Unit-test services with mocked provider adapters.
```

Deeper `AGENTS.md` files may specialize these rules but should not unnecessarily duplicate the root file.

---

## 18. Development commands

Target a simple local workflow.

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

### Python

Prefer a shared development command from the repository root, but each Python package should also be independently understandable.

Example:

```bash
uv sync
uv run fastapi dev api/app/main.py
```

### Database

Local PostgreSQL via Docker Compose is acceptable:

```bash
docker compose up -d postgres
```

Do not require Docker to run the frontend.

### OpenAPI client

```bash
cd frontend
pnpm api:generate
```

---

## 19. Testing strategy

### Backend/core

Unit tests should cover:

- application/business rules,
- Yuno request mapping,
- idempotency behavior,
- provider error mapping,
- webhook event processing/deduplication.

Use `MockPaymentGateway` or mocked HTTP transport; unit tests must not depend on live Yuno.

### API

Test:

- validation errors,
- success response schemas,
- dependency wiring,
- webhook signature valid/invalid cases,
- CORS/auth boundaries where relevant.

### Yuno sandbox integration tests

Keep them separate and explicitly marked:

```text
tests/integration/
```

They may require credentials and should not run as ordinary unit tests.

### Frontend

Test highest-value flows:

- initial loading/error states,
- checkout creation,
- Yuno SDK initialization boundary,
- payment outcome UI,
- retry/error UX.

For the hackathon, favor meaningful smoke/e2e tests over large low-value snapshot suites.

---

## 20. Observability

Use structured logs with a correlation/request ID.

Useful fields:

```text
request_id
merchant_order_id
payment_attempt_id
yuno_payment_id
operation
duration_ms
status
provider_status
```

Never include:

```text
private-secret-key
authorization tokens
PAN
CVV
raw payment credentials
full sensitive webhook payloads
```

If AI is added, capture:

```text
model
latency
tool_calls
token/cost metadata when available
request correlation ID
```

Do not log prompts containing sensitive customer/payment data by default.

---

## 21. Hackathon prioritization

When the challenge is revealed, implement in this order:

### P0 — vertical demo

- one compelling user journey,
- real frontend,
- FastAPI contract,
- backend service,
- real Yuno sandbox integration when credentials/features permit,
- persistent state only where required,
- webhook if payment state changes asynchronously.

### P1 — polish

- loading/error states,
- observability,
- graceful fallback,
- better visual experience,
- architecture diagram,
- README/demo instructions.

### P2 — sophistication

Only after P0 works:

- AI agents,
- Redis,
- background workers,
- richer analytics,
- extra payment paths,
- advanced optimization.

A smaller complete demo is better than a sophisticated incomplete platform.

---

## 22. Initial Codex bootstrap task

When this file is first added to a new repository, execute the following task:

> Read `AGENTS.md` completely and bootstrap the repository according to it.
>
> Create the monorepo skeleton for `frontend`, `api`, `backend`, `infra`, and `docs`.
>
> Set up:
>
> - Next.js App Router + TypeScript + Tailwind + shadcn/ui;
> - TanStack Query, React Hook Form, Zod;
> - Orval-generated client architecture;
> - Python 3.12+ managed with `uv`;
> - FastAPI + Pydantic API with `GET /health`;
> - plain-Python backend/core package with no FastAPI dependency;
> - SQLAlchemy 2.x and PostgreSQL configuration;
> - `PaymentGateway` protocol;
> - `YunoPaymentGateway` sandbox adapter skeleton;
> - `MockPaymentGateway` for tests;
> - webhook HMAC verification utility and tests;
> - `.env.example`;
> - project-scoped `.codex/config.toml` for the official Yuno MCP using environment-variable forwarding;
> - Docker Compose for PostgreSQL only;
> - lint/test/build scripts;
> - README with local setup and architecture diagram.
>
> Do **not** implement challenge-specific business logic yet.
> Do **not** add Redis, Celery, Kafka, Kubernetes, or extra services unless already required.
> Do not put real secrets in any file.
>
> Before finishing:
>
> 1. run Python lint/tests;
> 2. run frontend lint/build;
> 3. verify the dev UI in a browser;
> 4. inspect `git diff`;
> 5. report any unavailable credential or external-service dependency separately.

---

## 23. First task after the challenge is announced

After reading the challenge, do not immediately code.

First produce a short implementation note in `docs/decisions/challenge-plan.md` with:

```text
Problem
Target user
One-sentence value proposition
Demo journey
P0 scope
Explicit non-goals
Yuno capabilities required
AI capabilities required, if any
Data model changes
API endpoints
Main risks
Fallback/demo plan
```

Then implement the smallest end-to-end slice.

---

## 24. Official references

### Yuno

- Documentation index / LLM-readable map  
  https://docs.y.uno/llms.txt

- AI integrations, machine-readable docs and Yuno MCP  
  https://docs.y.uno/docs/ai-capabilities/building-ai-integrations-with-yunos-llms-and-mcp

- Authentication and idempotency  
  https://docs.y.uno/reference/getting-started/authentication

- API environments  
  https://docs.y.uno/reference/getting-started/api-environments

- Checkout Session object  
  https://docs.y.uno/reference/checkout-sessions/the-checkout-session-object

- Create Checkout Session  
  https://docs.y.uno/reference/sandbox-tested/checkout-sessions/create-checkout-session

- Web SDK quickstart  
  https://docs.y.uno/docs/sdks/overview/quickstart

- Full Checkout — Web Payments  
  https://docs.y.uno/docs/sdks/full-checkout/web-payments

- Configure webhooks  
  https://docs.y.uno/docs/webhooks/configure-webhooks

- Verify webhook signatures (HMAC)  
  https://docs.y.uno/docs/webhooks/verify-webhook-signatures-hmac

### OpenAI / Codex

- Official OpenAI plugins repository  
  https://github.com/openai/plugins

- Build Web Apps plugin  
  https://github.com/openai/plugins/tree/main/plugins/build-web-apps

- Codex Model Context Protocol configuration  
  https://developers.openai.com/codex/mcp/

---

## 25. Final principle

When in doubt, optimize for:

```text
working demo
> clean contract
> observable behavior
> secure payment integration
> simple architecture
> clever architecture
```

Keep the system easy enough that another team member—or another Codex worktree—can understand a layer and modify it without loading the entire application into context.
