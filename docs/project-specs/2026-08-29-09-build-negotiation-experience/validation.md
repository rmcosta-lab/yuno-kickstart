# Fase 09 — Validation

Gate: Using generated client types and injected conforming responses, the frontend renders one to three workflow sessions, quote changes, mandate violations, no-eligible-carrier escalation, comparison, one active winner, loading, reconnect, terminal, and retry states; frontend checks and browser smoke tests pass.

## Contract and scope integrity

- [ ] Injected success scenarios compile against generated `OperationResponse`, `NegotiationResponse`, session, quote, escalation, and commitment types without parallel transport DTOs.
- [ ] UI state types describe presentation only and do not calculate carrier rank, quote eligibility, mandate validity, or winner selection.
- [ ] `api/openapi.json` and `frontend/src/lib/api/generated/**` are unchanged.
- [ ] No API, backend, data, OpenAI, Twilio, Realtime, Yuno, payment, deployment, or production path enters the diff.
- [ ] No new dependency is added; if the plan changes, `frontend/package.json` and `pnpm-lock.yaml` move together under the single coordinator.

## Session and comparison scenarios

- [ ] One-session, two-session, and three-session scenarios render with correct carrier/source attribution and workflow state.
- [ ] Quote changes preserve earlier context and clearly identify current amount, currency, pickup window, conditions, validity, and mandate version.
- [ ] Rejected quotes show explicit mandate-violation reasons and remain distinct without relying on color alone.
- [ ] The no-eligible-carrier scenario renders a pre-contact escalation and no carrier session.
- [ ] A winner is highlighted only from the server-declared `ACTIVE` commitment; rejected and non-selected options remain visible.
- [ ] Loading, reconnecting, retryable error, empty/escalated, terminal success, and terminal failure are deterministic and visually distinct.
- [ ] Retry is keyboard-operable, re-enters the configured injected state, and performs no external mutation.

## Frontend checks

- [ ] `make frontend-check` passes from the repository root.
- [ ] Evidence records the underlying `pnpm lint`, `pnpm typecheck`, and `pnpm build` results.
- [ ] `git diff --check` passes.
- [ ] Final path review confirms only the approved Fase 09 spec and frontend ownership paths changed.

## Browser smoke tests

- [ ] Start `pnpm dev` from `frontend/` and exercise the deterministic session and comparison journeys with the browser testing flow first.
- [ ] Inspect console and runtime state with Chrome DevTools after the user flow; no uncaught error, hydration error, or accessibility-related runtime warning remains.
- [ ] Inspect network activity; injected scenarios make no unexpected API or provider request and expose no authorization value or credential.
- [ ] Verify `/sessions` and `/comparison` at 375×812 and a desktop viewport with no page-level horizontal overflow, clipped conditions, or inaccessible controls.
- [ ] Verify keyboard order, visible focus, retry/scenario labels, semantic status text, and meaningful state announcements.
- [ ] Verify long carrier names, conditions, rejection reasons, and MXN amounts wrap/read correctly.

## Security and privacy review

- [ ] Fixtures use synthetic carrier names, identifiers, rates, routes, and timestamps only.
- [ ] Source, rendered UI, console, network, screenshots, and diff contain no secret, bearer value, real phone number, real participant data, raw provider payload, or private recording reference.
- [ ] The UI labels injected scenarios as demo/simulated and does not claim that a carrier was contacted, a booking occurred, or a commitment became `VERIFIED`.

## Evidence to record before handoff

- [ ] Commit SHA and final changed-path list.
- [ ] Command outputs or concise result counts for lint, typecheck, build, and `git diff --check`.
- [ ] Browser-tested routes, scenario matrix, viewport sizes, console findings, and network findings.
- [ ] Any skipped check or unavailable capability, with its effect on the roadmap gate.
