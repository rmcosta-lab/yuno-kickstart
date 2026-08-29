# Fase 07 — Validation

Gate: Using the generated client types and an injected test boundary, the frontend submits the canonical prompt, renders the source and policy version, displays editable validation feedback, requires explicit approval, and handles loading, empty, error, retry, and success states without embedding mandate rules.

## Constitutional checks

- [ ] `pnpm lint` — zero warnings, run from `frontend/`
- [ ] `pnpm typecheck` (`tsc --noEmit`), run from `frontend/`
- [ ] `pnpm build` (`next build`), run from `frontend/`

## Screen coverage

Intake (`/intake`):

- [ ] Loading state while the draft mutation is in flight
- [ ] Empty state before any prompt is submitted
- [ ] Success state renders source prompt, `extraction_policy_version`, `draft_version`, proposed route/pickup, and proposed mandate
- [ ] Validation-error state renders `field_issues` inline and allows editing the prompt and resubmitting
- [ ] Retry path after a transient/error response

Mandate (`/mandate`):

- [ ] Empty state when no approval-eligible draft exists
- [ ] Loading state while the approve mutation is in flight
- [ ] Mandate fields (price cap, currency, pickup window, conditions, policy version) render read-only before approval
- [ ] Explicit approval action is required (no implicit approval on navigation or draft success)
- [ ] Success state renders the resulting operation id, mandate version, and status
- [ ] Conflict/error state (`STALE_DRAFT_VERSION`/`MANDATE_CONFLICT` and generic `ApiErrorResponse`) renders a safe message with a retry path

## Browser smoke tests

- [ ] Console: no errors across both screens and every state
- [ ] Network: requests only hit the injected test boundary (or, if unavailable, are visibly absent) — no unexpected calls
- [ ] Responsive: mobile (375×812) and desktop widths, no horizontal overflow or clipped controls
- [ ] Keyboard/focus: Tab reaches all form controls and the approval action in a sensible order, with a visible focus outline; error text is associated with its field

## Not applicable for this phase

- `uv run ruff check .` / `uv run pytest` — no Python change (frontend-only phase)
- OpenAPI/Orval generation — N/A (Fase 04 contract consumed as-is, no contract change)
- Yuno sandbox/mock, webhook, idempotency (server-side), RLS, CORS — N/A (no server call; only the client-generated `Idempotency-Key` header is exercised)
- Database schema/query — N/A (no persistence in this phase)

## Evidence

To be filled in during implementation (`implement-frontend-phase`) with command output, screenshots/DOM excerpts per state, and confirmation that no `frontend/src/lib/api/generated/**` file or `api/openapi.json` was edited.
