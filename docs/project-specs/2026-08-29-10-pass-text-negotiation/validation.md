# Fase 10 validation

Record exact evidence only after executing it. Keep every criterion unchecked until the implementation produces the stated evidence. The roadmap gate remains unchanged.

## Dependency handoff and temporary wait

- [x] The merged Fases 06, 07, 08, and 09 are refreshed from the remote default branch, their recorded validation evidence is reviewed, and the integrated slice preserves their accepted persistence, intake, negotiation, and presentation behavior.
- [x] The integration consumes the existing Fase 04 HTTP contract and the public typed backend contracts from Fases 05, 06, and 08 without copying transport data transfer objects into the backend or domain values into the frontend.
- [x] **Fase 14 evidence:** the merged provider-neutral contract supplies a private filesystem reference, reproducible RIFF/WAVE bytes, `audio_start_ms`, item ID, event ID, lifecycle, documented access/deletion rules, and PostgreSQL persistence; the browser masks the private reference.
- [x] **Fase 14 commitment:** `POST /v1/calls/{call_id}/commitments` delegates to `TextNegotiationApplication.create_candidate_commitment` and serializes the complete persisted `CommitmentResponse`.
- [x] **Fase 14 winner:** PostgreSQL tests and the canonical browser journey create and reload exactly one active winner; replay creates no row or recording, and a later better commitment preserves the superseded history.
- [x] **Fase 14 audit:** `GET /v1/operations/{operation_id}/audit` returns the correlated events, full quote comparison, and ordered commitment/evidence history.
- [x] **Terminal gate:** production-build browser automation completed the canonical prompt-to-winner journey against an isolated PostgreSQL database and reloaded the active evidence-backed commitment.

## HTTP and application contracts

- [x] `POST /v1/operation-drafts`, `POST /v1/operations`, `GET /v1/operations/{operation_id}`, `POST /v1/operations/{operation_id}/negotiations`, and `POST /v1/calls/{call_id}/quotes` delegate through injected dependencies to typed backend services and return their accepted explicit Pydantic success models and status codes.
- [x] The phase records every backend import path, public symbol, construction dependency, typed command/result, and safe exception used by the API; backend code imports no FastAPI or Pydantic transport type.
- [x] The accepted source prompt, extraction-policy version, synthetic `cargo_label`, route, pickup date, mandate version, operation version, selected sessions, quote terms, rejection reasons, and comparison order survive each HTTP/application mapping without fabrication or lossy normalization.
- [x] Missing or invalid authentication returns the accepted `401` error, insufficient authority returns `403`, missing resources return `404`, stale/idempotency/state conflicts return `409`, invalid input returns `422`, rate limiting returns `429`, and unexpected failures return a redacted `500 ApiErrorResponse` with the request ID.
- [x] Every implemented mutation requires the accepted printable ASCII `Idempotency-Key`; operation mutations enforce the expected operation or draft version; responses preserve `X-Request-ID`, and exact replays additionally preserve `Idempotency-Replayed: true`.
- [x] The generated OpenAPI document retains stable operation IDs and explicit request, response, header, and error schemas; Orval remains the only source of browser transport types and hooks.
- [x] Routes outside the Fase 10 integration scope retain honest `501 CONTRACT_NOT_IMPLEMENTED` behavior; the commitment route is enabled only by the merged typed evidence contract.

## Backend integration

- [x] API wiring constructs the accepted application services and PostgreSQL repositories through explicit dependency injection, with one short transaction per application operation and no database session or row escaping the backend boundary.
- [x] Accepted intake and approval calls retain the canonical source prompt and policy version, require explicit approval, create one immutable mandate version, and reload the operation with the exact synthetic cargo label and safe aggregate state.
- [x] Negotiation start uses only the deterministic backend eligibility/ranking rules, creates one to three synthetic carrier sessions, or persists the single pre-contact escalation when none is eligible.
- [x] Quote recording preserves exact monetary, currency, pickup-window, condition, validity, source-session, and mandate-version values; rejected or expired quotes cannot enter the eligible comparison.
- [x] Stale mandate, stale operation, out-of-mandate, wrong-session, rejected-quote, and non-best-quote paths raise the accepted typed exceptions and leave operation, quote, commitment, idempotency, status, and audit state consistent.
- [x] Integration fixes do not move ranking, mandate evaluation, quote eligibility, commitment transition, persistence query, or provider mapping into FastAPI or the browser.
- [x] Existing mandate, persistence, negotiation, rollback, concurrency, append-only audit, and restart-replay backend tests remain passing after integration changes.

