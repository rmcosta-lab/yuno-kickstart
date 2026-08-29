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
│   ├── project-specs/
│   │   ├── mission.md
│   │   ├── tech-stack.md
│   │   ├── roadmap.md
│   │   └── YYYY-MM-DD-NN-{slug}/
│   │       ├── requirements.md
│   │       ├── plan.md
│   │       └── validation.md
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

## 7.1 Development MCPs and remote environments

Use official MCP servers as development tools when their capability matches the task. They do not replace application dependencies, generated tests, migrations, or production integrations.

### Required discovery and setup flow

At the start of a task that involves GitHub, browser validation, UI components, Supabase, or Vercel:

1. Run `codex mcp list` in the environment where the task will execute.
2. Confirm that the required server is present, enabled, authenticated when needed, and exposes tools in the current Codex session.
3. If it is missing, use the official package or endpoint listed below. Prefer project-scoped `.codex/config.toml` entries over changing the user's global configuration.
4. If a machine-global change or interactive OAuth login is required, tell the user and request approval or user participation before continuing.
5. Restart Codex after configuration changes, run `codex mcp list` again, and make one harmless read-only tool call as a smoke test.

Never assume that an MCP available on the local machine is also available in a remote executor. Never install a similarly named unofficial package. Check the provider's current official documentation before changing a package, endpoint, authentication method, or tool policy.

### Capability routing

- **Chrome DevTools MCP:** inspect the rendered page, browser console, network requests, DOM state, screenshots, Lighthouse/performance traces, and runtime failures.
- **Playwright MCP:** exercise deterministic user journeys, form interactions, responsive states, navigation, and browser smoke/e2e checks.
- **shadcn MCP:** browse and search configured component registries and add shadcn components or blocks. Review every generated file and dependency.
- **GitHub MCP:** inspect and manage repositories, issues, pull requests, Actions, and reviews beyond what local `git` provides. Keep write operations approval-gated.
- **Supabase MCP:** search current Supabase documentation, inspect development schemas and migrations, query logs, run advisors, generate types, and perform explicitly requested development database work.
- **Vercel MCP:** search current Vercel documentation and inspect projects, deployments, build/runtime logs, domains, and deployment state. Use mutation tools only when the task explicitly requires the corresponding deployment change.

For a rendered frontend change, default to a Playwright user-flow smoke test followed by Chrome DevTools inspection of console and network errors. Use the shadcn MCP before hand-building a primitive that may already exist in the configured registry.

### Installation when a server is missing

Prerequisites for local STDIO servers:

- a current Node.js LTS release and `npm`/`npx`,
- a current stable Chrome installation for Chrome DevTools MCP,
- Node.js 18 or newer for Playwright MCP.

Use the following Codex commands from the project directory. `npx` may download the package on first use, so network access is required.

#### Chrome DevTools

```bash
codex mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest
```

#### Playwright

Use an isolated browser profile by default so cookies and local state are not shared across sessions:

```bash
codex mcp add playwright -- npx -y @playwright/mcp@latest --isolated
```

#### shadcn

```bash
codex mcp add shadcn -- npx -y shadcn@latest mcp
```

The repository must contain a valid `components.json` before component installation. The standard shadcn registry needs no extra authentication; keep private-registry tokens in environment variables, never in committed configuration.

#### GitHub

Use GitHub's official remote MCP server and bind authentication to an environment variable:

```bash
codex mcp add github --url https://api.githubcopilot.com/mcp/ --bearer-token-env-var GITHUB_PAT_TOKEN
```

Provide `GITHUB_PAT_TOKEN` through the local environment or secret store with the least privileges required for the task. Never place the token in `.codex/config.toml`, `AGENTS.md`, source files, logs, screenshots, or tool prompts. The CLI command writes shared Codex configuration; for this repository, prefer the project-scoped entry below.

#### Supabase

Start with a development project, project scoping, only the required feature groups, and read-only mode:

