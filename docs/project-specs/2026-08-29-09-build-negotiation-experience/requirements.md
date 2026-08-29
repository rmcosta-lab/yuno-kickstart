# Fase 09 — Build negotiation and comparison screens

## Coordination

- Priority: P0 frontend experience.
- Branch: `phase/09-build-negotiation-experience`.
- Owner: `ThallesCansi`.
- Tracking Issue: none requested.
- Depends on: 01 and 04, both merged with gate evidence in PRs #1 and #5.
- Conflicts with: none.
- Roadmap gate: generated client types and injected conforming responses render one to three workflow sessions, quote changes, mandate violations, no-eligible-carrier escalation, comparison, one active winner, and loading, reconnect, terminal, and retry states; frontend checks and browser smoke tests pass.

## Objective and user-visible outcome

Give the operations coordinator a truthful, inspectable view of an active text-mode negotiation before backend services are integrated. From the existing control tower, the coordinator can follow one to three carrier sessions, distinguish current and changed quotes, understand mandate rejections, see a pre-contact escalation when no carrier is eligible, compare eligible options, and identify exactly one active winner.

The terminal result is a polished frontend journey backed by deterministic injected responses that conform to the generated Phase 04 types. It is not a working backend negotiation and must not imply that a provider was contacted.

## Scope

Included:

- Replace the presentation-only `/sessions` and `/comparison` fixtures with a narrow injected data boundary whose payloads use generated `OperationResponse`, `NegotiationResponse`, `CarrierSessionResponse`, `QuoteResponse`, `CommitmentResponse`, and `ApiErrorResponse` types.
- Render deterministic scenarios for one, two, and three sessions; quote revision/history; `ELIGIBLE` and `REJECTED` quotes with explicit mandate reasons; no-eligible-carrier pre-contact escalation; and exactly one `ACTIVE` winner.
- Represent loading, reconnecting, retryable failure, terminal success, terminal provider/session failure, and empty/pre-contact escalation states without relying only on color.
- Preserve the existing control-tower navigation and visual language while improving the sessions/comparison hierarchy, responsive layout, keyboard behavior, status announcements, and retry interaction.
- Keep injected conforming fixtures deterministic so Fase 10 can replace the source with generated-client calls without rewriting presentational components.

Excluded:

- Editing `api/openapi.json` or any file under `frontend/src/lib/api/generated/**`.
- Live FastAPI, PostgreSQL, OpenAI, Twilio, Realtime, browser-audio, Yuno, payment, or carrier integration.
- Carrier filtering/ranking, quote or mandate validation, commitment eligibility, winner selection, idempotency, retry policy, or any other business decision in React code.
- Intake/mandate screens (Fase 07), API/backend wiring and text integration (Fase 10), voice/tool roundtrips (Fase 13), and evidence/recovery/audit behavior (Fases 14–16).
- New shared-stack, roadmap, deployment, production-access, or financial/telephony changes.

## Assumptions, risks, and fallback

- Assumption: the merged Phase 04 generated contract remains the browser/server source of truth throughout this phase.
- Assumption: Phase 10 will own live generated-client wiring; this phase needs only an injected source that can be replaced at the component boundary.
- Risk: deterministic scenarios could be mistaken for live operations. Mitigation: label the data as a demo scenario and issue no provider or product mutation.
- Risk: UI-derived winner or eligibility logic could diverge from the backend. Mitigation: render server-owned generated fields verbatim and assert only display invariants, never recalculate operational decisions.
- Risk: quote changes can obscure the current terms or rejection reason. Mitigation: preserve chronological/source context and expose current, superseded, eligible, and rejected states in text.
- Fallback: if a later service is unavailable or a generated hook cannot yet return success, keep the injected conforming source and deterministic state controls so the full negotiation/comparison screen gate remains reproducible.

## Acceptance criteria

- The coordinator can switch through conforming scenarios that show one, two, and three selected sessions with their generated carrier rank, channel, timestamps, and `SELECTED`, `ACTIVE`, `COMPLETED`, or `FAILED` state.
- Quote changes remain attributable to the correct carrier/session and expose amount, currency, pickup window, conditions, validity, mandate version, eligibility, and rejection reasons.
- A no-eligible-carrier response renders the generated pre-contact escalation and starts no visible carrier session.
- The comparison identifies exactly one server-declared `ACTIVE` commitment when a winner exists, does not infer one from price or rank, and keeps rejected/non-selected options visible.
- Loading, reconnecting, retryable error, terminal success, terminal failure, and empty/escalated outcomes are distinct, accessible, and reproducible without timing or provider credentials.
- Retry is an injected-source interaction only; it does not create an unapproved mutation or fabricate a backend success.
- Mobile and desktop layouts avoid page overflow and clipped content; status and changes are understandable by keyboard and screen-reader users and do not rely on color alone.
- No generated artifact, API/backend path, shared spec, provider integration, or manifest/lockfile changes unless the plan is explicitly revised and coordinated first.

