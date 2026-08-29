---
name: implement-phase
description: Coordinate a multi-layer Yuno × Nauta roadmap phase across frontend, API, and backend workers, then integrate and validate the vertical slice. Use for whole-phase or cross-layer implementation; use the layer-specific implementation skills for isolated work.
---

# Coordinate implementation of a Yuno × Nauta phase

Own scope, contracts, shared files, integration, and validation while independent workers implement non-overlapping application layers.

## 1. Resolve the phase

Read `AGENTS.md`, then inspect the current branch, worktree, `git status`, installed skills, and task-relevant MCP servers.

- Expected branch: `phase/NN-{slug}`, using the exact roadmap `Slug`
- Expected spec: `docs/project-specs/YYYY-MM-DD-NN-{slug}/`

Do not implement from `main`. Locate exactly one spec directory whose number and slug match the branch. If none or several match, stop and report the ambiguity.

Read completely:

1. `docs/project-specs/mission.md`
2. `docs/project-specs/tech-stack.md`
3. `docs/project-specs/roadmap.md`
4. `docs/decisions/challenge-plan.md`, when present
5. the phase `requirements.md`
6. the phase `plan.md`
7. the phase `validation.md`

Preserve unrelated and pre-existing changes. Identify the active P0/P1/P2 slice, acceptance criteria, non-goals, external dependencies, fallback, and the frontend, API, and backend workstreams actually required.

Refresh shared GitHub state before implementation. Require:

- the remote `phase/NN-{slug}` branch to exist and match the phase spec
- exactly one open `[Fase NN] Nome` coordination issue, assigned to the current phase owner
- the Issue's `Owner: @login` to match its sole assignee and the authenticated GitHub login
- the roadmap number, heading name, `Slug`, dependencies, conflicts, and gate to match the immutable metadata recorded when the phase was claimed
- the exact published planning commit recorded by `start-phase` to be an ancestor of the remote phase tip, with its recorded spec path present
- every declared dependency to be `DONE`
- no declared conflicting phase to be `IN_PROGRESS`, `REVIEW`, or `DRIFT`
- no merged phase pull request
- local history to contain the current remote phase history without divergence

Ordinary implementation requires shared state `IN_PROGRESS`. Continue from `REVIEW` only when the current request explicitly asks for changes to its open pull request. A handoff is valid only after the Issue assignee and `Owner: @login` agree and an Issue comment records the explicit transfer. Stop on a missing claim, claimant mismatch, branch/Issue disagreement, closed-unmerged pull request, inaccessible remote state, or any other `DRIFT`; do not adopt or recreate a claim implicitly.

Before any review-follow-up edit or delegation, require permission to create and conditionally release the coordination mutex and to convert the canonical pull request to draft or an equivalent repository-enforced merge block. Acquire the mutex, refresh the complete phase lifecycle and head, and reselect state. If the pull request merged, release the mutex and stop; route remote reconciliation to `finish-phase`. Otherwise establish the merge block, record its exact unblock action on the Issue, refresh and verify the same head and Issue attempt, then release the mutex in a finally step. Do not edit when merge blocking or its later unblock action is unavailable.

## 2. Make parallel execution safe

Before dispatching work, confirm the phase specification contains two decision-complete contract gates:

- **HTTP gate, owned by API:** HTTP method, `/v1` route, request/response fields, status codes, error semantics, Pydantic schemas, and OpenAPI output consumed by Orval
- **Application gate, owned by backend/core:** import path, public symbol names, async/sync call style, construction/dependency-injection method, and plain typed service inputs, outputs, and application exceptions that the API maps to and from Pydantic DTOs
- which layer owns webhook authentication, event processing, persistence, and provider calls
- the generated OpenAPI-to-Orval handoff when browser contracts change
- for checkout work, whether the phase ends at session/SDK initialization or includes token submission, server-side payment creation, and a defined immediate or webhook-confirmed result

Resolve contract gaps in the phase specification before workers independently encode incompatible assumptions. Never let the frontend hand-copy a provisional API DTO.

Assign one writer to every path. Default ownership is:

- frontend worker: `frontend/**`, including generated Orval files that must never be edited manually
- API worker: `api/**`, including Pydantic/OpenAPI source
- backend worker: `backend/**`
- coordinator: the active `docs/project-specs/YYYY-MM-DD-NN-{slug}/**` directory and exact cross-layer fixtures or shared paths assigned in `plan.md`

