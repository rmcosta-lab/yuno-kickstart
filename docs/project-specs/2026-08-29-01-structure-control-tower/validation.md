# Fase 01 — Validation

Gate: The frontend renders a responsive control tower shell with synthetic presentation-only fixtures for intake, mandate review, carrier sessions, comparison, evidence, recovery, escalation, and audit; loading, empty, and error states pass `make frontend-check` plus browser console, network, and responsive smoke tests.

## Constitutional checks

- [x] `pnpm lint` — zero warnings (`eslint . --max-warnings=0`, clean)
- [x] `pnpm typecheck` (`tsc --noEmit`, clean)
- [x] `pnpm build` (`next build`, all 11 routes prerendered as static content)

## Screen coverage (loading / empty / error, each)

Verified by toggling each screen's state control in a live `pnpm dev` session and inspecting the rendered DOM (skeleton present for loading, empty-state copy for empty, `Alert` copy for error, fixture content for populated).

- [x] Overview
- [x] Intake
- [x] Mandate review
- [x] Carrier / negotiation sessions
- [x] Quote comparison
- [x] Evidence
- [x] Recovery
- [x] Escalation
- [x] Audit trail

## Browser smoke tests

- [x] Console: no errors across all screens and state toggles (`read_console_messages` with `onlyErrors: true` returned none after visiting all 9 screens plus `/health`)
- [x] Network: no unexpected requests — the 9 control-tower screens issued no fetches beyond Next.js static assets/HMR; the only backend call is the pre-existing `GET /health` on the relocated `/health` route (unchanged legacy behavior, not new to this phase)
- [x] Responsive: checked at 375×812 (mobile) and native desktop width on Overview and Comparison — `document.documentElement.scrollWidth` never exceeded `clientWidth`; the primary nav scrolls horizontally within its own container (`overflow-x: auto`) instead of overflowing the page
- [x] Keyboard/focus: Tab reaches the skip-to-content link first, then nav links with a visible focus outline (`outline-style: solid`); the state-toggle control is a native `role="group"` of `<button>` elements with `aria-pressed`, fully keyboard-operable

## Not applicable for this phase

- OpenAPI/Orval generation — N/A (no contract change)
- Yuno sandbox/mock, webhook, idempotency — N/A (Volta does not use Yuno)
- Database schema/query — N/A (no persistence in this phase)
- Secrets/CORS/authorization — N/A (no server call)

## Evidence

- `pnpm lint`, `pnpm typecheck`, `pnpm build` run from `frontend/` on 2026-08-29, all clean. Build output listed 11 static routes: `/`, `/audit`, `/comparison`, `/escalation`, `/evidence`, `/health`, `/intake`, `/mandate`, `/recovery`, `/sessions`, `/_not-found`.
- Browser pass used the repository's own `pnpm dev` instance (Next.js 16.3.3 / Turbopack) via the in-app browser tool, one navigation per route plus a scripted click through all four state-toggle buttons per screen.
- No `frontend/src/lib/api/generated/**` or `api/openapi.json` file was touched; no new runtime dependency was added (shadcn `add badge card skeleton alert separator` only generated files under `frontend/src/components/ui/`, reusing already-installed `@base-ui/react` and `class-variance-authority`), so `frontend/package.json` and `frontend/pnpm-lock.yaml` are unchanged.
- The bootstrap homepage (`frontend/src/app/page.tsx`, using `health-experience.tsx`) was relocated to `frontend/src/app/(control-tower)/health/page.tsx` rather than deleted; it keeps its pre-existing live call to the FastAPI `/health` route, which predates and is out of scope for this phase.
