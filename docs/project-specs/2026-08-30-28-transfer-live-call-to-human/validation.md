# Phase 28 validation — Transfer a live call to the human coordinator

## Planning and coordination

- [x] Requirements, contracts, ownership, exclusions, risks, and fallback still match the Phase 28 roadmap gate on refreshed `origin/main`.
- [x] Phase 20 remains DONE through merged PR #34 with its gate evidence recorded.
- [x] Remote Phase 28 branch/PR state, conflicts, and overlapping telephony/API/frontend/shared-file pull requests were refreshed before implementation; no conflict or open Phase 28 PR was found.
- [x] Only the phase specification and approved backend/API/frontend/generated/migration paths enter the phase.

## Current official provider evidence

- [x] Current Twilio Call update documentation confirms the accepted way to change an in-progress call to server-owned TwiML without ending the remote leg.
- [x] Current Twilio `<Conference>` and Participants documentation confirms participant creation, join/leave events, first-participant callback ownership, and account CPS behavior used by the phase.
- [x] Current Twilio request-signature, trial/account, geographic calling, number, recording, disclosure, and consent constraints were reviewed; recording remains disabled and no trial or account mutation was authorized.
- [x] Provider fields used by the adapter are frozen from the official references below; individually authorized live trials exercised outbound consent, Media Streams, remote-leg conference redirection, coordinator dialing, and the complete callback-confirmed handoff.

## Backend/core authority and persistence

- [x] Public provider-neutral commands, readiness/context, handoff values/statuses/events, gateway, repository, service, and safe errors match `requirements.md` and import no FastAPI/Pydantic/provider payload.
- [x] One transaction validates the live call/version, reserves or replays the logical handoff, persists the fingerprint and AI fence, and appends the requested audit event before provider I/O; no transaction stays open across the network call.
- [x] Same-request replay is durable and side-effect free; changed payload, stale call, missing context, unknown destination, and another active handoff fail safely with zero provider I/O.
- [x] Callback event IDs deduplicate durably; reordered and partial-commit callback retries do not regress or fabricate state; outcomes correlate to the request.
- [x] Reservation races with pending AI audio and commitment-capable tools are deterministic: output is dropped/cleared and mutations fail with a safe authority error after the fence.
- [x] PostgreSQL-isolated persistence tests pass against PostgreSQL 17: the handoff round trip proves rollback before provider I/O, retry, durable replay after restart, callback deduplication, AI fencing, one correlated requested/joined audit outcome, schema constraints, upgrade/downgrade/upgrade, and a pre-DDL downgrade refusal when durable Phase 28 evidence exists. Migration review also restored the bounded `draft_version` constraint, aligned SQLAlchemy metadata, and indexed the handoff `operation_id` foreign key.

## Twilio adapter

- [x] The adapter updates only the expected live remote Call into the bounded conference and creates only the allowlisted coordinator participant.
- [x] Twilio URLs, credentials, E.164 values, Call/Conference/Participant identifiers, form fields, TwiML, HTTP responses, and provider exceptions remain inside the adapter/configuration boundary.
- [x] Injected-transport tests cover accepted redirect/add-participant behavior, authentication/permission/rate limit, definitive failure, timeout, connection loss, invalid/oversized response, and uncertain outcome.
- [x] Exact same-request replay cannot add a second coordinator; ambiguous outcomes remain explicit and a new provider retry is intentionally unsupported.
- [x] Logs, errors, representations, fixtures, and snapshots redact credentials, phone numbers, provider payloads, and private participant data.

## Public API and verified callback ingress