```bash
codex mcp add supabase --url "https://mcp.supabase.com/mcp?project_ref=<project-ref>&read_only=true&features=docs%2Cdatabase%2Cdebugging%2Cdevelopment"
codex mcp login supabase
```

Do not connect the Supabase MCP to production data by default. Remove `read_only=true` only for an explicitly requested schema/data mutation in a development project or branch. Keep manual approval enabled for mutating tools, review generated SQL, use migrations for durable schema changes, run security/performance advisors, and verify the result.

#### Vercel

```bash
codex mcp add vercel --url https://mcp.vercel.com
codex mcp login vercel
```

OAuth may open a browser. Do not place Vercel access tokens in `.codex/config.toml` or committed files.

### Project-scoped configuration

When the CLI cannot create a project-scoped entry, add the equivalent configuration to `.codex/config.toml` without credentials:

```toml
[mcp_servers.chrome-devtools]
command = "npx"
args = ["-y", "chrome-devtools-mcp@latest"]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 60

[mcp_servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp@latest", "--isolated"]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 60

[mcp_servers.shadcn]
command = "npx"
args = ["-y", "shadcn@latest", "mcp"]
enabled = true
startup_timeout_sec = 20
tool_timeout_sec = 60

[mcp_servers.github]
url = "https://api.githubcopilot.com/mcp/"
bearer_token_env_var = "GITHUB_PAT_TOKEN"
enabled = true
tool_timeout_sec = 60
default_tools_approval_mode = "writes"

[mcp_servers.supabase]
url = "https://mcp.supabase.com/mcp?project_ref=<project-ref>&read_only=true&features=docs%2Cdatabase%2Cdebugging%2Cdevelopment"
enabled = true
tool_timeout_sec = 60

[mcp_servers.vercel]
url = "https://mcp.vercel.com"
enabled = true
tool_timeout_sec = 60
```

Keep `<project-ref>` as a documented placeholder until a development Supabase project is selected. Do not commit a real project reference when its disclosure is not intended. `GITHUB_PAT_TOKEN` must be supplied by the environment or secret store and must never be committed.

### Remote environment rules

- Run discovery and the smoke test inside the actual remote session; a successful local `codex mcp list` is not evidence that the remote environment is ready.
- Prefer the official Streamable HTTP servers for GitHub, Supabase, and Vercel. Provide GitHub's PAT through the environment; complete OAuth for providers that support it in the environment/client that will use the stored session.
- STDIO servers require Node/npm and their browser dependencies in the remote image. When Codex provides a remote executor, set `experimental_environment = "remote"` on the relevant STDIO server and use headless, isolated browser profiles when supported.
- If the remote environment cannot launch a browser or receive an OAuth callback, report the limitation and use a browser-capable local/preview environment. Do not copy a personal browser profile, disable sandboxing, or embed credentials as a workaround.
- Forward secrets from the remote secret store with `env_vars` and `source = "remote"` when supported. Never hard-code them in `.codex/config.toml`, shell history, source files, logs, screenshots, or tool prompts.
- Keep mutating MCP tools approval-gated. GitHub branches/issues/PRs/workflows, database, deployment, domain, environment-variable, payment, refund, and other external state changes must remain within the explicit task scope.

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

## 15. Codex plugins and skills

Use official, current skills and plugins. Install a missing task-relevant skill before starting implementation. Do not load every skill for every task.

### Repository skill source

Use `.agents/skills` as the only repository-scoped skill source. Do not create or restore `.claude/skills`, and do not keep duplicate physical copies of the same skill in multiple directories.

- Keep project-authored workflow skills directly under `.agents/skills/<skill-name>/SKILL.md`.
- When a skill name already exists in `.agents/skills`, inspect the existing source and keep the intended canonical version instead of copying a duplicate over it.
- Treat package-provided entries such as the FastAPI skill as generated symlinks. Install project dependencies before validating them.
- Run `uvx library-skills --check` to validate managed symlinks without changing files. Do not pass `--claude`, because this repository does not maintain `.claude/skills`.
- Invoke a skill explicitly with `$skill-name`, or use `/skills` to inspect the skills available in the current Codex session.

