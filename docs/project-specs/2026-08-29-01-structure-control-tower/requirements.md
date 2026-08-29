# Fase 01 — Structure the control tower shell

## Objective, target user, and user-visible outcome

Give the Volta control tower a responsive Next.js shell so the operations coordinator can see the complete P0 journey's navigation and layout before any real data exists. The user-visible outcome is a browsable, presentation-only application: the coordinator can move between intake, mandate review, carrier sessions, comparison, evidence, recovery, escalation, and audit, and every screen shows a coherent loading, empty, or error state with synthetic fixtures.

## Scope

Included:

- App Router routes, layout, and navigation for: intake, mandate review, carrier/negotiation sessions, quote comparison, evidence, recovery, escalation, and audit trail.
- Reusable visual primitives (shadcn/ui + Base UI + Tailwind) used across those screens: status badges, timeline/audit list item, quote comparison card, session/call card, escalation banner.
- View-level state only: loading, empty, and error placeholders driven by local synthetic fixtures (no network calls).
- Responsive layout for mobile and desktop widths.

Excluded (left to later phases per the roadmap):

- Any call to a generated API client or FastAPI route (Fase 04/07/09/etc.).
- Any Yuno, OpenAI Realtime, or Twilio code — Volta does not use Yuno at all ([tech-stack.md](../tech-stack.md)).
- Business rules: mandate validation, carrier ranking, negotiation, commitment, or audit logic.
- Real Realtime/voice UI (Fase 13) and outbound-call controls (Fase 20).

Priority: P0 — this phase is one of the four phases that can start independently and is a prerequisite for Fase 07, 09, 16, and 20.

Assumptions:

- The existing bootstrap homepage (`frontend/src/app/page.tsx`, `health-experience.tsx`) is a placeholder the control tower shell replaces; nothing there is a durable contract.
- Screen content is fully synthetic (hardcoded/local fixtures) and clearly does not represent real operations.

Risks:

- Building UI ahead of the real HTTP contract (Fase 04) risks shapes that don't match the generated types later. Mitigation: keep fixtures as narrow local types colocated with each screen, not shared "DTO-shaped" modules, so Fase 07/09/16/20 can replace them without a wide refactor.

Fallback: if a screen's real data model is still uncertain, ship its shell with an explicit empty/placeholder state rather than guessing fixture shape.

## Dependencies, conflicts, gate, branch

- Depends on: none
- Conflicts with: none
- Gate (from [roadmap.md](../roadmap.md)): The frontend renders a responsive control tower shell with synthetic presentation-only fixtures for intake, mandate review, carrier sessions, comparison, evidence, recovery, escalation, and audit; loading, empty, and error states pass `make frontend-check` plus browser console, network, and responsive smoke tests.
- Branch: `phase/01-structure-control-tower`
- Tracking Issue: none (not requested)

## Owner

GitHub: `joaosouza11`

## Acceptance criteria (one coherent vertical slice)

- A coordinator can navigate from a landing/overview screen to each of: intake, mandate review, carrier sessions, comparison, evidence, recovery, escalation, and audit.
- Every screen renders a loading state, an empty state, and an error state using local synthetic fixtures and a manual state toggle (no live provider or timer dependency required for the demo).
- Layout does not overflow, clip controls, or produce inaccessible touch targets at mobile and desktop widths.
- No generated API file is edited; no network call is made from this phase's code.

## Layer decisions

- Frontend: App Router with Server Components as the default; `"use client"` only at the smallest interactive leaf (state toggles for demoing loading/empty/error, navigation menu interaction). Strict TypeScript, Tailwind CSS, shadcn/ui and Base UI primitives per [tech-stack.md](../tech-stack.md).
- API/BFF, Backend/core, Data, Yuno, AI: not applicable — this phase makes no server, database, or provider call.
- Security: no credentials, no `NEXT_PUBLIC_` secret, nothing beyond static synthetic content.
- Visual and accessibility: semantic HTML, labeled controls, visible focus states, sufficient contrast, and no reliance on color alone for status (e.g., `SIMULATED` vs `CANDIDATE` vs escalation states use icon + text + color).

## Ownership matrix

| Path | Writer |
| --- | --- |
| `frontend/src/app/**` (new control tower routes/layout) | Fase 01 (this phase) |
| `frontend/src/components/control-tower/**` (new shared primitives) | Fase 01 (this phase) |
| `frontend/src/app/page.tsx`, `frontend/src/components/health-experience.tsx` | Fase 01 (this phase) — replaced or relocated, not deleted silently without noting it in `plan.md`/PR |
| `docs/project-specs/2026-08-29-01-structure-control-tower/**` | Fase 01 (this phase) |
| `frontend/src/lib/api/generated/**`, `api/openapi.json` | Not touched by this phase (Fase 04 is sole initial writer) |
| Shared manifests (`frontend/package.json`, `pnpm-lock.yaml`) | Fase 01 only if a net-new primitive dependency is required; otherwise untouched |

HTTP contract gate and application contract gate: not applicable — this phase defines no backend-facing contract.
