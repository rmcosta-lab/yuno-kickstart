# Fase 26 — Accept and process inbound Twilio calls

## Coordination

- Priority: P0.1 completion of the real inbound telephony recovery path.
- Branch: `phase/26-accept-inbound-twilio-calls`.
- Workspace: `/private/tmp/yuno-kickstart-phase-26-accept-inbound-twilio-calls`.
- Owner and team contact: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fases 15 and 19. They are DONE through merged pull requests #22 and #28, with their required validation evidence recorded.
- Conflicts with: none.
- Roadmap gate: a signed Twilio voice webhook answers one authorized real inbound PSTN call; fail-closed server-owned correlation resolves the allowlisted synthetic caller and exactly one active operation; disclosure and recording consent precede the existing bidirectional Media Stream; the driver-delay path makes one mandate-safe update and persists status, brief, playable timestamp evidence, and audit events; focused negative tests and one authorized sandbox call pass.
- Scope choice: keep the roadmap scope exactly as written, follow `tech-stack.md`, and use the roadmap gate plus repository constitutional checks.

## Objective and terminal user-visible outcome

Allow the single allowlisted synthetic driver to call the configured Twilio demo number, hear the artificial-intelligence and recording disclosure, explicitly consent, and complete the deterministic driver-delay recovery through the existing Twilio-to-OpenAI bridge. The existing Recovery, Evidence, and Audit screens then refresh from the generated client and show the committed operation state, mandate-safe replacement, private playable evidence at its timestamp, structured brief, notification, and correlated audit events. No new frontend workflow or public application route is required.

## Included scope

- Add provider-only signed `application/x-www-form-urlencoded` ingress for an inbound voice request and its DTMF consent continuation; preserve the existing signed Media Stream WebSocket.
- Validate the exact configured public HTTPS URL and all form pairs with Twilio's supported request validator behavior before interpreting `AccountSid`, `CallSid`, `From`, `To`, or `Digits`.
- Map one configured synthetic E.164 caller to an opaque server-side caller label, then resolve exactly one eligible active operation and its active commitment. Zero or multiple matches fail closed and return no stream instructions.
- Persist a duplicate-safe inbound-call attempt and consent/stream/completion transitions keyed by provider call ID; provider identifiers are correlation data, never authorization by themselves.
- Announce artificial-intelligence participation and evidence recording, require explicit DTMF consent, and start `<Connect><Stream>` only after durable consent. Refusal, timeout, replay conflict, or correlation failure ends the call safely.
- Reuse the Fase 19 bounded bidirectional Media Stream and OpenAI Realtime bridge. Bind the stream to the resolved operation, existing committed call session, active commitment, caller label, and provider call through one opaque single-use token.
- Capture only the bounded post-consent audio needed for private demo evidence, convert it to the private storage's playable format, and never log or place it in Git, provider payloads, API responses, or audit metadata.
- Complete one fixed `MANDATE_SAFE` driver-delay scenario through the same backend recovery domain service used by the browser path; atomically persist the replacement/status, timestamp evidence metadata, a bounded structured brief, notification, recovery attempt, and safe correlated audit events.
- Reuse the existing operation, audit, and evidence-audio HTTP contracts so current frontend queries render the terminal result. Regenerate OpenAPI/Orval only to prove there is no unintended public-contract diff.
- Add deterministic API, WebSocket, backend application, persistence, replay, redaction, and cross-layer projection tests plus one separately authorized sandbox call.

## Excluded scope

- A new frontend screen, new public REST route, handwritten TypeScript DTO, redesign, call-control timeline, or browser-owned inbound correlation rule.
- Outbound-call behavior from Fases 18–20, multiple callers, multiple simultaneous calls, arbitrary scenarios, production traffic, SIP, SMS, email, or participant enrollment.
- Caller-ID-based authorization, selecting the first matching operation, a client-supplied operation ID, accepting ambiguous active state, or trusting `CallSid`, `From`, or custom stream parameters without the signed and server-bound context.
- Provider-native call recording, raw transcript persistence, general call recording, long-term audio retention, audio in PostgreSQL, or use of pre-consent audio as evidence. The application stores only the bounded consented evidence clip through the existing private evidence boundary.
- New mandate/quote policy, model-selected terms, an out-of-mandate path, coordinator mandate replacement, Yuno/payment work, remote migrations, deployment, number purchase/configuration, account mutation, or a real call without separate authorization.
- Shared mission, stack, roadmap, or challenge-plan edits in this branch.

