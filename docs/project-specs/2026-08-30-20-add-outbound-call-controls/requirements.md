# Fase 20 requirements — Add outbound-call controls and status

## Objective and user-visible outcome

- Give the operations coordinator one deliberate, truthful control for starting one authorized PSTN demo call from the existing live sessions view.
- Require an explicit confirmation and an explicit `Start demo call` action for the single synthetic allowlist label, then show `starting`, `live`, `ended`, or `failed` from the generated mutation state and normalized response only.
- Keep browser voice and text visible and usable as fallbacks. The terminal result is either the last provider-neutral status acknowledged by the create-call response or a safe failure with fallback actions; the browser never claims that a later provider callback was observed.
- Priority: P0.1 frontend integration.

## Included scope

- Add a narrow client component under `frontend/src/features/telephony/` and compose it into the existing live sessions experience without converting an App Router page into a Client Component.
- Select the existing operation session with the lowest `carrier.deterministic_rank`, display only its synthetic carrier name, use its generated `call_id`, and submit the fixed safe destination label `synthetic-carrier-one`.
- Require one unchecked-by-default checkbox confirming that the demo participant is authorized and that the call will use the server-owned AI-disclosure and press-1 continuation flow. Disable dialing until a live operation session exists and the checkbox is checked.
- Consume `useCreateOutboundCall` and generated request/response types. Send `authorized_by="coordinator-demo"`, the submit-time UTC timestamp, `ai_disclosure_required=true`, `recording_mode="DISABLED"`, and `recording_consent_required=false`.
- Generate one idempotency key per logical submit, retain it for an identical uncertain retry, and allocate a new key only after a completed result or changed selected session.
- Present the four roadmap states without inventing provider progress: mutation pending is `starting`; `QUEUED`, `INITIATED`, `RINGING`, and `IN_PROGRESS` are `live`; `COMPLETED` is `ended`; `BUSY`, `FAILED`, `NO_ANSWER`, `CANCELED`, and safe HTTP errors are `failed`.
- Add one focused Playwright test covering consent gating, one generated request, status presentation, safe failure, and both fallbacks; run one desktop browser smoke with console and network inspection.

## Excluded scope

- Polling, subscriptions, a status-read endpoint, callback-to-browser delivery, intermediate provider timing, reconnect/resume, automatic retry, multi-call controls, parallel dialing, detailed call timeline, or error-specific visual systems.
- Any Pydantic, OpenAPI, Orval, API/BFF, backend/core, persistence, Twilio adapter, Realtime transport, environment inventory, manifest, lockfile, or shared-spec change.
- Real phone numbers, editable destination labels, raw provider identifiers or payloads, credentials, signatures, audio, transcripts, participant data, account changes, deployment, recording, or an actual call.
- Inbound telephony, coordinator takeover, evidence/audit expansion, SMS/email, Yuno, payments, or production operations.

## Coordination and roadmap gate

- Branch: `phase/20-add-outbound-call-controls`.
- Workspace: `/private/tmp/yuno-kickstart-phase-20-add-outbound-call-controls`.
- Planning directory: `docs/project-specs/2026-08-30-20-add-outbound-call-controls/`.
- Owner and team contact: `rmcosta-lab`.
- Tracking Issue: none requested.
- Dependencies: Fase 16 is DONE through merged PR #23; Fase 19 is DONE through merged PR #28.
- Conflicts: none declared.
- Roadmap gate, unchanged: using the generated client, require consent and the explicit start action for one allowlisted destination label; display `starting`, `live`, `ended`, or `failed`; keep browser-voice and text fallbacks; expose no real phone number, credential, or raw provider payload; pass one focused frontend test and one desktop browser smoke test.

## Assumptions, risks, and fallback

- The merged Fase 19 generated contract is the complete browser/server boundary for this phase. It creates a call and returns one normalized status but exposes no browser status stream; the UI therefore labels only the response it actually received.
- The demo environment maps `synthetic-carrier-one` to the one authorized destination server-side. The browser displays the selected synthetic carrier name, never the allowlist mapping or phone number.
- Risk: a double click or uncertain response creates another provider mutation. Mitigation: disable while pending and preserve one idempotency key for the identical retry.
- Risk: `live` is mistaken for continuing observation. Mitigation: label the card as the latest accepted create-call result and state that provider/network diagnostics are outside this phase.
- Risk: a stale operation has no valid session. Mitigation: render dialing unavailable, preserve fallbacks, and require authoritative operation refresh rather than synthesizing an identifier.
- Fallback: if dialing is unavailable or fails, leave the safe failure visible and direct the coordinator to the existing browser voice and typed text controls. No provider failure is represented as PSTN success.

## Acceptance criteria