- [x] `POST /v1/calls/{call_id}/handoffs` enforces demo auth, explicit origin, rate limit, correlation, current call status, fresh human authorization, allowlisted label, and `Idempotency-Key` before provider I/O.
- [x] `GET /v1/calls/{call_id}/handoff-readiness` supplies the exact durable call-status timestamp and bounded safe context required by the POST without provider I/O or private identifiers.
- [x] `202` new/replay and safe `401`, `403`, `404`, `409`, `422`, `429`, `502`, `503`, and `504` semantics match `requirements.md` without leaking provider or participant data.
- [x] `GET /v1/calls/{call_id}/handoffs/{handoff_id}` returns the bounded durable projection without provider I/O and exposes only declared safe errors.
- [x] The context projection includes current mandate version/facts, eligible quote summaries, structured brief, and normalized call status, but no raw transcript, raw audio reference, provider payload, E.164 number, signature, or credential.
- [x] Twilio handoff callbacks verify exact signatures and expected account/call/conference/participant binding before typed parsing and delegation.
- [x] Missing/tampered/ambiguous callback input fails closed; duplicate valid callbacks return success only after durable duplicate-safe processing; retryable persistence failure returns non-success.
- [x] Stable operation IDs and declared Pydantic schemas/errors pass focused API contract tests; all public `422` responses use the safe envelope.

## OpenAPI, Orval, and frontend

- [x] API contract tests pass before generation; `api/openapi.json` and `frontend/src/lib/api/generated/**` were regenerated from accepted Pydantic/OpenAPI sources and reviewed.
- [x] The frontend uses only generated hooks/types and an injected test boundary; no handwritten duplicate HTTP DTO or provider field is added.
- [x] The live-session interface presents current mandate, quotes, structured brief, readiness status, and normalized call status before an explicit `Take over live call` confirmation.
- [x] Processing, `JOINED`, stale, `FAILED_SAFE`, `TIMED_OUT_SAFE`, duplicate-disabled, exact-replay recheck, and browser/text fallback states are truthful and preserve context; unsupported provider retry/termination is not offered.
- [x] Keyboard activation, visible focus, status announcements, disabled-state semantics, color-independent meaning, long content, and mobile/desktop layout pass focused tests and browser review.
- [x] Browser console and network inspection show no runtime error, raw transcript, real number, provider payload, signature, credential, or duplicate request.

## Cross-layer and security behavior

- [x] The fake-provider HTTP journey passes readiness, explicit authorized takeover, signed remote-participant callback, signed coordinator callback, AI fence, callback-confirmed `JOINED`, refreshed bounded read projection, remote-leg continuity evidence, and one correlated requested/joined audit outcome.
- [x] Deterministic adapter/service/API/bridge tests cover redirect failure, timeout, stale version, duplicate action/callback, callback reorder/tampering, partial callback commit, and AI audio/tool races in declared safe states without fabricated participation.
- [x] FastAPI remains a thin transport boundary; backend owns authority/state/audit; Twilio mapping stays in the adapter; React owns presentation and explicit user action only.
- [x] No raw audio/transcript, real E.164 destination, credential, signature, authorization header, provider payload, private participant data, or OpenAI secret enters Git, public responses, logs, errors, screenshots, or generated artifacts; synthetic test canaries are explicitly labeled.

## Required deterministic commands

- [x] `uv run ruff check .` passes for the affected Python workspace.
- [x] Root Python suite passes after the Phase 28 persistence, fake-provider integration, and live-callback race regression coverage: `686 passed, 45 skipped, 2 deselected`; the only warning is the existing Starlette `httpx` deprecation warning.
- [x] `make python-check` passes from the repository root after the local allowlist was corrected to the required label-to-E.164 JSON mapping and the missing-database test explicitly isolated `database_url=""`.
- [x] `make generate` passes from the repository root; OpenAPI export and Orval generation are deterministic.
- [x] `pnpm lint` passes from `frontend/`.
- [x] `pnpm build` passes from `frontend/` with 13 static pages.
- [x] `make check` passes after the live-callback race correction: Ruff, `686 passed, 45 skipped, 2 deselected`, frontend lint, typecheck, and the 13-page production build all pass.
- [x] Focused Phase 28 Playwright tests pass (`3 passed`); a coordinator rerun inside the managed sandbox hit the environment's `EMFILE` watcher limit and was stopped, with no code assertion failure.
- [x] Desktop and mobile browser smoke plus Playwright/Chrome DevTools console/network inspection pass; mobile width is 390/390 and Lighthouse snapshot accessibility is 100.
- [x] `git diff --check`, complete tracked/untracked review, and secret/privacy/phone/transcript/audio/provider-payload scans pass; matches are labeled synthetic test canaries only.