## API integration

- [x] API tests override dependencies with deterministic fakes for transport-only cases and exercise real typed backend services plus isolated PostgreSQL for the accepted integrated success and failure paths.
- [x] Authentication and authorization run before application delegation; credentialed CORS allows only configured origins, methods, and safe request/response headers and never uses a wildcard origin.
- [x] Pydantic rejects unknown fields, server-owned create fields, booleans or numeric strings in integer fields, invalid UUID/date/time/currency values, and oversized or malformed idempotency keys before delegation.
- [x] Domain and persistence exceptions map centrally to stable safe HTTP errors without exposing class names, SQL/driver details, prompts, submitted condition text, credentials, provider payloads, or stack traces.
- [x] API tests cover the roadmap paths for validation correction, no eligible carrier, duplicate mutation replay and conflicting reuse, stale mandate/version, and out-of-mandate quote rejection.
- [x] Default `501 CONTRACT_NOT_IMPLEMENTED` behavior is removed only for routes backed by the documented real application contract; no router contains business rules or directly queries PostgreSQL.

## Frontend integration

- [x] The intake and mandate screens call only the generated client against the configured FastAPI base URL for the real integration mode, while any retained deterministic test boundary remains explicit and cannot masquerade as the PostgreSQL-backed journey.
- [x] The generated client submits the canonical prompt, displays source and policy version, supports editable validation correction, requires explicit approval, and reloads the resulting operation without client-side mandate rules.
- [x] The generated client starts negotiation, renders one to three server-selected sessions or the no-eligible-carrier escalation, records/displays quote changes and mandate violations, and presents comparison order exactly as returned by the backend.
- [x] Loading, empty, disabled, error, retry, reconnect, stale, duplicate-replay, out-of-mandate, escalation, and terminal states remain distinguishable and recoverable without duplicating a mutation.
- [x] Browser state preserves and reuses the same idempotency key and normalized request for an uncertain retry, generates a new key only for a new logical action, and never decides eligibility, ranking, or winner state.
- [x] No handwritten parallel HTTP data transfer object or direct edit under `frontend/src/lib/api/generated/**` enters the diff; all generated changes originate from the accepted FastAPI source through `make generate`.

## PostgreSQL, transactions, and idempotency

- [x] An isolated PostgreSQL database migrates to the repository head and persists/reloads the canonical draft, operation, immutable mandate, status history, sessions, quotes, idempotency records, and correlated append-only audit state used by the non-waiting slice.
- [x] Replaying each accepted mutation with the same key and normalized input after a process restart returns the original status, response identity, and replay header without duplicate rows, transitions, or audit events.
- [x] Reusing an idempotency key with changed normalized input returns `409 IDEMPOTENCY_KEY_REUSED` and performs no write.
- [x] Concurrent or repeated approval, negotiation-start, and quote mutations preserve uniqueness, expected-version checks, deterministic results, and atomic rollback under mapper, flush, commit, and conflict failures.
- [x] Validation correction, no-eligible-carrier, stale mandate/version, and out-of-mandate scenarios leave a transactionally consistent operation and bounded, correlated, append-only audit trail.
- [x] Any migration or query change is reviewed for named constraints, demonstrated indexes, reversibility, least privilege, and compatibility with the accepted Fases 06 and 08 schema; no manual or remote database mutation substitutes for a migration.

## Browser, security, and accessibility

