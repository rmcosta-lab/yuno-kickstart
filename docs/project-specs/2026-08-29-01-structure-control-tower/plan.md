# Fase 01 — Plan

Single frontend writer for this phase (no parallel workstream split needed — this is a frontend-only phase per the roadmap).

## Task groups (dependency order)

1. **Shell and navigation**
   - App Router layout with persistent navigation across: Overview, Intake, Mandate, Sessions, Comparison, Evidence, Recovery, Escalation, Audit.
   - Route segments under `frontend/src/app/(control-tower)/...` as Server Components by default.

2. **Shared visual primitives** (`frontend/src/components/control-tower/`)
   - Status badge (`CANDIDATE` / `SIMULATED` / `VERIFIED`, `ACTIVE` / `SUPERSEDED`, escalation states).
   - Session/call card, quote comparison card, audit timeline item, escalation banner.
   - Check the configured shadcn registry before hand-building any primitive shadcn already covers.

3. **Synthetic fixtures** (`frontend/src/lib/fixtures/control-tower.ts` or colocated per screen)
   - Local, narrowly-typed fixture data per screen (not shared "DTO-shaped" types) so later phases can swap in generated types without a wide refactor.
   - A small client-side toggle per screen (loading / empty / error / populated) for demo and smoke-test purposes — smallest possible client boundary.

4. **Screens** (one per roadmap gate item), each with loading, empty, and error states:
   - Intake, Mandate review, Carrier/negotiation sessions, Quote comparison, Evidence, Recovery, Escalation, Audit trail.

5. **Replace the bootstrap homepage**
   - Fold or relocate `frontend/src/app/page.tsx` and `health-experience.tsx` into the new shell (e.g., as the Overview screen or a `/health` route) — note the change explicitly in the PR body, do not delete silently.

6. **Responsive and accessibility pass**
   - Verify mobile and desktop widths, keyboard navigation, focus states, and touch target sizing across all screens.

## Contract and ownership notes

- No OpenAPI/Orval generation step in this phase — nothing here depends on `make generate`.
- One writer (this phase) for every path listed in `requirements.md`'s ownership matrix.
- No shared stack or roadmap change is anticipated. If a primitive requires a new dependency not already in `frontend/package.json`, add it here and record the reason in the PR body.

## Checks

- `pnpm lint`, `pnpm typecheck`, `pnpm build` from `frontend/` (equivalent to `make frontend-check`) after each screen group, and once more before handoff.
- Manual browser pass per screen: toggle loading/empty/error, inspect console and network tabs, resize to mobile and desktop.

## Waits and temporary blockers

None identified. This phase has no dependency and no declared conflict.
