# Phase 12 implementation plan

## Ordered task groups

1. **Refresh and lock contracts.** Refresh `origin/main`, open phase/specification pull requests, and current official OpenAI Realtime WebRTC/client-secret documentation. Confirm the response fields, server-set safety identifier, session schema, and existing Phase 10/11/23 public symbols. Freeze the HTTP and application gates in `requirements.md` before dependent work.
2. **Add the provider-neutral issuance boundary.** Implement the frozen client-secret request/result/protocol and safe exceptions under `backend/src/yuno_backend/volta/realtime/`; preserve Phase 23 exports and architecture tests.
3. **Implement the OpenAI issuer.** Add the injected `httpx` adapter for `POST /v1/realtime/client_secrets`, map the accepted session configuration, validate expiry/session/model fields, translate failures, and prove secret/payload redaction with mock transport tests. Do not open a WebRTC call.
4. **Wire live extraction.** Construct `OpenAIIntakeExtractor` in the API application factory when explicitly configured, retain deterministic mode as a deliberate fallback, share caller-owned client lifecycle, and add focused dependency-wiring and safe-error tests for `POST /v1/operation-drafts`.
5. **Expose the client-secret route.** Add the Pydantic response, stable operation ID, bearer and exact-origin dependencies, keyed safety-identifier derivation, route/service wiring, rate-limit behavior, no-store headers on success and errors, and safe provider failure mapping. Unit-test each rejection before provider invocation and concurrent limit behavior.
6. **Regenerate and integrate.** Run API tests, `make generate`, inspect `api/openapi.json` and the Orval diff, rerun generation to prove determinism, and typecheck/build the unchanged frontend consumers. Do not hand-edit generated files.
7. **Validate and review.** Run focused backend/API tests, `make check`, `git diff --check`, architecture and import-boundary scans, full diff review, and targeted secret/log/representation scans. Record exact evidence in `validation.md`; credentialed OpenAI trials remain separate and require explicit authorization.

## Workstreams and ownership

- After task 1 freezes the contracts, the **backend writer** owns the provider-neutral issuer, OpenAI mapping, exports, and backend tests.
- In parallel, the **API writer** owns `api/**`, including the Pydantic/OpenAPI source, generated `api/openapi.json`, settings, extraction construction, HTTP schema/route/service/security/error behavior, and API tests. As an exact shared-path exception, the API writer also exclusively owns `.env.example`. The API writer uses a fake issuer until the backend contract lands and does not edit backend provider mapping.
- The **frontend writer** starts only after the API worker reports a stable OpenAPI checkpoint and exclusively owns `frontend/**`, including Orval generation under `frontend/src/lib/api/generated/**`. There is no handwritten UI change.
- The **phase coordinator** exclusively owns this specification directory, reviews integration, and records validation evidence; it does not regenerate artifacts while a layer worker owns them.
- Manifest and lockfile files remain untouched unless implementation proves a dependency is necessary; if so, the coordinator becomes their sole writer and records the reason before the paired update.

## Contract and integration checkpoints

- **Checkpoint A:** frozen method/path, response fields, statuses, error codes, cache headers, no request body, no idempotency semantics, and provider-neutral issuer symbols.
- **Checkpoint B:** backend mock tests show exact OpenAI request mapping, server-derived safety identifier, response validation, typed failures, and redaction without network access.
- **Checkpoint C:** API dependency tests show the live extraction adapter reaches the existing text application and all credential-route rejections occur before provider I/O.
- **Checkpoint D:** `make generate` commits the OpenAPI/Orval contract once; a second run is clean and the frontend builds against the generated operation.
- **Checkpoint E:** the complete focused and repository-wide gates pass with standard and ephemeral credentials absent from logs, errors, representations, artifacts, and diff.

## Shared decisions and external actions

- No mission, technology-stack, roadmap, challenge-plan, deployment, production-access, database, or migration change is planned.
- No temporary prerequisite wait remains: Phases 10, 11, and 23 are merged with gate evidence.
- No live provider call is required for the ordinary gate because Phases 02, 11, and 23 already recorded credentialed capability evidence. Any new credentialed smoke test must use synthetic content, remain separately marked, and receive explicit authorization.
- No browser call, phone call, participant contact, Yuno operation, payment, financial mutation, or unrelated remote change is authorized.