## HTTP and WebSocket contract gate

These are provider ingress contracts and remain outside OpenAPI. The browser continues to use the existing generated operation, audit, and evidence-audio contracts.

| Method and route | Input and success | Fail-closed semantics |
| --- | --- | --- |
| `POST /v1/telephony/twilio/inbound/voice` | Signed Twilio form including bounded `AccountSid`, `CallSid`, `From`, and `To`; `200 application/xml` announces AI and recording and returns one DTMF `<Gather>` to the consent route. | `403` for invalid/missing signature or account/destination mismatch; safe hangup TwiML for unallowlisted caller, no/multiple active correlations, replay conflict, or ineligible operation. No stream token is issued. |
| `POST /v1/telephony/twilio/inbound/consent` | Signed form for the same bound call, with `Digits=1`; `200 application/xml` returns one `<Connect><Stream>` using the configured `wss` URL and one opaque custom `binding` parameter. | Refusal/missing digit returns disclosure-safe hangup TwiML. Invalid signature is `403`; mismatched/consumed/expired call binding fails closed and emits no stream instruction. Consent is persisted before TwiML is returned. |
| `WS /v1/telephony/twilio/media` | Existing signed WebSocket handshake and `connected` → `start` → `media` → `stop` lifecycle; the `start` frame must match account, call, stream, inbound track, media format, and the single-use binding. | Preserve Fase 19 frame/queue/duration/single-stream bounds and safe close codes. Reject invalid signature, token replay, call/account mismatch, malformed/out-of-order/oversized frames, duplicate active stream, and pre-consent binding before Realtime or storage I/O. |

Twilio may add form parameters, so signature verification must use every received name/value pair and may not whitelist fields before validation. External origin reconstruction remains server-configured; forwarded host/scheme input is not trusted. The provider routes never echo a telephone number, raw form, signature, token, audio, or internal exception.

Existing browser-visible terminal contracts remain unchanged:

- `GET /v1/operations/{operation_id}` exposes the resulting `COMMITTED` operation, one active replacement commitment, and notification.
- `GET /v1/operations/{operation_id}/audit` exposes the recovery, brief, evidence-backed commitment history, and safe correlated events.
- `GET /v1/evidence/{evidence_id}/audio` streams the private playable artifact only through existing demo authorization and range semantics.

## Application contract gate

### Provider-neutral backend boundary

Add the smallest provider-neutral inbound application boundary under `yuno_backend.volta.telephony`; Twilio form/XML/frame types stay in `api/app/telephony/**`.

| Import path | Public symbols and construction | Typed behavior |
| --- | --- | --- |
| `yuno_backend.volta.telephony` | `InboundCallApplication`, `AcceptInboundCallInput`, `RecordInboundConsentInput`, `CompleteInboundRecoveryInput`, `InboundCallBinding`, `InboundCallAttempt`, `InboundCallStatus` | Construct with an inbound-attempt repository, caller-correlation repository, `TextNegotiationApplication` dependencies, private `EvidenceStorage`, clock, ID generator, fixed recovery fixture catalog, and limits. Inputs contain an opaque caller label and bounded provider IDs, never raw form/XML or FastAPI types. |
| `yuno_backend.volta.telephony` | `InboundCallerNotAllowed`, `InboundCorrelationNotFound`, `InboundCorrelationAmbiguous`, `InboundCallReplayConflict`, `InboundConsentRequired`, `InboundCallStateConflict` | Safe typed failures let API return reject/hangup behavior without leaking caller, operation candidates, provider payloads, storage paths, or database details. |
| `yuno_backend.volta.recovery.services` and `.commands` | Existing `SimulateInboundRecoveryService.simulate_in_transaction(...)` and `SimulateInboundRecoveryCommand` | Apply the fixed `MANDATE_SAFE` driver-delay terms under the current mandate and active commitment; the domain service remains authoritative for one winner, supersession, operation status, notification, evidence link, and recovery audit event. |
| `yuno_backend.volta.evidence.services` and `.commands` | Existing `GenerateBriefService.generate_in_transaction(...)` and `GenerateBriefCommand` | Persist a bounded deterministic brief for the resulting active commitment in the same application transaction; facts/changes describe only the accepted driver-delay fixture and contain no transcript or caller data. |
| `yuno_backend.volta.evidence.repositories` | Existing `EvidenceStorage`, extended only with a cleanup operation if needed for rollback-safe orphan removal | Store a bounded playable post-consent clip outside the database transaction, pass only its opaque recording reference into the recovery transaction, and remove the staged artifact if durable processing fails. Retrieval remains the existing authorized playback boundary. |

