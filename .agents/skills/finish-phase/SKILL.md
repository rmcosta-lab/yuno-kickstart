---
name: finish-phase
description: Submit a verified Yuno × Nauta phase through its template-compliant shared pull request, with an exact preview before publication, or reconcile local resources after that pull request is merged. Use only when the user explicitly asks to finish, submit, or reconcile a phase, or confirms the final publication preview from an active finish-phase workflow.
---

# Finish a Yuno × Nauta phase

Move one verified phase through the shared GitHub lifecycle without hiding failed gates or treating a local merge as team-wide completion.

A phase is `DONE` only when its required checks and phase validation passed, its canonical pull request is merged into the remote default branch, and its coordination issue is closed. A pushed branch, local merge, open pull request, or issue label alone is not completion.

## 1. Resolve mode and shared state

Read completely:

1. `AGENTS.md`
2. `docs/project-specs/mission.md`
3. `docs/project-specs/tech-stack.md`
4. `docs/project-specs/roadmap.md`
5. `docs/decisions/challenge-plan.md`, when present

Run the GitHub MCP discovery and harmless read-only smoke test required by `AGENTS.md`. Before taking a claim mutex, require create-only creation and conditional expected-SHA deletion of that mutex; permission to read, create, update, and reopen pull requests; permission to update or close the coordination Issue; update-only non-force publication to an existing phase ref; and conditional expected-SHA deletion for an explicitly requested verified remote phase cleanup. Require merge permission only in explicit-merge mode. Identify the remote default branch, fetch it, and inspect:

- current branch and worktree path
- `git status --short`, untracked files, and `git worktree list --porcelain`
- the exact `[Fase NN] Nome` coordination issue and assignee
- remote `phase/NN-{slug}`, using the exact roadmap `Slug`
- open, closed-unmerged, and merged pull requests from that branch
- dependency and conflict phases
- commits and complete diff against the remote default branch
- frontend, API, backend, and cross-layer validation evidence

Resolve the target from an explicitly named phase, Issue, or pull request. Otherwise use the current phase branch. If reconciliation is requested from another branch and several merged phases need reconciliation, stop and ask for the exact phase or pull request instead of guessing.

After resolving it, read the phase `requirements.md`, `plan.md`, and `validation.md` from the validated local/remote phase revision in submission, review-recovery, or explicit-merge mode, or from the merged remote-default revision in reconciliation mode.

Select modes in this precedence order: Reconciliation, Review recovery, Explicit merge, then Submission. A higher-precedence match must never fall through to Submission.

- **Submission:** no phase pull request of any state exists, or exactly one canonical pull request is open and the current request does not explicitly authorize merging that existing review. A closed-unmerged pull request is not Submission. Validate, commit, push, and create or update the canonical pull request. Even if the user asked to merge before a pull request existed, stop in `REVIEW` after creating it so repository checks and reviews can run.
- **Review recovery:** exactly one canonical pull request is closed without merge, no open or merged phase pull request exists, its branch and Issue remain consistent, and the user explicitly requests reopening that same pull request. Validate and restore its exact review; never create a replacement.
- **Reconciliation:** the canonical pull request is already merged. Verify remote completion, reconcile the issue, report newly eligible phases, and clean safe local resources.
- **Explicit merge:** exactly one canonical pull request is open at an already validated head, the worktree has no source change to publish, and the current user specifically asks to merge that existing review, not merely to “finish” or “submit” the phase. Verify repository approvals/checks, merge remotely, then reconcile. If validation requires a source or evidence change, return to submission, update the review, and stop in `REVIEW` before accepting a later merge request.

In submission, review-recovery, or explicit-merge mode, require the current branch to match `phase/NN-{slug}`, the remote phase branch to exist, the authenticated GitHub login to equal the sole Issue assignee and `Owner: @login`, the current roadmap fields to match the immutable metadata recorded at claim time, and the Issue, branch, planning commit/spec, and pull-request facts to be unique and consistent.

