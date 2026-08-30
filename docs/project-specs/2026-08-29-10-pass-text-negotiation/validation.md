# Fase 10 validation

Record exact evidence only after executing it. Keep every criterion unchecked until the implementation produces the stated evidence. The roadmap gate remains unchanged; the phase must not enter review or be reported as complete while any `WAITING_ON_PHASE_14` criterion remains open.

## Dependency handoff and temporary wait

- [ ] The merged Fases 06, 07, 08, and 09 are refreshed from the remote default branch, their recorded validation evidence is reviewed, and the integrated slice preserves their accepted persistence, intake, negotiation, and presentation behavior.
- [ ] The integration consumes the existing Fase 04 HTTP contract and the public typed backend contracts from Fases 05, 06, and 08 without copying transport data transfer objects into the backend or domain values into the frontend.
- [ ] **WAITING_ON_PHASE_14 — evidence:** real provider-neutral commitment evidence, including its playable private reference, `audio_start_ms`, item ID, event ID, lifecycle, access rules, and persistence, is supplied by the merged Fase 14 contract; no placeholder or invented evidence is accepted.
- [ ] **WAITING_ON_PHASE_14 — commitment:** `POST /v1/calls/{call_id}/commitments` delegates to the typed backend service and serializes a complete `CommitmentResponse` with real persisted evidence only after the Fase 14 handoff is available.
- [ ] **WAITING_ON_PHASE_14 — winner:** the canonical PostgreSQL-backed journey reaches and reloads exactly one active winner, with retry-safe transition and superseded history, only after a valid evidence-backed commitment can be created.
- [ ] **WAITING_ON_PHASE_14 — audit:** `GET /v1/operations/{operation_id}/audit` serializes the accepted complete correlated timeline, including commitment and evidence history, only after the Fase 14 audit/evidence records and public service boundary are available.
- [ ] **WAITING_ON_PHASE_14 — terminal gate:** the complete canonical prompt-to-winner browser evidence remains open until the evidence, commitment, winner, and audit criteria above all pass; partial prompt-to-comparison evidence is not reported as satisfying the roadmap gate.

## HTTP and application contracts

- [ ] `POST /v1/operation-drafts`, `POST /v1/operations`, `GET /v1/operations/{operation_id}`, `POST /v1/operations/{operation_id}/negotiations`, and `POST /v1/calls/{call_id}/quotes` delegate through injected dependencies to typed backend services and return their accepted explicit Pydantic success models and status codes.
- [ ] The phase records every backend import path, public symbol, construction dependency, typed command/result, and safe exception used by the API; backend code imports no FastAPI or Pydantic transport type.
- [ ] The accepted source prompt, extraction-policy version, synthetic `cargo_label`, route, pickup date, mandate version, operation version, selected sessions, quote terms, rejection reasons, and comparison order survive each HTTP/application mapping without fabrication or lossy normalization.
- [ ] Missing or invalid authentication returns the accepted `401` error, insufficient authority returns `403`, missing resources return `404`, stale/idempotency/state conflicts return `409`, invalid input returns `422`, rate limiting returns `429`, and unexpected failures return a redacted `500 ApiErrorResponse` with the request ID.
- [ ] Every implemented mutation requires the accepted printable ASCII `Idempotency-Key`; operation mutations enforce the expected operation or draft version; responses preserve `X-Request-ID`, and exact replays additionally preserve `Idempotency-Replayed: true`.
- [ ] The generated OpenAPI document retains stable operation IDs and explicit request, response, header, and error schemas; Orval remains the only source of browser transport types and hooks.
- [ ] Routes that remain dependent on Fase 14 stay honestly incomplete and are not backed by fabricated domain success, synthetic evidence metadata, or a transport-layer state transition.

## Backend integration

