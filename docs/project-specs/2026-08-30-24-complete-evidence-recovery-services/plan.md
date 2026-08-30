# Fase 24 — Plan

## Task groups

1. **Freeze the application boundary** — add the three commands, result-model extensions, safe exceptions, explicit exports, and focused construction/invariant tests. Confirm the symbols in `requirements.md` before persistence or service work depends on them.
2. **Extend persistence-neutral ports** — add notification update and explicit immutable mandate-replacement operations; reuse the inherited negotiation lookup for `call_id`. Update deterministic in-memory fakes without exposing sessions or SQLAlchemy types.
3. **Implement mandate replacement** — lock the operation, validate version and escalation ownership/state, build mandate version `current + 1`, activate it atomically, resolve the escalation, append status/audit entries, and cover success plus missing/foreign/resolved/stale/rollback cases.
4. **Implement explicit escalation** — resolve the call session to its operation, validate bounded context and expected version, preserve commitments, create one open escalation, transition status, append audit, and test duplicate/open-escalation and wrong-call cases.
5. **Implement notification acknowledgement** — lock the operation/notification scope, persist the first actor and timestamp, return identical retries without a second mutation, reject conflicting actors, and test missing/stale/rollback cases.
6. **Add the reversible migration and SQLAlchemy mapping** — extend escalation context and notification decision/acknowledgement storage with checks, foreign keys, and demonstrated indexes; implement mappers and repositories for every new field and the immutable mandate activation path.
7. **Run PostgreSQL integration checks** — repository round trips, migration upgrade/downgrade/re-upgrade, old/new mandate history, partial-ack constraint rejection, relationship constraints, idempotent acknowledgement, and injected transaction rollback.
8. **Final verification** — run backend Ruff/pytest, `make python-check`, import-boundary checks, secret/sensitive-context review, `git diff --check`, and inspect the complete diff.

## Ownership and sequencing

- One backend writer (`rmcosta-lab`) owns all Fase 24 implementation paths. No frontend or API writer is authorized in this branch.
- Groups 1–2 fix the contract before services and persistence proceed. Groups 3–5 may be developed independently only after those ports are stable, but they converge on the same unit of work and therefore must be integrated by the single writer.
- Group 6 follows the domain contract and precedes PostgreSQL verification. No manifest/lockfile edit is anticipated.

## Checkpoints

- After group 2: compare command fields and returned domain values with the already accepted Fase 04 request/response models without importing them.
- After group 3: prove both mandate rows reload and only the new row is active; prove failure leaves the previous active mandate and escalation unchanged.
- After groups 4–5: prove explicit escalation never mutates commitments and acknowledgement replay never changes actor, timestamp, operation version, or audit count.
- Before publication for review: refresh `origin/main`, confirm Fase 14 remains DONE, recheck conflicts (none), and tell the Fase 15 owner to refresh after Fase 24 merges.

## Shared decisions and temporary waits

- No shared mission, stack, roadmap, or challenge decision is carried by this phase.
- Fase 15 remains paused until Fase 24 completes and merges; its branch must refresh from `origin/main` before integration resumes.
- If implementation reveals a required HTTP-contract change, stop and coordinate through `manage-shared-specs`/the Fase 15 owner instead of editing API or generated files here.

## Explicit limits

No deployment, production access, live financial mutation, provider call, remote migration, API/OpenAPI/Orval change, frontend change, or unrelated remote action is authorized.