1. With no checked confirmation or no operation session, `Start demo call` is disabled and no request is sent.
2. The card shows exactly one synthetic carrier selected by lowest deterministic rank; it exposes no phone number, destination mapping, provider call ID, credential, or raw error payload.
3. One confirmed click invokes the generated mutation once with the authoritative operation/session IDs, fixed safe label, demo actor, current UTC authorization time, disclosure/recording literals, and one valid idempotency key.
4. Pending, accepted active, completed, and terminal/error outcomes render respectively as `starting`, `live`, `ended`, and `failed`, with text and `aria-live` semantics that do not rely on color.
5. An identical uncertain retry reuses its key; completed or changed-session actions do not reuse a previous logical-operation key. Duplicate clicks remain blocked while pending.
6. Browser voice and text fallback controls remain visible and usable before and after a failed call attempt; the PSTN control does not alter their Realtime lifecycle.
7. Loading, unavailable-session, disabled, pending, success, terminal, and safe error states remain keyboard accessible, wrap at desktop width, and preserve the existing Volta visual system.
8. The focused Playwright test, `pnpm lint`, `pnpm typecheck`, `pnpm build`, desktop browser smoke, console/network inspection, `git diff --check`, and sensitive-data review pass.

## HTTP contract gate

- Consume the existing generated `POST /v1/operations/{operation_id}/outbound-calls` contract only.
- Headers: existing demo bearer is supplied by `voltaFetch`; `Idempotency-Key` is a printable 8–128 character key owned per logical submit.
- Request: generated `CreateOutboundCallRequest` with the selected `call_session_id`, fixed `destination_label`, demo `authorized_by`, submit-time `authorized_at`, `ai_disclosure_required=true`, `recording_mode="DISABLED"`, and `recording_consent_required=false`.
- Success: existing `201 OutboundCallResponse`. The UI may use `status`, `created_at`, and `status_updated_at`; it must not render `provider_call_id`.
- Errors: generated safe `401`, `403`, `404`, `409`, `422`, `429`, `500`, `502`, `503`, and `504` envelopes become one concise `failed` presentation. `ApiHttpError` details may select safe retry guidance but raw bodies and provider details never enter the DOM.
- No API contract or generated artifact changes. A later status callback is not observable through this route and is not inferred.

## Application contract gate

- Add `frontend/src/features/telephony/outbound-call-control.tsx` exporting `OutboundCallControl`, constructed with the authoritative generated `OperationResponse` and no provider configuration.
- Add `frontend/src/features/telephony/index.ts` as the public feature export and compose the control inside `LiveOperation` in `frontend/src/features/negotiation/negotiation-experience.tsx`.
- Inputs are generated `OperationResponse`, `CarrierSessionResponse`, `CreateOutboundCallRequest`, and `OutboundCallResponseStatus`; the only mutation boundary is generated `useCreateOutboundCall`.
- Internal presentation state is a closed `idle | starting | live | ended | failed` union plus checkbox and idempotency-attempt metadata. Server data is not copied into a parallel DTO or global store.
- Safe generated responses produce the four labels above. `ApiHttpError<ApiErrorResponse>` and unexpected failures are caught at the feature boundary and reduced to non-sensitive guidance; exceptions do not escape into rendering.
- `crypto.randomUUID()` supplies idempotency keys. No new dependency, context provider, Server Action, Route Handler, backend import, or handwritten transport type is introduced.

## Browser/server handoff and terminal result

- Browser-to-server application traffic uses only the generated FastAPI client and existing authenticated `voltaFetch`. Twilio and standard OpenAI credentials remain server-side.
- The browser sends a safe destination label, not a phone number. Twilio disclosure, continuation consent, call creation, media, and terminal callbacks remain server-owned Fase 19 behavior.
- The terminal visible result is `ended` only when the create response itself is `COMPLETED`, otherwise the latest honest `live` or `failed` snapshot plus browser voice/text fallback. Durable or later provider status is not claimed.
- Yuno/payment handoff: none.

## Visual, accessibility, and security decisions

- Reuse existing `Card`, `Button`, `Checkbox`, `Alert`, and `StatusBadge` primitives and design tokens; no visual redesign.
- Use an associated checkbox label, visible focus, disabled explanation, a polite status region for progress/success, an alert for failure, and text labels independent of color.
- Show only the synthetic carrier display name and normalized four-state label. Masking is not a substitute for excluding provider IDs, numbers, errors, and payloads from the DOM.
- Never persist the checkbox, actor timestamp, idempotency key, mutation body, or result in local/session storage; never log them.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-20-add-outbound-call-controls/**` | Phase coordinator `rmcosta-lab` | Planning and validation evidence |
| `frontend/src/features/telephony/**` | `rmcosta-lab` | Outbound control, four-state projection, safe errors, and exports |
| `frontend/src/features/negotiation/negotiation-experience.tsx` | `rmcosta-lab` | Small composition point only; preserve browser voice and text behavior |
| `frontend/tests/e2e/outbound-call-controls.spec.ts` | `rmcosta-lab` | Focused generated-contract interaction and accessibility coverage |
| `frontend/src/lib/api/generated/**`, `api/openapi.json` | none | Consume merged generated contract; never edit manually |
| `frontend/package.json`, `pnpm-lock.yaml` | none | No dependency or script change planned |
| API, backend, migrations, provider adapters, `.env.example` | none | No writer in this frontend-only phase |
| Shared mission, stack, roadmap, challenge plan | none | No clarification required |
| Twilio/OpenAI accounts, deployment, numbers, participants, recordings | none | No external mutation authorized by phase start |
