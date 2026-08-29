---
name: changelog
description: Prepare or reconcile a serialized CHANGELOG.md update from merged Yuno × Nauta phase pull requests through the fixed docs/changelog branch. Use only when the user asks for release notes or changelog reconciliation; do not use from a phase branch.
---

# Update the Yuno × Nauta changelog

Publish validated, user-relevant release notes through one serialized documentation branch. Never edit `CHANGELOG.md` from a phase branch.

The fixed remote branch `docs/changelog` is the create-only lock. Its pull request is the shared review state. Delete that remote branch only after its merge is verified, or when repair mode proves it is an empty orphan and the user explicitly authorizes release.

## 1. Resolve shared state and target

Read:

- `AGENTS.md`
- `docs/project-specs/mission.md`, `docs/project-specs/tech-stack.md`, and `docs/project-specs/roadmap.md`
- matching merged phase `requirements.md`, `plan.md`, and `validation.md`
- `docs/decisions/challenge-plan.md`, when present
- the existing `CHANGELOG.md`, when present

Run the GitHub MCP discovery and harmless read-only smoke test from `AGENTS.md`. Require permission to read, create, update, assign, unassign, close, and reopen coordination Issues; to read, create, update, reopen, draft, and mark ready pull requests; to create refs with create-only semantics; to publish through update-only, non-force fast-forward operations; and to conditionally compare-and-delete the short-lived mutex and `docs/changelog` using their expected old SHA after the respective verification gate. Stop if credentials, tools, or branch protection make the lifecycle impossible to complete. Identify the remote default branch and inspect:

- remote `docs/changelog`
- every open or closed coordination Issue with the exact canonical title `[Changelog] <full-base-sha>` and its sole assignee when active
- open, closed-unmerged, and merged pull requests from that branch
- current worktrees and local branches
- every phase pull request included in the requested notes

Use the user-provided release, tag, date, or phase set as the target. For an Unreleased update without an explicit range, derive the candidate set from phase pull requests merged since the last changelog update and report that range before writing.

Stop when:

- authenticated GitHub access or the remote default branch is unavailable
- an included phase pull request is not merged, its coordination Issue is not closed, or required validation evidence is absent
- `docs/changelog` exists with work owned by another task and no explicit handoff recorded in its coordination Issue, unless the current request explicitly selects repair-orphan mode for a missing/incomplete Issue
- a changelog pull request was closed without merge and no recovery decision exists
- duplicate pull requests or divergent histories make the lock state ambiguous

## 2. Claim or reconcile the fixed branch

Select modes in this precedence order: Reconcile, Recover review, Repair orphan, Resume, then Prepare. A higher-precedence match must never fall through to Resume.

- **Prepare:** no active `docs/changelog` ref or unreconciled earlier task exists, and the target/base SHA is new or has exactly one closed canonical Issue whose recorded outcome is `ABANDONED`.
- **Resume:** the ref exists with one consistent changelog task and no pull request or exactly one open pull request; its sole Issue assignee and `Owner: @login` match the authenticated actor. A closed-unmerged pull request is not Resume. After a handoff, require the new assignee, updated owner field, and explicit transfer comment to all agree.
- **Repair orphan:** the fixed ref or its Issue exists without a consistent counterpart. Use only after an explicit repair request.
- **Recover review:** the fixed ref, Issue, and exactly one closed-unmerged pull request agree, no open or merged pull request exists, and the user explicitly requests reopening that same review.
- **Reconcile:** the canonical changelog pull request for the requested target is merged. This mode has precedence even when GitHub already auto-deleted the head ref. Verify the remote default branch contains the update, then release any remaining local resources and fixed remote lock.

`Prepare` applies only after every earlier target is fully reconciled. A retry on an unchanged base is permitted only through the single reusable `ABANDONED` Issue described below.

If create-only returns “already exists,” refresh shared state and stop or select the applicable existing mode. Never overwrite or force-update the fixed branch. If Issue creation fails after the ref succeeds, preserve the ref as an incomplete lock and require explicit reconciliation.

In prepare mode:

1. acquire `refs/heads/coordination/phase-claim-lock` as a short-lived create-only mutex
2. refresh the fixed branch, target/base SHA, pull requests, and every open or closed Issue with the exact canonical title; stop and release the mutex if canonical Issues are duplicated
3. create `docs/changelog` once at the refreshed remote-default SHA
4. generate a new attempt UUID; create `[Changelog] <full-base-sha>` only when no exact-title Issue exists, or reopen and reuse the single closed `ABANDONED` Issue when its prior attempt left no branch, pull request, unique commit, or unreconciled resource and the only current fixed ref is the empty ref created by this transaction
5. preserve the prior abandonment audit trail, assign the authenticated GitHub login, record `Current attempt: <uuid>`, `Outcome: ACTIVE`, `Owner: @login`, target, base SHA, and branch, and add a retry comment when reopening
6. release the short-lived mutex

