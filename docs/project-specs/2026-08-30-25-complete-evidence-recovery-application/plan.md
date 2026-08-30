# Fase 25 — Plan

## Task groups

1. **Freeze the facade contract** — add the six mutation inputs, two read inputs, complete projections, recovery fixture protocol, safe errors, and exports. Compare every field with the unchanged Fase 04 response models before persistence work depends on them.
2. **Make replay atomic and exact** — extend canonical operation names and the durable typed result snapshot; lock by operation name/key, compare fingerprints, and expose a shared service transaction pattern that commits mutation, audit, result snapshot, and idempotency together.
3. **Complete recap and brief facts** — extend commands/models for call ownership, rendered recap content/hash, and structured brief tuples; update services and in-memory fakes with missing/mismatched/replay/rollback tests.
4. **Define deterministic recovery fixtures** — implement the two provider-neutral scripts, validate the safe artifact through existing private evidence storage, and pass complete terms, evidence metadata, or escalation context into the recovery service.
5. **Complete atomic recovery** — persist safe replacement commitment plus distinct evidence, attempt and notification in one transaction; persist bad-path attempt plus contextual escalation without changing the commitment; cover stale, blocked, missing-evidence, concurrency, and rollback paths.
6. **Wrap Fase 24 mutations** — add facade methods and atomic replay for mandate replacement, explicit escalation, and notification acknowledgement without weakening their immutable-version, one-open-escalation, first-actor, or safe-context invariants.
7. **Complete operation and audit projections** — add repository list/query ports, active escalation and notification operation state, complete artifact histories, deterministic ordering, a stable cursor, and the 1–100 bound without direct SQL outside adapters.
8. **Add the reversible migration** — persist new recap, brief, recovery, evidence, and replay facts with ownership/check constraints and only demonstrated ordering/idempotency indexes; test upgrade, compatible downgrade, refusal before destructive DDL, and re-upgrade.
9. **Run PostgreSQL integration checks** — prove exact replay/conflict for all six mutations, complete round trips, cursor pages, good/bad scripts, missing evidence, stale races, constraints, and injected transaction failures.
10. **Final verification** — run backend Ruff/pytest, focused PostgreSQL suites, `make python-check`, import-boundary and sensitive-data checks, `git diff --check`, and full diff review.

## Ownership and sequencing

- One backend writer (`rmcosta-lab`) owns every Fase 25 implementation path and this specification directory. No API or frontend writer is authorized.
- Groups 1–2 freeze typed contracts and transaction semantics before parallelizable model/query work. Groups 3–6 may be developed independently only after that checkpoint, but the single writer integrates their shared unit-of-work and migration changes.
- Group 7 follows durable model contracts; group 8 follows all persisted facts and precedes PostgreSQL validation. No manifest or lockfile edit is anticipated.

## Contract and integration checkpoints

- After group 1: every accepted request field has one typed destination or documented deterministic fixture source; every response field has a durable backend source.
- After group 2: a replay after later operation changes returns the originally stored typed projection, while a different normalized request under the same key changes nothing.
- After group 3: recap hash/content and all four brief collections reload exactly and preserve ownership/order.
- After groups 4–5: safe recovery has distinct playable evidence for the replacement; bad recovery has complete bounded escalation context and preserves the winner.
- After group 6: all Fase 24 behavior remains green and the six facade mutations share identical replay semantics.
- After group 7: operation and audit results contain every accepted artifact, stable keyset order for artifact histories, the accepted business-ranked quote comparison, page bounds, and no raw recording bytes/path, transcript, contact, or provider payload.
- Before review: refresh `origin/main`, confirm Fases 10 and 24 remain DONE and conflicts remain absent, then notify the Fase 15 owner to refresh after merge.

## Shared decisions and temporary waits

- No mission, stack, roadmap, or challenge-plan change is carried by this phase.
- Contract clarification during integration: the accepted HTTP/API tests establish `quote_comparison` as a deterministic business ranking rather than a timeline collection. The backend keeps selected/better eligible quotes first and rejected quotes afterward; `(created_at, id, kind)` keyset ordering applies to paged artifact histories. This clarification changes no route, DTO, OpenAPI, or generated client and was communicated to the backend writer before final validation.
- Fase 15 remains paused until Fase 25 completes and merges; its worktree must then refresh from the resulting `origin/main` before API integration resumes.
- If implementation requires an HTTP-contract change, a provider, or a shared architecture decision, stop and coordinate through `manage-shared-specs` rather than editing API/generated/shared files here.

## Explicit limits

No deployment, production access, provider call, live financial or telephony mutation, remote migration, API/OpenAPI/Orval change, frontend change, manifest/lockfile change, or unrelated remote action is authorized.
