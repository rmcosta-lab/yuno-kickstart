---
name: implement-phase
description: Coordinate a multi-layer Yuno × Nauta roadmap phase across frontend, API, and backend workers, then integrate and validate the vertical slice. Use for whole-phase or cross-layer implementation; use layer skills for isolated work.
---

# Coordinate implementation of a Yuno × Nauta phase

Own scope, contracts, shared decisions, integration, and validation while layer workers edit non-overlapping paths.

## 1. Resolve the phase

Read `AGENTS.md`, inspect the branch, worktree, `git status`, installed skills, task-relevant MCP servers, global specs, and the matching phase `requirements.md`, `plan.md`, and `validation.md`.

Work from `phase/NN-{slug}`, not `main`. Require one matching dated phase directory and a readable remote phase branch. Verify that dependencies are merged, no declared conflicting phase is active, and no phase pull request is already merged. An open phase pull request is acceptable only when the user is explicitly requesting review follow-up.

When an Issue exists, use it to confirm the current owner and handoff; do not require attempt identifiers or duplicated lifecycle metadata. Stop on ambiguous ownership, a divergent branch, unresolved merge conflicts, or missing decisions that would make independent workers guess incompatible contracts.

Preserve unrelated changes. Identify the P0/P1/P2 outcome, acceptance criteria, non-goals, external dependencies, fallback, and the workstreams actually needed.

## 2. Make parallel work safe

Before delegation, make these gates decision-complete:

- **HTTP gate:** `/v1` routes, methods, request/response fields, status codes, errors, Pydantic schemas, and OpenAPI output
- **Application gate:** import path, public symbols, async/sync style, construction/DI, typed inputs/outputs, and application exceptions
- ownership of webhooks, persistence, provider calls, and the OpenAPI-to-Orval handoff
- the terminal checkout/payment result included in the phase

Assign one writer per path:

- frontend worker: `frontend/**`, including generated Orval output
- API worker: `api/**`, including Pydantic/OpenAPI source
- backend worker: `backend/**`
- coordinator: the active phase spec directory and explicitly assigned shared/integration paths

One owner must handle a manifest and its lockfile. Do not give two workers the same file. Record ownership exceptions in `plan.md` before delegation.

## 3. Handle shared-spec discoveries

When a worker discovers a needed stack or roadmap change:

1. distinguish a compatible dependency addition from a shared architecture/provider decision
2. pause only integration work that depends on the decision
3. have the coordinator inspect open pull requests touching the shared file
4. record the decision, reason, impact, affected phases, and communication in `plan.md`
5. update the global spec in this phase branch when the change is small and directly required; use `manage-shared-specs` on a documentation branch when it is broad or unrelated
6. tell affected phase owners to refresh after the decision merges

Do not silently rename or remove an active phase, weaken its gate, or redefine product/payment/security behavior. Add a follow-up phase for a materially different outcome or prerequisite. Do not use a repository-wide lock or wait for unrelated phases to finish.

Layer workers do not edit global specs unless the coordinator assigns the exact file to one worker and all other work on that file has stopped.

## 4. Dispatch layer work

When delegation is useful, run active workstreams in parallel:

- frontend: `implement-frontend-phase`
- API/BFF: `implement-api-phase`
- backend/core: `implement-backend-phase`

Give each worker the exact phase spec, acceptance criteria, agreed contracts, allowed paths, relevant existing changes, and validation commands. Workers return evidence and blockers without concurrently editing `validation.md`.

Frontend may build contract-independent presentation while the API contract is pending, but it must not invent DTOs. Integrate generated clients only after the actual OpenAPI export exists.

## 5. Coordinate changes and integrate

A contract change after parallel work begins requires:

1. pausing affected integration
2. updating the phase spec through the coordinator
3. notifying affected workers
4. updating Pydantic/OpenAPI before frontend integration
5. regenerating Orval through the frontend owner
6. rerunning affected tests and builds

Wait for workers, review their diffs/evidence, and verify layer boundaries, generated contracts, typed API-to-core calls, Yuno adapter isolation, request IDs, error mapping, idempotency, and webhook state transitions where applicable.

Apply only small integration fixes. Route substantial layer corrections back to the responsible worker.

## 6. Validate and record evidence

Run every applicable item in `validation.md`, including affected baseline gates:

```bash
uv run ruff check .
uv run pytest
pnpm lint
pnpm build
```

Regenerate and verify Orval after OpenAPI changes. Browser-test rendered flows and inspect console/network errors. Keep credentialed Yuno tests separate and never substitute production access.

The coordinator updates `validation.md`:

- `[x]` only for executed or directly inspected evidence
- exact commands or tools used
- `[ ]` plus a concise blocker for unresolved work
- separate frontend, API, backend, and integration results

Review the complete diff for secrets, PAN/CVV, sensitive payloads, manual generated-file edits, contract drift, architecture violations, overlapping shared-file changes, and unrelated work.

## 7. Report completion

Summarize the delivered journey, changed layers/files, contracts, shared decisions, checks and browser flows, external limitations, fallback, branch/Issue/PR state, and remaining blockers. Recommend `deep-review` when useful and `finish-phase` only when all required gates pass.