### Shared roadmap coordination

Treat `docs/project-specs/roadmap.md` as a static dependency graph. Every `### Fase NN — Nome` section declares a canonical `Slug:`, `Depends on: none|NN,...`, `Conflicts with: none|NN,...`, and `Gate:`. Require the slug to match `^[a-z0-9]+(?:-[a-z0-9]+)*$` and use it verbatim in coordination paths. The gate is the minimum evidence for review; it is not the shared `DONE` state. Phase numbers are identifiers, not an implicit execution sequence. Do not write mutable phase status, assignees, branches, or `✅` markers into the roadmap. Once any coordination Issue, branch, planning record, or pull request exists for a phase, freeze its number, heading name, slug, dependencies, conflicts, and gate; later scope changes use a new phase identity.

GitHub is the shared execution state:

- one canonical coordination issue `[Fase NN] Nome` records the owner and phase metadata
- one deterministic remote branch `phase/NN-{slug}`, using the roadmap's required static `Slug`, is the exclusive claim lock
- one pull request from that branch to the remote default branch represents review
- `DONE` requires the applicable checks and phase validation to pass, that pull request to be merged, and the issue to be closed

A phase is eligible only when every declared dependency is `DONE`, no declared conflict is active or in `DRIFT`, no shared branch, pull request, or assigned issue already claims it, and its sole Issue does not record the terminal empty-phase outcome `CANCELED`. A canceled phase never satisfies a dependency or becomes eligible again. Treat conflict edges as bidirectional. Use them when two phases would write the same serialized shared/root file or depend on the same unsettled decision.

`start-phase` and `manage-shared-specs` must use the create-only `refs/heads/coordination/phase-claim-lock` mutex around their cross-workflow check-and-create transaction; partial phase claims, orphan-lock repairs, implementation review blocking, fixed-task publication, and `finish-phase` review/merge/reconciliation mutations use the same mutex for their bounded refresh-and-mutate transaction. Refresh all relevant shared facts while holding it, create or repair the durable claim or review with the applicable create-only, update-only, or unique-Issue operation, and then release the short-lived mutex before long-running or local-only work. The durable branch is the claim; assignees and labels are not atomic locks. Never release a stale mutex based only on age or without confirming that no `start-phase`, `manage-shared-specs`, implementation, `changelog`, or `finish-phase` transaction remains active. The GitHub tool, credentials, and branch-protection policy must permit create-only refs, update-only non-force publication, and conditional compare-and-delete of only explicitly authorized coordination refs at their expected old SHA. If authenticated GitHub access or a remote default branch is unavailable, distributed coordination must stop rather than fall back to local-only state.

Frontend, API, and backend may run in parallel inside one claimed phase under `implement-phase`. Separate phases may run in parallel only when the dependency graph makes each one eligible. `manage-shared-specs` exclusively owns `docs/project-specs/mission.md`, `docs/project-specs/tech-stack.md`, `docs/project-specs/roadmap.md`, and `docs/decisions/challenge-plan.md` through the remote branch `refs/heads/docs/project-specs`; it does not own the dated phase directories below `docs/project-specs/`. Each claimed phase owns only its exact `docs/project-specs/YYYY-MM-DD-NN-{slug}/` directory through its coordinator. `manage-shared-specs` must not change its global files while any phase is `IN_PROGRESS`, `REVIEW`, or `DRIFT`. The only exception is an explicit restore-roadmap operation that pauses affected work and restores only uniquely reconstructable frozen phase metadata while preserving, without mutating, at most the authoritative stale-Issue or uniquely identified incomplete-claim facts documented by that skill. `changelog` exclusively owns `CHANGELOG.md` through `docs/changelog`. Keep other global shared files read-only unless an exact path has exclusive ownership through the conflict graph or another serialized task. Release a fixed branch only after its pull-request merge is verified, or after explicit repair proves it is an empty orphan and records any incomplete Issue as abandoned. A retry from the same unchanged base must reopen the single canonical `ABANDONED` Issue with a new attempt identifier; never create a duplicate exact-title Issue.

