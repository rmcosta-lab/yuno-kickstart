# Fase 09 — Plan

One frontend writer owns this isolated workstream. No API or backend worker is needed.

## Task groups in dependency order

1. **Freeze the consumed display contract**
   - Inventory the Phase 04 generated fields needed from `OperationResponse`, `NegotiationResponse`, sessions, quotes, escalation, and active commitment.
   - Define the frontend-only injected source and UI-state discriminants under `frontend/src/features/negotiation/` without copying transport DTOs or defining business rules.
   - Record presentation invariants: zero sessions only with the no-eligible/pre-contact outcome, at most three sessions, and a winner displayed only from the server-declared active commitment.

2. **Build deterministic conforming scenarios**
   - Create synthetic sources for one, two, and three sessions; quote revision; mandate rejection; pre-contact escalation; active winner; reconnect; retryable error; terminal success; and terminal failure.
   - Use generated types with compile-time conformance and stable timestamps/identifiers; label every scenario as simulated demo data.
   - Keep retry deterministic and side-effect free.

3. **Implement the session experience**
   - Evolve `/sessions` from generic cards into a workflow view that preserves rank evidence, channel, progression, quote changes, mandate violations, timestamps, and current/terminal state.
   - Keep the page a Server Component and place state controls/retry in the smallest client leaf.
   - Reuse current control-tower and shadcn primitives before adding a new primitive.

4. **Implement the comparison experience**
   - Render all current/rejected options with terms, conditions, validity, mandate version, and rejection reasons.
   - Emphasize exactly one server-declared active winner without sorting, ranking, validating, or selecting in the browser.
   - Render the no-eligible escalation as a terminal pre-contact outcome rather than an empty successful comparison.

5. **Accessibility and responsive polish**
   - Verify semantic structure, keyboard path, focus visibility, status announcements, non-color cues, long-condition wrapping, and mobile/desktop hierarchy.
   - Exercise loading, reconnect, retry, empty/escalated, active, completed, and failed states without hidden timers.

6. **Integration checkpoint and verification**
   - Confirm the source boundary can later be replaced by generated-client reads without changing presentational component contracts.
   - Run `make frontend-check`, then the browser flow in the required Playwright-first/Chrome-DevTools-second order.
   - Inspect the final diff for generated files, unexpected dependencies, secrets, real participant data, and unrelated changes.

## Contracts and generation

- Contract decisions precede component work; the Phase 04 generated models remain authoritative.
- No Pydantic/OpenAPI change and no `make generate` run are planned. If implementation discovers a missing transport field, stop and coordinate an owning API phase instead of hand-copying or editing generated output.
- Fase 10 is the integration checkpoint that replaces the injected source with real generated-client behavior. Fase 09 must leave that seam explicit.

## Tests and evidence near changed behavior

- TypeScript exhaustive state handling and generated-type conformance stay beside the injected source and scenario fixtures.
- The frontend currently has no automated test script; do not add a test dependency solely for this phase. Exercise deterministic state/scenario controls in browser smoke tests and record exact evidence in `validation.md`.
- Run focused lint/typecheck while iterating, followed by the full frontend lint/typecheck/build gate.

## Ownership and coordination

- The one-writer matrix in `requirements.md` is authoritative; no parallel writer touches the same route, feature, shared component, manifest, or lockfile.
- No shared mission, stack, roadmap, challenge-plan, generated-client, manifest, or lockfile change is anticipated.
- If an active pull request starts touching a required shared component, coordinate and refresh this branch before editing that file.
- No deployment, production access, provider call, live telephony/financial mutation, or unrelated remote change is authorized.

## Waits and temporary blockers

None. Fases 01 and 04 are merged with validation evidence, Fase 09 has no conflicts, and no remote branch or pull request previously represented this phase at claim time.