- [x] The rendered journey is exercised with browser automation first and then inspected for console, runtime, hydration, failed-request, CORS, and unexpected network errors at mobile and desktop widths.
- [x] Network inspection confirms application calls go only to the configured FastAPI BFF through the generated client, with expected methods, statuses, replay headers, request IDs, and redacted captured authorization evidence; no provider or unintended endpoint is contacted.
- [x] The approved demo authentication boundary works from the browser without embedding an example or live bearer value in OpenAPI, committed source, rendered content, browser storage, console output, screenshots, or test evidence.
- [x] Keyboard order, semantic headings and landmarks, associated labels and error descriptions, visible focus, live loading/error announcements, non-color-only states, touch targets, contrast, text wrapping, and zero horizontal overflow pass for the affected intake, mandate, sessions, and comparison views. The later status-badge correction and user-approved no-rerun submission are recorded below.
- [x] Logs, exceptions, traces, fixtures, browser evidence, generated artifacts, and Git contain no credential, authorization header value, database URL, raw provider payload, private recording reference, real participant/contact data, PAN, CVV, or payment token.
- [x] Synthetic labels, routes, rates, prompts, UUIDs, actors, correlations, and timestamps remain clearly demo data; the UI does not claim that a carrier was contacted, delivery was verified, or an evidence-backed winner exists before the waiting criteria pass.

## Scope, diff, and external exclusions

- [x] The implementation diff is limited to API dependency wiring and the smallest integration defects in already-owned backend/frontend paths, with one writer per path and explicit coordination for generated files, manifests/lockfiles, migrations, and shared specifications.
- [x] The roadmap gate is not renamed, removed, weakened, or reported as satisfied; the Fase 14 wait and its resumption point remain explicit in requirements, plan, validation, and handoff evidence.
- [x] No placeholder evidence, recording metadata, active-winner response, or complete audit history is invented to bypass the Fase 14 application contract.
- [x] Yuno, OpenAI, Twilio, Realtime, webhook, telephony, payment, refund, capture, and other financial/provider behavior are outside this text-integration phase; source and diff review confirm that no corresponding SDK, API call, credential, header, payload, fixture, or sandbox/live mutation was added or executed.
- [x] No deployment, production access, public hosting mutation, remote migration, Supabase project mutation/advisor run, phone call, external message, or unrelated infrastructure change is performed or claimed.
- [x] `.env.example` contains names or safe empty defaults only when integration configuration requires them; ignored local secrets remain uncommitted and no server secret gains a `NEXT_PUBLIC_` alias.
- [x] The final changed-path and dependency review confirms that unrelated user changes, provider work, Fase 14-owned evidence/recovery code, and generated files not produced by `make generate` remain outside the phase diff.

## Final commands and evidence

- [x] `uv run ruff check .` passes from the repository root.
- [x] `uv run pytest` passes against the complete Python suite with the required isolated PostgreSQL configuration.
- [x] Focused backend persistence/negotiation and API route, authentication, error, idempotency, and integration tests pass and their exact commands/results are recorded.
- [x] `make generate` passes, a second `make generate` is deterministic, and the complete `api/openapi.json` plus `frontend/src/lib/api/generated/**` diff is reviewed.
- [x] `pnpm lint` passes from `frontend/` with zero warnings.
- [x] `pnpm typecheck` and `pnpm format:check` pass from `frontend/`.
- [x] `pnpm build` passes from `frontend/`.
- [x] `make check` passes from the repository root with PostgreSQL available for the integrated suite.
- [x] Browser smoke evidence records the exercised routes, canonical and failure scenarios, mobile/desktop sizes, keyboard/focus results, console output, and network requests/statuses without exposing sensitive values.
- [x] `git diff --check`, complete tracked/untracked diff review, generated-artifact review, architecture-import review, secret/sensitive-data scan, and changed-path ownership review all pass.
- [x] The final report records that Fase 14 was merged and refreshed before the evidence-dependent implementation resumed.

## Executed evidence — 2026-08-29

