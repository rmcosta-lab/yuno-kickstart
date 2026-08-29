---
name: manage-shared-specs
description: Initialize or update the global Yuno × Nauta mission, tech stack, roadmap, and challenge decision through the fixed branch docs/project-specs. Use for serialized project-specification work before or between phases; do not use for per-phase specs or implementation.
---

# Manage shared Yuno × Nauta specifications

Create or update the project-wide specification baseline with one remote writer. This workflow owns only:

- `docs/project-specs/mission.md`
- `docs/project-specs/tech-stack.md`
- `docs/project-specs/roadmap.md`
- `docs/decisions/challenge-plan.md`, when the challenge is known

The fixed remote branch `refs/heads/docs/project-specs` is the create-only lock. The similarly named `docs/project-specs/` directory is a repository path, not the lock. Do not initialize the global files from `start-phase` or edit them concurrently from phase branches. This workflow does not own dated phase directories below `docs/project-specs/`.

## 1. Resolve the serialized task

Read `AGENTS.md` completely, then inspect the allowed files that already exist. Preserve their references when a file has not been created yet.

Run the GitHub MCP discovery and harmless read-only smoke test required by `AGENTS.md`. Require:

- an authenticated repository with a remote default branch and baseline commit
- permission to read, create, update, assign, unassign, close, and reopen coordination Issues and to read, create, update, reopen, draft, and mark ready pull requests
- create-only Git ref creation
- update-only, non-force fast-forward publication to an existing fixed ref
- conditional compare-and-delete of the short-lived mutex and fixed ref using their expected old SHA after each applicable verification gate
- branch protection that permits the fixed lock lifecycle without bypassing default-branch protection

Inspect:

- remote branch `refs/heads/docs/project-specs`
- every open or closed coordination Issue with the exact canonical title `[Specs] <full-base-sha>`
- open, closed-unmerged, and merged pull requests from the fixed branch
- local branches and worktrees
- every current or historical phase Issue, branch, planning record, and pull request, including closed and merged facts

Stop while any phase is `IN_PROGRESS`, `REVIEW`, or `DRIFT`; changing the graph or project-wide decisions underneath active work would invalidate its claim and contracts. The only exception is explicit restore-roadmap mode below: pause affected work, require one uniquely reconstructable frozen historical snapshot, and restore only that snapshot even when the phase's underlying lifecycle would otherwise be `IN_PROGRESS` or `REVIEW`. This exception may coexist only with lifecycle facts that can be preserved without interpretation or mutation: the single stale-open-Issue form backed by an authoritative merged pull request, or one uniquely identified paused incomplete claim with no duplicate Issue, branch, or pull request. Every other inconsistency still stops. Also stop when the fixed branch belongs to another owner without a recorded handoff, a specs pull request was closed without merge and has no recovery decision, or shared facts are duplicated or divergent. A missing or incomplete Issue may bypass only the ownership stop when the current request explicitly selects repair-orphan mode.

## 2. Select mode

Select modes in this precedence order: Reconcile, Recover review, Restore roadmap, Repair orphan, Resume, then Prepare. A higher-precedence match must never fall through to Resume.

- **Prepare:** remote branch `refs/heads/docs/project-specs` is absent, no earlier task is unreconciled, and this is either a new target/base SHA or a same-base retry with exactly one closed canonical Issue whose recorded outcome is `ABANDONED`.
- **Resume:** one consistent task exists with no pull request or exactly one open pull request; its sole Issue assignee and `Owner: @login` match the authenticated actor. A closed-unmerged pull request is not Resume. After a handoff, require the new assignee, updated owner field, and explicit transfer comment to all agree.
- **Repair orphan:** the fixed ref or its Issue exists without a consistent counterpart. Use only after an explicit repair request.
- **Recover review:** the fixed ref, Issue, and exactly one closed-unmerged pull request agree, no open or merged pull request exists, and the user explicitly requests reopening that same review.
- **Restore roadmap:** the user explicitly requests repair, the fixed ref is absent, affected work is paused, and every phase `DRIFT` consists of current roadmap fields differing from one uniquely reconstructable frozen historical snapshot, optionally combined with either one authoritative merged pull request whose sole Issue remained stale and open or one uniquely identified paused incomplete claim that this workflow leaves untouched.
- **Reconcile:** the canonical specs pull request for this target is merged, even when GitHub already auto-deleted its head branch.

In prepare or restore-roadmap mode:

