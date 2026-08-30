# Fase 20 validation — Add outbound-call controls and status

## Planning and coordination

- [x] Scope follows the roadmap exactly; implementation details follow `tech-stack.md`; validation uses the roadmap gate plus constitutional checks.
- [x] Fase 16 is DONE through merged PR #23 and Fase 19 is DONE through merged PR #28; no conflict is declared.
- [x] Owner is `rmcosta-lab`, branch is `phase/20-add-outbound-call-controls`, no tracking Issue was requested, and no shared-spec clarification is required.
- [x] Before implementation publication, dependency, conflict, branch, and overlapping frontend pull-request state were refreshed with `git ls-remote` and `gh pr list`; Fases 16/19 remain merged, the remote Phase 20 branch was readable, and no open overlapping pull request existed.
- [x] Only the phase specification, approved frontend feature/composition, and focused E2E test enter the phase; `git status`, the complete diff, and path-sensitive review confirmed the boundary.

## Generated contract and user action

- [x] The component consumes generated `OperationResponse` and `useCreateOutboundCall`; source/diff review found no direct `fetch`, copied DTO, generated edit, backend import, Server Action, or Route Handler.
- [x] With no session or unchecked confirmation, `Start demo call` is disabled and the focused Playwright network fixture observed zero outbound-call requests.
- [x] One checked action selects the lowest-rank synthetic session and sends exactly one request with its operation/session IDs, `synthetic-carrier-one`, `coordinator-demo`, a current UTC timestamp, disclosure true, recording disabled/consent false, and one valid `Idempotency-Key`; the focused Playwright assertion passed.
- [x] Duplicate clicks are blocked while pending; the focused Playwright assertion proves an identical uncertain retry preserves both key and complete request body/timestamp, while a completed attempt gets a new key and a changed session changes the logical signature.

## Status truthfulness and fallbacks

- [x] Focused Playwright coverage proves mutation pending renders `starting`; `QUEUED`/`INITIATED`/`RINGING`/`IN_PROGRESS` render `live`; `COMPLETED` renders `ended`; terminal negative statuses and a safe 503 render `failed`.
- [x] Rendered copy states that the display is the latest accepted create-call result and does not imply polling, subscription, or later provider observation.
- [x] Focused Playwright coverage proves browser voice and typed text fallbacks remain visible and usable before and after a failed attempt; independent Chrome smoke found zero outbound controls in simulated preview mode.
- [x] Failure preserves safe retry/fallback guidance without rendering the synthetic raw error or provider identifier and never claims a successful call.

## Accessibility, visual, and security

- [x] Source inspection and browser evidence confirm the native checkbox has one associated hit-target label, the button is keyboard-native with visible focus, status uses `aria-live`, failure uses an alert, and text/icon labels carry meaning independently of color.
- [x] Focused Desktop Chrome execution and the independent Chrome screenshot show the existing Volta layout/primitives/tokens without clipping or horizontal overflow; all required states passed the same focused flow.
- [x] DOM, console, network evidence, screenshots, and diff review expose no real phone number, editable destination, allowlist mapping, real provider identifier/payload, credential, signature, authorization header, idempotency value, audio, transcript, or private participant data; synthetic provider/error fixtures are asserted absent from the DOM.
- [x] The focused Playwright storage assertions and source review confirm checkbox, actor/timestamp, key, body, and result are not persisted to local/session storage or logged.

## Focused and deterministic checks

- [x] `PLAYWRIGHT_SKIP_WEB_SERVER=1 pnpm exec playwright test tests/e2e/outbound-call-controls.spec.ts --project=chromium` passes from `frontend/` against `pnpm build && pnpm start`, with intercepted synthetic API traffic. The production-server path avoids a host-level Next dev Watchpack `EMFILE` loop observed with the nominal dev-server command.
- [x] `pnpm lint` passes from `frontend/` (also covered by the root gate).
- [x] `pnpm typecheck` passes from `frontend/` (also covered by the root gate).
- [x] `pnpm build` passes from `frontend/` and was repeated immediately before the production-server browser run.
- [x] `make frontend-check` passes from the repository root (`lint`, `typecheck`, and production `build`).
- [x] `git diff --check`, complete tracked/untracked review, generated/manifests unchanged review, and targeted sensitive-data scans pass.

## Desktop browser smoke

- [x] At Desktop Chrome width, the credential-free focused Playwright journey with intercepted responses confirmed disabled consent/session gates, one explicit start, `starting`, accepted `live` and `ended`, `failed`, and both fallbacks.
- [x] Native keyboard semantics, visible focus classes, checkbox/status announcements, button disabled state, and failure alert were directly inspected; the focused browser flow passed.
- [x] The focused journey produced only generated BFF traffic and the intentional synthetic 503 produced one expected redacted Chromium resource-console entry; no application exception, direct Twilio/OpenAI/provider request, or unexpected console warning/error occurred. Independent Chrome smoke on `/sessions` reported no console warnings/errors.
- [x] Smoke evidence is credential-free UI validation only; no PSTN call, provider trial, account mutation, or participant contact occurred.

## Not applicable or explicitly excluded

- [x] `uv run ruff check .` and `uv run pytest` are not implementation gates for this frontend-only phase; no Python changes are planned.
- [x] OpenAPI/Orval regeneration is not applicable because the merged generated contract is consumed unchanged.
- [x] Yuno sandbox/mock, webhook, RLS, database, CORS, and payment checks are not applicable.
- [x] Twilio signature/media/idempotency implementation tests remain owned by merged Fase 19; this phase tests only browser request behavior and client-side logical-attempt key reuse.
- [x] No credentialed call, deployment, provider/account mutation, participant contact, recording, production access, or financial operation is authorized by phase start.
