# Fase 10 — Implementation plan

## Gate and temporary wait

The roadmap gate remains unchanged: the generated client must complete the canonical prompt-to-winner text journey against PostgreSQL, with the listed negative paths, API tests, `make generate`, `make check`, and browser console/network inspection passing. Starting the phase does not make an incomplete response acceptable.

`WAITING_ON_PHASE_14`: Fase 08 persists only an opaque `evidence_id`, while the accepted `CommitmentResponse`, operation/audit projections, and terminal winner require real `CommitmentEvidenceResponse` fields. Work through persisted quote comparison may proceed now. Commitment serialization, evidence-bearing audit output, and terminal prompt-to-winner validation must wait until Fase 14 merges its typed evidence application contract and persistence. No fake recording reference, `audio_start_ms`, item/event ID, lifecycle, recap, or other placeholder may cross the API.

## Task groups in dependency order

1. **Freeze the cross-layer mapping before parallel work**
   - Inventory every accepted Phase 04 request/response field against the public Fases 05/06/08 symbols and freeze backend-command, domain-result, Pydantic-response, and safe-exception mappings.
   - Keep the existing `/v1` paths, operation IDs, authorization, idempotency, stale-state, and error schemas authoritative. Out-of-mandate current-version quotes remain persisted `REJECTED` results; stale mandate/version requests remain write-free conflicts.
   - Define one API application adapter over injected typed services and PostgreSQL units of work; routers stay transport-only and the backend imports neither FastAPI nor Pydantic.
   - Freeze deterministic text fixtures for the canonical Thursday/MXN 9,000 operation, one-to-three carrier selection, quote revisions, an over-mandate quote, and no eligible carrier. The backend remains the only owner of eligibility, comparison, and winner decisions.

2. **Repair backend integration defects that do not depend on Fase 14**
   - Carry `cargo_label` through the deterministic extraction proposal, persisted draft, approved operation, mappers, repositories, and operation projection; add a reversible migration and round-trip/backfill tests if the durable schema changes.
   - Extend durable idempotency to draft creation and approval and expose replay metadata for all integrated mutations. A same-key/same-normalized-request replay must return the original logical result without new rows, versions, statuses, or audit events; changed input must raise a safe conflict. Preserve the Fase 08 replay guarantees for negotiation and quotes.
   - Add typed query/projection services needed to reload an operation, sessions, quote history, comparison, and current safe audit state from PostgreSQL. Do not synthesize the evidence-dependent commitment projection.
   - Keep deterministic extraction as the text-mode fallback; OpenAI extraction wiring remains owned by later provider phases.

3. **Wire the FastAPI boundary through quote comparison**
   - Replace `CONTRACT_NOT_IMPLEMENTED` only for the application operations whose responses can be serialized completely: draft creation, approval, operation retrieval without an active evidence-dependent commitment, negotiation start, quote recording, and the safe pre-evidence audit/read projection.
   - Construct the deterministic extractor, services, carrier catalog, clock/ID providers, async session factory, and units of work in centralized dependencies. Map domain failures to the accepted safe `401/403/404/409/422/500` responses and propagate `Idempotency-Replayed: true` from durable replay metadata.
   - Add API tests against PostgreSQL for validation correction, no eligible carrier, stale draft/operation/mandate, out-of-mandate quote retention, same-request replay, changed-payload key reuse, rollback, authorization ordering, request IDs, safe errors, and reloads.
   - Leave commitment/evidence-complete operation and audit paths honestly unavailable until the wait clears; never return a partial success that Pydantic fills with invented values.

4. **Replace frontend demo sources with the live generated-client seam**
   - Add an explicit browser demo-auth boundary: the coordinator supplies the opaque demo bearer at runtime, it is held in memory only, and the generated fetch mutator adds it to `Authorization`. Do not create a `NEXT_PUBLIC_` bearer value, persist the token in browser storage, or log/render it.
   - Switch intake and mandate approval from their injected fixture boundary to generated mutations while preserving logical idempotency keys across uncertain retries and regenerating them only for a changed/new action.
   - Replace the Fase 09 injected negotiation read source with generated operation reads and text controls that start selection and submit the deterministic carrier quotes. Invalidate/refetch server state after mutations; do not infer eligibility, ordering, or a winner in React.
   - Preserve accessible loading, validation, conflict, retry/reconnect, no-eligible, rejected-quote, and comparison states. Before Fase 14, visibly stop after comparison and do not expose an action that fabricates evidence or claims a winner.