1. resolve the exact current remote-default SHA
2. acquire `refs/heads/coordination/phase-claim-lock` at that SHA with a create-only operation
3. while holding the mutex, refresh all phase states, the fixed specs lifecycle, and every open or closed Issue with the exact canonical title; outside restore-roadmap mode, stop and release the mutex if a phase is `IN_PROGRESS`, `REVIEW`, or `DRIFT`; in restore-roadmap mode, stop unless affected work is paused and each `DRIFT` still has the same uniquely reconstructable frozen-field mismatch, with only the optional authoritative merged-PR/stale-open-Issue or uniquely identified paused incomplete-claim fact allowed; in every mode, stop if remote branch `refs/heads/docs/project-specs` now exists or canonical Issues are duplicated
4. create `refs/heads/docs/project-specs` at the refreshed remote-default SHA with a create-only operation
5. generate a new attempt UUID; create `[Specs] <full-base-sha>` only when no exact-title Issue exists, or reopen and reuse the single closed `ABANDONED` Issue when its prior attempt left no branch, pull request, unique commit, or unreconciled resource and the only current fixed ref is the empty ref created by this transaction
6. assign the authenticated GitHub login as sole owner
7. preserve the prior abandonment audit trail and record `Current attempt: <uuid>`, `Outcome: ACTIVE`, `Owner: @login`, base SHA, branch, requested files, and requested outcome; add a retry comment when reopening
8. release the short-lived mutex; report global coordination `DRIFT` if release fails while preserving the specs branch and Issue

Never create a second exact-title Issue for the same base SHA. If Issue creation or reopening fails after ref creation, preserve the ref as an incomplete lock, release the short-lived mutex if safely possible, and require explicit reconciliation. Never overwrite, force-update, or delete an unmerged fixed branch that contains a unique commit or pull request. Repair mode may delete only an empty orphan after its explicit verification and authorization gate.

In repair-orphan mode:

Before acquiring the mutex, inspect the orphan read-only, present the exact resume or abandonment actions and remote mutations, and obtain the user's choice, target, owner confirmation, any handoff, and authorization. Never wait for user input while holding the global mutex.

1. after the choice, acquire the same short-lived coordination mutex with a create-only operation and refresh the fixed ref, default branch, Issues, pull requests, commits, and worktrees; stop if the chosen repair no longer matches the refreshed facts
2. inspect the fixed ref's tip and diff against its recorded or reachable base
3. if unique commits or a pull request exist, never delete the ref; verify and apply the preconfirmed target, owner, and handoff, create or reopen the single canonical Issue as needed, generate a new recovery attempt UUID, assign the authenticated owner as sole assignee, record the prior attempt's recovery disposition plus `Current attempt: <uuid>`, `Outcome: ACTIVE`, and `Owner: @login`, and add an audit comment before resuming; if the owner changes, update the sole assignee and owner field together and add the preconfirmed explicit transfer comment
4. if an empty ref has no pull request, apply the preconfirmed choice: to resume, create or reopen the single canonical Issue as needed, generate a new recovery attempt UUID, assign the authenticated owner as sole assignee, preserve the prior attempt audit trail, and record `Current attempt: <uuid>`, `Outcome: ACTIVE`, `Owner: @login`, target, base, branch, and any required owner-transfer comment before any work; to abandon, create the canonical Issue if absent, reuse the current attempt UUID or generate a recovery UUID, record the prior owner, reason, and actor, set `Outcome: ABANDONED`, remove every assignee, and close the Issue before deleting only that empty ref
5. if only an incomplete Issue exists, apply the preconfirmed choice: for resume, select the exact fixed-ref SHA from a uniquely recorded prior branch tip or pull-request head when later work existed, otherwise use the exact recorded base SHA only after proving no later work ever existed; require that SHA to be reachable and consistent with the Issue history, stop without creating a ref when it is absent or ambiguous, then create the ref at that exact SHA with create-only semantics, generate a new recovery attempt UUID, reopen the Issue when needed, assign the authenticated owner as sole assignee, preserve the audit trail, and record `Current attempt: <uuid>`, `Outcome: ACTIVE`, and `Owner: @login` plus the selected SHA and any required owner-transfer comment before any work; for abandonment, reuse its current attempt UUID or generate a recovery UUID when absent, record the prior owner, set `Outcome: ABANDONED`, remove every assignee, and close the Issue
6. release the short-lived mutex and refresh shared state