In reconciliation mode, the merged pull request is the durable authority. The remote phase branch, local phase branch, or local phase worktree may already be absent. An open Issue paired with one valid merged phase pull request is a specifically reconcilable form of `DRIFT`, not a reason to stop before reconciliation.

Always stop when:

- authenticated shared GitHub access or the remote default branch is unavailable
- required validation remains failed or unexecuted
- a required sandbox, browser, webhook, or credential-dependent gate is represented as passed without evidence
- duplicate or contradictory Issues or pull requests prevent identification of one canonical merged or pending change

In submission, review-recovery, or explicit-merge mode, also stop when:

- the claim is absent, belongs to another owner without a recorded handoff, or is in `DRIFT` for any reason other than the exact sole closed pull request selected by review-recovery mode
- dependencies are not `DONE` or a declared conflicting phase is active or in `DRIFT`
- a phase pull request was closed without merge unless review-recovery mode selected that exact sole pull request
- merge conflicts or unresolved files exist
- remote and local phase histories diverge
- the diff contains unrelated changes that cannot be separated safely

In reconciliation mode, stop instead of closing the Issue when the current roadmap removed or changed the phase's frozen metadata, the pull request targeted the wrong base, its merged revision lacks required phase evidence, dependencies were not valid for the merge, or the merged result cannot be matched unambiguously to the phase.

Do not use destructive cleanup or force operations to make preflight pass.

Before changing local content in submission mode when a pull request is already open, acquire the coordination mutex, refresh the complete lifecycle, and reselect the mode. If it merged, release the mutex and switch to reconciliation without editing. Otherwise convert it to draft, or establish an equivalent repository-enforced merge block and record its exact unblock action on the Issue, before releasing the mutex; stop if the repository cannot prevent merge during the edit window or cannot later remove that block.

## 2. Revalidate the phase

For submission, review recovery, or explicit merge, run every final gate required by `validation.md`. For a complete cross-layer code phase, the minimum is:

```bash
uv run ruff check .
uv run pytest
pnpm lint
pnpm build
```

Run commands from the correct repository or package directory. Regenerate the Orval client first when OpenAPI changed. Browser-test affected rendered flows and inspect console, network, and runtime errors. Keep credentialed Yuno sandbox tests separate; report missing credentials instead of substituting production access.

Verify the applicable invariants:

- FastAPI routers remain thin and backend/core does not import FastAPI
- browser code does not call Yuno private APIs or expose private/server credentials
- mutable Yuno operations preserve logical idempotency keys
- webhooks authenticate raw bytes before parsing and process events idempotently
- logs and artifacts contain no secrets, PAN, CVV, auth headers, or sensitive full payloads
- no unnecessary service, worker, cache, or infrastructure was added
- Pydantic/OpenAPI and the generated Orval client agree
- the API-to-core typed interface has no DTO or provider-model leakage

Update the phase's unique `validation.md` with final evidence before committing. Never mark an unexecuted criterion complete. Record the exact validated tree or commit SHA and invalidate that evidence if the source changes afterward.

## 3. Update phase-owned records before submission

Only in submission, review-recovery, or explicit-merge mode, update files inside the active phase spec directory when their evidence changed. In reconciliation mode, read evidence from the merged revision and never create post-merge local evidence.

Treat `docs/project-specs/mission.md`, `docs/project-specs/tech-stack.md`, `docs/project-specs/roadmap.md`, and `docs/decisions/challenge-plan.md` as owned by `manage-shared-specs`. Only the exact active dated phase directory under `docs/project-specs/` is phase-owned. Treat `AGENTS.md`, README, root configuration, and other shared documentation as read-only unless `plan.md` assigned that exact path and the roadmap conflict graph plus current GitHub state prove exclusive cross-phase ownership. Otherwise defer the change to an appropriate serialized task.

