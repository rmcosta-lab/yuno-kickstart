---
name: changelog
description: Prepare CHANGELOG.md entries from merged Yuno × Nauta phase pull requests through an ordinary documentation pull request. Use when the user asks for release notes or changelog reconciliation; do not use for unmerged work.
---

# Update the Yuno × Nauta changelog

Build concise release notes from merged evidence. Use an ordinary short-lived documentation branch and pull request; do not maintain a fixed branch, coordination Issue, mutex, or attempt lifecycle.

## 1. Resolve the target

Read `AGENTS.md`, global project specs, matching merged phase specs/validation, the existing `CHANGELOG.md`, and the merged pull-request diffs included in the requested release notes.

Use authenticated GitHub access when publication is requested. Identify the remote default branch and the user-provided release, date, tag, or phase range. For an Unreleased update without an explicit range, propose phase pull requests merged since the last changelog update and report the range before writing.

Stop when an included phase pull request is not merged, required validation evidence is absent, the target range is ambiguous, or another open changelog pull request edits the same section and cannot be coordinated safely.

Use the current branch when it is already an appropriate documentation branch. Otherwise create a short-lived branch such as `docs/changelog-{topic}` from the latest remote default branch. Never edit the changelog from an unrelated active phase branch.

## 2. Build entries from evidence

For each included phase, use its merged diff, merge commit, phase requirements, and validation evidence. Do not infer a shipped outcome from a plan, commit subject, or unchecked criterion.

If `CHANGELOG.md` does not exist, create:

```markdown
# Changelog

## Unreleased
```

Under `## Unreleased`, use only supported categories:

- `### Added`
- `### Changed`
- `### Fixed`
- `### Security`

Write user- or operator-visible outcomes, not implementation activity. Mention sandbox-only or fallback behavior when it matters to the demo. Avoid duplicate entries.

Never include secrets, authentication headers, PAN, CVV, payment tokens, raw webhook payloads, customer data, private URLs, unsupported claims, or sensitive vulnerability details.

## 3. Date a release only when requested

When explicitly requested:

1. move current Unreleased entries under `## YYYY-MM-DD`
2. add a new empty `## Unreleased` above it
3. preserve previous dated sections in descending order

Preparing notes does not authorize a tag, GitHub Release, deployment, production access, remote migration, or financial operation.

## 4. Validate and publish

Check every entry against merged code and executed validation. Run `writing-guidelines` on the changed prose and check for sensitive values or claims that exceed the evidence.

Review the diff, stage only `CHANGELOG.md`, and commit `Update changelog: <target>`. Refresh the remote default branch and any open changelog pull request before pushing. Resolve ordinary conflicts without force or overwrite.

Create or update one pull request:

- head: the short-lived changelog branch
- base: the remote default branch
- title: `[Docs] Update changelog: <target>`
- body: included merged pull requests, validation sources, limitations, and explicit non-release scope

Stop in review. Merge only when the user explicitly requests the remote merge and checks/approvals pass.

## 5. Reconcile after merge

Verify the remote default branch contains the merged changelog. Refresh a clean local default branch with fast-forward only. Remove a clean changelog worktree and safely merged local branch when appropriate; preserve dirty or unmerged resources. Delete the remote documentation branch only when authorized and after verifying the merge.

## 6. Report

Report the target/range, evidence, entries, checks, branch, pull request, head or merge SHA, limitations, cleanup, and remote mutations. Confirm that no tag, GitHub Release, deployment, production access, remote migration, financial operation, or force-push occurred.
