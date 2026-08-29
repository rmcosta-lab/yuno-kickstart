---
name: manage-shared-specs
description: Initialize or update the Yuno × Nauta mission, tech stack, roadmap, and challenge decision through an ordinary documentation or phase pull request. Use for project-wide decisions; do not use for dated per-phase specifications or implementation.
---

# Manage shared Yuno × Nauta specifications

Keep the project-wide baseline useful without turning documentation into a coordination system. This skill may change:

- `docs/project-specs/mission.md`
- `docs/project-specs/tech-stack.md`
- `docs/project-specs/roadmap.md`
- `docs/decisions/challenge-plan.md`, after the challenge is known

Global specs are living documents during the hackathon. Active phases do not block an update, but affected developers must be told about decisions that change their assumptions.

## 1. Read the current baseline

Read `AGENTS.md` and every existing target file completely. Inspect the current branch, worktree, remote default branch, open pull requests, and active remote phase branches. Compare those branches with the default branch when they may already edit a requested shared file. Preserve unrelated changes.

Use authenticated GitHub access when the task includes publication. Stop when the remote repository or default branch cannot be read, or when another open pull request edits the same lines and the changes cannot be coordinated safely.

Choose the smallest suitable publication path:

- Include a small, directly required specification change in the active phase pull request when nothing else must depend on it before that pull request merges.
- Use a short-lived branch such as `docs/specs-{topic}` for initial specs, broad reorganization, a change unrelated to one phase, a decision that other active phases need, or a supporting phase that must enter the roadmap before the current phase finishes.
- Update an existing open specification pull request when it has the same owner and purpose; otherwise coordinate rather than overwriting it.

Create a dedicated specs branch from the latest remote default branch, never from a phase branch. Use a clean default-branch checkout or a separate worktree so phase commits and uncommitted changes cannot enter the specs pull request.

Do not create a fixed specs branch, coordination mutex, attempt UUID, or special specs Issue.

## 2. Confirm the decision

Present the current baseline, requested change, affected active phases, and unresolved decisions. Ask only what is needed to establish:

1. product intent: target user, problem, value, P0 journey, non-goals, and demo success
2. architecture: whether the `AGENTS.md` defaults remain valid and why any deviation is justified
3. roadmap/challenge: phase outcomes, dependencies, conflicts, gates, and announced challenge requirements

Do not infer a product pivot, new infrastructure, production access, or financial operation. A developer preference is not enough to change a shared architecture or data/security boundary. Require approval from the user or designated team lead; when neither exists, require agreement from every affected phase owner and stop on disagreement.

When a change affects an active phase, route its `plan.md` update through that phase's coordinator and record the decision in the body of whichever pull request carries it. Tell affected owners to refresh their branch. Pause only integration work that depends on the unsettled decision.

## 3. Edit the shared files

### `mission.md`

Record the problem, target user, one-sentence value proposition, P0 journey and success signal, included scope, non-goals, P1/P2 priorities, assumptions, risks, and fallback.

### `tech-stack.md`

Record accepted frontend, API/BFF, backend/core, data, Yuno, optional AI, testing, and deployment decisions. Treat `AGENTS.md` as the default, explain accepted deviations, and link a decision record when one exists.

Do not copy transient dependency versions that belong in manifests and lockfiles. Adding a compatible library usually needs only a manifest change; update `tech-stack.md` when the choice changes a shared architectural, operational, or provider decision.

### `roadmap.md`

Keep phases outcome-oriented and vertical:

```markdown
### Fase 04 — Resultado da fase

Slug: resultado-da-fase
Depends on: 02
Conflicts with: none
Gate: evidência observável mínima para enviar a fase à revisão
```

Require unique numbers and slugs, lowercase kebab-case slugs, known dependency/conflict IDs, no self-reference, no dependency cycle, and a concrete gate. Treat conflicts as bidirectional.

Future unstarted phases may be added, removed, or reorganized. Do not silently rename, remove, or weaken the gate of an active or merged phase. Use an explicit clarification for a small correction. When an active phase discovers a material prerequisite, publish the supporting phase through a dedicated specs pull request based on the remote default branch, record the temporary wait in the active phase plan/Issue, and resume after the prerequisite phase pull request merges. If the original outcome or gate is no longer valid, move the remaining outcome to a follow-up phase instead of claiming the original phase complete.

Do not put status, owners, branches, Issues, pull requests, or completion markers in the roadmap.

### `challenge-plan.md`

Create or update this file only after the challenge is announced. Include problem, target user, value proposition, demo journey, P0 scope, non-goals, required Yuno and optional AI capabilities, data/API changes, risks, and fallback. Version proposed routes under `/v1` and distinguish facts from assumptions and credential/sandbox dependencies.

Verify current Yuno behavior with the official Yuno MCP or official machine-readable documentation. Never guess provider contracts.

## 4. Validate and publish

Review the complete diff and check for secrets, personal data, dynamic phase status, and unsupported provider claims. Self-review repository prose. Use `writing-guidelines` when the documents will be published externally or the user explicitly requests a prose audit. Validate the roadmap graph only when it changed.

Stage only intended files and use a descriptive commit such as `Update shared project specifications`. Before pushing, refresh the remote branch and relevant open pull requests. Resolve ordinary conflicts without force-pushing or overwriting another developer's work.

When a dedicated pull request is needed:

- head: the short-lived documentation branch
- base: the remote default branch
- title: `[Specs] <concise decision>`
- body: decisions, affected files/phases, validation, assumptions, and sources

When only one phase needs the change and nothing else must depend on it before merge, the phase coordinator records the decision and impact in both `plan.md` and the phase pull-request body instead of opening a second pull request. A dedicated specs pull request takes precedence when another active phase needs the decision or a supporting prerequisite phase must be added before the current phase can finish.

Do not push the default branch directly. Merge only when the user explicitly requests it and repository checks and approvals pass. After merge, refresh affected phase branches; delete short-lived branches only when safe and authorized.

## 5. Report

Report the branch and pull request, files changed, decisions made, affected phases, roadmap validation, sources consulted, checks run, and any coordination still required. Confirm that no implementation, deployment, production access, remote migration, financial operation, or force-push occurred unless separately requested.
