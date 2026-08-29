---
name: start-phase
description: Claim and specify an eligible Yuno × Nauta roadmap phase through shared GitHub coordination, or explicitly reconcile its coordination mutex or incomplete claim. Use for phase start/specification and claim recovery; do not use for implementation.
---

# Start a Yuno × Nauta phase

Claim one eligible roadmap phase without implementing it. Treat the roadmap as the static dependency graph and GitHub as the shared runtime state. A phase number is an identifier, not an implicit dependency or queue position.

Preserve the architecture, security, and hackathon priorities from `AGENTS.md`. Make a cross-layer phase executable by independent frontend, API, and backend workers without overlapping file ownership.

## 1. Read project and coordination context

If the user explicitly requests reconciliation of `coordination/phase-claim-lock`, enter the stale-mutex procedure in Section 6 before enforcing phase-specification prerequisites. Read `AGENTS.md` and remote GitHub coordination facts, but do not require `docs/project-specs/` to exist; this makes a mutex left by failed specs bootstrap recoverable.

For phase selection, claim, or incomplete-claim repair, read these files completely:

1. `AGENTS.md`
2. `docs/project-specs/mission.md`
3. `docs/project-specs/tech-stack.md`
4. `docs/project-specs/roadmap.md`
5. `docs/decisions/challenge-plan.md`, when the challenge has been announced and the file exists

Inspect `git status`, the current branch, configured remotes, existing branches, and `git worktree list --porcelain`. Preserve unrelated changes and do not modify anything yet.

Run the task-relevant MCP discovery required by `AGENTS.md`. Confirm that the official GitHub MCP is enabled and authenticated in the current environment, identify the repository and its remote default branch, fetch its current state, and make one harmless read-only GitHub call. The tool and credentials must allow reading, creating, updating, assigning, unassigning, closing, and reopening coordination Issues; create-only Git ref creation, including recreation at an exact authoritative SHA; fast-forward-only publication to an existing ref; and conditional compare-and-delete of only the explicitly authorized short-lived mutex or verified empty abandoned/canceled claim using its expected old SHA. Branch protection must not make those lifecycles impossible to complete. An authenticated equivalent may be used only when it provides the same Issue, pull-request, create-only ref, fast-forward publication, and conditional ref-deletion guarantees.

The remote default branch and GitHub Issue, branch, and pull-request state are authoritative for distributed coordination. Inspect the fixed remote branch `refs/heads/docs/project-specs` and its Issue/PR as well. Local branches and worktrees are only additional diagnostics.

Stop and report the prerequisite when:

- the remote repository or remote default branch cannot be read
- the remote default branch has no baseline commit
- authenticated shared GitHub access is unavailable
- a required specification file is missing from the remote default branch; use `manage-shared-specs` before claiming a phase
- remote branch `refs/heads/docs/project-specs` or an unreconciled shared-specs Issue/pull request indicates a global specification update is active
- unrelated changes would be captured by the phase
- the challenge brief or a product decision required to scope the phase is unavailable

Keep references to the future `docs/project-specs/` files. Do not remove them merely because the directory has not been created yet. A phase cannot bootstrap its own roadmap because its slug, graph eligibility, and canonical ref all depend on that roadmap already existing.

## 2. Parse the roadmap dependency graph

Roadmap phase headings use `### Fase NN — Nome`. Every phase must declare these static fields directly in its section:

```markdown
### Fase 04 — Nome

Slug: nome
Depends on: 02
Conflicts with: none
Gate: evidência observável mínima para enviar a fase à revisão
```