## HTTP contract gate

This phase consumes but does not change the accepted Phase 04 contract:

| Method and route | Generated result used by the UI | Display semantics |
| --- | --- | --- |
| `GET /v1/operations/{operation_id}` | `200 OperationResponse` | Sessions, quote history, negotiation summary, active commitment, open escalation, operation status, and version are server-owned. |
| `POST /v1/operations/{operation_id}/negotiations` | `201 NegotiationResponse` | One to three sessions or `pre_contact_escalation`; never both fabricated by the UI. |

The injected source may return conforming success values or a sanitized `ApiErrorResponse` scenario for `401`, `403`, `404`, `409`, `422`, `429`, `500`, or `501`. The screen presents retry only for the configured retryable scenario and never displays raw requests, authorization values, stack traces, or provider payloads. No HTTP request is required to pass this phase; Fase 10 owns live transport and error mapping.

## Frontend application boundary

- Import path: `frontend/src/features/negotiation/` (new, frontend-only).
- Public symbols: a `NegotiationExperience` interactive leaf and a `NegotiationExperienceSource` interface; any fixture-source constructor remains explicitly demo-only and colocated beneath this feature.
- Construction: the App Router pages remain Server Components and pass an injected source/scenario descriptor into the smallest client leaf. Presentational session and comparison components receive generated response types or narrow view-only props derived without business decisions.
- Typed input/output: source reads resolve generated `OperationResponse` and optional `NegotiationResponse`; safe failure scenarios expose generated `ApiErrorResponse` plus a UI-owned retryability flag. UI state discriminants may describe loading/reconnecting/ready/terminal/error but must not duplicate transport DTOs.
- Exceptions: the feature catches source/transport failures at its boundary and maps them to sanitized visible state. No backend exception, FastAPI type, raw `Response`, or provider payload crosses into presentation components.

There is no backend application-service import or construction in this frontend-only phase.

## Browser/server and provider handoff

The eventual browser/server handoff remains HTTPS/JSON through the Orval-generated client to this repository's FastAPI BFF. For this phase the same generated response types are supplied by an injected deterministic source, with no network or provider call. There is no Yuno handoff and no payment data. OpenAI/Twilio/browser voice remain out of scope. The user-visible terminal result is a clearly simulated negotiation/comparison screen state, not a booking, verified commitment, or contacted carrier.

## Layer, security, visual, and accessibility decisions

- Frontend: App Router and Server Components by default; use one narrow client boundary for scenario/retry state. TanStack Query hooks are not required until live data is introduced, and query data must not be mirrored into global context.
- API/BFF, backend/core, and data: no changes. Generated server decisions are displayed, not recalculated.
- AI, Yuno, and telephony: no code or credential usage.
- Security: use synthetic identifiers, names, rates, and conditions only. Do not log or render authorization headers, secrets, phone numbers, raw provider payloads, or real participant data.
- Visual: retain the established Volta control-tower tokens and components; use clear session progression, quote-change provenance, and comparison hierarchy rather than decorative provider chrome.
- Accessibility: semantic headings/tables or lists, programmatic status text, `aria-live` only for meaningful state changes, visible focus, labeled retry/scenario controls, sufficient contrast, and text/icon cues in addition to color.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-09-build-negotiation-experience/**` | `ThallesCansi` | Phase coordinator owns requirements, plan, and validation. |
| `frontend/src/app/(control-tower)/sessions/**` | Fase 09 frontend writer | Own page composition and conforming session scenarios. |
| `frontend/src/app/(control-tower)/comparison/**` | Fase 09 frontend writer | Own page composition and conforming comparison scenarios. |
| `frontend/src/features/negotiation/**` | Fase 09 frontend writer | Own injected source, state orchestration, and negotiation-specific view components. |
| `frontend/src/components/control-tower/**` | Fase 09 frontend writer only where shared presentation must evolve | Preserve existing consumers and avoid business logic. |
| `frontend/src/lib/api/generated/**`, `api/openapi.json` | No Fase 09 writer | Consume only; never hand-edit or regenerate without an approved contract change. |
| `frontend/package.json`, `pnpm-lock.yaml` | No expected writer | No dependency is planned; if unavoidable, one coordinator owns manifest and lockfile together after plan revision. |
| `docs/project-specs/{mission,tech-stack,roadmap}.md`, `docs/decisions/challenge-plan.md` | No Fase 09 writer | No shared decision change is required. Coordinate through `manage-shared-specs` if that changes. |
| `api/**`, `backend/**`, all other frontend routes | No Fase 09 writer | Explicitly out of scope. |