Every repair-resume path must finish the Issue update successfully before implementation continues. If an Issue update, assignment, unassignment, reopen, or close fails, preserve the ref and stop; if ref recreation fails, preserve the Issue and stop. The closed `ABANDONED` Issue remains the sole canonical Issue for its base SHA. A later prepare on that unchanged base must reopen and reuse it with a new attempt UUID; it must not create a replacement. If the mutex cannot be acquired or released, ownership and contents cannot be established, or more than one exact-title Issue exists, preserve every fixed ref and stop. Never infer repair authorization from age.

In recover-review mode, acquire the mutex, refresh the Issue attempt, fixed ref, remote default, and every pull request, and verify the fixed tip equals the closed pull request's validated head. Reopen that same pull request, record the recovery audit on the Issue, and release the mutex in a finally step. Never create a replacement pull request. If the ref is missing, repair it first at the exact reachable pull-request head; if GitHub or repository policy cannot reopen the review, preserve the ref and report the external blocker.

After acquiring the short-lived mutex in any mode, treat its release as a required finally step on every success, failure, or early-stop path. If verified release fails, report global coordination `DRIFT` and do not hide the blocked mutex.

For prepare, resume, or restore-roadmap mode, create or reuse a tracking local branch in the dedicated sibling worktree `../yuno-kickstart-project-specs`.

Before changing local content for a generation whose pull request is open, acquire the coordination mutex, refresh the complete lifecycle, and reselect the mode. If it is already merged, release the mutex and switch to reconciliation without editing. Otherwise convert it to draft, or establish an equivalent repository-enforced merge block and record its exact unblock action on the Issue, before releasing the mutex; stop if the repository cannot prevent merge during the edit window or cannot later remove that block.

## 3. Confirm specification intent

Before editing, present the current baseline and unresolved decisions. Use at most three grouped questions:

1. **Mission:** confirm target user, problem, value proposition, P0 journey, non-goals, and demo success.
2. **Architecture:** keep the `AGENTS.md` stack and boundaries, or record explicit accepted deviations?
3. **Roadmap and challenge:** confirm vertical phases, dependency/conflict graph, gates, and the challenge decision when announced?

Do not infer product direction, challenge requirements, new infrastructure, production access, or financial operations. If the answers cannot define the requested files, stop with the missing decisions.

In restore-roadmap mode, do not ask for or accept new product scope. Present the historical evidence and exact restoration diff, require confirmation for that repair only, and leave every unrelated specification byte unchanged.

## 4. Write the shared files

### `docs/project-specs/mission.md`

Record:

- problem and target user
- one-sentence value proposition
- P0 demo journey and success signal
- included scope and explicit non-goals
- P1/P2 priorities
- assumptions, risks, and fallback

### `docs/project-specs/tech-stack.md`

Record the accepted frontend, API/BFF, backend/core, data, Yuno, optional AI, testing, and deployment decisions. Treat `AGENTS.md` as the default. Explain every accepted deviation and point to a decision record when one exists.

Do not duplicate transient dependency versions that belong in manifests and lockfiles. Verify unfamiliar or version-sensitive libraries with the required current official documentation before changing a decision.

### `docs/project-specs/roadmap.md`

Define outcome-oriented vertical phases, not separate frontend, API, and backend roadmaps. Every phase uses:

```markdown
### Fase 04 — Resultado da fase

Slug: resultado-da-fase
Depends on: 02
Conflicts with: none
Gate: evidência observável mínima para enviar a fase à revisão
```

Require:

- unique phase numbers and canonical branch names
- `Slug` matching `^[a-z0-9]+(?:-[a-z0-9]+)*$`
- `none` for an empty dependency or conflict list
- known IDs, no self-dependency or self-conflict, and no dependency cycle
- bidirectional interpretation of every conflict edge
- conflicts for phases that would write the same serialized shared file or depend on the same unsettled decision
- a concrete review gate

Before accepting a roadmap diff, compare the baseline section and recorded GitHub metadata for every phase that has any coordination Issue, branch, planning record, or pull request. From the first such fact onward, its `NN`, heading name, `Slug`, `Depends on`, `Conflicts with`, and `Gate` are immutable, and its section cannot be removed. Stop when the candidate changes any frozen field or when history cannot be matched unambiguously. Represent a changed outcome with a new phase number and dependency/conflict edges; do not rewrite historical identity or silently migrate coordination facts from this workflow.