## Authorized sandbox handoff

- [x] Every live attempt was individually authorized. The latest bounded execution used allowlisted `coordinator-1` as the remote destination and `coordinator-3` as the requested human coordinator, used a temporary Cloudflare Quick Tunnel, kept recording disabled, retained redacted state/timing evidence only, and shut down both API and tunnel afterward.
- [x] In the sixth individually authorized sandbox attempt, the user confirmed directly that `coordinator-1` remained connected and conversed with `coordinator-3` in the same call; recording remained disabled.
- [x] The final individually authorized sandbox attempt passed the complete gate. Consent and Media Stream connected; both signed participant callbacks returned `204`; the durable projection reached and remained `JOINED`; the Conference SID was bound; four callback event IDs were retained; one AI authority fence, one `HANDOFF_REQUESTED` audit event, and one `HANDOFF_JOINED` audit event persisted. The participants had left when the sanitized evidence query ran, so both presence flags truthfully read false without regressing the terminal `JOINED` outcome. Focused bridge/tool-race tests prove pending AI output is dropped and commitment-capable tools remain fenced, while the browser journey proves the same durable `JOINED` projection is rendered truthfully.
- [x] Unsuccessful or partially evidenced attempts remain reported separately rather than presented as full gate evidence. The first and third attempts received no consent; the second and fourth reached consent/Media Stream but ended before handoff. The fifth exposed missing durable normalization for nonterminal call statuses; the safety gate correctly prevented the coordinator dial. After that correction, the sixth produced a real two-person conversation, but the remote `participant-join` callback raced ahead of Conference binding persistence and received `403`; later signed callbacks were accepted, both participants were observed, and the final durable projection was conservatively `FAILED_SAFE` after both left rather than fabricated `JOINED`. The binding store correction was then covered by focused in-memory and isolated PostgreSQL race regressions before the final successful live attempt.

## Explicitly not authorized by phase start

- [x] No deployment, production access, provider account/number/permission change, real-carrier contact, unapproved PSTN call, recording, Yuno operation, payment, financial mutation, or unrelated remote mutation is authorized.

## Official provider references refreshed on 2026-08-30

- [Twilio Call resource](https://www.twilio.com/docs/voice/api/call-resource): an in-progress call can begin new TwiML through a Call update.
- [Twilio `<Conference>`](https://www.twilio.com/docs/voice/twiml/conference): conference start/end and participant join/leave callbacks provide asynchronous evidence; the first participant owns the callback configuration.
- [Twilio Conference Participants resource](https://www.twilio.com/docs/voice/api/conference-participant-resource): creating a participant initiates an outbound call into an active conference and is subject to account call-per-second limits.
- [Twilio webhook security](https://www.twilio.com/docs/usage/webhooks/webhooks-security): exact URL and all evolving form parameters participate in signature verification.
- [Twilio trial account](https://www.twilio.com/docs/usage/trials): trial Voice calls are restricted to verified recipients and the sign-up geography.
- [Twilio Voice dialing permissions](https://www.twilio.com/docs/voice/api/dialing-permissions-resources): destination countries remain account-controlled to reduce toll-fraud exposure.
- [Twilio recording considerations](https://help.twilio.com/articles/360011522553-Legal-Considerations-with-Recording-Voice-and-Video-Communications): recording requires jurisdiction-appropriate consent; Phase 28 keeps recording disabled.