5. **Pre-wait integration checkpoint**
   - Exercise prompt -> validation correction -> approval -> negotiation -> valid/rejected quote comparison against PostgreSQL, plus the no-eligible and duplicate/stale paths.
   - Run focused backend/API/frontend checks and inspect browser console and network traffic. Record that this checkpoint is useful progress, not the Fase 10 gate.

6. **Formalize and clear the prerequisite**
   - Before evidence-dependent implementation resumes, obtain authority for the shared roadmap change and use `manage-shared-specs` on a dedicated specifications branch to make Fase 14 a formal prerequisite for Fase 10 without renaming the phase or weakening its gate. Notify the owners of Fases 12, 14, 15, and 17 because their sequencing or integration branches are affected.
   - Keep this branch at `WAITING_ON_PHASE_14` for commitment/evidence work. After the roadmap clarification and Fase 14 merge, refresh `phase/10-pass-text-negotiation` from the remote default branch before touching shared backend persistence/application paths; resolve overlaps with the Fase 14 owner rather than duplicating or overwriting them.

7. **Complete the post-Fase-14 slice**
   - Consume the merged evidence repository/service contract to validate `evidence_id`, serialize the real nested evidence in `CommitmentResponse`, expose the evidence-bearing active commitment in operation/audit reads, and wire candidate commitment creation without changing the accepted HTTP contract.
   - Add the final text control that creates a commitment only from the server-selected best eligible quote and supplied real evidence fixture owned by Fase 14. Verify exactly one active winner and durable same-request replay with the original response and replay header.
   - Complete the canonical browser prompt-to-winner journey and all roadmap negative paths against PostgreSQL; no recap, recovery, provider, voice, or telephony work is pulled into this phase.

8. **Generation and final verification**
   - Run API contract tests, then `make generate`; review `api/openapi.json` and Orval output, and require a second generation to be clean. No accepted schema change is expected, so any diff is reviewed as a contract decision before frontend consumers change.
   - Run focused tests beside each change, followed by `make python-check`, `make frontend-check`, and `make check`.
   - Browser-test the full text journey at mobile and desktop widths, then inspect console, failed requests, request/replay headers, authorization redaction, and absence of provider traffic. Review migrations, generated artifacts, secrets, unrelated changes, and `git diff --check`.

## Workstreams and one-writer ownership

Contract decisions in task group 1 complete before the three implementation writers start. Their paths do not overlap; generated artifacts belong to the API writer even though one output directory is under `frontend/`.

| Workstream | Sole writer | Paths | May start |
| --- | --- | --- | --- |
| Backend integration and persistence | Fase 10 backend writer | `backend/src/yuno_backend/volta/{intake,mandates,negotiations,persistence}/**`, any new provider-neutral integration/query package, `backend/migrations/**`, `backend/tests/volta/**` | After task group 1; evidence-dependent paths only after Fase 14 refresh. |
| API wiring and contract generation | Fase 10 API writer | `api/app/**`, `api/tests/**`, `api/openapi.json`, `frontend/src/lib/api/generated/**` | After task group 1 and each backend public contract checkpoint. |
| Frontend live journey | Fase 10 frontend writer | `frontend/src/app/(control-tower)/{intake,mandate,sessions,comparison}/**`, `frontend/src/features/negotiation/**`, `frontend/src/lib/api/volta-fetch.ts`, auth/handoff helpers, focused frontend checks | After the API mapping is frozen; terminal winner only after generated post-Fase-14 handoff. |
| Phase coordination | Phase coordinator | `docs/project-specs/2026-08-29-10-pass-text-negotiation/**`, `.env.example` if the obsolete fixture flag changes, final integration/diff review | Throughout. |
| Shared roadmap clarification | `manage-shared-specs` owner on its dedicated branch | `docs/project-specs/roadmap.md` and directly required coordination notes only | Independently, followed by owner notification and branch refresh. |
| Manifests and lockfiles | Phase coordinator only if unavoidable | `pyproject.toml` with `uv.lock`; `frontend/package.json` with `pnpm-lock.yaml` | No dependency is planned; revise the plan before writing. |

## Scope guardrails

- No deployment, production access, provider credential, OpenAI/Twilio/Yuno call, real carrier contact, booking, payment, or financial mutation is authorized.
- No mission, stack, challenge-plan, or other roadmap change belongs on the phase branch; the prerequisite is formalized through `manage-shared-specs`.
- No generated file is hand-edited, no HTTP DTO is copied into TypeScript, and no evidence/commitment field is guessed to make the browser look complete.
