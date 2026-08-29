# Phase 11 validation

Keep every item unchecked until its evidence is recorded. The ordinary suite must not require a credential or network connection. Never commit a key, authorization header, source prompt, policy text, full provider payload/response, extracted private value, or credentialed evidence file.

## Provider-neutral contract and fallback

- [ ] `ExtractionRequest`, `IntakeExtractor`, typed safe exceptions, and `DeterministicIntakeExtractor` match the application contract in `requirements.md`.
- [ ] The deterministic extractor returns the canonical fixed proposal without network access and is usable anywhere the OpenAI implementation is injected.
- [ ] Architecture tests prove the provider-neutral intake package imports no `httpx`, FastAPI, Pydantic API schema, SQLAlchemy/database, frontend, or OpenAI module.
- [ ] The adapter output constructs only the merged Phase 05 immutable domain values; deterministic draft eligibility remains outside the adapter.

## OpenAI adapter and strict output

- [ ] Current official [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [Responses create](https://developers.openai.com/api/reference/resources/responses/methods/create) contracts are refreshed and any relevant drift is recorded before implementation.
- [ ] `httpx.MockTransport` proves the exact GA `/v1/responses` request uses the configured model, versioned server policy, strict JSON Schema, `additionalProperties: false`, `store: false`, explicit timeout, and no Realtime field.
- [ ] A schema-valid canonical response maps exactly to route, pickup date/window, MXN maximum, allowed conditions, and escalation conditions.
- [ ] Refusal, incomplete response, missing/extra fields, wrong primitive or collection types, malformed JSON, invalid dates/decimal/currency, duplicate/ambiguous output, unexpected item types, and oversized values raise `InvalidExtractionResponse` without constructing a proposal.
- [ ] The caller owns and closes `httpx.AsyncClient`; the adapter creates no global or hidden client and adds no OpenAI SDK dependency.

## Errors, timeouts, retries, and redaction

- [ ] Mocked 401/403, unavailable model, 429, timeout, connection error, retryable 5xx, non-retryable 4xx, malformed error body, and unexpected provider response map to the documented safe exception vocabulary.
- [ ] Retryable categories use bounded sequential attempts and injected backoff; non-retryable categories execute exactly once; exhaustion raises the stable final category without concurrent attempts.
- [ ] Exceptions, `repr`, logs, diagnostics, and captured test failures contain only allowlisted safe metadata and exclude API keys, bearer/authorization values, source prompts, policy text, full payloads/responses, and extracted values.
- [ ] The request sets `store: false`; tests and implementation retain no provider response or source prompt outside the typed return/error boundary.

## Credentialed OpenAI evidence

- [ ] The credentialed test is registered with `openai_credentialed`, skips safely without explicit `OPENAI_API_KEY`, and is excluded from accidental provider execution.
- [ ] With explicit authorization and synthetic input, `gpt-5.6-luna` returns the strict canonical proposal through the product adapter; the result records only date, model, pass/fail category, latency, and safe request/rate-limit metadata.
- [ ] No standard credential, authorization value, raw request/response, source prompt, or extracted field value appears in Git, terminal evidence, logs, screenshots, or test reports; ignored temporary evidence is deleted after review.
- [ ] A failed or unavailable credentialed run is reported as a provider limitation and leaves the deterministic fallback intact; it is never represented as a pass.

## Repository checks

- [ ] `uv run ruff check .`
- [ ] `uv run pytest`
- [ ] `uv run pytest backend/tests/volta/intake backend/tests/volta/integrations/openai -m "not openai_credentialed"`
- [ ] `make python-check`
- [ ] Separately authorized: `uv run --env-file .env pytest backend/tests/volta/integrations/openai -m openai_credentialed`
- [ ] `git diff --check`
- [ ] Complete diff, public-export, forbidden-import, retry, redaction, secret, and path-scope review passes.
- [ ] `api/**`, `frontend/**`, `api/openapi.json`, generated clients, persistence code, `backend/pyproject.toml`, `uv.lock`, `.env.example`, and shared specs are unchanged; root `pyproject.toml` changes only to register the credentialed marker.

## Final gate

- [ ] **PASS:** every roadmap requirement has recorded evidence, mocked and ordinary checks pass, and the separately marked credentialed result is reported accurately without exposing a standard credential.
- [ ] **BLOCKED:** record any unresolved provider contract, model access, redaction, retry, test, or shared-file blocker and keep Phase 12 from consuming the adapter.
