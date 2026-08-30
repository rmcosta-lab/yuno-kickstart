# Phase 12 — Expose the Realtime session boundary

## Objective and terminal outcome

- **Objective:** wire the accepted OpenAI intake extractor into the live text application and expose a secure FastAPI boundary that mints one narrowly configured, short-lived Realtime client secret for the authorized demo operator.
- **Target user:** the operations coordinator who needs natural-language intake and a browser voice session without receiving the standard OpenAI credential.
- **User-visible outcome:** the existing intake route uses the OpenAI extractor when configured, and the generated client can request an ephemeral credential for the later Phase 13 WebRTC flow. This phase does not create a peer connection or active call.
- **Priority:** P0, because it unlocks browser voice while preserving deterministic text mode.

## Scope

### Included

- Compose `OpenAIIntakeExtractor` into the existing `TextNegotiationApplication` factory while retaining the deterministic extractor as an explicit no-network fallback.
- Add a provider-neutral client-secret issuer contract and an OpenAI adapter for `POST /v1/realtime/client_secrets`, reusing the accepted Phase 23 session values and narrow English, audio, VAD, instruction, and tool configuration.
- Add `POST /v1/realtime/client-secrets` with explicit demo-bearer authorization, required allowlisted `Origin`, bounded per-identity rate limiting, and a server-derived privacy-preserving safety identifier.
- Return only the ephemeral value, expiry, safe session identifier, and configured model through a typed Pydantic response; do not expose the standard key or raw provider session payload.
- Set `Cache-Control: no-store, private, max-age=0` and `Pragma: no-cache` on every successful credential response and safe error response from this route.
- Translate provider-neutral extraction and credential failures into stable public errors without leaking prompts, instructions, credentials, provider payloads, or internal exceptions.
- Regenerate `api/openapi.json` and `frontend/src/lib/api/generated/**` through `make generate` and verify the generated operation without hand-editing it.
- Add safe configuration names for the OpenAI key, model/session policy, and keyed safety-identifier derivation where the current inventory does not already cover them.

### Excluded

- Browser WebRTC setup, microphone or playback handling, Realtime event/tool roundtrips in the browser, reconnect behavior, or any rendered UI change; Phase 13 owns those outcomes.
- FastAPI telephony WebSocket ingress, Twilio, outbound calls, call-status webhooks, recordings, or media bridging; Phases 18–20 own those outcomes.
- New negotiation, mandate, commitment, evidence, persistence, migration, or audit rules.
- Client-controlled model, instructions, tools, voice, VAD, safety identifier, expiry, or provider payload fields.
- Automatic provider calls in ordinary tests, deployment, production access, real participant data, Yuno, payments, or financial mutations.
- Changes to the mission, technology stack, roadmap, or challenge decision.

## Dependencies, coordination, and gate

- **Depends on:** Phase 10, merged in PR #15 with the PostgreSQL-backed text journey; Phase 11, merged in PR #11 with the extraction adapter; Phase 23, merged in PR #13 with the Realtime adapter contract and credentialed evidence.
- **Conflicts with:** none.
- **Branch:** `phase/12-expose-realtime-boundary`.
- **Owner:** `ThallesCansi`; no tracking Issue was requested.
- **Roadmap gate:** FastAPI wires structured extraction to the OpenAI adapter and exposes a tested `/v1` Realtime client-secret contract that authorizes the demo identity, validates allowed origins, rate limits requests, supplies a privacy-preserving safety identifier, disables caching, and returns a narrowly scoped short-lived credential; OpenAPI and Orval regenerate, and logs and errors contain no standard or ephemeral secret.
- **Fallback:** deterministic extraction and the integrated text journey remain available when OpenAI configuration or Realtime issuance is unavailable. Provider failure stays visible and never masquerades as a live voice session.

## Decisions and assumptions

