---
name: deep-review
description: Run a read-only, multi-agent review of a Yuno × Nauta branch, path, PR, or uncommitted change set. Use when the user explicitly asks for a deep or pre-merge review; issue a merge verdict only for a published commit SHA.
---

# Deep review Yuno × Nauta changes

Return one prioritized, evidence-backed report. Do not edit, stage, commit, merge, push, deploy, call a financial operation, or mutate a remote service.

## 1. Resolve the review target

Accept one of these targets:

- PR number: inspect with the official GitHub MCP; use read-only `gh pr view` and `gh pr diff` only when MCP access is unavailable and disclose the fallback
- branch: discover the remote default branch and compare with their merge base
- path: inspect committed, staged, unstaged, and untracked changes under that path
- commit range: inspect the requested range and surrounding source
- no argument: inspect the current branch and worktree

Handle repository states explicitly:

- On a phase branch, fetch and compare against the merge base with the remote default branch when both refs have commits. Do not substitute a stale local `main`.
- On the local branch that tracks the remote default branch, review staged, unstaged, and untracked work instead of stopping automatically.
- On an unborn repository, review requested files and relevant untracked files without calling `merge-base`.
- Include untracked files from `git status --porcelain`; ordinary `git diff` omits them.
- If the resolved change set is empty, report that and stop.

Read the surrounding source, tests, configuration, generated API contract, and documentation for every questionable hunk. A diff alone is not enough context.

For a phase branch or pull request, use read-only GitHub inspection to record the exact reviewed head SHA and check the lightweight coordination facts: the roadmap phase and slug match the branch, every dependency is DONE with required validation recorded and its pull request merged, no declared conflict is active, the phase spec exists, no more than one pull request is open for the branch, closed pull-request history is preserved, and any shared-spec decision is explained in the phase plan and pull-request body. Check the tracking Issue and owner when an Issue exists, but do not require attempt identifiers or duplicate lifecycle metadata. If GitHub state is unavailable, continue with the locally resolvable review and state that coordination and mergeability could not be verified.

## 2. Load product intent

Read completely:

1. `AGENTS.md`
2. `docs/project-specs/mission.md`
3. `docs/project-specs/tech-stack.md`
4. `docs/project-specs/roadmap.md`
5. `docs/decisions/challenge-plan.md`, when present
6. matching phase `requirements.md`, `plan.md`, and `validation.md`, when present

Use the active P0/P1/P2 scope, demo journey, non-goals, acceptance criteria, risks, and fallback to distinguish defects from intentional exclusions.

When the phase used parallel implementation workstreams, also load the ownership matrix and shared-contract checkpoints. Treat overlapping writes, uncoordinated shared-file edits, and contract changes that were not propagated to every affected layer as reviewable integration risks.

When a finding depends on Yuno behavior, consult the current official Yuno MCP `documentation.read` tool when available; otherwise use `https://docs.y.uno/llms.txt` and the relevant official page. Do not rely on remembered endpoints, payloads, enum values, authentication, SDK methods, or webhook formats.

## 3. Review through three distinct lenses

Launch three subagents in parallel because explicit invocation of this skill requests a multi-agent review. Give each reviewer the resolved target, safe commands to reproduce it, project context, and a read-only instruction. If delegation is unavailable, perform three separate local passes and disclose the limitation.

### A. Correctness and architecture

Review runtime behavior, types, async/state transitions, error handling, regressions, tests, and the three-layer boundary. Confirm that:

- the frontend calls FastAPI and uses Yuno directly only through the official browser SDK boundary
- FastAPI routers remain thin and own HTTP concerns rather than business rules
- backend/core remains plain Python and does not import FastAPI
- external providers are hidden behind protocols/adapters
- FastAPI OpenAPI remains the browser contract and generated TypeScript DTOs were not hand-edited or duplicated
- Pydantic/OpenAPI, Orval output, and the typed API-to-core service interface remain mutually consistent
- frontend, API, backend, and coordinator changes stayed within their assigned ownership boundaries
- no unnecessary internal network hop, microservice, queue, cache, or infrastructure was introduced

### B. Payments, security, and data

Review Yuno mapping against current official docs, sandbox/production separation, Web SDK tokenization, secret exposure, PAN/CVV handling, authentication headers, structured-log redaction, authorization, CORS, input validation, idempotency, retry behavior, provider error mapping, webhook raw-body HMAC verification, constant-time comparison, deduplication, delivery-order assumptions, migrations, RLS, and server-only administrative keys.

Treat payment, refund, cancellation, capture, deployment, remote migration, or production mutation as prohibited in this read-only review.

### C. Product, accessibility, and demo quality

Review the target user's end-to-end journey, P0 completeness, loading/error/retry states, accessibility, keyboard and focus behavior, responsiveness, reduced motion, Server/Client Component choices, browser/runtime errors, observability, graceful credential/provider fallback, README/demo instructions, and whether sophistication displaced the working demo.

Do not require AI, Redis, background workers, richer analytics, extra payment paths, or additional services unless the active roadmap phase explicitly includes them and P0 is already complete.

## 4. Require actionable findings

Each subagent returns findings with:

- **Severity:** high, medium, or low
- **Location:** exact `file:line`
- **Issue:** one or two factual sentences
- **Impact and correction:** concrete consequence and fix
- **Evidence:** relevant behavior, command, official source, contract, or project rule
- **Lens:** A, B, or C

Reviewers must say explicitly when their lens is clean and must not invent findings to fill a quota.

## 5. Verify and consolidate

Wait for all three reviews. Deduplicate overlaps and independently verify every high-severity or disputed claim by reading source or running a safe focused check.

Drop speculative, incorrect, already-generated, out-of-scope, or purely stylistic findings that do not affect the phase. Sort remaining findings by severity, then file. If no findings survive verification, say so explicitly and report residual risks or checks that could not run.

## 6. Present the report

Use this structure:

```markdown
# Deep review: target

## High

- [ ] `file:line`: issue. Impact and correction. Evidence. (A, B)

## Medium

- [ ] `file:line`: issue. Impact and correction. Evidence. (C)

## Low

- [ ] `file:line`: issue. Impact and correction. Evidence. (A)
```

Make local file locations clickable when supported. For a branch or pull request whose exact reviewed head SHA is published to a readable remote, end with a merge verdict valid only for that SHA. For local-only commits, staged, unstaged, untracked, or unborn targets, identify the reviewed commit or paths and omit the merge verdict because the reviewed bytes are not published for merge. In every mode, include counts by severity, checks run, coordination status, external or credential limitations, and an offer to fix selected findings in a separate implementation request. Any later change invalidates the reviewed snapshot. Do not apply fixes from this skill.