### Check skills before work

Follow this sequence in the environment that will run the task:

1. Run `/skills` in Codex and search for each skill required by the task.
2. Inspect repository-scoped skills:

   ```bash
   rtk rg --files .agents/skills
   ```

3. Run `/plugins` and confirm that the official Vercel plugin is installed when a `vercel:*` skill is required.
4. If a `SKILL.md` file exists but the skill is absent from `/skills`, restart Codex and check again.
5. Install only the missing skills from the official sources below.
6. Restart Codex after installation. Newly installed skills may become available only in the next turn or session.
7. Repeat `/skills` and confirm the exact skill identifier before continuing.

A local skills inventory does not prove that a remote environment has the same skills. Repeat this check in remote Codex sessions and ephemeral workspaces.

### Required skill routing

Use this table to select skills. A skill remains inactive when its trigger does not match the task.

| Skill | Use it when |
| --- | --- |
| `manage-shared-specs` | Initializing or updating global mission, stack, roadmap, or challenge decisions through their serialized branch |
| `start-phase` | Atomically claiming and specifying an eligible roadmap phase without implementing it |
| `implement-phase` | Coordinating a complete phase across frontend, API, and backend workstreams |
| `implement-frontend-phase` | Implementing an isolated frontend workstream |
| `implement-api-phase` | Implementing an isolated FastAPI/BFF workstream |
| `implement-backend-phase` | Implementing an isolated backend/core workstream |
| `deep-review` | Running an explicitly requested read-only, SHA-specific, pre-merge multi-agent review |
| `finish-phase` | Submitting a verified phase through its shared pull request or reconciling after remote merge; never deploying |
| `changelog` | Publishing merged phase results through the serialized `docs/changelog` branch and reconciling its lock |
| `library-skills` | Discovering, checking, or repairing package-provided skill symlinks |
| `frontend-app-builder` | Building a new frontend surface or performing a substantial redesign for the hackathon |
| `frontend-testing-debugging` | Testing or debugging rendered UI, responsive behavior, browser errors, or interactions |
| `react-best-practices` | Writing, reviewing, or refactoring React and Next.js code |
| `shadcn-best-practices` | Selecting or composing shadcn/ui components; the official standalone skill declares the identifier `shadcn` |
| `supabase-best-practices` | Designing or reviewing Supabase/Postgres work; the official standalone skill declares the identifier `supabase-postgres-best-practices` |
| `writing-guidelines` | Reviewing `README.md`, `docs/**/*.md`, and `docs/decisions/challenge-plan.md` after prose changes |
| `openai-docs` | Configuring or troubleshooting Codex, MCP, OpenAI APIs, models, SDKs, or other OpenAI products only |
| `vercel:ai-sdk` | Implementing an AI feature that the challenge genuinely requires; do not add AI to create novelty |
| `frontend-design` | Defining a distinctive visual direction before building or reshaping a major UI |
| `vercel:nextjs` | Working with App Router, Server Components, route organization, data boundaries, or Next.js architecture |
| `vercel:react-best-practices` | Running a Vercel-focused React performance and quality review |
| `vercel:shadcn` | Checking current shadcn CLI, registry, and composition guidance in a Vercel/Next.js workflow |
| `web-design-guidelines` | Reviewing accessibility, responsiveness, interaction design, and UX after UI changes |
| `vercel:agent-browser-verify` | Running a browser smoke test after visual changes or after starting a dev server |
| `vercel:verification` | Verifying the complete frontend to API to backend flow with evidence |

For a substantial frontend slice, use this order when every step applies:

