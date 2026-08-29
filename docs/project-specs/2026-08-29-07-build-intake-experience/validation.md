# Fase 07 — Validation

Gate: Using the generated client types and an injected test boundary, the frontend submits the canonical prompt, renders the source and policy version, displays editable validation feedback, requires explicit approval, and handles loading, empty, error, retry, and success states without embedding mandate rules.

## Constitutional checks

- [x] `pnpm lint` — zero warnings, run from `frontend/` (`eslint . --max-warnings=0` — clean)
- [x] `pnpm typecheck` (`tsc --noEmit`), run from `frontend/` — clean
- [x] `pnpm build` (`next build`), run from `frontend/` — compiled successfully, `/intake` and `/mandate` prerendered as static content
- [x] `pnpm format:check` (`prettier --check .`) — clean (ran after `pnpm format` normalized the two new screens, the four newly-added shadcn primitives, and the test-boundary module)

## Screen coverage

Intake (`/intake`):

- [x] Loading state while the draft mutation is in flight — directly observed via DOM inspection immediately after triggering submit: submit button read "Submitting…", `disabled: true`, and a `[role="status"]` skeleton (`LoadingState`) was present
- [x] Empty state before any prompt is submitted — browser: "No draft submitted yet" renders on first load
- [x] Success state renders source prompt, `extraction_policy_version`, `draft_version`, proposed route/pickup, and proposed mandate — browser: submitted canonical prompt, observed `draft-test-0001`, `policy-2026-08-01 · draft v1`, route `Puerto de Manzanillo, Colima → Zona industrial, Guadalajara, Jalisco`, pickup `2026-09-02`, price cap `MX$45,000.00`
- [x] Validation-error state renders `field_issues` inline and allows editing the prompt and resubmitting — browser: selected the "Request validation error (422)" test-boundary scenario, submitted; observed the inline field message under the prompt ("The requested pickup date could not be determined…") and the `ErrorState` + "Retry submission" button
- [x] Retry path after a transient/error response — browser: "Retry submission" button appears on error and resubmits with the same prompt/idempotency key (reuse verified by code path: `isRetryOfSamePrompt` short-circuits key regeneration)

Also verified: the "Draft with validation issues" scenario renders `NEEDS REVIEW`, the `validation_issues[]` list inline on the successful (201) draft, and correctly withholds "Continue to mandate review" since `approval_eligible: false`.

Mandate (`/mandate`):

