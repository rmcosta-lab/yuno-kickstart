# Fase 20 validation — Add outbound-call controls and status

## Planning and coordination

- [x] Scope follows the roadmap exactly; implementation details follow `tech-stack.md`; validation uses the roadmap gate plus constitutional checks.
- [x] Fase 16 is DONE through merged PR #23 and Fase 19 is DONE through merged PR #28; no conflict is declared.
- [x] Owner is `rmcosta-lab`, branch is `phase/20-add-outbound-call-controls`, no tracking Issue was requested, and no shared-spec clarification is required.
- [ ] Before implementation publication, refresh dependency, conflict, branch, and overlapping frontend pull-request state.
- [ ] Only the phase specification, approved frontend feature/composition, and focused E2E test enter the phase.

## Generated contract and user action

- [ ] The component consumes generated `OperationResponse` and `useCreateOutboundCall`; no direct `fetch`, copied DTO, generated edit, backend import, Server Action, or Route Handler exists.
- [ ] With no session or unchecked confirmation, `Start demo call` is disabled and the network observes zero outbound-call requests.
- [ ] One checked action selects the lowest-rank synthetic session and sends exactly one request with its operation/session IDs, `synthetic-carrier-one`, `coordinator-demo`, a current UTC timestamp, disclosure true, recording disabled/consent false, and one valid `Idempotency-Key`.
- [ ] Duplicate clicks are blocked while pending; an identical uncertain retry preserves its key, while a completed attempt or selected-session change gets a new key.

## Status truthfulness and fallbacks

- [ ] Mutation pending renders `starting`; `QUEUED`/`INITIATED`/`RINGING`/`IN_PROGRESS` render `live`; `COMPLETED` renders `ended`; terminal negative statuses and safe HTTP errors render `failed`.
- [ ] Copy states that the display is the latest accepted create-call result and does not imply polling, subscription, or later provider observation.
- [ ] Browser voice and typed text fallbacks remain visible and usable before and after a failed PSTN attempt, and simulated preview mode performs no outbound request.
- [ ] Failure preserves safe retry/fallback guidance without exposing raw error bodies, provider identifiers, or claiming a successful call.

## Accessibility, visual, and security

- [ ] The checkbox has an associated label; the action is keyboard operable; focus is visible; status uses `aria-live`; failure uses an alert; meaning does not rely on color.
- [ ] Disabled, unavailable-session, `starting`, `live`, `ended`, and `failed` states fit the existing desktop layout without clipping or overflow and reuse existing Volta primitives/tokens.
- [ ] The DOM, console, network evidence, fixtures, screenshots, and diff expose no real phone number, editable destination, allowlist mapping, provider call ID/payload, credential, signature, authorization header, idempotency key, audio, transcript, or private participant data.
- [ ] Checkbox, actor/timestamp, key, body, and result are not persisted to local or session storage and are not logged.

## Focused and deterministic checks

- [ ] `pnpm test:e2e -- outbound-call-controls.spec.ts` passes from `frontend/` with intercepted synthetic API traffic.
- [ ] `pnpm lint` passes from `frontend/`.
- [ ] `pnpm typecheck` passes from `frontend/`.
- [ ] `pnpm build` passes from `frontend/`.
- [ ] `make frontend-check` passes from the repository root, or any exact overlap with the commands above is recorded without duplicate claims.
- [ ] `git diff --check`, complete tracked/untracked review, generated/manifests unchanged review, and targeted sensitive-data scans pass.

## Desktop browser smoke

- [ ] At desktop width, exercise the live sessions journey with synthetic intercepted responses: confirm disabled consent gate, one explicit start, `starting`, one accepted `live` or `ended` result, one `failed` result, and both fallbacks.
- [ ] Keyboard, focus, checkbox announcement, button disabled state, status announcement, and failure alert behave correctly.
- [ ] After the journey, browser console inspection shows no errors and network inspection shows only the expected generated BFF request with no direct Twilio/OpenAI/provider request.
- [ ] Smoke evidence is explicitly reported as a credential-free UI check, not a PSTN call or provider trial.

## Not applicable or explicitly excluded

- [x] `uv run ruff check .` and `uv run pytest` are not implementation gates for this frontend-only phase; no Python changes are planned.
- [x] OpenAPI/Orval regeneration is not applicable because the merged generated contract is consumed unchanged.
- [x] Yuno sandbox/mock, webhook, RLS, database, CORS, and payment checks are not applicable.
- [x] Twilio signature/media/idempotency implementation tests remain owned by merged Fase 19; this phase tests only browser request behavior and client-side logical-attempt key reuse.
- [x] No credentialed call, deployment, provider/account mutation, participant contact, recording, production access, or financial operation is authorized by phase start.
