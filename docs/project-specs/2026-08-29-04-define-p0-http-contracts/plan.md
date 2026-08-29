# Fase 04 implementation plan

## Work order

1. **Freeze the transport vocabulary**
   - Add small shared enums and scalar conventions for UUIDs, UTC timestamps, ISO dates, integer minor-unit money, versions, states, and opaque cursors.
   - Add the uniform safe error, field issue, request ID, idempotency, and stale-version contract before feature models.
   - Confirm that server-owned lifecycle and disposition fields never appear in create requests.

2. **Define Pydantic contracts by journey**
   - Intake draft and operation approval/retrieval.
   - Negotiation, carrier session, quote, evidence, candidate commitment, recap, and brief.
   - Inbound recovery simulation, mandate replacement, escalation, notification acknowledgement, and audit pagination.
   - Keep transport schemas in `api/app/schemas/**`; do not import or create backend domain models.

3. **Declare the `/v1` route surface**
   - Register the stable operation IDs, typed path/query/header/body inputs, success responses, and route-specific safe errors from `requirements.md`.
   - Apply the configured demo bearer dependency to every `/v1` route while keeping `/health` public.
   - Require `Idempotency-Key` and the appropriate draft or operation version on mutations.
   - Keep default contract behavior honest with `501 CONTRACT_NOT_IMPLEMENTED`; use dependency overrides or route-level fakes only in tests.

4. **Prove transport semantics close to the contract**
   - Test valid examples and rejected unknown fields for every model family.
   - Test missing/invalid authorization before delegation, safe Pydantic failures, correlation IDs, and explicit CORS headers.
   - Use deterministic injected fakes to test success serialization, same-key replay, changed-payload idempotency conflict, stale draft/operation mapping, resource absence, mandate/state conflict, and unexpected safe errors.
   - Assert stable unique operation IDs, required headers, route-specific response codes, security schemes, and no unversioned Volta path in OpenAPI.

5. **Generate and integrate the browser contract**
   - Run `make generate-openapi`, review `api/openapi.json`, then run Orval through `make generate`.
   - Review generated names and ensure mutation/query functions expose required headers, versions, typed successes, and typed bodies without manual edits.
   - Run generation again and require no diff on the second run.

6. **Run final checks and scope review**
   - Run focused API tests while iterating, followed by `make check`.
   - Review the complete diff, generated artifacts, secret/config inventory, and `git diff --check`.
   - Confirm that `backend/**`, UI source, provider code, deployment, migrations, and unrelated shared specifications did not change.

## Workstreams and ownership

| Workstream | Owner | Paths | Starts after |
| --- | --- | --- | --- |
| Contract vocabulary and feature DTOs | Fase 04 API writer | `api/app/schemas/**` | Requirements accepted. |
| Transport policies and route declarations | Fase 04 API writer | Contract routers, dependencies, error handling, `api/app/main.py`, `.env.example` | Shared errors and headers are fixed. |
| API contract tests | Fase 04 API writer | `api/tests/**` | Each model/route group exists; tests stay adjacent to changes. |
| OpenAPI and Orval generation | Fase 04 API writer | `api/openapi.json`, `frontend/src/lib/api/generated/**` | Route contract tests pass. |
| Typed Orval header generation | Fase 04 API writer | `frontend/orval.config.ts` | OpenAPI review confirms required header parameters; coordinator assigns this exact file exclusively. |
| Phase coordination and final integration | `CaioRuas24010` | Phase spec, diff review, final validation | All workstreams complete. |

There is one writer for every affected path. Generated frontend artifacts remain owned by the API writer in this phase; a frontend worker may review their usability but must not edit them. No backend workstream exists because application services and domain behavior are explicitly deferred.

## Contract checkpoints

- Checkpoint 1: common IDs, versions, money, states, safe errors, authorization, and idempotency conventions are reviewed before route-specific work.
- Checkpoint 2: all Pydantic request and response models validate canonical fixtures before route registration.
- Checkpoint 3: API tests and OpenAPI agree on every operation ID, header, success, and error response before Orval runs.
- Checkpoint 4: generated TypeScript passes type checking before the complete repository check.

## Shared files and dependencies

- No mission, stack, roadmap, or challenge-plan update is expected. If implementation exposes a shared decision, pause the affected work, notify active phase owners, route the decision through `manage-shared-specs`, and refresh this branch after it merges.
- No new dependency is expected. If one becomes necessary, the coordinator owns the manifest and matching lockfile as a pair, records the reason here, checks open pull requests touching them, and refreshes the branch before generation.
- Phase 04 is the sole initial writer for `api/openapi.json` and `frontend/src/lib/api/generated/**`. Later API contract phases must refresh after this phase merges.
- Orval 8 omits OpenAPI header parameters from named generated arguments unless `output.headers` is enabled. The coordinator inspected both local worktrees and the active remote phase branches on 2026-08-29 and found no concurrent change to `frontend/orval.config.ts`. That exact configuration file is therefore assigned exclusively to the Fase 04 API writer so required idempotency and version headers compile into the generated client. This is a compatible generator setting, not a dependency, stack, or shared-architecture change; manifests and lockfiles remain unchanged.
- Shared-spec pull request #2 merged while this phase was active and made English the primary demo language. The coordinator refreshed this branch from `origin/main` at commit `519a3de`; `RequestedLanguage.EN_US` was already part of the accepted transport enum, so the contract shape and generated client require no change. Canonical API fixtures now use `EN_US`, while `ES_MX` remains an explicitly supported contract value. Later consumers must follow the merged English journey.
- No temporary prerequisite is known. If one appears, record the wait here rather than weakening the gate.

## Safety boundaries

- Do not deploy, use production access, dial a participant, mutate a provider, create a payment, or apply a remote migration.
- Do not log or commit bearer tokens, prompts containing personal data, provider payloads, participant contact details, or private recording references.
- Use synthetic fixtures and deterministic fakes only.
- Do not turn contract DTOs into business rules or make FastAPI a backend dependency.