- [ ] API wiring constructs the accepted application services and PostgreSQL repositories through explicit dependency injection, with one short transaction per application operation and no database session or row escaping the backend boundary.
- [ ] Accepted intake and approval calls retain the canonical source prompt and policy version, require explicit approval, create one immutable mandate version, and reload the operation with the exact synthetic cargo label and safe aggregate state.
- [ ] Negotiation start uses only the deterministic backend eligibility/ranking rules, creates one to three synthetic carrier sessions, or persists the single pre-contact escalation when none is eligible.
- [ ] Quote recording preserves exact monetary, currency, pickup-window, condition, validity, source-session, and mandate-version values; rejected or expired quotes cannot enter the eligible comparison.
- [ ] Stale mandate, stale operation, out-of-mandate, wrong-session, rejected-quote, and non-best-quote paths raise the accepted typed exceptions and leave operation, quote, commitment, idempotency, status, and audit state consistent.
- [ ] Integration fixes do not move ranking, mandate evaluation, quote eligibility, commitment transition, persistence query, or provider mapping into FastAPI or the browser.
- [ ] Existing mandate, persistence, negotiation, rollback, concurrency, append-only audit, and restart-replay backend tests remain passing after integration changes.

## API integration

- [ ] API tests override dependencies with deterministic fakes for transport-only cases and exercise real typed backend services plus isolated PostgreSQL for the accepted integrated success and failure paths.
- [ ] Authentication and authorization run before application delegation; credentialed CORS allows only configured origins, methods, and safe request/response headers and never uses a wildcard origin.
- [ ] Pydantic rejects unknown fields, server-owned create fields, booleans or numeric strings in integer fields, invalid UUID/date/time/currency values, and oversized or malformed idempotency keys before delegation.
- [ ] Domain and persistence exceptions map centrally to stable safe HTTP errors without exposing class names, SQL/driver details, prompts, submitted condition text, credentials, provider payloads, or stack traces.
- [ ] API tests cover the roadmap paths for validation correction, no eligible carrier, duplicate mutation replay and conflicting reuse, stale mandate/version, and out-of-mandate quote rejection.
- [ ] Default `501 CONTRACT_NOT_IMPLEMENTED` behavior is removed only for routes backed by the documented real application contract; no router contains business rules or directly queries PostgreSQL.

## Frontend integration

- [ ] The intake and mandate screens call only the generated client against the configured FastAPI base URL for the real integration mode, while any retained deterministic test boundary remains explicit and cannot masquerade as the PostgreSQL-backed journey.
- [ ] The generated client submits the canonical prompt, displays source and policy version, supports editable validation correction, requires explicit approval, and reloads the resulting operation without client-side mandate rules.
- [ ] The generated client starts negotiation, renders one to three server-selected sessions or the no-eligible-carrier escalation, records/displays quote changes and mandate violations, and presents comparison order exactly as returned by the backend.
- [ ] Loading, empty, disabled, error, retry, reconnect, stale, duplicate-replay, out-of-mandate, escalation, and terminal states remain distinguishable and recoverable without duplicating a mutation.
- [ ] Browser state preserves and reuses the same idempotency key and normalized request for an uncertain retry, generates a new key only for a new logical action, and never decides eligibility, ranking, or winner state.
- [ ] No handwritten parallel HTTP data transfer object or direct edit under `frontend/src/lib/api/generated/**` enters the diff; all generated changes originate from the accepted FastAPI source through `make generate`.

## PostgreSQL, transactions, and idempotency

- [ ] An isolated PostgreSQL database migrates to the repository head and persists/reloads the canonical draft, operation, immutable mandate, status history, sessions, quotes, idempotency records, and correlated append-only audit state used by the non-waiting slice.
- [ ] Replaying each accepted mutation with the same key and normalized input after a process restart returns the original status, response identity, and replay header without duplicate rows, transitions, or audit events.
- [ ] Reusing an idempotency key with changed normalized input returns `409 IDEMPOTENCY_KEY_REUSED` and performs no write.
- [ ] Concurrent or repeated approval, negotiation-start, and quote mutations preserve uniqueness, expected-version checks, deterministic results, and atomic rollback under mapper, flush, commit, and conflict failures.
- [ ] Validation correction, no-eligible-carrier, stale mandate/version, and out-of-mandate scenarios leave a transactionally consistent operation and bounded, correlated, append-only audit trail.
- [ ] Any migration or query change is reviewed for named constraints, demonstrated indexes, reversibility, least privilege, and compatibility with the accepted Fases 06 and 08 schema; no manual or remote database mutation substitutes for a migration.