Restore-roadmap mode is the narrow inverse: reconstruct each mismatched section from its canonical Issue metadata, published planning record, branch, and pull request; require those sources to agree; restore only the frozen fields or removed section; and reject additions, product edits, graph redesign, or any repair that would choose between conflicting histories. Do not close a stale phase Issue, create a missing Issue/ref, or otherwise repair an incomplete claim in this workflow. After the restoration is merged and reconciled, route those lifecycle corrections to `finish-phase` or `start-phase` respectively.

Keep the roadmap static. Do not add `✅`, assignees, branches, Issues, pull requests, or status fields.

### `docs/decisions/challenge-plan.md`

Create or update this file only after the challenge is announced. Include:

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

Version proposed routes under `/v1`. Distinguish facts, assumptions, sandbox or credential dependencies, and fallbacks. Before recording Yuno behavior, use the current official Yuno MCP documentation tool when available or the official machine-readable documentation fallback from `AGENTS.md`. Never guess provider contracts.

## 5. Validate and publish

Review the complete diff and run `writing-guidelines` on every changed prose file. Validate the roadmap graph and verify that no secret, credential, personal data, dynamic phase state, or unsupported provider claim was added.

Stage only the allowed files. Commit:

```text
Update shared project specifications
```

Immediately before remote publication, reacquire the coordination mutex and refresh the fixed ref, exact Issue attempt, remote default, all pull-request states, and any recorded merge block. If the pull request merged, an expected block disappeared, the ref disappeared, the attempt changed, or another generation appeared, do not push or recreate anything; release the mutex and reclassify the task. Update only the existing fixed ref with a non-force, update-only fast-forward operation that rejects a missing or changed ref. Then create or update one pull request:

- head: `docs/project-specs`
- base: remote default branch
- title: `[Specs] Update project specifications`
- body: decisions, changed files, graph validation, unresolved assumptions, external documentation used, and `Closes #<specs-issue>`

For an existing blocked pull request, publish its verified head and only then mark a draft ready or execute the recorded equivalent unblock action. Refresh the pull request and branch again before releasing the mutex. If unblock fails, keep the recorded block, report review-blocked state, and do not claim normal review. If a concurrent merge contains the published head, switch to reconciliation; if it merged an earlier head, preserve the newer branch/local commit, report `DRIFT`, and do not clean or delete it. Treat mutex release as a required finally step.

Normal mode stops in review. Merge only when the current user explicitly asks for the remote merge and all repository checks and approvals pass; perform the final refresh and merge while holding the same mutex, then continue with generation-safe reconciliation. Never push the default branch directly.

## 6. Reconcile after merge

In reconciliation mode:

1. acquire the short-lived coordination mutex and refresh all generations, unless explicit-merge mode already holds that mutex; in that case reuse it and do not reacquire
2. verify the canonical pull request is merged and the remote default branch contains the exact specification changes
3. verify its coordination Issue is closed, or close the single stale Issue linked to the authoritative merged pull request
4. record the reconciled generation's Issue, attempt UUID, base SHA, pull-request head SHA, and merge SHA
5. compare the current remote `refs/heads/docs/project-specs` ref and Issue attempt with that exact generation; if either belongs to a later/different generation or has a newer commit, preserve it and report only the older target as merged
6. delete remote `refs/heads/docs/project-specs` only with a conditional compare-and-delete that requires its current tip and coordination Issue attempt to match the reconciled generation; if the available tool cannot enforce the expected tip, preserve the ref
7. always release the short-lived mutex in a finally step and refresh remote shared state
8. after releasing the mutex, compare any local fixed branch and worktree with the recorded generation; preserve either resource when it belongs to another generation or contains a newer commit or uncommitted change
9. update a clean local default branch with fast-forward only when available
10. remove the clean project-specs worktree only when it belongs to the reconciled generation
11. delete the local fixed branch with a safe non-force operation only when it belongs to that generation and Git recognizes it as merged

Delete the remote fixed branch only after merged content is verified. If verification fails, preserve the ref and stop.

## 7. Report

Report the mode, target/base SHA, Issue, branch, pull request, changed specification files, confirmed decisions, roadmap validation, official sources consulted, merge SHA when applicable, local and remote cleanup, and every skipped or blocked item.

Confirm that no phase implementation, tag, GitHub Release, deployment, production access, remote migration, financial operation, force-push, or unverified lock deletion occurred.
