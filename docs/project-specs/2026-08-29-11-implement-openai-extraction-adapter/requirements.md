# Phase 11 — Implement the OpenAI extraction adapter

## Objective and terminal outcome

- **Objective:** turn an English coordinator intake prompt into the provider-neutral `OperationProposal` accepted by the merged mandate core, using the OpenAI Responses API behind a narrow extraction protocol.
- **Target user:** the operations coordinator who needs a reviewable operation and mandate draft before any operational authority exists.
- **User-visible outcome:** this backend-only phase adds no screen or HTTP route; its terminal result is a tested adapter that Phase 12 can wire into `POST /v1/operation-drafts`, with the deterministic extractor retained for local tests and fallback demonstrations.
- **Priority:** P0, because natural-language intake is part of the complete browser journey.

## Scope

### Included

- A provider-neutral intake-extraction request, protocol, safe exception vocabulary, and deterministic fallback under the Volta core namespace.
- An OpenAI adapter using the current GA `POST /v1/responses` interface, `gpt-5.6-luna` selected by the merged Phase 02 account trial, `store: false`, a versioned server policy, and strict Structured Outputs JSON Schema.
- Exact translation from the validated structured response to the existing immutable `Route`, `PickupWindow`, `Money`, `MandateProposal`, and `OperationProposal` values.
- Explicit timeouts and bounded retries for safe, non-mutating extraction attempts, with injected transport and delay boundaries for deterministic tests.
- Mocked tests for request mapping, strict output validation, refusal/incomplete responses, authentication, model availability, rate limiting, provider failures, timeouts, network failures, retry decisions, and redaction.
- A separately marked, credential-gated synthetic test that reproduces the accepted Phase 02 extraction capability without committing evidence or exposing `OPENAI_API_KEY`.

### Excluded

- FastAPI routes, dependency wiring, HTTP error mapping, authorization, CORS, OpenAPI, Orval, or frontend changes.
- OpenAI Realtime session configuration, client-secret minting, WebRTC, WebSocket events, tools, voice, evidence, or telephony.
- Approval, mandate enforcement, carrier selection, negotiation, commitment, persistence, or audit-rule changes.
- An OpenAI SDK dependency, deployment, production access, real carrier or personal data, and any Yuno, payment, phone, or financial mutation.
- Changes to the mission, technology stack, roadmap, challenge plan, or generated artifacts.

## Dependencies, coordination, and gate

- **Depends on:** Phase 02, merged in PR #3 with credentialed extraction evidence; Phase 05, merged in PR #6 with the provider-neutral proposal contract.
- **Conflicts with:** none.
- **Branch:** `phase/11-implement-openai-extraction-adapter`.
- **Owner:** `ThallesCansi`; no tracking Issue was requested.
- **Roadmap gate:** a backend adapter implements schema-validated intake extraction behind a provider-neutral protocol; mocked tests cover strict output validation, provider errors, timeouts, retries, and redaction, while a separately marked credentialed test reproduces the accepted Phase 02 extraction capability without exposing a standard credential.
- **Fallback:** the deterministic extractor implements the same protocol and remains the no-network boundary for local tests and demonstrations. Provider failure is reported honestly and never converted into fabricated extracted facts.

## Decisions and assumptions