Use the exact `Slug` value in every branch, worktree, Issue field, pull request, and spec path. Require lowercase ASCII kebab-case matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`; never derive a second slug from the phase title.

Use `none` explicitly for a phase with no dependencies or conflicts. `Depends on` contains only genuine prerequisites. Do not infer that Fase 04 depends on Fase 03 from numbering alone. `Conflicts with` names phases that cannot be active at the same time because they contend for an intentionally serialized resource, shared file, or decision. Treat every conflict edge as bidirectional even if declared in only one phase.

Stop on duplicate phase numbers or canonical branch names, an invalid or missing `Slug`, unknown dependency or conflict IDs, self-dependencies, self-conflicts, dependency cycles, an empty or missing `Gate`, or malformed metadata. Do not silently invent an execution order.

Keep the roadmap static: do not append `✅`, status labels, assignees, branch names, or other mutable execution state to it. Phase completion comes from the shared GitHub lifecycle below. Once a phase has any coordination Issue, branch, planning record, or pull request, treat its number, heading name, slug, dependencies, conflicts, and gate as immutable. A mismatch between the roadmap and recorded phase metadata is `DRIFT`, not a new phase claim.

## 3. Reconstruct shared phase state

For every phase, inspect:

- every open or closed coordination Issue with the exact title `[Fase NN] Nome`, including its attempt and outcome fields
- the remote branch `phase/NN-{slug}`
- open, closed-unmerged, and merged pull requests whose head is that branch
- the published planning commit and phase spec path recorded by the Issue
- dependency and conflict states
- the pull request's base branch and merge state

Apply `DRIFT` first whenever facts contradict the protocol. Otherwise derive state in this precedence order; do not maintain a second mutable status field in the roadmap:

| State | Required shared facts |
| --- | --- |
| `DRIFT` | Shared facts disagree, including changed frozen roadmap metadata, duplicate Issues or pull requests, a branch without a consistent Issue, an assigned Issue without its branch, a missing published planning commit/spec, any closed-unmerged phase pull request, a closed Issue without a valid merged pull request or verified empty-claim abandonment/cancellation, a merge without required validation evidence, or a merged pull request whose Issue remains stale. |
| `DONE` | The canonical phase pull request is merged into the remote default branch after its required checks and phase validation passed, and the coordination issue is closed. |
| `CANCELED` | The sole Issue is closed and unassigned with `Outcome: CANCELED`, and audit evidence proves the phase never had a planning commit, pull request, or unique work and has no branch. This terminal state never satisfies a dependency. |
| `REVIEW` | Exactly one phase Issue is open and assigned, the remote phase branch contains the published planning commit and spec, and exactly one pull request from it is open against the remote default branch, with no other phase pull request. |
| `IN_PROGRESS` | Exactly one phase Issue is open and assigned, the remote phase branch contains the published planning commit and spec, and no pull request of any state exists for this claim. |
| `BLOCKED` | The phase is otherwise unclaimed, but a dependency is not `DONE` or a declared conflict is active. |
| `READY` | Every dependency is `DONE`; no declared conflicting phase is `IN_PROGRESS`, `REVIEW`, or `DRIFT`; no remote phase branch or phase pull request exists; and the Issue is absent, uniquely open and unassigned, or uniquely closed and unassigned with a verified `Outcome: ABANDONED` empty-claim audit. |

A remote phase branch is the exclusive claim lock. Even an incomplete claim with only that branch is reserved and must be reconciled as `DRIFT`; it is never `READY`.

`ABANDONED` releases one empty attempt and allows the same phase to become `READY` or `BLOCKED` again. `CANCELED` retires that empty phase identity permanently. Represent any replacement outcome with a new roadmap phase; never reactivate or silently rename a canceled phase.

A closed-unmerged pull request is recovered only by reopening that same canonical pull request through the explicit `finish-phase` recovery mode after its branch and validated head are restored. Until reopening succeeds it remains `DRIFT`. Never create a replacement pull request; if repository policy prevents reopening, report that external blocker and preserve the claim.

## 4. Select an eligible phase

Only a phase in `READY` may be claimed.

- If the user names a phase, verify that exact phase is `READY`.
- Otherwise, select the lowest-numbered phase among the current `READY` set.
- Never select “the first numbered phase” without evaluating dependencies and shared claims.
- If no phase is `READY`, report each incomplete phase with its state and concrete blocker.

Even when a phase's own reducer returns `READY`, do not claim it while the shared-specs workflow is active or unreconciled.

This allows Fase 04 to start as soon as its own dependencies are `DONE`, even while unrelated Fases 01 or 03 remain active.

Frame the selected phase according to the hackathon priority:

1. **P0:** one compelling vertical demo journey
2. **P1:** loading/error states, observability, graceful fallback, visual polish, and demo documentation
3. **P2:** AI, Redis, workers, richer analytics, or extra payment paths only after P0 works

Tell the user the selected phase, target result, included scope, exclusions, gate, dependencies, conflicts, affected layers, and fallback.

## 5. Confirm the claim

Before any write, use the available structured question tool when possible. Ask at most these three grouped questions:

1. **Scope and approach:** keep the roadmap scope, non-goals, architecture, and stack, or request a global/static adjustment?
2. **Shared claim:** authorize the short-lived create-only claim mutex and its release, creation of the create-only remote phase branch, creation or assignment of the coordination Issue, and publication of the planning commit to that branch?
3. **Validation:** use the roadmap gate plus the applicable Python, frontend, OpenAPI, browser, and payment-security checks, or add criteria?

Put the recommended default first and preserve free-form answers. Do not infer scope expansion, production access, financial mutations, deployment, or new infrastructure from an implementation preference.

If the user requests a global/static adjustment, stop before creating any ref and route the change to `manage-shared-specs`. Resume phase selection only after that specification pull request is merged and reconciled. `start-phase` may clarify a phase plan within already accepted metadata, but it must not diverge from or rewrite the global roadmap.

## 6. Claim the phase atomically

After confirmation, use `refs/heads/coordination/phase-claim-lock` as a short-lived global mutex for only the critical claim transaction. This prevents two developers from concurrently claiming different phases whose conflict was not visible to either initial read.

Claim it in this order:

1. Resolve the exact current commit SHA of the remote default branch.
2. Create the mutex ref at that SHA with a create-only Git ref operation. If it already exists, stop and report the active or stale claim transaction; never wait and never delete it based only on age.
3. While holding the mutex, refresh the remote default SHA, `refs/heads/docs/project-specs` lifecycle, and all phase Issue, branch, pull-request, dependency, and conflict facts.
4. If the selected phase is no longer `READY` or the shared-specs workflow is active/unreconciled, release only the empty mutex authorized in the confirmation and stop. Do not silently switch phases.
5. Create `refs/heads/phase/NN-{slug}` at the refreshed remote default SHA with a create-only Git ref operation that fails when the ref already exists.
6. Treat successful phase ref creation as the durable exclusive claim. Never use an operation that can update, overwrite, or force an existing ref.
7. Generate a new attempt UUID. Create the exact coordination Issue only when no exact-title Issue exists; reuse the unique open unassigned Issue; or reopen the unique closed Issue only when its prior attempt is a verified empty-claim `ABANDONED`, left no pull request, planning commit, unique work, or prior branch, and the only current phase ref is the empty ref created by this transaction. Never create a duplicate exact-title Issue.
8. Resolve the authenticated GitHub login, assign that exact login as the sole phase owner, preserve prior attempt history, and record `Current attempt: <uuid>`, `Outcome: ACTIVE`, `Owner: @login`, phase number, heading name, canonical slug, branch, base SHA, `Depends on`, `Conflicts with`, gate, and planned spec path in the Issue body. Add a retry comment when reopening an abandoned Issue.
9. Release the short-lived mutex as a required finally step. If release fails, report global coordination `DRIFT`; the phase branch and Issue remain reserved.

The mutex ref contains no unique work and exists only around the compare-and-create transaction. If the process stops while holding it, release it only through an explicit reconciliation after inspecting current GitHub activity and confirming no claim transaction remains active.

During a live claim, treat mutex release as a required finally step on every success, failure, or early-stop path after acquisition. If verified release fails, preserve all durable refs, report global coordination `DRIFT`, and never hide the blocked mutex.

If the create-only phase ref reports that the branch already exists, release the mutex, refresh shared state, and stop. If Issue creation, reopen, assignment, or update fails, leave the remote phase branch reserved, release the mutex if safely possible, report the partial claim as `DRIFT`, and provide the reconciliation needed. If a later local setup step fails, preserve the consistent remote claim. Do not delete a durable phase claim automatically.

### Reconcile a stale claim mutex

Enter mutex-reconciliation mode only when the user explicitly asks to repair `coordination/phase-claim-lock`. This mutex also protects shared-specs and changelog publication, orphan-lock repairs, implementation review blocking, and `finish-phase` publication, review recovery, merge, and remote reconciliation. Do not combine mutex reconciliation with any new phase, specs, implementation, changelog, or finish operation.

1. Identify the exact mutex ref and SHA, remote default SHA, authenticated maintainer, and all phase refs, Issues, and pull requests created around the interrupted transaction.
2. Verify that the mutex points to a commit reachable from the remote default branch and contains no unique commit.
3. Preserve and report any partial phase branch as its own durable claim; never delete it as part of mutex repair.
4. Require explicit confirmation that no `start-phase`, `manage-shared-specs`, `implement-phase`, directly invoked layer implementation, `changelog`, or `finish-phase` transaction using this mutex is still running and explicit authorization to delete only the mutex ref.
5. Delete the exact mutex, refresh GitHub state, and report the released SHA and every partial claim still requiring reconciliation.

If identity, ref contents, active-operation status, or authorization is uncertain, preserve the mutex and stop. Age alone is never evidence that deletion is safe.

### Reconcile an incomplete phase claim

Resume or abandon an incomplete claim only when the user explicitly requests reconciliation and the branch, commits, pull requests, Issue history, recorded base/planning SHA, and intended owner have been inspected. Require an explicit ownership confirmation or handoff before creating or assigning an Issue and worktree. Never infer ownership from possession of a local checkout.

Before acquiring the mutex, inspect the incomplete claim read-only, present the exact resume, abandonment, or cancellation actions and remote mutations that apply, and obtain the user's choice, ownership confirmation, handoff, and deletion authorization. Never wait for user input while holding the global mutex.

Perform the repair as its own mutex transaction, never together with a new phase claim:

1. after the choice, acquire `refs/heads/coordination/phase-claim-lock` with create-only semantics
2. refresh the incomplete phase branch, every exact-title Issue, pull request, commit, owner fact, and the current roadmap metadata; stop if the chosen repair no longer matches the refreshed facts
3. stop on duplicate Issues, multiple pull requests, a changed frozen field, a competing owner, unique work that does not match the intended phase, an unmatched pull request, or any other ambiguity; one closed canonical pull request may be inspected only to restore its exact branch head before routing to `finish-phase`
4. when the branch exists with unique commits or a pull request, preserve it; create or reopen only the single canonical Issue, generate a new recovery attempt UUID, assign the confirmed owner as sole assignee, and record `Current attempt: <uuid>`, `Outcome: ACTIVE`, `Owner: @login`, immutable metadata, exact branch tip, planning state, prior-attempt disposition, any required explicit owner-transfer comment, and an audit comment; if its sole pull request is closed-unmerged, do not resume implementation and route the restored claim to `finish-phase` PR recovery
5. when an empty branch has no planning commit or pull request, apply the preconfirmed resume, attempt-abandonment, or phase-cancellation choice; resume creates or reopens only the single canonical Issue, generates a new recovery attempt UUID, assigns the confirmed owner as sole assignee, and explicitly records `Current attempt: <uuid>`, `Outcome: ACTIVE`, `Owner: @login`, immutable metadata, exact branch tip, empty planning state, prior-attempt disposition, any required explicit owner-transfer comment, and an audit comment; abandonment or cancellation creates or reuses the single Issue, reuses its current attempt UUID or generates a recovery UUID when absent, records the prior owner, actor, reason, base SHA, and the chosen `Outcome: ABANDONED|CANCELED`, removes every assignee, closes it, and only then deletes that exact empty branch with explicit authorization
6. when an active Issue exists without its branch, recreate the deterministic ref with create-only semantics at the unique closed pull request's recorded head SHA or the last recorded branch tip when either exists; otherwise use the exact recorded planning SHA, or the recorded base SHA only when no later work ever existed; require the selected SHA to be reachable and consistent with all Issue and pull-request history, generate and record a new recovery attempt UUID with `Current attempt: <uuid>` and `Outcome: ACTIVE`, atomically assign the confirmed owner as sole assignee and update `Owner: @login`, preserve the prior attempt disposition, add the recovery audit and any required explicit owner-transfer comment, and stop without inventing a ref when no authoritative SHA exists
7. when only an incomplete Issue exists and no planning commit, pull request, or unique work ever existed, allow explicit attempt abandonment or phase cancellation by reusing its current attempt UUID or generating a recovery UUID when absent, recording its prior owner, actor, reason, and selected `Outcome: ABANDONED|CANCELED`, removing every assignee, and closing it
8. release the mutex as a required finally step on every path; if Issue repair, close, reopen, assignment, ref creation, or authorized empty-ref deletion fails, preserve every remaining durable fact and report `DRIFT`

Only after a resume transaction succeeds may the confirmed owner create the worktree or publish missing planning artifacts. A verified abandoned empty claim is unclaimed and may later be reclaimed by reopening its sole canonical Issue with a new attempt UUID. A canceled phase remains closed and is never selected again. Never let two repair sessions create, select, or reopen Issues outside the mutex, and never abandon or cancel a claim that has a planning commit, unique work, or a pull request.

To cancel a phase that has never been claimed, require an explicit cancellation request, acquire the mutex, refresh all phase and dependency facts, and verify that no Issue except one optional closed `ABANDONED` tombstone, branch, planning commit, pull request, or unique work exists. Create or reuse the sole Issue, generate a cancellation attempt UUID, record the immutable metadata, actor, reason, and `Outcome: CANCELED`, remove every assignee, close it, release the mutex in a finally step, and report every downstream dependency now blocked. Never use cancellation as a substitute for completing a dependency.

Do not depend on optional labels or a GitHub Project for correctness. They may mirror state for convenience, but the issue, branch, pull request, and remote default branch remain the source of truth.

## 7. Create the worktree and publish planning

Create a local branch that tracks the claimed remote branch and a dedicated worktree:

- branch: `phase/NN-{slug}`
- worktree: sibling directory `../yuno-kickstart-phase-NN-{slug}`
- spec directory inside that worktree: `docs/project-specs/YYYY-MM-DD-NN-{slug}/`

Write all phase files inside the new worktree, not the original worktree. If the sibling directory requires permission, request it instead of silently choosing another location.

After writing the planning artifacts:

1. review the complete diff
2. stage only the active phase specification
3. create `Start Fase NN: Nome`
4. reacquire the coordination mutex and refresh the exact Issue attempt, owner, phase ref, pull requests, frozen metadata, dependencies, and conflicts
5. stop without publishing if the attempt, owner, eligibility, branch tip, or another shared fact changed
6. update only the existing phase ref with a non-force, update-only fast-forward operation that rejects a missing or changed ref
7. while still holding the mutex, update the coordination Issue with the published spec path and planning commit
8. release the mutex as a required finally step on every path

The published planning commit makes scope and contracts visible before implementation begins. If commit, push, or Issue update fails, keep the remote claim and every unique commit, report its exact shared state, and do not represent the phase as consistently `IN_PROGRESS`.

Do not deploy, change remote infrastructure, apply a remote migration, merge a pull request, or call a Yuno financial operation.

## 8. Verify the shared challenge decision when required

Do not create or update `docs/decisions/challenge-plan.md` from a phase. When the challenge has been announced, require `manage-shared-specs` to publish this global decision before any challenge-specific phase can be claimed.

Read the merged file and verify that it includes exactly:

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

Version proposed routes under `/v1`. Confirm that the decision distinguishes facts, assumptions, sandbox or credential dependencies, and fallbacks. If a required decision is absent or stale, stop and direct the user to `manage-shared-specs`; do not repair it from the phase branch.

## 9. Write the phase specification

Create these files in the phase spec directory.

### `requirements.md`

- objective, target user, and user-visible outcome
- included and excluded scope
- declared dependencies, conflicts, assumptions, risks, and demo fallback
- coordination issue and claimed remote branch
- P0, P1, or P2 priority and traceability to the roadmap
- ownership across frontend, API/BFF, and backend/core
- two contract-first gates: an HTTP gate owned by API/Pydantic/OpenAPI for routes and DTO semantics, and an application gate owned by backend/core that fixes import path, symbol names, async/sync call style, construction/DI, typed service inputs, outputs, and exceptions
- the complete Yuno browser-to-server handoff and terminal phase outcome, such as session initialization only or token submission plus payment confirmation
- an ownership matrix with one writer per path: frontend owns `frontend/**`, API owns `api/**`, backend owns `backend/**`, and the coordinator owns the active phase spec directory plus exact shared paths proven exclusive by the conflict graph and current GitHub state
- `docs/project-specs/mission.md`, `docs/project-specs/tech-stack.md`, `docs/project-specs/roadmap.md`, and `docs/decisions/challenge-plan.md` as exclusively owned by `manage-shared-specs`, and `CHANGELOG.md` as exclusively owned by `changelog`; the coordinator owns only the active dated phase directory, while other documentation and root configuration remain read-only unless an exact exclusive exception is recorded
- any shared/root file also needed by another active phase, with that cross-phase write either represented by `Conflicts with` or deferred to a dedicated serialized task
- API, data, Yuno, AI, security, privacy, visual, and accessibility decisions that apply
- acceptance criteria that prove one coherent end-to-end slice

### `plan.md`

- small numbered task groups in dependency order
- separate HTTP and API-to-core contract gates before dependent parallel work when either interface is new or changing
- separate frontend, API, and backend workstreams that can run concurrently after their contracts are decision-complete
- an explicit integration group for OpenAPI generation, Orval regeneration, cross-layer tests, and the final browser journey
- one owner for every shared file; layer workers report requested shared changes to the coordinator instead of editing them concurrently
- no concurrent cross-phase ownership of the same shared/root file; use the declared conflict edge or a later serialized task
- a serialized dependency-install task with one explicit owner whenever a package manifest and a lockfile belong to different ownership scopes
- explicit files or domains where that improves clarity
- provider adapters instead of leaked external dictionaries or transport details
- tests near the behavior they verify
- OpenAPI regeneration after Pydantic contract changes
- final lint, test, build, browser, secret-review, and diff verification
- no deploy, production access, live payment mutation, or remote change beyond the confirmed coordination workflow without explicit authorization

### `validation.md`

- unchecked `- [ ]` criteria grouped by affected layer or risk
- separate evidence groups for frontend, API, backend, and cross-layer integration
- a method or command for every automatable criterion
- Python gates: `uv run ruff check .` and `uv run pytest`
- frontend gates: `pnpm lint` and `pnpm build`
- Orval regeneration and compile validation when OpenAPI changes
- browser smoke test plus console/runtime inspection for rendered UI changes
- mocked Yuno transports for ordinary tests and separately marked credentialed sandbox integration tests
- raw-body HMAC, idempotency, secret redaction, PAN/CVV, RLS, CORS, and authorization checks when applicable

Add other existing scripts such as type-check, unit, or e2e gates only when the repository defines them or the phase needs them. Keep checks proportional; do not require database, Yuno sandbox, AI, or browser checks from a phase that cannot exercise them.

## 10. Report the result

Report the phase, priority, shared state, coordination Issue, remote and local branch, worktree path, planning commit, spec directory, verified challenge decision when required, user decisions, dependencies and conflicts, active workstreams, ownership boundaries, HTTP and application contract gates, Yuno or external dependencies, fallback, and unresolved prerequisites.

State `IN_PROGRESS` only when the Issue, remote branch, owner, planning commit, and published spec path agree. Remind the user that cross-layer implementation begins with `implement-phase` from the phase worktree; a single-layer request may use the matching specialized implementation skill directly.