Record an architectural exception in `docs/decisions/` instead of silently overriding a convention, but apply the same exclusive shared-file rule.

Do not append `✅` or another dynamic status to `docs/project-specs/roadmap.md`. The roadmap is the static dependency graph.

Never update `CHANGELOG.md` from a phase branch, even when no other phase is active. Only the serialized `changelog` workflow owns that file after the relevant phase pull requests are merged.

## 4. Commit and publish the phase

In submission, review-recovery, or explicit-merge mode:

1. refresh the complete phase lifecycle and reselect the mode; if the pull request is now merged, do not create or publish a local completion commit and switch to reconciliation only when the merged head contains all intended work
2. review `git status` and the complete diff
3. stage only explicit files belonging to the phase; never use a blanket command that captures unrelated work
4. create a commit named `Complete Fase NN: Nome` when uncommitted phase work exists
5. rerun any gate invalidated by the commit operation or generated artifacts
6. immediately before push, acquire the coordination mutex, refresh the Issue, remote phase ref, all pull-request states, remote default, merge state, and any recorded merge block and reselect the mode again; if the pull request merged or an expected block disappeared, preserve any local commit not contained in remote review, do not push or recreate a missing branch, and stop instead of reporting `DONE` when intended work is absent from the merge
7. update only the existing remote `phase/NN-{slug}` with a non-force, update-only fast-forward operation that rejects a missing or changed ref, then refresh shared state and release the mutex as a required finally step

Do not force-push, rebase, push the remote default branch, tag, deploy, apply remote migrations, or call a financial operation.

If the push fails, leave the issue and remote branch intact, report the shared state, and stop.

## 5. Create or update the canonical pull request

Before drafting the pull request, read `.github/pull_request_template.md`. Preserve its heading order, Markdown structure, HTML guidance comments, tables, and checklist items. Fill every section from verified phase facts; write `None` or `N/A` when a section does not apply. Never remove a section, invent validation evidence, mark an unexecuted check as passed, or replace an external limitation with an optimistic claim.

In submission mode, create exactly one pull request with:

- head: `phase/NN-{slug}`
- base: the discovered remote default branch
- title: `[Fase NN] Nome`
- body: the completed repository template, including outcome, scope, dependencies, validation evidence, external limitations, fallback, and `Closes #<coordination-issue>`

If the canonical pull request is open, update it instead of creating another. In review-recovery mode, reopen the exact closed pull request; never create a replacement. Verify its head SHA equals the validated remote phase SHA. Keep the coordination issue open and assigned while the pull request is under review.

Before creating a pull request or changing an existing pull request's title, base, or body, present one complete publication preview containing:

- repository and pull-request action (`create`, `update`, or `reopen`), plus `mark ready` or the recorded equivalent unblock action when the canonical pull request is merge-blocked
- exact title, base, and head
- complete rendered body, without elisions or summaries
- validated remote head SHA

Ask the user to confirm that exact preview. A general request to “finish” or “submit” the phase, a shell/tool approval, or approval of an earlier draft is not confirmation of the final publication preview. Do not perform the GitHub mutation until the user confirms it. On the confirmation turn, acquire `refs/heads/coordination/phase-claim-lock`, refresh the complete phase lifecycle, merge state, remote default, Issue, branch, and every pull request, and reselect the mode before any mutation. If the pull request merged, cancel the previewed mutation and switch to reconciliation only when the merge contains all intended work; otherwise stop with the retained local difference. Compare every previewed field and head SHA with the confirmed preview; if the SHA, mode, or any field changed, release the mutex, show the revised complete preview, and obtain confirmation again. Create, update, or reopen only the exact canonical pull request, verify its title, base, body, and head SHA, and only then perform the previewed `mark ready` or recorded equivalent unblock action. Refresh once more and release the mutex as a required finally step. If reopen or unblock is unavailable, preserve the claim and report the repository-policy blocker; never create a replacement. No confirmation is needed when an existing canonical pull request already matches the required open, unblocked state, title, base, head, and body and no remote update will occur.

