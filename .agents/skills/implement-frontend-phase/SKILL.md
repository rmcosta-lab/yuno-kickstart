---
name: implement-frontend-phase
description: Implement the frontend workstream of a specified Yuno × Nauta phase in Next.js and verify its generated API integration and browser behavior. Use for frontend-only work or when delegated by implement-phase; do not use for FastAPI or backend/core implementation.
---

# Implement the frontend phase workstream

Deliver the assigned browser experience inside `frontend/**` without redefining server contracts or editing another layer.

## 1. Resolve scope and tools

Read `AGENTS.md`, `frontend/AGENTS.md` when present, `docs/project-specs/mission.md`, `docs/project-specs/tech-stack.md`, `docs/project-specs/roadmap.md`, the active phase `requirements.md`, `plan.md`, and `validation.md`, and `docs/decisions/challenge-plan.md` when present. Inspect `git status` and preserve unrelated changes.

When delegated, use the exact phase spec and verified shared claim supplied by `implement-phase`. For review follow-up, require the coordinator's refreshed proof that the pull request is draft or equivalently merge-blocked before editing.

When directly invoked, require the current branch to match `phase/NN-{slug}` using the roadmap `Slug`, locate exactly one matching `docs/project-specs/YYYY-MM-DD-NN-{slug}/`, and refresh GitHub state. Require the roadmap number, heading name, slug, dependencies, conflicts, and gate to match the immutable metadata recorded when the phase was claimed. Resolve the authenticated GitHub login and require it to equal both the sole Issue assignee and `Owner: @login`. Verify that the planning SHA recorded by `start-phase` is an ancestor of the remote branch and that its spec path exists. A handoff is valid only after assignee, owner field, and an explicit Issue transfer comment agree.

Require shared state `IN_PROGRESS` for ordinary direct work or `REVIEW` only when the request explicitly targets follow-up on its sole open pull request. Stop and route to `finish-phase` reconciliation if any phase pull request is merged. Also stop on absence, ambiguity, claimant mismatch, missing planning publication, inaccessible remote state, dependency or conflict failure, closed-unmerged pull request, or branch/Issue disagreement. When directly invoked for review follow-up, acquire the coordination mutex, refresh the lifecycle, stop if merged, convert the pull request to draft or an equivalent repository-enforced merge block, record the exact unblock action on the Issue, verify its unchanged head/attempt and recorded block, and release the mutex in a finally step before editing; stop if blocking or its later unblock action cannot be completed.

Extract the assigned user journey, frontend acceptance criteria, frozen HTTP contract, Yuno browser boundary, loading/error/fallback states, and allowed paths. Default write ownership is `frontend/**` only. Do not edit `api/**`, `backend/**`, phase specs, docs, or root/shared configuration unless the coordinator explicitly assigns that exact path.

Use the current agent's MCP discovery in the execution environment. In Codex, run `codex mcp list`; in Claude Code, run `claude mcp list` or use `/mcp`. Confirm shadcn, Playwright, and Chrome DevTools capabilities before UI work; follow the setup and approval rules in `AGENTS.md` if directly invoked, or report missing shared configuration to the coordinator when delegated.

Use Context7 when current Next.js, React, Tailwind, TanStack Query, React Hook Form, Zod, or SDK documentation is needed; do not guess version-sensitive APIs.

## 2. Implement the browser experience

- Use Next.js App Router and TypeScript strict mode.
- Prefer Server Components; add `"use client"` only for browser state, event handlers, forms, SDK initialization, or other real interactivity.
- Use TanStack Query for remote server state, React Hook Form with Zod for interactive forms, and shadcn primitives before creating bespoke equivalents.
- Build the complete phase journey with explicit loading, empty, error, retry, success, and credential/provider fallback states that apply.
- Preserve accessibility, keyboard and focus behavior, responsive layout, and reduced-motion behavior where relevant.

Use the shadcn MCP before hand-building a primitive that may exist in the configured registry. Review every generated component and dependency.

## 3. Respect API and Yuno boundaries

Call only the FastAPI API through the generated Orval client. Do not hand-copy Pydantic DTOs, create parallel request/response types, or manually edit generated files.

If the OpenAPI contract is not yet available, implement only contract-independent presentation and report the integration checkpoint. Never invent temporary DTOs that can drift from the server. After the API contract is materialized, regenerate the client with the repository's `api:generate` command and fix resulting type errors.

Use Yuno's official Web SDK only for browser-side payment UI/tokenization required by the phase. Checkout sessions and payments remain server-created. Never expose, receive, persist, or log `YUNO_PRIVATE_SECRET_KEY`, PAN, CVV, auth headers, one-time payment credentials, or sensitive full payloads.

Before changing Yuno SDK usage, confirm the Yuno MCP with the same agent-specific discovery flow. If it is missing, follow the project setup/discovery rules before implementation. Use the official machine-readable documentation fallback only when MCP setup or session restart is unavailable in the current environment, report that limitation, and never guess SDK methods or callbacks.

## 4. Verify the frontend workstream

Run focused frontend tests when defined, then the required gates from `frontend/`:

```bash
pnpm lint
pnpm build
```

For rendered changes, exercise the assigned user flow with Playwright, then inspect console and network errors with Chrome DevTools. Cover relevant responsiveness, keyboard/focus behavior, loading/error/retry states, and the Yuno SDK boundary. Do not claim a credentialed flow passed when only a fallback or mock was exercised.

Review the frontend diff for hand-written API DTOs, manual generated-client edits, server secrets, browser calls to Yuno private APIs, unnecessary client components, and out-of-scope files.

## 5. Return evidence

Report the user-visible outcome, files changed, contracts consumed and any deviation, generated-client status, commands/checks with results, browser/external evidence, fallback used, skipped gates or blockers, requested shared-file changes, and confirmation that no secret or unauthorized remote/financial mutation occurred. When delegated, do not edit shared `plan.md` or `validation.md`; return exact evidence to `implement-phase`. Update shared records only when explicitly assigned exclusive ownership.