- Current official OpenAI documentation supports browser WebRTC through an ephemeral key minted server-side with the standard key at `POST /v1/realtime/client_secrets`; the browser later uses the ephemeral key with `POST /v1/realtime/calls`. The BFF returns a client secret only and does not proxy SDP or create the call in this phase.
- The server, not the browser, fixes the Realtime session configuration and sends `OpenAI-Safety-Identifier` while minting the secret. A keyed HMAC-SHA256 over the stable synthetic demo subject produces the lowercase 64-character identifier; neither the bearer token nor the derivation secret is retained in logs or public models.
- The credential endpoint has no request body and is intentionally not idempotent: each authorized request creates a new short-lived credential, while the existing sliding-window limiter bounds retries and abuse. No `Idempotency-Key` or replay header applies.
- The provider response is accepted only when the secret, future expiry, session identifier, and expected model/session type are present and bounded. Raw provider objects, request IDs, and configuration are not forwarded.
- `Origin` is required and must exactly match one configured CORS origin before the provider is called. This is a browser abuse boundary in addition to ordinary CORS behavior, not a substitute for bearer authorization.
- The existing `httpx.AsyncClient`, application lifespan, and injected transport seams are reused. No new runtime dependency is expected; any discovered dependency change must keep its manifest and lockfile under one writer.
- Extraction remains non-authoritative: the OpenAI adapter proposes structured facts, then existing draft validation and explicit coordinator approval preserve the mandate boundary.
- Official references: [Realtime WebRTC](https://developers.openai.com/api/docs/guides/realtime-webrtc) and [Realtime client secrets](https://developers.openai.com/api/reference/resources/realtime/subresources/client_secrets).

## HTTP contract gate

`POST /v1/realtime/client-secrets` has stable `operation_id="create_realtime_client_secret"` and no request body.

| Result | Contract |
| --- | --- |
| `201 Created` | `RealtimeClientSecretResponse { client_secret, expires_at, session_id, model }`; `client_secret` is bounded and excluded from representations, and the response includes `X-Request-ID`, `Cache-Control: no-store, private, max-age=0`, and `Pragma: no-cache`. |
| `401` | Missing or invalid configured demo bearer; `WWW-Authenticate: Bearer`; provider not called. |
| `403` | Missing or non-allowlisted `Origin`, or an authenticated actor without authority; provider not called. |
| `429` | Authorized identity exceeded the configured window; stable `RATE_LIMITED` envelope and `Retry-After`; provider not called. |
| `502` | Typed OpenAI authentication, model, invalid-response, timeout, transport, or provider failure becomes a single safe `REALTIME_UNAVAILABLE` envelope with no upstream detail. |
| `500` | Unexpected failure uses the existing safe internal-error envelope. |

The route never accepts or returns the standard API key, safety identifier, session instructions, tool schema, bearer value, provider request ID, or raw provider response. Cache-prevention headers apply to the route's typed errors as well as success.

The existing `POST /v1/operation-drafts` request and success schema remain unchanged. Its runtime construction uses `OpenAIIntakeExtractor` when the optional provider configuration is present, maps typed extraction failures to the existing safe error envelope, and preserves the deterministic fallback only when explicitly configured rather than silently converting provider failure into synthetic success.

## Application contract gate

| Import path | Public symbols | Construction, typed inputs/outputs, and exceptions |
| --- | --- | --- |
| `yuno_backend.volta.realtime.client_secrets` | `RealtimeClientSecretRequest`, `RealtimeClientSecret`, `RealtimeClientSecretIssuer` | Frozen request carries the accepted `RealtimeSessionRequest`; frozen result carries a redacted secret plus expiry, session ID, and model ID. `issue(request) -> RealtimeClientSecret` is async and raises only provider-neutral Realtime exceptions. |
| `yuno_backend.integrations.openai.client_secrets` | `OpenAIRealtimeClientSecretConfig`, `OpenAIRealtimeClientSecretIssuer` | Constructed with a caller-owned `httpx.AsyncClient` and immutable config. It owns the official HTTPS URL, authorization and safety headers, narrow session payload mapping, response validation, timeout, and provider-error translation. |
| `yuno_backend.volta.intake.extraction` | existing `IntakeExtractor`, `ExtractionRequest` | `TextNegotiationApplication` continues to depend on this protocol; API dependency construction injects `OpenAIIntakeExtractor` or the explicitly selected deterministic fallback without changing application inputs or outputs. |
| `app.realtime_service` | `RealtimeClientSecretService`, `get_realtime_client_secret_service` | API-side adapter derives the safety identifier from the authorized synthetic subject, invokes the issuer once, maps only safe fields to the Pydantic response, and owns no provider payload mapping. Tests inject a fake service/issuer. |

The backend remains free of FastAPI and Pydantic API schemas. The API never constructs provider JSON in a router, and the OpenAI adapter never imports an API or frontend module.

## Acceptance criteria

- An authorized request from an allowlisted origin returns the typed secret response once, with all no-store headers and a stable generated-client operation.
- Missing/invalid bearer, missing/untrusted origin, and exhausted rate limits fail before client-secret issuance and use the declared status, error code, request ID, and headers.
- Captured provider requests prove the standard key stays in the server authorization header, the safety identifier is a stable lowercase HMAC digest, and the narrow session contains only the accepted model, English audio/VAD behavior, fixed instructions, and allowlisted tools.
- Malformed, expired, wrong-session, wrong-model, timeout, authentication, rate-limit, and provider responses become safe typed failures; no provider payload or status detail crosses the HTTP boundary.
- Repeated successful requests are not replayed and remain bounded by the limiter; concurrent requests do not bypass the configured per-identity limit.
- `POST /v1/operation-drafts` uses the configured OpenAI extractor in dependency-wiring tests while the explicit deterministic mode remains reproducible without network access.
- Tests and scans prove the standard key, ephemeral secret, bearer token, safety derivation secret, safety identifier, instructions, source prompt, authorization headers, and raw provider payloads are absent from logs, exceptions, representations, validation errors, generated files, and diffs.
- OpenAPI and Orval regenerate deterministically; existing consumers typecheck and build; `make check` and focused API/backend tests pass.

## Risks and security

- **Credential exposure:** keep both credentials out of representations and logs, return the ephemeral value only over the authorized no-store response, and scan captured errors and generated artifacts.
- **Public-demo abuse:** require bearer plus exact origin, derive one bounded identity, apply the sliding-window limiter before network I/O, and expose `Retry-After` without provider detail.
- **Over-broad session authority:** fix the model, instructions, tools, audio, voice, and VAD server-side; reject provider responses that do not match the expected session.
- **Provider drift or outage:** validate the current official schema during implementation, keep provider mapping isolated, map failures safely, and preserve explicit deterministic text mode.
- **Extraction changes operational authority:** retain structured validation and coordinator approval; no extraction result creates an operation or commitment directly.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-12-expose-realtime-boundary/**` | `ThallesCansi` | Phase coordinator owns planning and validation evidence. |
| `backend/src/yuno_backend/volta/realtime/**` and focused tests | Phase 12 backend writer | Owns only the provider-neutral client-secret issuer values/protocol and exports; preserves Phase 23 connection contracts. |
| `backend/src/yuno_backend/integrations/openai/client_secrets.py`, package exports, and focused tests | Phase 12 backend writer | Sole owner of client-secret provider mapping, validation, timeout, and redaction. |
| `api/app/config.py`, `.env.example`, and configuration tests | Phase 12 API writer | Owns server-only settings and safe inventory names; never adds a public OpenAI secret. |
| `api/app/realtime_service.py`, router/schema/security/error wiring, and `api/tests/**` | Phase 12 API writer | Owns the HTTP boundary, extraction composition, origin/authorization/rate-limit/cache semantics, and safe error mapping. |
| `api/openapi.json` and `frontend/src/lib/api/generated/**` | Phase 12 coordinator | Generated only through `make generate` after the Pydantic contract is stable; never hand-edited. |
| `frontend/src/**` outside generated client | No Phase 12 writer | No rendered UI or browser Realtime lifecycle change. |
| `backend/pyproject.toml`, `api/pyproject.toml`, `uv.lock` | No writer expected | Existing `httpx` is reused; a discovered dependency change requires one coordinator-owned manifest/lockfile update. |
| Mission, stack, roadmap, challenge plan | No Phase 12 writer | No shared decision is planned; a broad discovered decision routes through `manage-shared-specs`. |