Treat `docs/project-specs/mission.md`, `docs/project-specs/tech-stack.md`, `docs/project-specs/roadmap.md`, and `docs/decisions/challenge-plan.md` as exclusively owned by `manage-shared-specs`, and `CHANGELOG.md` as exclusively owned by `changelog`; never edit them from a phase. Treat other `docs/**`, excluding the active dated phase-spec directory, plus `README.md`, `AGENTS.md`, `.env.example`, `.codex/**`, root workspace/configuration and lock files, checked-in OpenAPI snapshots outside layer directories, and `docker-compose.yml` as global shared paths. They are read-only by default during parallel phases. Assign one of those other exact paths only when the phase plan proves exclusive ownership through the roadmap conflict graph and current GitHub state; otherwise defer it to a serialized task.

Record every exception in `plan.md` before delegation. Do not give two concurrent workers or phases write access to the same file. Layer workers report required shared-file or cross-layer changes to the coordinator rather than making them implicitly.

Serialize dependency changes that touch multiple ownership scopes. Before delegation, assign one owner for both the package manifest and lockfile update, or let the coordinator perform the install; never let a layer worker update its manifest while another writer concurrently owns the resulting lockfile.

If an active workstream touches Yuno and the Yuno MCP is absent, follow the project setup/discovery rules before implementation. Use the official documentation fallback only when MCP setup or session restart cannot be completed in the current environment, and record that limitation.

## 3. Dispatch layer work

When delegation is available, launch one worker for each active layer in parallel:

- frontend uses `implement-frontend-phase`
- API/BFF uses `implement-api-phase`
- backend/core uses `implement-backend-phase`

Give each worker the exact phase spec, acceptance criteria, frozen contracts, allowed paths, relevant existing changes, validation commands, and the instruction to return evidence and blockers without editing shared validation records. For review follow-up, also provide the refreshed proof that the canonical pull request is draft or equivalently merge-blocked.

The backend can proceed from its frozen application-service contract. The frontend can build presentation and interaction concurrently, but API-bound integration and Orval regeneration must wait for API tests and the actual OpenAPI export. If the HTTP contract is not yet materialized, let the frontend complete contract-independent work and hold generated-client integration at an explicit checkpoint rather than inventing types.

If delegation is unavailable, apply the same layer skills sequentially in dependency-aware order while preserving their ownership boundaries. Do not duplicate their stack-specific instructions in this coordinator.

## 4. Coordinate checkpoints

Monitor worker progress and unblock only in-scope issues. A contract change after parallel work begins requires:

1. pausing affected integration work
2. updating the phase specification through the coordinator
3. notifying every affected layer
4. updating Pydantic/OpenAPI first
5. having the frontend owner regenerate the Orval client
6. rerunning affected tests and builds

Do not silently broaden scope or allow a worker preference to redefine product behavior, payment semantics, architecture, provider choice, or a data/security boundary.

Never authorize a deployment, production access, remote migration, environment-variable mutation, or payment/refund/cancel/capture operation merely because a worker requests it. Such actions require explicit current user scope.

## 5. Integrate the vertical slice

Wait for all active workers. Review their diffs and evidence, then verify:

- each worker stayed inside assigned paths
- API Pydantic schemas and generated TypeScript clients agree
- FastAPI calls typed backend services directly without a new network hop
- API DTOs do not leak into the backend domain and Yuno transport models do not leak across the application
- frontend code calls only FastAPI except for the official Yuno browser SDK boundary
- shared request IDs, error mapping, idempotency, and webhook state transitions remain coherent where applicable

Apply only the smallest integration fixes necessary. Route a substantial layer-specific correction back to the responsible worker rather than absorbing it into the coordinator.

## 6. Validate and record evidence

Run every applicable item in `validation.md`, including the baseline gates for affected layers:

```bash
uv run ruff check .
uv run pytest
pnpm lint
pnpm build
```

Run commands from the correct repository or package directory. After a changed OpenAPI contract, require the frontend owner to regenerate Orval, then verify the generated diff and build. If the coordinator must rerun mutating codegen, record a temporary ownership transfer in `plan.md` and ensure frontend work is no longer concurrent. For rendered changes, execute the Playwright user-flow smoke test and inspect console and network errors with Chrome DevTools as required by `AGENTS.md`.

Independently rerun the integration gates rather than treating worker reports as sufficient. The coordinator alone consolidates worker evidence in `validation.md`:

- `[x]` only for an executed or directly inspected criterion
- the command, tool, or evidence used
- `[ ]` plus a concise blocker for unresolved work
- separate frontend, API, backend, and integration results

Inspect the complete diff for secret exposure, PAN/CVV or sensitive payloads, accidental generated-file edits, contract drift, architecture violations, and unrelated changes.

## 7. Report completion

Summarize the delivered user journey, workstreams completed, contract decisions, files or domains changed, integration outcome, checks and browser flows executed, failed or skipped external gates, credential/sandbox dependencies, fallback behavior, coordination issue, remote phase branch, and remote actions performed by this skill, which should normally be none.

Recommend `deep-review` for a pre-merge audit and `finish-phase` only when every required layer and integration criterion passes.