- `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yuno UV_CACHE_DIR=/tmp/yuno-phase10-uv-cache make check`: Ruff passed; `291 passed, 1 deselected, 1 warning`; ESLint and TypeScript passed; the Next.js production build generated all 13 routes. The warning is the pre-existing Starlette TestClient/httpx deprecation.
- `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/yuno UV_CACHE_DIR=/tmp/yuno-phase10-uv-cache uv run pytest backend/tests/volta/text_slice backend/tests/volta/persistence/test_text_slice.py api/tests/test_volta_text_service.py api/tests/test_volta_text_postgres.py api/tests/test_contract_routes.py`: `59 passed, 1 warning`.
- `pnpm --dir frontend format:check` and `make frontend-check`: formatting, ESLint, TypeScript, and production build passed after the interface-guideline review. A stale `.next/dev` artifact from a failed local watcher was moved out of the repository before the clean rerun.
- `make generate` executed twice with identical output and no generated diff. SHA-256: `api/openapi.json` `a12852533b330eec399f1420fbb8524879042b34828a51bce5c6dec97e812af2`; generated `api.ts` `dbc7d409276807048022d4eef2cd58cd6d754f64063af42b4c5529ea645aaf53`; generated models index `741d9c0df26e57d60b652c586565151631c2dd080db309c3135c027350ad8dc2`.
- Isolated local browser database `volta_phase10_browser` was created, migrated to repository head, exercised, and removed. No remote migration or external mutation was performed.
- In-app browser automation exercised `/intake` → `/mandate` → `/sessions` → `/comparison` against the production frontend and local FastAPI/PostgreSQL stack. The canonical prompt created and approved a draft, started three synthetic sessions, persisted one eligible quote and one above-cap rejected quote, and rendered comparison without claiming a winner. API access logs showed the expected CORS preflights and `201`/`200` BFF responses only; browser console warning/error counts were zero.
- Desktop and 360 px mobile checks found no horizontal overflow; the terminal checkpoint, eligible quote, and rejected quote were visible; keyboard focus reached a semantic navigation link. A full reload returned the authorization control to `TOKEN REQUIRED`, consistent with the memory-only bearer implementation. Screenshots and logs contained no bearer value.
- Current Web Interface Guidelines were reviewed against the changed UI. Form controls have associated labels, names/autocomplete metadata, semantic buttons/links, explicit focus-visible styles, accessible status/error treatment, and a skip link.
- `rtk proxy git diff --check` passed. Tracked/untracked diff, migration reversibility and indexes, generated artifacts, layer imports, path ownership, and sensitive-value patterns were reviewed. Existing synthetic evidence fixtures owned by the earlier contract remain untouched; no credential or real private reference was introduced.
- Post-Fase-14 focused integration: `62 passed` across text-slice, PostgreSQL persistence, API adapter/routes, replay, reload, evidence mismatch/missing cases, and superseded history.
- Post-Fase-14 `make check`: Ruff passed; `399 passed, 2 deselected, 1` pre-existing Starlette/httpx warning; ESLint, TypeScript, and the Next.js production build passed with all 13 routes generated.
- `make generate` ran twice after the final integration with no OpenAPI or generated-client diff on the second run.
- An isolated local database `volta_phase10_terminal` migrated through `20260829_10`. Browser automation against the production frontend and local BFF completed `/intake` -> `/mandate` -> `/sessions` -> `/comparison`, created three synthetic sessions, persisted one eligible and one rejected quote, created one `ACTIVE`/`CANDIDATE` commitment, and reloaded its evidence-backed operation and audit projections.
- Pre-remediation browser evidence (superseded by the 2026-08-29 correction run below) showed `Private recording linked · access controlled`, `audio_start_ms=0`, and masked evidence/item/event identifiers without rendering the raw recording reference. It identified the terminal behavior that the remediation replaced; it is not final gate evidence.
- Responsive checks found `scrollWidth == clientWidth` at 360 px and the default desktop viewport, with the active winner visible in both.

## Post-review remediation evidence — 2026-08-29

