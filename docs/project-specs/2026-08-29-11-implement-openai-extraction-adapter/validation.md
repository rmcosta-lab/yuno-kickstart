# Phase 11 validation

Keep every item unchecked until its evidence is recorded. The ordinary suite must not require a credential or network connection. Never commit a key, authorization header, source prompt, policy text, full provider payload/response, extracted private value, or credentialed evidence file.

## Provider-neutral contract and fallback

- [x] `ExtractionRequest`, `IntakeExtractor`, typed safe exceptions, and `DeterministicIntakeExtractor` match the application contract in `requirements.md`.
- [x] The deterministic extractor returns the canonical fixed proposal without network access and is usable anywhere the OpenAI implementation is injected.
- [x] Architecture tests prove the provider-neutral intake package imports no `httpx`, FastAPI, Pydantic API schema, SQLAlchemy/database, frontend, or OpenAI module.
- [x] The adapter output constructs only the merged Phase 05 immutable domain values; deterministic draft eligibility remains outside the adapter.

## OpenAI adapter and strict output

- [x] Current official [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [Responses create](https://developers.openai.com/api/reference/resources/responses/methods/create) contracts are refreshed and any relevant drift is recorded before implementation.
- [x] `httpx.MockTransport` proves the exact GA `/v1/responses` request uses the configured model, versioned server policy, strict JSON Schema, `additionalProperties: false`, `store: false`, explicit timeout, and no Realtime field.
- [x] A schema-valid canonical response maps exactly to route, pickup date/window, MXN maximum, allowed conditions, and escalation conditions.
- [x] Refusal, incomplete response, missing/extra fields, wrong primitive or collection types, malformed JSON, invalid dates/decimal/currency, duplicate/ambiguous output, unexpected item types, and oversized values raise `InvalidExtractionResponse` without constructing a proposal.
- [x] The caller owns and closes `httpx.AsyncClient`; the adapter creates no global or hidden client and adds no OpenAI SDK dependency.

## Errors, timeouts, retries, and redaction

- [x] Mocked 401/403, unavailable model, 429, timeout, connection error, retryable 5xx, non-retryable 4xx, malformed error body, and unexpected provider response map to the documented safe exception vocabulary.
- [x] Retryable categories use bounded sequential attempts and injected backoff; non-retryable categories execute exactly once; exhaustion raises the stable final category without concurrent attempts.
- [x] Exceptions, `repr`, logs, diagnostics, and captured test failures contain only allowlisted safe metadata and exclude API keys, bearer/authorization values, source prompts, policy text, full payloads/responses, and extracted values.
- [x] The request sets `store: false`; tests and implementation retain no provider response or source prompt outside the typed return/error boundary.

## Credentialed OpenAI evidence

- [x] The credentialed test is registered with `openai_credentialed`, skips safely without explicit `OPENAI_API_KEY`, and is excluded from accidental provider execution.
- [x] With explicit authorization and synthetic input, `gpt-5.6-luna` returns the strict canonical proposal through the product adapter; the result records only date, model, pass/fail category, latency, and safe request/rate-limit metadata.
- [x] No standard credential, authorization value, raw provider request/response, source prompt, or extracted field value appears in Git, terminal evidence, logs, screenshots, or test reports; no temporary credentialed evidence was created.
- [x] An unavailable credentialed run is reported as a provider limitation and leaves the deterministic fallback intact; it is never represented as a pass.

## Repository checks

- [x] `uv run ruff check .`
- [x] `uv run pytest`
- [x] `uv run pytest backend/tests/volta/intake backend/tests/volta/integrations/openai -m "not openai_credentialed"`
- [x] `make python-check`
- [x] Separately authorized: `RUN_OPENAI_CREDENTIALED=1 uv run --env-file .env pytest backend/tests/volta/integrations/openai/test_credentialed.py -m openai_credentialed --durations=1`
- [x] `git diff --check`
- [x] Complete diff, public-export, forbidden-import, retry, redaction, secret, and path-scope review passes.
- [x] `api/**`, `frontend/**`, `api/openapi.json`, generated clients, persistence code, `backend/pyproject.toml`, `uv.lock`, `.env.example`, and shared specs are unchanged; root `pyproject.toml` changes only to register the credentialed marker.

## Final gate

- [x] **PASS:** every roadmap requirement has recorded evidence, mocked and ordinary checks pass, and the separately marked credentialed result is reported accurately without exposing a standard credential.
- [ ] **BLOCKED:** no provider contract, model access, redaction, retry, test, or shared-file blocker remains.

## Recorded evidence

- On 2026-08-29, the coordinator refreshed the official OpenAI Structured Outputs, Responses create, and `gpt-5.6-luna` model pages. The current contract confirms GA `POST /v1/responses`, `store: false`, strict `text.format` JSON Schema, refusal content, terminal statuses, and variable response-output arrays. The adapter therefore validates terminal state and output structure instead of indexing the first item.
- Official HTTPX documentation was refreshed after Context7 was unavailable in this session. It confirms scoped/caller-owned `AsyncClient`, per-request timeouts, `MockTransport`, and the timeout/transport exception hierarchy used by the adapter and tests.
- `uv run ruff check .` passed.
- `uv run pytest backend/tests/volta/intake backend/tests/volta/integrations/openai -m "not openai_credentialed"` passed: 39 tests, 1 credentialed test deselected.
- `uv run pytest` passed: 217 tests, 10 skipped, 1 credentialed test deselected, with one existing FastAPI/Starlette `httpx` deprecation warning.
- `make python-check` passed with the same 217-test result and warning.
- `env -u OPENAI_API_KEY -u RUN_OPENAI_CREDENTIALED uv run pytest backend/tests/volta/integrations/openai -m openai_credentialed` skipped the single credentialed test and made no provider call; 35 mocked tests were deselected.
- On 2026-08-29, after explicit user authorization, `RUN_OPENAI_CREDENTIALED=1 uv run --env-file .env pytest backend/tests/volta/integrations/openai/test_credentialed.py -m openai_credentialed --durations=1` passed the strict canonical synthetic extraction through `gpt-5.6-luna`: PASS, 3.00-second test call, 3.07-second process result. No provider request ID or rate-limit metadata was emitted or retained.
- `git diff --check`, complete path-scope review, forbidden-import scanning, public-export review, and targeted credential/prompt/payload/log review passed. The only shared-file change is pytest marker registration/exclusion in root `pyproject.toml`.
- One explicitly authorized synthetic OpenAI extraction call was performed. No Yuno/payment/phone/database mutation, deployment, production access, or other external mutation was performed. The standard credential, prompt, request, and response were not printed or persisted, and the deterministic extractor remains the tested no-network fallback.