## Browser, security, and accessibility

- [ ] The rendered journey is exercised with browser automation first and then inspected for console, runtime, hydration, failed-request, CORS, and unexpected network errors at mobile and desktop widths.
- [ ] Network inspection confirms application calls go only to the configured FastAPI BFF through the generated client, with expected methods, statuses, replay headers, request IDs, and redacted captured authorization evidence; no provider or unintended endpoint is contacted.
- [ ] The approved demo authentication boundary works from the browser without embedding an example or live bearer value in OpenAPI, committed source, rendered content, browser storage, console output, screenshots, or test evidence.
- [ ] Keyboard order, semantic headings and landmarks, associated labels and error descriptions, visible focus, live loading/error announcements, non-color-only states, touch targets, contrast, text wrapping, and zero horizontal overflow pass for the affected intake, mandate, sessions, and comparison views.
- [ ] Logs, exceptions, traces, fixtures, browser evidence, generated artifacts, and Git contain no credential, authorization header value, database URL, raw provider payload, private recording reference, real participant/contact data, PAN, CVV, or payment token.
- [ ] Synthetic labels, routes, rates, prompts, UUIDs, actors, correlations, and timestamps remain clearly demo data; the UI does not claim that a carrier was contacted, delivery was verified, or an evidence-backed winner exists before the waiting criteria pass.

## Scope, diff, and external exclusions

- [ ] The implementation diff is limited to API dependency wiring and the smallest integration defects in already-owned backend/frontend paths, with one writer per path and explicit coordination for generated files, manifests/lockfiles, migrations, and shared specifications.
- [ ] The roadmap gate is not renamed, removed, weakened, or reported as satisfied; the Fase 14 wait and its resumption point remain explicit in requirements, plan, validation, and handoff evidence.
- [ ] No placeholder evidence, recording metadata, active-winner response, or complete audit history is invented to bypass the Fase 14 application contract.
- [ ] Yuno, OpenAI, Twilio, Realtime, webhook, telephony, payment, refund, capture, and other financial/provider behavior are outside this text-integration phase; source and diff review confirm that no corresponding SDK, API call, credential, header, payload, fixture, or sandbox/live mutation was added or executed.
- [ ] No deployment, production access, public hosting mutation, remote migration, Supabase project mutation/advisor run, phone call, external message, or unrelated infrastructure change is performed or claimed.
- [ ] `.env.example` contains names or safe empty defaults only when integration configuration requires them; ignored local secrets remain uncommitted and no server secret gains a `NEXT_PUBLIC_` alias.
- [ ] The final changed-path and dependency review confirms that unrelated user changes, provider work, Fase 14-owned evidence/recovery code, and generated files not produced by `make generate` remain outside the phase diff.

## Final commands and evidence

- [ ] `uv run ruff check .` passes from the repository root.
- [ ] `uv run pytest` passes against the complete Python suite with the required isolated PostgreSQL configuration.
- [ ] Focused backend persistence/negotiation and API route, authentication, error, idempotency, and integration tests pass and their exact commands/results are recorded.
- [ ] `make generate` passes, a second `make generate` is deterministic, and the complete `api/openapi.json` plus `frontend/src/lib/api/generated/**` diff is reviewed.
- [ ] `pnpm lint` passes from `frontend/` with zero warnings.
- [ ] `pnpm typecheck` and `pnpm format:check` pass from `frontend/`.
- [ ] `pnpm build` passes from `frontend/`.
- [ ] `make check` passes from the repository root with PostgreSQL available for the integrated suite.
- [ ] Browser smoke evidence records the exercised routes, canonical and failure scenarios, mobile/desktop sizes, keyboard/focus results, console output, and network requests/statuses without exposing sensitive values.
- [ ] `git diff --check`, complete tracked/untracked diff review, generated-artifact review, architecture-import review, secret/sensitive-data scan, and changed-path ownership review all pass.
- [ ] The final report distinguishes completed non-waiting integration evidence from every open `WAITING_ON_PHASE_14` criterion and directs resumption only after the accepted Fase 14 branch is merged and refreshed.
