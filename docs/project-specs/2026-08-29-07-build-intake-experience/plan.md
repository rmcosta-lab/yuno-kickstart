# Fase 07 — Plan

Single frontend writer for this phase (no parallel workstream split needed — this is a frontend-only phase per the roadmap).

## Task groups (dependency order)

1. **Injected test boundary** (`frontend/src/lib/api/intake-test-boundary.ts`)
   - A fetch-compatible function matching `voltaFetch`'s call shape, returning `OperationDraftResponse`/`OperationResponse`/`ApiErrorResponse`-shaped fixtures built only from the generated model types (no parallel hand-authored DTOs).
   - Cover: a clean draft, a draft with `validation_issues`, an approval-eligible draft, a `STALE_DRAFT_VERSION` conflict on approve, and a generic `VALIDATION_ERROR`.
   - Gated by `NEXT_PUBLIC_INTAKE_USE_TEST_BOUNDARY` (defaults on until Fase 10 lands) so removal later is a one-line change, not a rewrite.

2. **Intake screen** (`frontend/src/app/(control-tower)/intake/`)
   - Replace the Fase 01 fixture list with a client-leaf form: `source_prompt` textarea (1–10000 chars, Zod-validated) + `requested_language` control (default `EN_US` per the confirmed English demo language).
   - Submit calls `useCreateOperationDraft` with a client-generated `Idempotency-Key` (one per logical submission, regenerated on prompt edit) and the injected `request` boundary.
   - Render the returned draft: source prompt, `extraction_policy_version`, `draft_version`, `proposed_route`, `proposed_pickup_date`, `proposed_mandate` (price cap formatted from `maximum_amount_minor`/currency, pickup window, conditions).
   - Render `validation_issues` inline per field; let the coordinator edit the pre-filled prompt and resubmit.
   - Loading, empty (no draft submitted yet), error (`ApiErrorResponse` safe message + field issues), retry, and success states.
   - Provide the coordinator a next step to `/mandate` once a draft is `approval_eligible`.

3. **Mandate screen** (`frontend/src/app/(control-tower)/mandate/`)
   - Replace the Fase 01 fixture list with a client-leaf view of the current approval-eligible draft (via a small local/session handoff from the intake screen — no new backend state in this phase).
   - Render mandate fields read-only: price cap, currency, pickup window, allowed/escalation conditions, `extraction_policy_version`.
   - Require an explicit, separate confirm action (not automatic) before calling `useApproveOperation` with `ApproveOperationRequest { approval_actor, draft_id, expected_draft_version }`; `approval_actor` is a visibly labeled demo constant.
   - On success, render the resulting `OperationResponse` summary (operation id, mandate version, status). On error, render the safe `ApiErrorResponse` message, including a distinct path for `STALE_DRAFT_VERSION`/`MANDATE_CONFLICT` with a way to refresh/retry.
   - Loading, empty (no eligible draft), error, retry, and success states.

4. **Shared primitives check**
   - Before adding any new UI primitive, check the configured shadcn registry and Fase 01's `frontend/src/components/control-tower/**` (status badge, page header, loading/empty/error state, screen-state demo) for reuse; add a new primitive only if none fits (e.g., an inline field-error list), and note it in the PR body.

5. **Accessibility and responsive pass**
   - Labeled inputs with associated error text, keyboard-operable submit/approve controls, visible focus states, mobile and desktop widths without overflow or clipped controls.

## Contract and ownership notes

- No OpenAPI/Orval generation step in this phase — the Fase 04 contract is consumed as-is; if a mismatch is found, it is reported, not silently patched into a hand-copied type.
- One writer (this phase) for every path in `requirements.md`'s ownership matrix; `frontend/src/lib/api/generated/**` and `api/openapi.json` are read-only.
- No new dependency is anticipated (React Hook Form, Zod, TanStack Query, and shadcn primitives are already in the stack per [tech-stack.md](../../project-specs/tech-stack.md)). If the field-error list needs a primitive the registry lacks, add it here and record the reason in the PR body.
- No shared stack or roadmap change is anticipated.

## Checks

- `pnpm lint`, `pnpm typecheck`, `pnpm build` from `frontend/` after each task group, and once more before handoff.
- Manual browser pass per screen: submit the canonical prompt, trigger a validation-issue response, trigger a `STALE_DRAFT_VERSION` approval conflict, complete a successful approval; inspect console and network tabs; resize to mobile and desktop; verify keyboard/focus behavior.

## Waits and temporary blockers

None identified. Both dependencies (Fase 01, Fase 04) are merged; no declared conflict exists.
