# Fase 05 implementation plan

## Work order

1. **Freeze the public application vocabulary**
   - Create the Volta mandates namespace and public modules named in `requirements.md`.
   - Implement immutable UUID, UTC time, route, pickup-window, Decimal money, proposal, issue, draft, mandate, operation, action, and decision values.
   - Keep constructors local and safe; redact source prompts from representations before services or repositories exist.

2. **Separate draft validation from approved authority**
   - Implement a pure validator that converts semantic problems into stable ordered `DraftValidationIssue` values.
   - Cover route endpoints, pickup order, amount, P0 currency, language, conditions, and extraction-policy reference.
   - Ensure validation creates no operation, mandate, or authority and never returns raw submitted values inside reasons.

3. **Define persistence-neutral ports and deterministic test doubles**
   - Add repository, unit-of-work, clock, and ID-generator protocols with no SQLAlchemy/database import.
   - Put in-memory repositories, rollback/commit recording, fixed clock, and fixed IDs under backend tests only.
   - Fix public exception fields and stable reason ordering before application services depend on them.

4. **Implement draft creation and explicit approval services**
   - `CreateIntakeDraftService` retains the prompt and policy version, validates the proposal, creates draft version 1, and commits once.
   - `ApproveOperationService` checks existence, expected version, eligibility, and prior approval; it creates operation and mandate version 1 from immutable copies and commits once.
   - Test repository failures and rejected operations without adding database-specific rollback behavior beyond the unit-of-work contract.

5. **Implement deterministic mandate evaluation**
   - Evaluate action authority and active mandate version before price, currency, pickup window, and conditions.
   - Return all safe rejection reasons in a fixed order; derive `MandateConflict` from the same decision so boolean and exceptional paths cannot drift.
   - Prove single and combined violations, inclusive window boundaries, exact Decimal comparison, and immutability.

6. **Run final architecture and scope review**
   - Run focused backend tests during iteration, then `make python-check` from the repository root.
   - Scan the Volta core for FastAPI, Pydantic API, SQLAlchemy, database, provider, and secret imports.
   - Review `git diff`, `git diff --check`, public exports, prompt redaction, manifest/lockfile stability, and absence of unrelated changes.

## Workstreams and ownership

| Workstream | Owner | Paths | Starts after |
| --- | --- | --- | --- |
| Domain values and errors | Fase 05 backend writer | `backend/src/yuno_backend/volta/mandates/{models,errors}.py` | Requirements accepted. |
| Ports and commands | Fase 05 backend writer | `backend/src/yuno_backend/volta/mandates/{commands,repositories}.py` | Public vocabulary fixed. |
| Draft creation and approval services | Fase 05 backend writer | `backend/src/yuno_backend/volta/mandates/services.py` | Models, commands, errors, and ports fixed. |
| Unit and architecture tests | Fase 05 backend writer | `backend/tests/volta/mandates/**` | Each behavior is specified; tests remain adjacent to its implementation. |
| Public exports | Fase 05 backend writer | Volta/mandates `__init__.py` files and additive root export only if needed | Symbols and service behavior pass tests. |
| Phase coordination | `rmcosta-lab` | Phase spec directory and final diff/validation evidence | All implementation workstreams complete. |

One writer owns all backend paths because this is one narrow backend-only phase. Parallel work is limited to read-only review or non-overlapping test preparation; no second writer edits the same module.

## Contract checkpoints

- Checkpoint 1: public domain types, commands, service signatures, exceptions, and protocol method signatures match `requirements.md` before implementation branches internally.
- Checkpoint 2: validation reason codes and ordering pass pure unit tests before draft creation consumes them.
- Checkpoint 3: repository/unit-of-work fakes prove service orchestration without importing a database before Fase 06 begins.
- Checkpoint 4: Phase 04 transport examples can be mapped explicitly to domain commands in tests or fixtures without importing Pydantic models.
- Checkpoint 5: final public exports and exception fields are recorded for Fases 06 and 10 before submission.

## Shared files and downstream coordination

- No shared mission, stack, roadmap, challenge-plan, manifest, lockfile, OpenAPI, or generated-client change is expected.
- If implementation requires a new global decision, pause only the affected work, notify owners of Fases 06, 08, 10, 11, and 14, and route a broad decision through `manage-shared-specs` before continuing.
- Fase 06 consumes repository and unit-of-work protocols; Fases 08 and 14 extend the domain; Fase 10 maps the application contract into FastAPI. They must refresh from this phase after its pull request merges.
- No temporary prerequisite is known. If one appears, record the wait here instead of weakening the gate.

## Safety boundaries

- Do not deploy, use production access, apply a migration, call a provider, create a payment, dial a participant, or perform any external mutation.
- Do not log or commit raw real prompts, participant details, credentials, provider payloads, or private recording references.
- Use synthetic fixtures and deterministic fakes only.
- Do not move API transport rules, persistence implementation, carrier selection, negotiation, recovery, or provider behavior into this phase.