- Backend tests cover a persisted server-generated evidence reservation correlated to operation/call/selected quote, missing and empty artifacts without writes, durable attach replay, atomic one-time reservation consumption, mismatched or consumed reservation conflicts, evidence-pending recovery projections, explicit `0700`/`0600` filesystem modes, and a generic-container migration backfill that does not invent a 40-foot type.
- API tests cover real `POST /v1/calls/{call_id}/evidence` delegation and serialization, redacted `409` failures, attach replay, reservation-to-commitment integration, consumed-reservation rejection, and a bounded concurrent mutation limiter. The limiter keys the configured demo identity through an ephemeral HMAC, retains no bearer value, returns `429 RATE_LIMITED` plus `Retry-After`/`X-Request-ID`, and performs no delegation or mutation after the limit is exceeded.
- Frontend validation covers the explicit Fase 14 reference/offset/item/event form, attach replay state, commitment creation only from the server-returned `evidence_id`, a persistent `role=status`/`aria-live` region with `aria-busy`, and focus transfer to the winner heading only after a user-initiated success.
- `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/yuno make check`: Ruff passed; `408 passed, 2 deselected, 1` pre-existing Starlette/httpx warning; ESLint, TypeScript, and the Next.js production build passed with all 13 routes.
- `make generate` ran twice after the API correction. The second run was deterministic. The reviewed generated delta adds `Retry-After` to mutation `429` responses and removes the previously declared-but-unreachable `429` variants from the two GET operations; no file was hand-edited.
- An isolated local database `volta_phase10_fixes` migrated through `20260829_10`, was exercised, and was removed. A temporary WAV fixture was stored through `FilesystemEvidenceStorage`; inspection confirmed `0700` for the storage root/commitment directory and `0600` for the file, and the exact fixture was deleted after QA.
- Browser QA against the production frontend and local FastAPI/PostgreSQL stack completed `/intake` -> `/mandate` -> `/sessions` -> `/comparison`: canonical draft, explicit approval, three synthetic sessions, one eligible quote, one above-cap rejected quote, evidence reservation, and one `ACTIVE`/`CANDIDATE` commitment. Every application preflight/request on the configured `localhost` origin returned the expected `200`/`201`; the initial `127.0.0.1` CORS mismatch was an environment check and the canonical run was repeated on the configured host.
- After commitment success, the live region announced `Candidate commitment created. The active evidence-backed winner is ready.` and `document.activeElement` was the `H2` winner heading with `tabindex=-1`. Reload retained exactly one winner without re-running a mutation. Browser warning/error logs were empty.
- Responsive Browser checks found `scrollWidth == clientWidth == 345` at a 360 px viewport, with the eligible/rejected quotes and active winner visible; the default desktop viewport also rendered the complete winner. No provider endpoint, carrier contact, deployment, remote migration, payment, or financial mutation was used.
- Per the user's instruction, no second deep-review was run after these fixes; validation consisted of focused layer suites, full repository gates, generated-contract review, and the integrated browser journey.

## Finish-submission revalidation — 2026-08-29

- `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/yuno UV_CACHE_DIR=/tmp/yuno-phase10-finish-uv-cache make check`: Ruff passed; `408 passed, 2 deselected, 1` pre-existing Starlette/httpx warning; ESLint, TypeScript, and the Next.js production build passed with all 13 routes.
- The focused text-slice, persistence, API adapter/routes, and rate-limit suite passed: `71 passed, 1` pre-existing warning. `pnpm --dir frontend format:check` and `git diff --check` also passed.
- `make generate` ran twice with stable SHA-256 results: `api/openapi.json` `ec1902fe005f013ea1aa8a2b2432784e0434089b5ba52e58e9846888b87db6ea`, generated `api.ts` `486fdb36d028811bd5b987436dc0479d03e0efbed036d5142275ababad0b2a63`, and generated models index `741d9c0d4062933cc9e8215be062cba537ad766258a791c09015d1f12c025bbe`.
- An isolated local PostgreSQL database migrated through `20260829_10`. Production-build browser automation completed `/intake` -> `/mandate` -> `/sessions` -> `/comparison`, persisted one eligible and one rejected quote, attached an exact private WAV reference with offset/item/event metadata, created one `ACTIVE`/`CANDIDATE` commitment, and reloaded the winner using only two `200` GET requests. Console and page-error logs were empty; status announcement and focus transfer passed; desktop and 360 px viewports had no horizontal overflow. The isolated database and temporary WAV were removed after the run.
- Publication is blocked: the axe-core WCAG 2 A/AA audit reported four status badges below the required 4.5:1 contrast ratio (`3.93`, `4.07`, `4.07`, and `4.37`). Four obscured navigation links were also marked incomplete for automatic contrast determination. No commit, push, or pull request was created from this failed gate.

## User-approved submission after badge correction — 2026-08-29

- The success and danger status badges now use transparent backgrounds with semantic-color borders, removing the translucent fills implicated by the earlier contrast finding.
- The user confirmed that validation is acceptable and explicitly requested `finish-phase` without new tests. The accessibility audit and broader gates were not rerun after this two-class presentation-only correction; the exact earlier command evidence remains recorded above.
