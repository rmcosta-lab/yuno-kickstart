---
name: implement-backend-phase
description: Implement the plain-Python backend/core workstream of a specified Yuno × Nauta phase, including services, repositories, persistence, and provider adapters. Use for backend-only work or when delegated by implement-phase; do not use for FastAPI or frontend implementation.
---

# Implement the backend/core phase workstream

Deliver business behavior inside `backend/**` behind typed application interfaces, independent of FastAPI and provider transport details.

## 1. Resolve scope and ownership

Read `AGENTS.md`, `backend/AGENTS.md` when present, `docs/project-specs/mission.md`, `docs/project-specs/tech-stack.md`, `docs/project-specs/roadmap.md`, the active phase `requirements.md`, `plan.md`, and `validation.md`, and `docs/decisions/challenge-plan.md` when present. Inspect `git status` and preserve unrelated changes.

When delegated, use the exact phase spec, agreed contracts, and allowed paths supplied by `implement-phase`.

When directly invoked, require `phase/NN-{slug}`, one matching dated phase directory, a readable remote phase branch, DONE dependencies with required validation recorded and pull requests merged, no active declared conflict, and no merged phase pull request. Refresh bidirectional conflicts before work. Use a tracking Issue to confirm ownership when one exists. An open pull request is acceptable only when the user explicitly requests review follow-up; refresh it before editing and again before pushing. Route a closed-unmerged pull request through `finish-phase` before implementation resumes. Stop on ambiguity, divergent history, unresolved conflicts, or missing contract decisions.

Extract the assigned business rules, application-service interface, repository behavior, data changes, Yuno or AI capabilities, idempotency requirements, webhook state transitions, fallback, and allowed paths. Default write ownership is `backend/**` only. Do not edit `api/**`, `frontend/**`, phase specs, global specs, docs, root/shared configuration, or `infra/**` unless the coordinator explicitly assigns that exact path after checking for concurrent edits.

Report any required shared migration, environment, Docker, or workspace change to the coordinator instead of editing a concurrently owned path.

Use Context7 when current SQLAlchemy, httpx, PostgreSQL client, OpenAI SDK, or other library behavior is needed; do not guess version-sensitive APIs.

## 2. Keep core independent and typed

- Implement business rules and state transitions in small plain-Python services/domain modules.
- Define typed application inputs, outputs, protocols, and exceptions for the API boundary.
- Keep repository access behind interfaces and SQLAlchemy details out of domain rules.
- Do not import FastAPI or API-layer Pydantic DTOs.
- Hide Yuno, OpenAI, Supabase, and other providers behind adapters; do not leak provider dictionaries through services.
- Prefer deterministic code and structured outputs before introducing agents or tool loops.

Use structured logging with correlation identifiers and operational fields needed by the phase. Never log secrets, auth headers, PAN, CVV, raw payment credentials, sensitive full webhook payloads, or prompts containing customer/payment data.

## 3. Implement persistence and providers safely

Before changing a Yuno adapter, use the current agent's MCP discovery in the execution environment. In Codex, run `codex mcp list`; in Claude Code, run `claude mcp list` or use `/mcp`. If the Yuno MCP is missing, follow the project setup/discovery rules before implementation. Use `https://docs.y.uno/llms.txt` and the relevant official page only when MCP setup or session restart is unavailable in the current environment, report that limitation, and match current endpoints, payloads, enums, headers, authentication, idempotency, environments, and errors rather than relying on memory.

Keep `httpx.AsyncClient`, base URLs, headers, timeouts, retries, idempotency headers, and provider error translation inside the Yuno integration adapter. Default to sandbox. Never perform a payment, refund, cancellation, capture, or other financial mutation unless the current user explicitly authorizes that exact operation and environment.

For mutable operations, create and persist one UUID idempotency key per logical attempt. Reuse it for retries of the same uncertain operation, use a new key only for a genuinely new operation, and prevent concurrent duplicates.

Process accepted webhook events idempotently, persist a deduplication key, tolerate out-of-order delivery, and update local state through application services. The API authenticates raw webhook bytes before delegation; the backend must not depend on FastAPI request objects.

Use explicit migrations for durable database changes. If Supabase is involved, run MCP discovery in the execution environment, start read-only against a development project, enforce RLS on exposed schemas, and require explicit scope before any remote mutation. Keep service-role credentials server-side.

## 4. Test backend behavior

Add focused unit tests for applicable behavior:

- business rules and state transitions
- application service inputs, outputs, and exceptions
- repository behavior and migrations
- Yuno request/response mapping and provider error translation
- idempotency key reuse and duplicate suppression
- webhook deduplication and out-of-order events
- fallback behavior without live credentials

Use `MockPaymentGateway` or mocked HTTP transports. Keep credentialed sandbox tests separately marked under integration tests. Run focused tests, then applicable Python gates from the correct workspace:

```bash
uv run ruff check .
uv run pytest
```

Review the backend diff for FastAPI/API DTO imports, leaked provider models, unpersisted idempotency, unsafe retries, sensitive logging, unnecessary infrastructure, remote mutations, and out-of-scope files.

## 5. Return interfaces and evidence

Report the outcome, files changed, application contract produced and any deviation, persistence/provider changes, commands/checks with results, credentialed or external checks skipped, fallback behavior, blockers, requested shared-file or migration changes, and confirmation that no secret or unauthorized remote/financial mutation occurred. When delegated, do not edit shared `plan.md` or `validation.md`; return exact evidence to `implement-phase`. Update shared records only when explicitly assigned exclusive ownership.