Never create a second exact-title Issue for the same base SHA. If Issue creation or reopening fails, preserve the fixed ref, release the short-lived mutex if safely possible, and enter repair-orphan mode on a later explicit request.

In repair-orphan mode:

Before acquiring the mutex, inspect the orphan read-only, present the exact resume or abandonment actions and remote mutations, and obtain the user's choice, target, owner confirmation, any handoff, and authorization. Never wait for user input while holding the global mutex.

1. after the choice, acquire `refs/heads/coordination/phase-claim-lock` as a short-lived create-only repair mutex
2. refresh the fixed ref, Issue, pull requests, commits, worktrees, and remote default branch; stop if the chosen repair no longer matches the refreshed facts
3. if unique commits or a pull request exist, never delete the ref; verify and apply the preconfirmed target, owner, and handoff, create or reopen the single canonical Issue as needed, generate a new recovery attempt UUID, assign the authenticated owner as sole assignee, record the prior attempt's recovery disposition plus `Current attempt: <uuid>`, `Outcome: ACTIVE`, and `Owner: @login`, and add an audit comment before resuming; if the owner changes, update the sole assignee and owner field together and add the preconfirmed explicit transfer comment
4. if an empty ref has no pull request, apply the preconfirmed choice: to resume, create or reopen the single canonical Issue as needed, generate a new recovery attempt UUID, assign the authenticated owner as sole assignee, preserve the prior attempt audit trail, and record `Current attempt: <uuid>`, `Outcome: ACTIVE`, `Owner: @login`, target, base, branch, and any required owner-transfer comment before any work; to abandon, create the canonical Issue if absent, reuse the current attempt UUID or generate a recovery UUID, record the prior owner, reason, and actor, set `Outcome: ABANDONED`, remove every assignee, and close the Issue before deleting only that empty ref
5. if only an incomplete Issue exists, apply the preconfirmed choice: for resume, select the exact fixed-ref SHA from a uniquely recorded prior branch tip or pull-request head when later work existed, otherwise use the exact recorded base SHA only after proving no later work ever existed; require that SHA to be reachable and consistent with the Issue history, stop without creating a ref when it is absent or ambiguous, then create the ref at that exact SHA with create-only semantics, generate a new recovery attempt UUID, reopen the Issue when needed, assign the authenticated owner as sole assignee, preserve the audit trail, and record `Current attempt: <uuid>`, `Outcome: ACTIVE`, and `Owner: @login` plus the selected SHA and any required owner-transfer comment before any work; for abandonment, reuse its current attempt UUID or generate a recovery UUID when absent, record the prior owner, set `Outcome: ABANDONED`, remove every assignee, and close the Issue
6. release the repair mutex and refresh shared state

Every repair-resume path must finish the Issue update successfully before implementation continues. If an Issue update, assignment, unassignment, reopen, or close fails, preserve the ref and stop; if ref recreation fails, preserve the Issue and stop. The closed `ABANDONED` Issue remains the sole canonical Issue for its base SHA. A later prepare on that unchanged base must reopen and reuse it with a new attempt UUID; it must not create a replacement. If the mutex cannot be acquired or released, ownership and contents cannot be established, or more than one exact-title Issue exists, preserve every ref and stop. Never infer repair authorization from age.

In recover-review mode, acquire the mutex, refresh the Issue attempt, fixed ref, remote default, and every pull request, and verify the fixed tip equals the closed pull request's validated head. Reopen that same pull request, record the recovery audit on the Issue, and release the mutex in a finally step. Never create a replacement pull request. If the ref is missing, repair it first at the exact reachable pull-request head; if GitHub or repository policy cannot reopen the review, preserve the ref and report the external blocker.

After acquiring the short-lived mutex in any mode, treat its release as a required finally step on every success, failure, or early-stop path. If verified release fails, report global coordination `DRIFT` and do not hide the blocked mutex.

For prepare or resume, create a tracking local branch and a dedicated sibling worktree at `../yuno-kickstart-changelog`. Preserve any existing consistent worktree; stop on an unrelated occupant.

Before changing local content for a generation whose pull request is open, acquire the coordination mutex, refresh the complete lifecycle, and reselect the mode. If it is already merged, release the mutex and switch to reconciliation without editing. Otherwise convert it to draft, or establish an equivalent repository-enforced merge block and record its exact unblock action on the Issue, before releasing the mutex; stop if the repository cannot prevent merge during the edit window or cannot later remove that block.

## 3. Build entries from merged evidence

For every included phase, use:

