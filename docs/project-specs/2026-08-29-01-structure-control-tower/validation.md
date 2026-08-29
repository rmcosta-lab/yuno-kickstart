# Fase 01 — Validation

Gate: The frontend renders a responsive control tower shell with synthetic presentation-only fixtures for intake, mandate review, carrier sessions, comparison, evidence, recovery, escalation, and audit; loading, empty, and error states pass `make frontend-check` plus browser console, network, and responsive smoke tests.

## Constitutional checks

- [ ] `pnpm lint` — zero warnings
- [ ] `pnpm typecheck`
- [ ] `pnpm build`

## Screen coverage (loading / empty / error, each)

- [ ] Overview
- [ ] Intake
- [ ] Mandate review
- [ ] Carrier / negotiation sessions
- [ ] Quote comparison
- [ ] Evidence
- [ ] Recovery
- [ ] Escalation
- [ ] Audit trail

## Browser smoke tests

- [ ] Console: no errors across all screens and state toggles
- [ ] Network: no unexpected requests (this phase makes none)
- [ ] Responsive: mobile width and desktop width checked per screen, no overflow or clipped controls
- [ ] Keyboard/focus: navigation and interactive elements reachable and visibly focused

## Not applicable for this phase

- OpenAPI/Orval generation — N/A (no contract change)
- Yuno sandbox/mock, webhook, idempotency — N/A (Volta does not use Yuno)
- Database schema/query — N/A (no persistence in this phase)
- Secrets/CORS/authorization — N/A (no server call)

## Evidence

(Fill in during `finish-phase` with actual command output and screenshots/notes from the browser pass.)