`AcceptInboundCallInput` atomically resolves one active caller binding, verifies an active commitment, reserves one provider call, and returns the existing commitment's `call_id` plus an opaque single-use binding. `RecordInboundConsentInput` advances `AWAITING_CONSENT` to `CONSENTED` exactly once. `CompleteInboundRecoveryInput` requires the consented/streaming attempt, post-consent audio, a bounded evidence offset/item/event identifier, and one correlation ID; it stores the artifact and commits the recovery, brief, attempt status, and audit facts as one logical operation. Identical retries return the stored result, while a changed payload or second active commitment fails without another mutation.

The caller-correlation repository owns explicit server-side bindings from an opaque synthetic caller label to operation ID. Eligibility requires exactly one binding whose operation is active for recovery, has exactly one active commitment, is not already blocked by an open escalation, and has no other active inbound attempt. A database uniqueness constraint protects one active attempt per operation and provider call. No scan-and-pick-first behavior is allowed.

## Browser/server, Twilio, OpenAI, and evidence handoffs

- Browser/server: existing generated queries poll or refresh operation/audit/evidence state. No browser value participates in inbound authorization or correlation.
- Twilio/server: signed HTTPS callbacks and the signed/authorized WSS stream terminate at FastAPI. Raw `From` is compared against server configuration, reduced to an opaque label, and discarded from application commands and logs.
- Server/OpenAI: the existing Fase 19 provider-neutral `RealtimeGateway` carries audio and tool events. Standard OpenAI credentials, Twilio auth token, and stream binding remain server-only.
- Application: the driver-delay completion calls the same recovery and brief services as the browser recovery flow. Neither Twilio nor the model can select terms, bypass mandate checks, or claim success.
- Evidence: only post-consent bounded audio is stored privately. Audit and UI receive an opaque reference indirectly through `evidence_id` plus timestamp/item/event metadata; no raw audio or filesystem path is exposed.
- Yuno/payment: none.

## Acceptance criteria

1. A valid signed inbound webhook from the configured account, number, and allowlisted synthetic caller resolves exactly one eligible operation and returns disclosure/consent TwiML; invalid signatures and zero/ambiguous correlations perform no stream, Realtime, evidence, or recovery mutation.
2. AI and recording disclosure is presented before DTMF consent. Only durable consent for the same provider call can mint and consume one stream binding; refusal, mismatch, expiry, or replay ends safely.
3. The existing media bridge accepts one signed, correctly bound bidirectional stream and preserves Fase 19 lifecycle, size, timeout, capacity, disconnect, and redaction controls.
4. Only bounded post-consent audio reaches private evidence storage. Pre-consent audio, raw forms, signatures, caller numbers, transcripts, standard credentials, provider payloads, and storage references never enter logs, errors, audit metadata, fixtures with real data, API responses, or Git.
5. One driver-delay completion uses the existing mandate-safe recovery service, supersedes exactly one active commitment, advances the operation once, and persists one recovery, notification, playable timestamp evidence, structured brief, inbound attempt status, and correlated audit sequence.
6. Duplicate voice/consent/start/stop/completion delivery returns or preserves the stored result and cannot duplicate a commitment, evidence artifact, brief, notification, or audit event. Changed reuse and concurrent attempts fail closed.
7. The existing operation/audit/evidence endpoints project the completed result and the current Recovery/Evidence/Audit screens render it after refresh without a handwritten contract or frontend-owned business rule.
8. Focused API/backend/PostgreSQL tests, `make check`, a clean `make generate`, browser smoke of the existing result surfaces, `git diff --check`, and secret/privacy/audio/provider-payload review pass.
9. A separately authorized sandbox call records participant label, country, origin class, endpoint, disclosure/consent text, recording purpose, cost/duration, retention/cleanup, result, and redacted evidence. Without that authorization and proof, the phase gate remains incomplete.

