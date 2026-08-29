---
name: implement-api-phase
description: Implement the FastAPI/BFF workstream of a specified Yuno × Nauta phase and publish an accurate Pydantic/OpenAPI contract. Use for API-only work or when delegated by implement-phase; do not use for frontend or backend business logic.
---

# Implement the API/BFF phase workstream

Deliver HTTP contracts and thin orchestration inside `api/**` without moving business rules or provider integration into FastAPI.

## 1. Resolve scope and contract

Read `AGENTS.md`, `api/AGENTS.md` when present, `docs/project-specs/mission.md`, `docs/project-specs/tech-stack.md`, `docs/project-specs/roadmap.md`, the active phase `requirements.md`, `plan.md`, and `validation.md`, and `docs/decisions/challenge-plan.md` when present. Inspect `git status` and preserve unrelated changes.

When delegated, use the exact phase spec and verified shared claim supplied by `implement-phase`. For review follow-up, require the coordinator's refreshed proof that the pull request is draft or equivalently merge-blocked before editing.

When directly invoked, require the current branch to match `phase/NN-{slug}` using the roadmap `Slug`, locate exactly one matching `docs/project-specs/YYYY-MM-DD-NN-{slug}/`, and refresh GitHub state. Require the roadmap number, heading name, slug, dependencies, conflicts, and gate to match the immutable metadata recorded when the phase was claimed. Resolve the authenticated GitHub login and require it to equal both the sole Issue assignee and `Owner: @login`. Verify that the planning SHA recorded by `start-phase` is an ancestor of the remote branch and that its spec path exists. A handoff is valid only after assignee, owner field, and an explicit Issue transfer comment agree.

Require shared state `IN_PROGRESS` for ordinary direct work or `REVIEW` only when the request explicitly targets follow-up on its sole open pull request. Stop and route to `finish-phase` reconciliation if any phase pull request is merged. Also stop on absence, ambiguity, claimant mismatch, missing planning publication, inaccessible remote state, dependency or conflict failure, closed-unmerged pull request, or branch/Issue disagreement. When directly invoked for review follow-up, acquire the coordination mutex, refresh the lifecycle, stop if merged, convert the pull request to draft or an equivalent repository-enforced merge block, record the exact unblock action on the Issue, verify its unchanged head/attempt and recorded block, and release the mutex in a finally step before editing; stop if blocking or its later unblock action cannot be completed.

Extract the assigned endpoints, Pydantic request/response fields, status codes, application-service interface, error mapping, auth/CORS requirements, webhook transport behavior, and allowed paths. Default write ownership is `api/**` only. Do not edit `frontend/**`, `backend/**`, generated frontend files, phase specs, docs, or root/shared configuration unless the coordinator explicitly assigns that exact path.

Use the available FastAPI skill for framework-specific conventions. When current FastAPI or Pydantic behavior matters, use Context7 as required by `AGENTS.md` rather than relying on memory.

## 2. Publish the HTTP contract first

- Define explicit Pydantic models for every exposed request and response.
- Version application routes under `/v1`; keep `/health` unversioned unless the phase specification says otherwise.
- Keep OpenAPI operation names, schemas, status codes, and error responses stable and accurate for Orval generation.
- Do not edit TypeScript DTOs or generated client files; signal the coordinator when the OpenAPI output is ready.

If a contract must change after frontend work begins, stop API integration work and report the proposed change to the coordinator. Resume only after the phase specification and affected workers are synchronized.

## 3. Keep FastAPI thin

FastAPI owns HTTP validation, dependency wiring, authentication/authorization boundaries, explicit CORS, error translation, correlation/request IDs, webhook ingress, and request orchestration. Delegate business decisions, state transitions, repositories, Yuno server-side calls, and provider strategy to typed backend services imported directly in-process.

Translate between Pydantic DTOs and backend application inputs/outputs at the boundary. Do not make the backend import FastAPI or API Pydantic DTOs, leak raw Yuno dictionaries through responses, or add a network hop between API and core.

Before modifying Yuno webhook headers, signatures, or payload handling, use the current agent's MCP discovery in the execution environment. In Codex, run `codex mcp list`; in Claude Code, run `claude mcp list` or use `/mcp`. If the Yuno MCP is missing, follow the project setup/discovery rules before implementation. Use the official machine-readable documentation fallback only when MCP setup or session restart is unavailable in the current environment, and report that limitation.

For Yuno webhooks, read raw request bytes, read `x-hmac-signature`, verify HMAC-SHA256 with constant-time comparison, reject invalid signatures, and only then parse JSON and delegate idempotent event processing to the backend. Return HTTP 200 quickly after accepted processing. Never log signatures, auth headers, secrets, PAN/CVV, or sensitive full payloads.

Do not call Yuno private/server APIs directly from routers. Transport verification is an API concern; provider integration belongs behind the backend adapter.

## 4. Test the API boundary

Add focused tests for the behavior in scope, including applicable cases for:

- request validation and success response schemas
- status codes and application-error translation
- dependency wiring with mocked backend services
- auth and CORS boundaries
- valid and invalid raw-body webhook signatures
- OpenAPI schema stability for the changed contract

Run the repository's focused API tests, then applicable Python gates from the correct workspace:

```bash
uv run ruff check .
uv run pytest
```

Review the API diff for business rules, database queries, provider HTTP calls in routers, inaccurate OpenAPI, sensitive logging, permissive credentialed CORS, and out-of-scope files.

## 5. Return the contract and evidence

Report the outcome, files changed, HTTP contract produced, application contract consumed and any deviation, the tested OpenAPI export checkpoint, commands/checks with results, webhook/auth/CORS evidence, skipped gates or blockers, requested shared-file changes, and confirmation that no secret or unauthorized remote/financial mutation occurred. When delegated, do not edit shared `plan.md` or `validation.md`; return exact evidence to `implement-phase`. Update shared records only when explicitly assigned exclusive ownership.
