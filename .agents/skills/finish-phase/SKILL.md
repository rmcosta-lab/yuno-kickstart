---
name: finish-phase
description: Validate and submit a Yuno × Nauta phase through its pull request, explicitly merge an approved review, or reconcile local resources after merge. Use when the user asks to finish, submit, merge, or reconcile a phase; never deploy.
---

# Finish a Yuno × Nauta phase

A phase is done when its required validation passes and its pull request is merged into the remote default branch. A tracking Issue is useful but not required for correctness.

## 1. Resolve the target and mode

Read `AGENTS.md`, the global specs, the matching phase `requirements.md`, `plan.md`, and `validation.md`, the current branch/worktree state, and the complete diff against the remote default branch. Inspect the remote `phase/NN-{slug}`, its pull requests, dependencies, conflicts, and tracking Issue when present.

Use authenticated GitHub access for publication. Stop when the repository/default branch cannot be read, the target is ambiguous, required validation is missing or failed, histories diverge, conflicts are unresolved, or unrelated changes cannot be separated safely.

Select one mode:

- **Submission:** validate, commit, push, and create or update the phase pull request. Stop in review.
- **Review follow-up:** validate and publish requested changes to the existing open pull request.
- **Explicit merge:** merge an already reviewed pull request only when the user specifically requests the remote merge and checks/approvals pass.
- **Reconciliation:** verify an already merged pull request, close its tracking Issue when appropriate, refresh local `main`, and clean safe local resources.

If the sole pull request was closed without merge, reopen it when supported and explicitly requested. Otherwise preserve the branch and ask whether to continue on a new pull request; do not invent or hide history.

Do not use coordination mutexes, attempt UUIDs, draft/ready state machines, force operations, or synthetic drift statuses.

## 2. Revalidate the phase

Run every applicable gate from `validation.md`. A complete cross-layer code phase normally includes:

```bash
uv run ruff check .
uv run pytest
pnpm lint
pnpm build
```

Run commands from the correct directory. Regenerate Orval when OpenAPI changed. Browser-test rendered journeys and inspect console/network errors. Keep credentialed Yuno sandbox tests separate and report missing credentials honestly.

Verify applicable invariants:

- FastAPI stays thin and backend/core does not import FastAPI
- the browser does not call Yuno private APIs or expose server credentials
- idempotency, raw-body webhook authentication, deduplication, and sensitive-log redaction remain correct
- Pydantic/OpenAPI and generated clients agree
- no unnecessary infrastructure displaced the P0 demo
- shared stack/roadmap changes are explained in `plan.md` and the pull-request body, with affected phases identified

Update the phase's `validation.md` with exact evidence. Never mark an unexecuted criterion complete, and rerun affected checks after source changes.

## 3. Review and publish the branch

For submission or review follow-up:

1. refresh the remote default branch, phase branch, and pull-request state
2. review `git status` and the complete diff
3. stage only explicit phase files and approved shared-spec changes
4. commit `Complete Fase NN: Nome` when needed
5. rerun checks invalidated by generated artifacts or final edits
6. integrate current remote-default changes with a normal non-force workflow when needed
7. push `phase/NN-{slug}` without force and verify the remote head

Do not push the default branch directly, rewrite another developer's history, tag, deploy, apply a remote migration, or perform a financial operation.

## 4. Create or update the pull request

Read `.github/pull_request_template.md` when present and preserve its structure. Create or update one pull request:

- head: `phase/NN-{slug}`
- base: the remote default branch
- title: `[Fase NN] Nome`
- body: outcome, scope, dependencies, validation evidence, limitations, fallback, shared-spec decisions, and `Closes #<issue>` when a tracking Issue exists

Do not duplicate an open pull request. Report its URL, exact head SHA, checks, review state, and mergeability. Submission and review follow-up stop here; an open pull request is not done.

## 5. Merge only with explicit authorization

Immediately before merging, refresh the pull request and require:

- the head SHA is the validated/reviewed SHA
- required CI checks and approvals pass
- GitHub reports the pull request mergeable
- no newer commit invalidated evidence

Use a repository-supported non-force strategy. Do not bypass protection, dismiss reviews, resolve a non-trivial conflict automatically, or delete the remote branch without separate authorization.

After merge, refresh GitHub and the remote default branch before reporting success, then reconcile.

## 6. Reconcile after merge

Verify that the merged pull request contains the intended phase changes and validation evidence. Close a still-open tracking Issue linked to that pull request when appropriate.

Report downstream phases whose dependencies are now merged. Do not write status into the roadmap.

For local cleanup:

1. require the local default-branch worktree to be clean
2. fetch and advance it with fast-forward only
3. verify the merged result locally
4. remove the clean phase worktree when requested or clearly part of reconciliation
5. delete the local phase branch only when Git recognizes it as safely merged

Preserve dirty worktrees and branches Git cannot safely delete. Delete the remote phase branch only with explicit authorization after verifying the merge and current branch head.

## 7. Report

Report the phase outcome, selected mode, branch, pull request and head/merge SHAs, validation by layer, browser/external checks, shared-spec decisions, fallback, Issue state, newly unblocked phases, cleanup, and every remote mutation. Confirm that no deployment, production access, remote migration, financial mutation, force-push, or unauthorized branch deletion occurred.