1. `frontend-design` for the visual direction
2. `frontend-app-builder` for implementation
3. `vercel:nextjs`, `react-best-practices`, and shadcn guidance for framework and component quality
4. `frontend-testing-debugging` and `vercel:agent-browser-verify` for rendered checks
5. `web-design-guidelines` for accessibility, responsive behavior, and UX review
6. `vercel:verification` for the complete frontend to API to backend journey

Do not invoke both React best-practice variants only to duplicate the same review. Use `react-best-practices` during implementation and reserve `vercel:react-best-practices` for a dedicated Vercel performance pass.

### Install the Build Web Apps skills

For this repository, install the five official Build Web Apps skills into `.agents/skills` so the team can version them with the project. Source them only from `openai/plugins`.

First, keep only the missing `--path` values in this command. The installer stops when a destination directory already exists.

```bash
codex_skill_installer="${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py"

rtk python3 "$codex_skill_installer" \
  --repo openai/plugins \
  --path \
    plugins/build-web-apps/skills/frontend-app-builder \
    plugins/build-web-apps/skills/frontend-testing-debugging \
    plugins/build-web-apps/skills/react-best-practices \
    plugins/build-web-apps/skills/shadcn-best-practices \
    plugins/build-web-apps/skills/supabase-best-practices \
  --dest .agents/skills
```

If the system installer script is unavailable, invoke `$skill-installer` in Codex and provide the same `openai/plugins` repository paths. Do not replace these sources with similarly named community skills.

The official source folder names and declared identifiers differ for two skills:

- `shadcn-best-practices` declares `name: shadcn`
- `supabase-best-practices` declares `name: supabase-postgres-best-practices`

Do not rename their frontmatter. Use the identifier displayed by `/skills`.

The Build Web Apps bundle also contains Stripe guidance. Ignore it in this project because Yuno is the payment orchestration layer.

### Install standalone design and writing skills

Install these skills at project scope when `/skills` does not list them:

```bash
rtk npx skills add anthropics/skills --skill frontend-design
rtk npx skills add vercel-labs/agent-skills --skill web-design-guidelines
rtk npx skills add vercel-labs/agent-skills --skill writing-guidelines
```

Follow the installer prompt and select Codex plus project scope. Do not choose global scope unless the user requests the skill for every repository.

`openai-docs` is a Codex system skill. Do not install a duplicate copy. If it is missing, restart Codex, update the Codex installation through the supported distribution, and check `/skills` again.

### Install Vercel skills

The `vercel:*` identifiers come from the official Vercel plugin distributed through the Codex Plugin Directory:

1. Run `/plugins` in Codex.
2. Search for `Vercel` under **Developer Tools**.
3. Confirm that the plugin source is the official Codex directory entry.
4. Select **Install Plugin** or **Enable**.
5. Restart Codex.
6. Run `/skills` and confirm `vercel:ai-sdk`, `vercel:nextjs`, `vercel:react-best-practices`, `vercel:shadcn`, `vercel:agent-browser-verify`, and `vercel:verification`.

Do not copy Vercel plugin cache directories into the repository. The plugin manager owns installation and updates.

### Verify installed skill files

After repository-scoped installation, verify the skill metadata:

```bash
rtk rg -n '^name:|^description:' .agents/skills/*/SKILL.md
```

The check must show a valid `name` and `description` for every installed skill. Treat a missing file, invalid frontmatter, or absent `/skills` entry as an incomplete installation.

### GitHub, Supabase, and Yuno skill rules

- Use the official GitHub MCP server for repositories, issues, pull requests, Actions, and reviews beyond local `git`. Keep writes within the explicit task scope.
- Use the official Supabase skill and MCP when Supabase is selected. Check current documentation and the changelog, enable Row Level Security (RLS), protect service-role credentials, and verify migrations and queries.
- Do not use a generic payment skill for Yuno. Use the Yuno MCP for current documentation and schemas. Financial mutations must remain explicit and use sandbox during development.

