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

## Recorded deviations

- **Injection mechanism (contract mismatch found, not patched).** `requirements.md` assumed the generated hooks' `request` option (`SecondParameter<typeof voltaFetch>`) was a pluggable fetcher that could be swapped for a fixture-returning function. Inspecting `frontend/src/lib/api/generated/api.ts` and `frontend/src/lib/api/volta-fetch.ts` shows `request` is actually just extra `RequestInit` merged into the one real `fetch()` call inside `voltaFetch` — it cannot replace the network call itself, since every generated mutation function (`createOperationDraft`, `approveOperation`) calls `voltaFetch(url, options)` directly with no fetcher-injection point. This is the exact scenario `requirements.md`'s Fallback clause anticipated: the gate requires generated types and an injected boundary, not a specific injection mechanism. Applied fallback: `frontend/src/lib/api/intake-test-boundary.ts` exports plain async functions (`createOperationDraftFixture`, `approveOperationFixture`) with the same request/response shapes as the generated mutation functions, built only from `@/lib/api/generated/models` types and reusing the real `ApiHttpError` class from `volta-fetch.ts` for error cases. Each screen calls `useCreateOperationDraft`/`useApproveOperation` (the generated hooks, used unconditionally to satisfy the Rules of Hooks) when `NEXT_PUBLIC_INTAKE_USE_TEST_BOUNDARY` is off, or a manually constructed `useMutation({ mutationFn: <fixture fn> })` when it's on, and renders whichever result is active. Swapping to Fase 10's real backend is deleting the boundary-mutation branch per screen, not a rewrite.
- **Test-boundary scenario selection.** Neither `requirements.md` nor `plan.md` specified how a coordinator (or the browser smoke test) picks which fixture scenario a submission hits. Added a small `<Select>` labeled "Test boundary scenario (no live backend yet)" on each screen, visible only when the test boundary is enabled, offering the fixture scenarios listed above (task group 1). It unmounts entirely once the flag flips off.
- **Draft handoff to `/mandate`.** Implemented as `frontend/src/lib/operation-draft-handoff.ts` (not `intake/` or `mandate/` — it's shared by both). Reads go through a `useSyncExternalStore`-backed hook (`useApprovalEligibleDraft`) rather than `useEffect` + `useState`, because: (a) a plain `useEffect` that calls `setState` unconditionally on mount is flagged by this repo's `eslint-plugin-react-hooks` "no setState in effect" rule, and (b) reading `sessionStorage` directly during render (to avoid the effect) would cause a hydration mismatch between the server/first-paint (`window` undefined) and the client. `useSyncExternalStore` is the React-documented solution for exactly this browser-only, hydration-safe read; a tiny in-module pub/sub (`notifyListeners`) drives re-renders on same-tab writes/clears, since the native `storage` event never fires for writes made in the same tab that made them.
- **Idempotency-key storage.** Kept in component state (not a ref) for both screens. An early ref-based draft (`useRef`, mutated inside the render body / read inside a function passed to `handleSubmit`) was rejected by the same `eslint-plugin-react-hooks` "refs" rule (ref reads/writes are only allowed inside effects or real event-handler execution, not woven into values passed to another function during render). The key is now computed and stored via `useState`, updated only from inside the actual submit/approve event handlers, and reused across a retry of the same prompt/draft, regenerated otherwise — same idempotency behavior, ESLint-clean.
- **Button-as-link.** `frontend/src/components/ui/button.tsx` wraps Base UI's `Button`, which defaults `nativeButton=true` and warns in the console if its `render` target isn't a real `<button>` (e.g. a `next/link` `<a>`). The "Continue to mandate review" and "Back to intake" links use the exported `buttonVariants()`/plain Tailwind classes on a `Link` directly instead of `<Button render={<Link .../>}>`, avoiding the warning while keeping the same visual treatment.
- **Shared config.** Added `NEXT_PUBLIC_INTAKE_USE_TEST_BOUNDARY=true` to the root `.env.example` (directly required only by this phase; no other phase depends on it before merge, per `AGENTS.md`'s shared-spec rule).
- **New shadcn primitives.** `frontend/src/components/ui/{input,textarea,label,select}.tsx` did not exist in the configured `base-nova` registry output yet; added via `pnpm dlx shadcn@latest add input textarea label select` (no hand-built replacements). No `form` primitive existed in the registry to add; form wiring uses React Hook Form's `register`/`Controller` directly against the existing primitives instead.

## Checks

- `pnpm lint`, `pnpm typecheck`, `pnpm build` from `frontend/` after each task group, and once more before handoff.
- Manual browser pass per screen: submit the canonical prompt, trigger a validation-issue response, trigger a `STALE_DRAFT_VERSION` approval conflict, complete a successful approval; inspect console and network tabs; resize to mobile and desktop; verify keyboard/focus behavior.

## Waits and temporary blockers

None identified. Both dependencies (Fase 01, Fase 04) are merged; no declared conflict exists.