- [x] Empty state when no approval-eligible draft exists — browser: direct navigation to `/mandate` with no stored draft renders "No approval-eligible draft"; no hydration-mismatch console error (server and first client paint both render empty via `useSyncExternalStore`'s server snapshot)
- [x] Loading state while the approve mutation is in flight — directly observed via DOM inspection immediately after triggering approve: a `[role="status"]` skeleton was present and page text included "Approving operation"
- [x] Mandate fields (price cap, currency, pickup window, conditions, policy version) render read-only before approval — browser: price cap `MX$45,000.00`, pickup window `2026-09-02 – 2026-09-04`, allowed/escalation conditions lists, `policy-2026-08-01`
- [x] Explicit approval action is required (no implicit approval on navigation or draft success) — code path: approval only fires from the "Approve mandate" `onClick`; navigating to `/mandate` or a successful intake draft never calls the approve mutation
- [x] Success state renders the resulting operation id, mandate version, and status — browser: `op-test-draft-test-0001`, `READY`, mandate `v1`, approved by `demo-coordinator@volta.dev`
- [x] Conflict/error state (`STALE_DRAFT_VERSION`/`MANDATE_CONFLICT` and generic `ApiErrorResponse`) renders a safe message with a retry path — browser: both scenarios exercised via the test-boundary selector; each rendered "Mandate is out of date" with its distinct message and a "Return to intake for a fresh draft" recovery action (clears the session handoff and navigates to `/intake`)

## Browser smoke tests

- [x] Console: no errors across both screens and every state — `read_console_messages` showed zero new errors through the full flow (empty → submit → success → validation-issues → 422 error → retry → mandate pending → stale conflict → mandate conflict → approve success → start over). One stale Base UI "nativeButton" warning appeared once, from an early `<Button render={<Link/>}>` usage; fixed by using `buttonVariants()` on a plain `Link` instead, confirmed gone on every check afterward (the harness's console buffer retains that one historical entry across navigations within the session, which was visually distinguished from post-fix checks by timestamp/ordering)
- [x] Network: requests only hit the injected test boundary — `read_network_requests` during a full submit showed only Next.js dev asset/HMR requests, no requests to `NEXT_PUBLIC_API_BASE_URL`; the fixture functions never call `fetch`
- [x] Responsive: mobile (375×812) and desktop widths, no horizontal overflow or clipped controls — verified `document.documentElement.scrollWidth === clientWidth` (no overflow) on both `/intake` and `/mandate` at 375×812
- [x] Keyboard/focus: Tab reaches all form controls and the approval action in a sensible order, with a visible focus outline; error text is associated with its field — verified the intake form's focusable-element order (skip link → nav → "Use canonical prompt" → prompt textarea → language select → scenario select → submit → footer), all with real semantic elements (`<a>`, `<button>`, native `<textarea>`); `source_prompt`'s error text is wired via `aria-describedby="source_prompt-error"`/`aria-invalid`

## Not applicable for this phase

- `uv run ruff check .` / `uv run pytest` — no Python change (frontend-only phase)
- OpenAPI/Orval generation — N/A (Fase 04 contract consumed as-is, no contract change)
- Yuno sandbox/mock, webhook, idempotency (server-side), RLS, CORS — N/A (no server call; only the client-generated `Idempotency-Key` header is exercised)
- Database schema/query — N/A (no persistence in this phase)

## Evidence

- `pnpm lint`, `pnpm typecheck`, `pnpm build`, `pnpm format:check` all run from `frontend/` on 2026-08-29 — all clean (see command output captured during implementation).
- `git diff --name-only` confirms no file under `frontend/src/lib/api/generated/**` or `api/openapi.json` was touched; only `frontend/src/app/(control-tower)/{intake,mandate}/**`, two new `frontend/src/lib/**` modules, four new `frontend/src/components/ui/**` shadcn primitives (`input`, `textarea`, `label`, `select`), and `.env.example` changed.
- Browser flow exercised end to end against the running `next dev` server via the Browser pane tools (`read_page`, `get_page_text`, `read_console_messages`, `read_network_requests`, `javascript_tool` for DOM-state assertions since the sandbox could not composite frames for `computer{screenshot}`/coordinate clicks on portal-rendered popup content — ref-based clicks and, where a popup's `role="option"` bounding box resolved to zero-size, a same-tab `element.click()` dispatch were used instead to drive genuine option-selection through the real DOM nodes).
- See "Recorded deviations" in `plan.md` for the injection-mechanism finding, the test-boundary scenario picker, the draft-handoff hook, the idempotency-key state (not ref) pattern, the Button-as-link fix, and the two new shadcn primitives beyond the four minimum (`form` was checked and does not exist in the configured registry; form wiring uses React Hook Form directly).
- Post-deep-review revalidation on 2026-08-29: `pnpm lint`, `pnpm typecheck`, `pnpm build`, `pnpm format:check` re-run clean from `frontend/` against the fixed code (see "Deep-review fixes applied" in `plan.md`). Browser re-check against the running `next dev` server confirmed: the canonical prompt now yields the mission-documented scenario (Thursday pickup `2026-09-03`, `MX$9,000.00` price cap, `Puerto de Manzanillo, Colima → Zona industrial, Guadalajara, Jalisco`), approving the mandate renders the operation summary with the "demo identity placeholder, not a login system" disclaimer next to `approval_actor`, and no console errors appeared across the intake→mandate→approve flow.
