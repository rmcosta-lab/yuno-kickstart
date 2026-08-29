# Fase 09 — Validation

Gate: Using generated client types and injected conforming responses, the frontend renders one to three workflow sessions, quote changes, mandate violations, no-eligible-carrier escalation, comparison, one active winner, loading, reconnect, terminal, and retry states; frontend checks and browser smoke tests pass.

## Contract and scope integrity

- [x] Injected success scenarios compile against generated `OperationResponse`, `NegotiationResponse`, session, quote, escalation, and commitment types without parallel transport DTOs. `satisfies` checks live in `frontend/src/features/negotiation/demo-source.ts`.
- [x] UI state types describe presentation only and do not calculate carrier rank, quote eligibility, mandate validity, or winner selection. The presentation filters quotes by server-owned `call_id` and highlights only the generated active commitment's `quote_id`.
- [x] `api/openapi.json` and `frontend/src/lib/api/generated/**` are unchanged. The OpenAPI SHA-256 remains `a12852533b330eec399f1420fbb8524879042b34828a51bce5c6dec97e812af2`, and a Git-tree comparison against the pre-implementation baseline is empty.
- [x] No API, backend, data, OpenAI, Twilio, Realtime, Yuno, payment, deployment, or production path enters the diff.
- [x] No new dependency is added; `frontend/package.json` and `pnpm-lock.yaml` remain unchanged with SHA-256 values `08f82af17edb9560e87685ea10b6312b76ca3dccf02970ec5d063d1d78f8815c` and `e98f8135c31719bc1c0be7b04c9a0d982dcbbb947be25d41e7c0d03b1a576290`.

## Session and comparison scenarios

- [x] One-session, two-session, and three-session scenarios render with correct carrier/source attribution and workflow state. Playwright counted exactly 1, 2, and 3 semantic session-list items.
- [x] Quote changes preserve earlier context and clearly identify current amount, currency, pickup window, conditions, validity, and mandate version.
- [x] Rejected quotes show explicit mandate-violation reasons and remain distinct through `REJECTED`, icon, heading, and text in addition to color.
- [x] The no-eligible-carrier scenario renders a pre-contact escalation and no carrier session.
- [x] A winner is highlighted only from the server-declared `ACTIVE` commitment; DevTools and Playwright counted exactly one `aria-current="true"` option while rejected and non-selected quotes remained in the accessibility tree.
- [x] Loading, reconnecting, retryable error, empty/escalated, terminal success, and terminal failure are deterministic and visually distinct across all nine scenario options.
- [x] Retry is keyboard-operable, re-enters the configured reconnecting state, and performs no external mutation. Playwright reached the native button after 13 Tab presses, observed a 3 px focus-visible ring, pressed Enter, and rendered the reconnecting state with three preserved sessions.

## Frontend checks

- [x] `PATH=/home/ABTLUS/thalles24006/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback:$PATH make frontend-check` passes from the repository root. The explicit runtime path was required because the coordinator shell did not expose `pnpm` on `PATH`.
- [x] The underlying `pnpm --dir frontend lint`, `pnpm --dir frontend typecheck`, and `pnpm --dir frontend build` all pass; Next.js 16.3.3 generated 13 static pages.
- [x] `git diff --check` passes.
- [x] Final path review confirms only this validation file and the approved sessions, comparison, and `frontend/src/features/negotiation/**` ownership paths changed.

## Browser smoke tests

- [x] Started `pnpm dev --hostname 127.0.0.1 --port 3000` from `frontend/` and exercised `/sessions` and `/comparison` with Playwright first. The integrated Browser was attempted first per `frontend-testing-debugging` but reported no connected browser; the repository-authorized Playwright fallback was used.
- [x] Inspected console and runtime state with Chrome DevTools after the user flow; no console message, uncaught error, hydration error, accessibility runtime warning, or framework error dialog remained.
- [x] Inspected network activity; Playwright and Chrome DevTools found no XHR, fetch, WebSocket, EventSource, or preflight request from the injected scenarios and no credential-like rendered text.
- [x] Verified `/sessions` and `/comparison` at 375×812 and 1440×1000 with no page-level horizontal overflow, clipped conditions, or inaccessible controls.
- [x] Verified keyboard order, a visible 3 px retry focus ring, native select/retry labels, semantic status text, and polite live announcements in the accessibility tree.
- [x] Verified long carrier names, conditions, rejection reasons, and MXN amounts wrap/read correctly in mobile and desktop evidence.

## Security and privacy review

- [x] Fixtures use synthetic carrier names, identifiers, rates, routes, and timestamps only.
- [x] Source, rendered UI, console, network, screenshots, and diff contain no secret, bearer value, real phone number, real participant data, raw provider payload, or private recording reference.
- [x] The UI labels injected scenarios as `SIMULATED · NO CONTACT` and does not claim that a carrier was contacted, a booking occurred, or a commitment became `VERIFIED`.

## Evidence to record before handoff

- [x] Planning base SHA: `bf6e392` (`Start Fase 09: Build negotiation and comparison screens`). The final submission head SHA is recorded in the pull request and finish-phase report because a commit cannot contain its own hash. Final changed paths: the Phase 09 `validation.md`; `/sessions/page.tsx`; `/comparison/page.tsx`; deletion of both obsolete route-local `fixtures.ts` files; and new `frontend/src/features/negotiation/{demo-source,index,negotiation-experience,presentation,types}.{ts,tsx}` files.
- [x] `pnpm lint`: pass with zero warnings; `pnpm typecheck`: pass; `pnpm build`: pass with 13 static pages; `git diff --check`: pass.
- [x] Browser-tested `/sessions` and `/comparison`: all nine scenarios, 375×812 and 1440×1000, zero relevant console messages, zero API/provider transport requests, no horizontal overflow, exactly one active winner, and deterministic keyboard retry.
- [x] Unavailable capability: the integrated Browser had no connected instance. Playwright fallback plus the required Chrome DevTools follow-up both passed, so the roadmap gate is unaffected. Provider credentials and live integrations were not needed or used by this frontend-only phase.

## Submission revalidation

- `PATH=/home/ABTLUS/thalles24006/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback:$PATH make frontend-check` passed again before publication: ESLint reported zero warnings, TypeScript emitted no errors, and Next.js 16.3.3 generated 13 static pages.
- Playwright exercised all nine `/sessions` scenarios at 1440×1000, counted exactly one, two, and three sessions for the corresponding scenarios, confirmed zero sessions for the pre-contact escalation, and found no page-level horizontal overflow.
- Keyboard revalidation reached `Retry simulated read` after 13 Tab presses, observed the 3 px focus-visible ring, pressed Enter, and rendered the reconnecting state with three preserved sessions.
- `/comparison` rendered four quote records, two explicit mandate rejections, earlier terms, and exactly one `aria-current="true"` winner at 1440×1000; the 375×812 viewport had no page-level horizontal overflow.
- Playwright reported zero errors and zero warnings for the tested routes and no non-static network request. Chrome DevTools, after explicit navigation to `/comparison`, reported no console message, no XHR/fetch/WebSocket/EventSource/preflight request, no framework error dialog, and no credential-like rendered text.
- `origin/main` had advanced only through merged Fase 05 backend/core and phase-documentation paths; it had no overlap with Fase 09 frontend or phase-spec ownership paths.