Use the [official OpenAI plugin catalog](https://github.com/openai/plugins). Do not use the deprecated `openai/skills` repository as the primary source for Build Web Apps skills.

---

## 16. Codex working rules

Before editing:

1. Read this `AGENTS.md`.
2. Inspect the existing repository before proposing new structure.
3. Check installed plugins and skills using Section 15. Install any missing task-relevant skill before continuing.
4. Check MCP servers using Section 7.1. Install or configure any missing task-relevant MCP before continuing.
5. If touching Yuno, query current Yuno docs/MCP before implementation.
6. If touching an unfamiliar dependency, verify its current official docs rather than guessing.
7. Make the smallest coherent change that completes a vertical slice.

After editing:

1. run relevant unit tests,
2. run Ruff/Python checks,
3. regenerate OpenAPI client if contract changed,
4. run TypeScript/lint/build,
5. browser-test rendered frontend changes,
6. review `git diff`,
7. ensure no secrets were created or logged,
8. use `writing-guidelines` after changing `README.md`, documentation, or the challenge plan,
9. update README/architecture notes only when behavior or setup changed.

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
> - project-scoped `.codex/config.toml` for the official Yuno, GitHub, Chrome DevTools, Playwright, shadcn, Supabase, and Vercel MCPs, using environment-variable forwarding or credential-free remote endpoints;
> - repository-scoped Build Web Apps skills from Section 15, installed from their official `openai/plugins` paths;
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

First askt to produce a short implementation note in `docs/decisions/challenge-plan.md` with:

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

- [Codex skills and repository scope](https://developers.openai.com/codex/skills/)

- [Build Web Apps skill sources](https://github.com/openai/plugins/tree/main/plugins/build-web-apps/skills)

- [Official Vercel plugin source](https://github.com/openai/plugins/tree/main/plugins/vercel)

- [Vercel Labs agent skills](https://github.com/vercel-labs/agent-skills)

- [Anthropic frontend design skill](https://github.com/anthropics/skills/tree/main/skills/frontend-design)

### Development MCPs

- [GitHub MCP Server](https://github.com/github/github-mcp-server)

- [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp)

- [Playwright MCP](https://github.com/microsoft/playwright-mcp)

- [shadcn MCP](https://ui.shadcn.com/docs/mcp)

- [Supabase MCP](https://supabase.com/docs/guides/ai-tools/mcp)

- [Vercel MCP](https://vercel.com/docs/agent-resources/vercel-mcp)

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

<!-- context7 -->
Use Context7 MCP to fetch current documentation whenever the user asks about a library, framework, SDK, API, CLI tool, or cloud service — even well-known ones like React, Next.js, Prisma, Express, Tailwind, Django, or Spring Boot. This includes API syntax, configuration, version migration, library-specific debugging, setup instructions, and CLI tool usage. Use even when you think you know the answer — your training data may not reflect recent changes. Prefer this over web search for library docs.

Do not use for: refactoring, writing scripts from scratch, debugging business logic, code review, or general programming concepts.

## Steps

1. Always start with `resolve-library-id` using the library name and what to look up in the library's documentation, unless the user provides an exact library ID in `/org/project` format
2. Pick the best match (ID format: `/org/project`) by: exact name match, description relevance, code snippet count, source reputation (High/Medium preferred), and benchmark score (higher is better). If results don't look right, try alternate names or queries (e.g., "next.js" not "nextjs", or rephrase the question). Use version-specific IDs when the user mentions a version
3. `query-docs` with the selected library ID and what to look up in the library's documentation (not single words), scoped to a single concept. If the question spans multiple distinct concepts (e.g. routing and auth and caching), make a separate `query-docs` call per concept with the same library ID, unless the question is about how the concepts interact — combined queries dilute ranking and return shallow results for each topic
4. Answer using the fetched docs
<!-- context7 -->