- Phase 02 selected `gpt-5.6-luna` after a successful account-visible strict extraction trial on 2026-08-29. The model remains explicit configuration so a later account-access decision can replace it without changing the application protocol.
- The adapter uses the already accepted `httpx.AsyncClient` dependency. The caller owns client lifecycle; the adapter receives the client and immutable configuration rather than creating a global client.
- The server policy has a stable version and fixed instructions to extract only explicit facts, represent absence explicitly, and never grant operational authority. Source prompt and policy text are excluded from representations, exceptions, and logs.
- The request uses `store: false` and a strict JSON Schema with required fields and `additionalProperties: false`. The adapter still validates response status, terminal state, refusal, output item shape, JSON types, dates, decimal money, currency, and unexpected fields before constructing domain values.
- Ordinary semantic validation remains in `CreateIntakeDraftService`; schema-valid model output is only a proposal and cannot approve an operation or bypass deterministic mandate rules.
- Extraction is non-mutating, so bounded retries may cover connection failures, timeouts, HTTP 429, and HTTP 5xx. Authentication/authorization failures, unavailable models, refusals, invalid output, and other non-retryable HTTP 4xx responses fail immediately. Tests pin the maximum attempt count and injected backoff; no concurrent duplicate attempts are allowed.
- Safe diagnostics may retain failure category, HTTP status, provider request ID, model ID, attempt count, and duration. They never retain authorization values, source prompts, policy text, full payloads/responses, or extracted field values.
- Current contract references: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [Responses create](https://developers.openai.com/api/reference/resources/responses/methods/create).

## HTTP contract gate

Phase 11 changes no HTTP contract and does not regenerate OpenAPI or Orval. The accepted Phase 04 boundary remains authoritative:

- `POST /v1/operation-drafts` accepts the existing typed intake request and returns the existing draft response on success.
- Phase 12 will compose extraction with `CreateIntakeDraftService`, authorize the caller, and translate typed extraction failures into the already accepted safe error envelope and status semantics.
- No provider status, request ID, raw output, model payload, or OpenAI exception may cross the HTTP boundary.

## Application contract gate

| Import path | Public symbols | Construction and behavior |
| --- | --- | --- |
| `yuno_backend.volta.intake.extraction` | `ExtractionRequest`, `IntakeExtractor`, `DeterministicIntakeExtractor` | `ExtractionRequest` is a frozen typed input with a redacted `source_prompt`, requested language, and extraction-policy version. `IntakeExtractor.extract(request) -> OperationProposal` is async. The deterministic implementation is constructed with a fixed proposal or injected pure mapping and performs no network access. |
| `yuno_backend.volta.intake.errors` | `ExtractionError`, `ExtractionAuthenticationError`, `ExtractionModelUnavailableError`, `ExtractionRateLimitError`, `ExtractionTimeoutError`, `ExtractionProviderError`, `InvalidExtractionResponse` | Provider-neutral, safe exceptions expose only bounded categories and optional safe metadata; messages and representations contain no prompt, credential, provider payload, or extracted values. |
| `yuno_backend.integrations.openai.extraction` | `OpenAIExtractionConfig`, `OpenAIIntakeExtractor` | Constructed with an owned-by-caller `httpx.AsyncClient`, immutable config, and injected async delay. `extract(request) -> OperationProposal` maps the strict Responses payload to existing domain values or raises only the public extraction exceptions. |

The OpenAI module owns URLs, authorization headers, JSON Schema, provider request/response parsing, retry classification, and provider error translation. The provider-neutral module imports no `httpx`, FastAPI, Pydantic API schema, database, or OpenAI type. Phase 12 may depend only on the public extraction protocol and exceptions when composing the accepted intake-draft service.

## Acceptance criteria

- The canonical synthetic English prompt produces the exact provider-neutral route, pickup date/window, MXN maximum, allowed conditions, and escalation conditions expected by the Phase 05 contract.
- Missing, extra, incorrectly typed, malformed, refused, or incomplete model output never constructs a proposal and raises a safe typed exception.
- Domain validation remains authoritative: the adapter does not approve a draft, normalize an out-of-policy fact into eligibility, or conceal validation issues.
- Tests prove the selected retryable failures stop at the configured attempt limit, non-retryable failures execute once, backoff is injected, and simultaneous retry attempts are not created.
- Tests scan exceptions, representations, request diagnostics, and captured logs for absence of the API key, authorization header, source prompt, policy text, full payloads, and extracted values.
- The credentialed test uses only synthetic data, is skipped without explicit credentials, records only redacted pass/fail metadata, and deletes or ignores any local evidence.
- `backend/**` imports no FastAPI or frontend module; API/OpenAPI/Orval and existing mandate behavior remain unchanged.
- `uv run ruff check .`, `uv run pytest`, focused backend tests, `make python-check`, and `git diff --check` pass.

## Risks and security

- **Invented or malformed facts:** strict schema plus independent parser/type validation; the deterministic draft validator still decides eligibility.
- **Provider drift:** current official contracts are reviewed during implementation, provider shapes stay inside the adapter, and mock fixtures cover unexpected responses.
- **Retry amplification and latency:** bounded sequential attempts, explicit deadlines, retry classification, injected backoff, and no hidden SDK retry layer.
- **Sensitive prompt or credential leakage:** redacted fields, allowlisted diagnostic metadata, `store: false`, synthetic tests, ignored `.env`, and direct secret/log review.
- **Account or model failure:** fail with a typed safe error and keep the deterministic extractor available; do not silently claim a live extraction succeeded.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-11-implement-openai-extraction-adapter/**` | `ThallesCansi` | Phase coordinator owns requirements, plan, and validation evidence. |
| `backend/src/yuno_backend/volta/intake/**` | Phase 11 backend writer | Sole owner of the provider-neutral extraction protocol, fallback, and exceptions. |
| `backend/src/yuno_backend/integrations/openai/**` | Phase 11 backend writer | Sole owner of OpenAI request/response mapping and retry/redaction behavior. |
| `backend/tests/volta/intake/**` and `backend/tests/volta/integrations/openai/**` | Phase 11 backend writer | Mocked, architecture, redaction, and separately marked credentialed tests. |
| `backend/src/yuno_backend/volta/**/__init__.py` and `backend/src/yuno_backend/integrations/**/__init__.py` | Phase 11 backend writer | Export only the accepted public application contract and preserve existing exports. |
| Root `pyproject.toml` | Phase 11 coordinator | Only registration/exclusion semantics for the credentialed pytest marker; refresh active branches before editing this shared file. |
| `backend/pyproject.toml`, `uv.lock`, `.env.example` | No writer expected | `httpx` and `OPENAI_API_KEY` already exist; dependency or environment inventory changes require a recorded plan update and one owner for the manifest/lockfile pair. |
| `api/**`, `frontend/**`, `api/openapi.json`, generated clients | No Phase 11 writer | No HTTP, UI, or generated contract change. |
| Shared mission, stack, roadmap, and challenge decision | No Phase 11 writer | A broad discovered decision routes through `manage-shared-specs`; this phase carries none. |