## Assumptions, risks, and fallback

- Assumption: merged Fases 15 and 19 remain the authoritative recovery facade, evidence playback, signed Twilio ingress, Media Stream bridge, and generated frontend surface.
- Assumption: the demo operator explicitly provisions one synthetic caller-to-operation binding before the call; the public webhook never accepts an operation ID.
- Risk: signature validation breaks behind a proxy or when Twilio adds fields. Mitigation: configured exact public URLs, all received form pairs, the supported validator, HTTPS/WSS, and focused proxy/parameter tests.
- Risk: a provider retry or two concurrent calls duplicate a replacement. Mitigation: durable provider-event/attempt keys, database uniqueness, row locking, single-use binding, deterministic idempotency keys, and one transactional completion facade.
- Risk: storing evidence before PostgreSQL commit leaves an orphan. Mitigation: stage through private storage, add bounded cleanup when required, and test rollback/cleanup; never fabricate a database-only playable reference.
- Risk: the Media Stream ends before enough post-consent evidence exists. Mitigation: mark the inbound attempt failed, preserve the previous commitment, store no brief or recovery success, clean staged audio, and expose no false completion.
- Risk: sandbox credentials, a public endpoint, caller enrollment, or legal consent wording is unavailable. Mitigation/fallback: keep deterministic text/browser voice and the existing recovery fixture as the demo path, report the sandbox gate unmet, and do not dial or deploy.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-26-accept-inbound-twilio-calls/**` | Fase 26 coordinator (`rmcosta-lab`) | Requirements, plan, validation, and any temporary wait. |
| `backend/src/yuno_backend/volta/telephony/**`, inbound application/domain contracts | Fase 26 backend writer (`rmcosta-lab`) | Provider-neutral correlation, consent/status/replay, and atomic recovery orchestration only. |
| `backend/src/yuno_backend/volta/persistence/**`, one versioned migration | Fase 26 backend writer (`rmcosta-lab`) | Inbound binding/attempt repositories, constraints, idempotency, and rollback-safe evidence lifecycle. |
| `backend/tests/**inbound**`, focused recovery/persistence tests | Fase 26 backend writer (`rmcosta-lab`) | Domain, concurrency, replay, redaction, storage cleanup, and PostgreSQL coverage. |
| `api/app/telephony/**`, telephony router/wiring/config | Fase 26 API writer (`rmcosta-lab`) | Raw signed ingress, TwiML, binding, Media Stream extension, safe errors, and dependency construction. |
| `api/tests/**telephony**`, matching contract/security tests | Fase 26 API writer (`rmcosta-lab`) | Signature, correlation, consent, stream, completion, and negative transport coverage. |
| `api/openapi.json`, `frontend/src/lib/api/generated/**` | Fase 26 coordinator, generated verification only | Regenerate from source and require zero semantic public-contract change; never hand-edit. |
| `frontend/src/features/recovery/**`, existing Recovery/Evidence/Audit pages | Fase 26 frontend verification writer (`rmcosta-lab`) | No planned source edit; browser-test the persisted terminal projection. A real defect may be fixed only after contract ownership is rechecked. |
| `.env.example`, setup docs | Fase 26 coordinator only if required | Names and safe empty defaults for inbound caller binding/public URLs/limits; never include a real number, SID, token, origin, or participant data. |
| `backend/pyproject.toml`, `api/pyproject.toml`, `uv.lock` | Fase 26 coordinator as one manifest/lock pair only if proven necessary | Prefer the already installed official Twilio validation capability; review any dependency before adding it. |
| Shared mission, stack, roadmap, challenge plan; Twilio account/number; deployment | no Fase 26 writer | No shared or external mutation is carried by phase start. |
