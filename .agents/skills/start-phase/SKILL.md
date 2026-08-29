---
name: start-phase
description: Claim and specify an eligible Yuno × Nauta roadmap phase with its deterministic branch and lightweight GitHub coordination. Use for phase start and planning; do not use for implementation.
---

# Start a Yuno × Nauta phase

Prepare one eligible phase for implementation. Use a branch and pull request as the shared state; avoid mutexes, attempt identifiers, and recovery state machines.

## 1. Read project context

Read completely:

1. `AGENTS.md`
2. `docs/project-specs/mission.md`
3. `docs/project-specs/tech-stack.md`
4. `docs/project-specs/roadmap.md`
5. `docs/decisions/challenge-plan.md`, when present

Inspect `git status`, branches, worktrees, the remote default branch, open phase/specification pull requests, and Issues when available. Preserve unrelated changes.

Use authenticated GitHub access for remote coordination. Stop when the remote repository or default branch cannot be read, a required global spec is missing, unrelated changes would enter the phase, or a decision needed to scope the phase is unresolved.

## 2. Parse the roadmap

Each phase uses:

```markdown
### Fase 04 — Nome

Slug: nome
Depends on: 02
Conflicts with: none
Gate: evidência observável mínima para enviar a fase à revisão
```

Require unique numbers and slugs, lowercase kebab-case slugs, valid references, no self-dependency or self-conflict, no dependency cycle, and a concrete gate. Treat conflict edges as bidirectional. Phase numbers are identifiers, not implicit ordering.

Keep mutable status out of the roadmap. Do not silently rename, remove, or weaken the gate of a phase that already has a branch or pull request. Use a follow-up phase for a materially different outcome.

## 3. Select an eligible phase

Use this lightweight state model:

- **DONE:** a phase pull request is merged into the remote default branch.
- **REVIEW:** a phase pull request is open.
- **ACTIVE:** the remote phase branch exists without a merged pull request.
- **BLOCKED:** a dependency is not DONE or a declared conflicting phase is ACTIVE/REVIEW.
- **READY:** dependencies are DONE, no declared conflict is active, and no remote branch or open/merged pull request already represents the phase.

If the user names a phase, require it to be READY. Otherwise choose a READY phase that best advances the P0 demo, using phase number only as a tie-breaker. Report concrete blockers when none is ready.

Refresh remote state immediately before claiming. If `phase/NN-{slug}` already exists, coordinate with its owner instead of overwriting it. This branch-existence check is the practical claim; a small race is acceptable for a hackathon because concurrent branch creation allows only one winner.

## 4. Confirm scope

Before remote writes, confirm:

- selected phase, included scope, exclusions, dependencies, conflicts, gate, and fallback
- creation of `phase/NN-{slug}`, an optional `[Fase NN] Nome` tracking Issue, and the planning commit
- validation appropriate to the affected frontend, API, backend, integration, browser, and payment risks

Do not infer deployment, production access, financial mutations, or unrelated infrastructure.

If a global decision is unresolved, use `manage-shared-specs`. A small decision directly required by this phase may be carried in the phase branch; a broad or unrelated update should use a short-lived documentation branch. Active phases do not need to finish first.

## 5. Create the branch and worktree

1. Refresh the remote default branch, dependencies, conflicts, and existing phase branches/pull requests.
2. Create `phase/NN-{slug}` from the latest remote default branch without force or overwrite. Stop if it already exists.
3. When Issues are available, create or reuse one `[Fase NN] Nome`, assign the current owner, and record the branch, phase result, dependencies, conflicts, and gate. Do not add attempt UUIDs or synthetic lifecycle fields.
4. Create a tracking local branch and sibling worktree at `../yuno-kickstart-phase-NN-{slug}`.
5. Create `docs/project-specs/YYYY-MM-DD-NN-{slug}/` in that worktree.

If Issue creation or local worktree setup fails after branch creation, preserve the branch and report the partial setup. Repair it directly on the next attempt; do not create a second phase branch or a recovery protocol.

An explicitly abandoned empty claim may be deleted only after verifying that it has no unique commit or pull request and obtaining authorization for that exact branch deletion. Preserve any branch with work.

## 6. Write the phase specification

Create these files in the phase directory.

### `requirements.md`

Record:

- objective, target user, and user-visible outcome
- included/excluded scope, priority, assumptions, risks, and fallback
- dependencies, conflicts, gate, branch, and tracking Issue when used
- acceptance criteria for one coherent vertical slice
- affected frontend, API/BFF, backend/core, data, Yuno, AI, security, visual, and accessibility decisions
- the HTTP contract gate: route, request/response, status, and error semantics
- the application contract gate: import path, public symbols, construction, typed inputs/outputs, and exceptions
- the Yuno browser/server handoff and the phase's terminal user-visible result
- a one-writer ownership matrix for layer paths, the phase spec directory, generated files, manifests/lockfiles, and any shared files

Global specs are not exclusively locked. The phase coordinator may update them when directly required, but must record the reason and impact, check open pull requests touching those files, and notify affected phase owners. Layer workers request these edits through the coordinator.

### `plan.md`

Record:

- small task groups in dependency order
- contract decisions before dependent parallel work
- non-overlapping frontend, API, and backend workstreams
- one owner per path, including shared files and manifest/lockfile pairs
- OpenAPI/Orval generation and integration checkpoints
- tests near changed behavior and final lint/test/build/browser checks
- any shared stack or roadmap change, affected phases, communication required, and branch-refresh point
- no deployment, production access, live financial mutation, or unrelated remote change without explicit authorization

### `validation.md`

Use unchecked criteria grouped by affected layer or risk. Include applicable commands and evidence for:

```bash
uv run ruff check .
uv run pytest
pnpm lint
pnpm build
```

Add OpenAPI/Orval, browser, Yuno sandbox/mock, webhook, idempotency, secrets, RLS, CORS, and authorization checks only when the phase exercises them. Keep validation proportional.

## 7. Publish planning

Review the diff, stage only the phase planning files and any explicitly approved shared-spec clarification, and commit `Start Fase NN: Nome`. Refresh the remote branch and pull requests once more, then push normally without force.

Update the tracking Issue with the planning path/commit when an Issue exists. Do not deploy, merge a pull request, apply a remote migration, or perform a Yuno financial operation.

## 8. Report

Report the phase, priority, branch, worktree, planning commit, spec directory, optional Issue, dependencies/conflicts, ownership, contract gates, validation, fallback, any shared decision carried by the phase, and unresolved prerequisites. Direct cross-layer implementation to `implement-phase`.
