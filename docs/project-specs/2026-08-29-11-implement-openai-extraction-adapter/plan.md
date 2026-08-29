# Phase 11 implementation plan

1. **Freeze contracts and provider facts**
   - Refresh current OpenAI Structured Outputs and Responses create documentation before writing provider mappings.
   - Reconfirm the merged Phase 02 model/result and the exact Phase 05 `OperationProposal` constructors.
   - Add the provider-neutral extraction request, protocol, safe exceptions, and deterministic implementation first so the OpenAI adapter has a stable target.
   - Register the separately credentialed pytest marker in root `pyproject.toml`; make no dependency or lockfile change.

2. **Implement strict provider mapping**
   - Add immutable OpenAI configuration for base URL, model `gpt-5.6-luna`, timeout, bounded attempts, policy version/instructions, and safe backoff.
   - Inject the caller-owned `httpx.AsyncClient` and async delay boundary.
   - Build `POST /v1/responses` with bearer authentication, `store: false`, the versioned server policy, synthetic-safe request metadata, and strict JSON Schema.
   - Parse only the documented terminal response shape; reject refusals, incomplete responses, missing/extra output, malformed JSON, invalid types/dates/decimal values, and unsafe size bounds before constructing an `OperationProposal`.

3. **Translate failure and retry behavior**
   - Map authentication, unavailable-model, rate-limit, timeout/network, retryable 5xx, non-retryable provider, and invalid-output paths to the public safe exception vocabulary.
   - Retry only the explicitly selected non-mutating transient categories, sequentially and within the configured limit; inject delay so unit tests do not sleep.
   - Allowlist diagnostic metadata and prove source prompts, policy text, credentials, full provider bodies, and extracted values cannot enter exceptions or logs.

4. **Test beside the behavior**
   - Add protocol/fallback and architecture tests under `backend/tests/volta/intake/**`.
   - Use `httpx.MockTransport` under `backend/tests/volta/integrations/openai/**` for exact request mapping, success parsing, strict validation, every error category, retry counts, timeout, redaction, and client-lifecycle ownership.
   - Add a separately marked, environment-gated synthetic credentialed test that calls the accepted model only when explicitly invoked and retains no raw response or secret.
   - Run focused Ruff/pytest during iteration, then `make python-check`.

5. **Integrate exports and close evidence**
   - Export only the accepted public symbols; run forbidden-import and provider-leak scans.
   - Confirm `api/**`, `frontend/**`, OpenAPI, Orval, persistence, manifests/lockfile, `.env.example`, and shared specs remain unchanged except the planned pytest marker registration.
   - Run `git diff --check`, review the complete diff and secret-sensitive terms, and record exact command/evidence results in `validation.md`.
   - Run the credentialed test only with explicit local credentials and report it separately from the ordinary deterministic suite.

## Ownership and sequencing

- One backend writer owns `backend/src/yuno_backend/volta/intake/**`, `backend/src/yuno_backend/integrations/openai/**`, their tests, and required package exports.
- The phase coordinator owns this specification directory and the narrow pytest-marker edit in root `pyproject.toml`.
- Contract modules land before adapter and tests depend on them. There is no parallel frontend or API workstream, no OpenAPI/Orval generation checkpoint, and no browser validation because the phase is backend-only.
- Before touching root `pyproject.toml`, refresh open phase/specification pull requests and coordinate if another branch owns that shared file. Refresh `origin/main` before publication and before Phase 12 consumes the result.
- No shared stack or roadmap change is planned, and no temporary prerequisite wait remains.
- No deployment, production access, live provider mutation beyond the separately invoked synthetic extraction read, phone call, Yuno operation, payment, or unrelated remote change is authorized.