- the merged pull-request diff and merge commit on the remote default branch
- the merged phase specification and validation evidence
- observed sandbox, credential, browser, webhook, or fallback limitations

Do not infer a shipped outcome from a commit subject, plan, or unchecked criterion when source or validation contradicts it.

If `CHANGELOG.md` does not exist, create:

```markdown
# Changelog

## Unreleased
```

Under `## Unreleased`, use only categories with supported entries:

- `### Added`
- `### Changed`
- `### Fixed`
- `### Security`

Write concise bullets in terms of the target user's or operator's outcome, not implementation activity. Mention sandbox-only or fallback behavior when that limitation affects the demo. Avoid duplicate entries already present under Unreleased.

Never include secrets, API keys, authentication headers, PAN, CVV, payment tokens, raw webhook payloads, customer PII, private URLs, real database rows, unsupported claims, internal vulnerability details, or provider identifiers.

## 4. Date a release only when requested

When the user explicitly asks to prepare a dated release:

1. move current Unreleased entries under `## YYYY-MM-DD`
2. add a new empty `## Unreleased` above the dated section
3. preserve prior dated sections in descending order

Preparing notes does not authorize a tag, GitHub Release, deployment, production credential use, remote migration, or financial operation.

## 5. Verify and publish for review

Check every entry against merged diffs and executed validation, and run `writing-guidelines` on the changed prose. Confirm that the file contains no sensitive values and does not claim unexecuted Yuno sandbox, webhook, browser, or production behavior.

In prepare or resume mode:

1. show and review the `CHANGELOG.md` diff
2. stage only `CHANGELOG.md`
3. commit `Update changelog: target`
4. immediately before remote publication, reacquire the mutex and refresh the fixed ref, exact Issue attempt, remote default, all pull-request states, and any recorded merge block; if the pull request merged, an expected block disappeared, the ref disappeared, the attempt changed, or another generation appeared, do not push or recreate anything and reclassify the task
5. update only the existing `docs/changelog` ref with a non-force, update-only fast-forward operation that rejects a missing or changed ref
6. create or update one pull request to the remote default branch titled `[Docs] Update changelog: target`
7. include the merged phase pull requests, validation sources, limitations, explicit non-release scope, and `Closes #<changelog-issue>` in the body
8. publish the verified head, then mark an existing draft ready or execute the recorded equivalent unblock action, refresh branch and pull-request state, and release the mutex as a required finally step; if unblock fails, keep the block and report review-blocked state

If a concurrent merge contains the published head, switch to reconciliation. If it merged an earlier head, preserve the newer branch/local commit, report `DRIFT`, and do not clean or delete it. Stop with the changelog task in review otherwise. Do not merge unless the current user explicitly asks for the remote merge and all required checks and approvals pass; perform the final refresh and merge while holding the same mutex, then continue with generation-safe reconciliation.

## 6. Reconcile after merge

After the canonical changelog pull request is merged:

1. acquire the short-lived coordination mutex and refresh all generations, unless explicit merge already holds that mutex; in that case reuse it and do not reacquire
2. fetch and verify the remote default branch contains the changelog commit
3. verify the changelog coordination Issue is closed, or close the single stale Issue linked to the authoritative merged pull request
4. record the reconciled generation's Issue, attempt UUID, target/base SHA, pull-request head SHA, and merge SHA
5. compare the current remote `docs/changelog` ref and Issue attempt with that exact generation; if either belongs to a later/different generation or has a newer commit, preserve it and report only the older target as merged
6. delete remote `docs/changelog` only with a conditional compare-and-delete that requires its current tip and coordination Issue attempt to match the reconciled generation; if the available tool cannot enforce the expected tip, preserve the ref
7. always release the short-lived mutex in a finally step and refresh remote shared state
8. after releasing the mutex, compare any local fixed branch and worktree with the recorded generation; preserve either resource when it belongs to another generation or contains a newer commit or uncommitted change
9. update a clean local default branch with fast-forward only when available
10. remove the clean changelog worktree only when it belongs to the reconciled generation
11. delete the local changelog branch with a safe non-force operation only when it belongs to that generation and Git recognizes it as merged

Outside the empty-orphan exception in explicit repair mode, remote deletion is allowed only in reconciliation mode after merged content is verified on the remote default branch. If verification fails, preserve the ref and stop. Never force-delete a local branch or delete an unmerged remote changelog branch that contains unique work or a pull request.

## 7. Report

Report the target and merged phase range, selected mode, exact evidence used, entries changed, checks performed, branch and pull request, head or merge SHA, external limitations, cleanup, and every remote mutation.

Confirm that no tag, GitHub Release, deployment, production access, remote migration, financial operation, force-push, or unverified lock deletion occurred.