Submission and review-recovery modes stop here with shared state `REVIEW`. Do not call the phase `DONE`, close the issue manually, clean the worktree, or merge locally.

Report repository checks, reviews, and mergeability as observed facts. Do not bypass branch protection or claim approval from a missing check.

## 6. Merge only with explicit authorization

Acquire `refs/heads/coordination/phase-claim-lock`, refresh the complete phase lifecycle, and reselect the mode immediately before any merge mutation. Merge the canonical pull request only when the current user explicitly requests that remote merge and all of these are true:

- the pull request head SHA is exactly the validated and, when requested, reviewed SHA
- required CI checks pass
- required human or automated reviews are satisfied
- GitHub reports the pull request mergeable against the remote default branch
- no newer commit invalidated evidence
- the issue-closing reference is present

Use a repository-supported, non-force merge strategy. Do not resolve a non-trivial conflict, dismiss a review, bypass protection, or delete the remote branch without separate explicit authorization.

After the merge operation, refresh GitHub and the remote default branch before reporting success. Reuse the held mutex for the remote portion of immediate reconciliation instead of reacquiring it, then release it in one finally step before local cleanup. If the merge does not occur, release the mutex and preserve the claim.

## 7. Reconcile after remote merge

In reconciliation mode, acquire the coordination mutex unless explicit merge already holds it, refresh all phase and roadmap facts, and verify from the merged pull request and remote default branch that the conditions below hold. Treat release as a required finally step on every failure or early return and preserve all durable resources when verification fails.

- the canonical pull request is merged into the remote default branch
- the merged result contains the intended phase changes
- the merged revision contains the required phase validation evidence and matches the checks accepted for merge
- the coordination Issue is closed or is the single stale open Issue linked to this merged pull request

If the merged pull request and its validation evidence are authoritative but the issue remained open, close it as a safe lifecycle reconciliation and record the merged pull request in the issue. A closed issue without a valid merged pull request is not safe to reconcile as `DONE`.

Recompute the roadmap graph from current shared state and report every downstream phase that has just become `READY`. Do not assume the next numeric phase is eligible and do not write mutable status into the roadmap.

If this reconciliation reused or acquired the coordination mutex, release it after the remote merge, Issue state, and graph snapshot are consistent. Do not hold the global mutex while fetching local refs, advancing a local branch, or removing a worktree.

For local cleanup, perform only the steps whose resources exist:

1. locate the worktree of the remote default branch and require it to be clean
2. fetch, then advance its local branch with `--ff-only` to the remote default branch
3. verify the merged result is present locally
4. remove the phase worktree when it exists and is clean
5. delete the local phase branch when it exists and the safe non-force operation recognizes it as fully merged

If a squash or rebase merge prevents safe local branch deletion, leave the local branch and report it. Never force-delete it.

Never delete the remote phase branch unless the user explicitly requests that exact cleanup after the merge is verified. For that request, acquire the coordination mutex unless already held from explicit merge, refresh the Issue attempt, every pull request, and the current ref, and use a conditional compare-and-delete that succeeds only when the ref tip equals the authoritative merged pull-request head and no later attempt, commit, or review exists. If the tool cannot enforce the expected tip or any fact changed, preserve the branch. Release the mutex in a finally step.

## 8. Report the result

Report the phase and P0/P1/P2 outcome, selected mode, shared state, coordination issue, pull request and exact head/merge SHAs, validation status for frontend, API, backend, and integration, browser and external checks, contract consistency, credential or sandbox limitations, remote default branch, newly `READY` downstream phases, local cleanup performed or retained resources, remaining changes, and every remote mutation.

Use `REVIEW` after submission or successful review recovery and `DONE` only after validated remote merge plus Issue closure. Confirm that no deployment, production access, remote migration, financial mutation, force-push, or unauthorized remote branch deletion occurred.
