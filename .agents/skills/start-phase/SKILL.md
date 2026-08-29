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

- **DONE:** a phase pull request with the required validation evidence is merged into the remote default branch.
- **REVIEW:** a phase pull request is open.
- **ACTIVE:** the remote phase branch exists and no pull request is open or merged, including recovery after a pull request was closed without merge.
- **BLOCKED:** a dependency is not DONE or a declared conflicting phase is ACTIVE/REVIEW.
- **READY:** dependencies are DONE, no declared conflict is active, and no remote branch or pull request of any state already represents the phase.

If the user names a phase, require it to be READY. Otherwise choose a READY phase that best advances the P0 demo, using phase number only as a tie-breaker. Report concrete blockers when none is ready.

Refresh remote state immediately before claiming. Create the new branch with an operation that fails when the ref already exists; never update an existing branch during the claim. If `phase/NN-{slug}` already exists, coordinate with its owner instead of overwriting it. If only a closed-unmerged pull request remains, do not treat the phase as READY; route recovery through `finish-phase`, which may reopen it or request an explicit decision about a replacement review.

## 4. Resolve scope and authority

An explicit request to start the selected phase authorizes its branch, workspace, planning commit, and normal push. Create a tracking Issue only when the user explicitly asks for one; do not interrupt the phase start merely to offer it. Ask only when the phase, scope, or owner is ambiguous.

Before writing, report:

- selected phase, included scope, exclusions, dependencies, conflicts, gate, and fallback
- creation of `phase/NN-{slug}`, the planning commit, and an optional `[Fase NN] Nome` tracking Issue only when requested
- validation appropriate to the affected frontend, API, backend, integration, browser, and payment risks

Do not infer deployment, production access, financial mutations, or unrelated infrastructure.

If a global decision is unresolved, use `manage-shared-specs`. A small decision directly required by this phase may be carried in the phase branch when nothing else must depend on it before merge. A broad or unrelated update, or a supporting phase that must start first, uses a short-lived documentation branch. Active phases do not need to finish first.

## 5. Prepare the local branch and workspace

1. Refresh the remote default branch, dependencies, conflicts, and existing phase branches/pull requests.
2. Create the local `phase/NN-{slug}` from the latest remote default branch. Do not publish an empty remote branch.
3. Use the current checkout when it is clean and can switch safely to the phase branch. Use a sibling worktree such as `../yuno-kickstart-phase-NN-{slug}` when another branch must remain checked out or parallel local work needs isolation.
4. Create `docs/project-specs/YYYY-MM-DD-NN-{slug}/` in the selected workspace.

If local setup fails, preserve or remove only the local resources within the user's request. No remote claim exists until the planning commit is published.

## 6. Write the phase specification

Create these files in the phase directory. Keep them to a few decision-complete bullets for a narrow phase; omit non-applicable contract, layer, and risk details.

### `requirements.md`

Record:

- objective, target user, and user-visible outcome
- included/excluded scope, priority, assumptions, risks, and fallback
- dependencies, conflicts, gate, branch, and tracking Issue when used
- owner GitHub login or team contact, especially when no tracking Issue exists
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
- any temporary wait on a prerequisite discovered after this phase started
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

Review the diff, stage only the phase planning files and any explicitly approved shared-spec clarification, and commit `Start Fase NN: Nome`. Refresh dependencies, conflicts, remote branches, and pull requests once more. Publish the planning commit by creating the new remote `phase/NN-{slug}` ref with an operation that fails if the branch exists. This single push claims the phase and exposes its owner/spec together.

If another developer created the branch first, preserve the local planning commit, report the competing claim, and coordinate instead of overwriting it. After a successful push, refresh declared conflicts again before implementation. Two conflicting refs can be created concurrently; if that happens, both claims stop until their owners choose which phase proceeds. Preserve the other planning-only branch until its owner explicitly releases it after inspection.

When the user requested a tracking Issue and Issues are available, create or reuse `[Fase NN] Nome`, assign the owner, and record the branch, result, dependencies, conflicts, gate, planning path, and commit. Do not add attempt UUIDs or synthetic lifecycle fields.

Do not deploy, merge a pull request, apply a remote migration, or perform a Yuno financial operation.

## 8. Report

Report the phase, priority, branch, workspace, planning commit, spec directory, optional Issue, dependencies/conflicts, ownership, contract gates, validation, fallback, any shared decision carried by the phase, and unresolved prerequisites. Direct cross-layer implementation to `implement-phase`.
