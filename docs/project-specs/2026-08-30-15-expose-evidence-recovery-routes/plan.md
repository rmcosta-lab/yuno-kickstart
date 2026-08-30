# Fase 15 — Plan

## Task groups

1. **Freeze the integration map** — compare every accepted Fase 04 request/response with the merged Fase 10, 14, and 24 public application symbols, error vocabulary, persistence results, and idempotency behavior. Record an explicit field-by-field mapping before modifying API code.
2. **Resolve the durable query/idempotency checkpoint** — prove that one backend-facing facade can return recap, brief, recovery, post-contact escalation, notification, and audit projections and can durably replay each mutation. The API must not query repositories or synthesize request-only state. If this boundary is absent, pause here and add a supporting backend phase through `manage-shared-specs`.
3. **Extend application construction** — reuse the existing engine/session factory, construct fresh unit-of-work-backed Fase 14/24 services behind one application facade, retain the existing evidence-storage and text-slice behavior, and dispose the engine through the current lifecycle.
4. **Wire evidence, recap, and brief operations** — preserve the accepted evidence reservation/commitment order, enforce call/operation/commitment ownership, delegate recap/brief generation, and project only durable backend values to existing DTOs.
5. **Wire recovery mutations** — translate inbound scenarios and existing deterministic fixture terms into `SimulateInboundRecoveryCommand`; translate mandate replacement, explicit escalation, and acknowledgement requests into the Fase 24 commands; return the durable operation/recovery/escalation/notification results.
6. **Complete operation and audit projections** — return active post-contact escalation and notifications on operations, plus bounded recap, brief, recovery, escalation, notification, evidence, commitment, quote, and event histories in stable order with the accepted cursor/limit behavior.
7. **Centralize safe translation and replay** — map typed backend errors to the accepted `404`/`409` codes, retain stale current-version reporting, and prove identical replay versus conflicting reuse for every mutation without logging bodies or sensitive context.
8. **Verify the PostgreSQL journey** — exercise good recovery, bad escalation, mandate replacement/resumption, notification acknowledgement, missing evidence, stale version, rollback, and complete audit retrieval through FastAPI against isolated PostgreSQL state.
9. **Final verification** — run focused API tests, `make python-check`, unchanged OpenAPI/generated-client checks, `git diff --check`, and full diff/secret/sensitive-data review.

## Ownership and sequencing

- One API writer (`rmcosta-lab`) owns all implementation paths in this API-only phase.
- Groups 1–2 are hard prerequisites. No route wiring proceeds while the durable projection/idempotency boundary is unresolved.
- Group 3 fixes construction before groups 4–6. Evidence/recap/brief and recovery mappings can be developed independently only after the facade contract is stable, but the single writer integrates them into `VoltaTextContractService`.
- Group 7 follows the mutation/result mappings. Group 8 proves the complete HTTP-to-PostgreSQL behavior before final validation.
- No backend, frontend, generated artifact, manifest, lockfile, migration, or shared specification has a Fase 15 writer.

## Contract and integration checkpoints

- After group 1: every public request field has one typed destination or an explicitly justified server-owned derivation; every response field comes from durable backend state rather than API memory.
- After group 2: the facade returns bounded artifact histories and uses durable idempotency fingerprints/results. If not, record the temporary wait and stop implementation.
- After group 4: identical evidence/recap/brief replay returns the same durable identifiers and timestamps; missing/mismatched ownership fails safely.
- After group 5: one good simulation produces exactly one active replacement and notification; one bad simulation preserves the commitment and creates one open escalation; replacement and acknowledgement use Fase 24 behavior.
- After group 6: audit and operation responses include the new artifacts in deterministic order without raw/private data.
- Before review: regenerate OpenAPI and Orval only as a verification command, confirm a clean second generation and zero generated diff, then run the final gate.

## Temporary wait discovered during planning

Fase 24 completed the three missing recovery mutation services. The merged backend still needs to demonstrate a public application/query projection for recap content, brief fields, recovery attempts, post-contact escalations, notifications, and their complete audit history. `TextNegotiationApplication.get_operation_audit` currently exposes events, quote comparison, negotiation, and commitment history only.

Implementation therefore pauses after task group 2 if no existing backend boundary satisfies the requirements. The coordinator must then use `manage-shared-specs` to add the smallest backend prerequisite, publish and merge it, and refresh this branch from `origin/main`. This wait does not authorize direct repository access from API code or a change to the accepted HTTP contract.

The task-group-2 audit on 2026-08-30 confirmed that the boundary is absent. Two independent read-only subagents found the same blockers: missing durable HTTP response facts for recaps, briefs, recoveries, post-contact escalations, and notifications; incomplete operation/audit projections; no atomic fingerprinted idempotency for the six remaining mutations; and no safe backend-owned recovery fixture/evidence projection that the API can reuse without inventing state. `attach_commitment_evidence` remains the only Fase 15 operation already integrated honestly.

The user approved the supporting-phase path. Pull request [#19](https://github.com/rmcosta-lab/yuno-kickstart/pull/19) adds Fase 25 — Complete the evidence and recovery application facade — dependent on Fases 10 and 24, and makes Fase 15 depend on it. Fase 15 implementation remains paused until that specification merges, Fase 25 is started, implemented, validated, and merged, and this branch refreshes from the resulting `origin/main`.

## Shared decisions and branch refresh

- No mission, stack, roadmap, or challenge-plan change is carried by Fase 15.
- The query/idempotency checkpoint requires Fase 25; the separate specs pull request #19 records the dependency while this plan records the temporary wait.
- Refresh `origin/main`, the declared dependencies, remote phase refs, and pull requests immediately before implementation publication and again before review.

## Validation strategy

- Focused unit tests for transport conversion, response projection, exception translation, application construction, and engine cleanup.
- Route tests for bearer authorization ordering, required idempotency headers, rate limits, replay headers, path/body validation, stable operation IDs, statuses, and response schemas.
- PostgreSQL tests for durable replay/conflict, version races, rollback, good and bad recovery, replacement, acknowledgement, and complete artifact/audit round trips.
- Contract drift checks for `api/openapi.json` and `frontend/src/lib/api/generated/**`; a generation command must produce no diff.
- Final Python quality, whitespace, diff, secret, raw-evidence, transcript, contact, and provider-payload review.

## Explicit limits

No deployment, production access, provider call, live financial or telephony mutation, remote database migration, frontend change, backend change, contract/generated change, or unrelated remote action is authorized.
