# Fase 27 — Send and verify WhatsApp recaps

## Outcome and scope

- **Objective:** send the bounded recap for the final active winner to one allowlisted, synthetic Twilio WhatsApp Sandbox participant and show trustworthy asynchronous delivery state in the control tower.
- **Target user:** the Volta operations coordinator running the authorized hackathon fixture.
- **Terminal result:** the recap remains `SIMULATED` until a valid Twilio callback reports `delivered` and the commitment has playable `audio_start_ms` evidence; only then does the durable projection and UI show `VERIFIED`.
- **Priority:** P0.1 hackathon evidence. The deterministic browser journey remains usable if Twilio, the Sandbox session, or the public callback is unavailable.
- **Included:** provider-neutral delivery authority and persistence, Twilio Programmable Messaging adapter for WhatsApp, signed status-callback ingress, public send/read contracts, OpenAPI/Orval regeneration, and visible control-tower status.
- **Excluded:** production sender onboarding, custom template approval, bulk or real-carrier messaging, SMS/email, inbound chat, free-form recipient entry, contact management, deployment, and any unapproved live delivery.

## Roadmap and coordination

- Branch: `phase/27-send-verified-whatsapp-recaps`.
- Owner/team contact: `rmcosta-lab`; no tracking Issue was requested.
- Dependencies: Fases 19 and 25 are DONE through merged PRs #28 and #21.
- Conflicts: none. Fase 22 is also DONE through merged PR #43; merged specs PR #44 explicitly permits Fase 27 after the trial.
- Gate: the roadmap gate is unchanged and governs review.
- No shared mission, tech-stack, roadmap, or challenge-plan edit is planned. The accepted WhatsApp decision from merged specs PRs #41 and #44 is consumed as written.

## Acceptance criteria

- A coordinator explicitly requests one delivery for the active winner's existing recap using an allowlisted participant label, `Idempotency-Key`, current operation version, and positive attestations that the participant joined the Sandbox and opened the 24-hour customer-service window.
- The backend verifies the active winner, recap, evidence, and playable offset, reserves one fingerprinted logical delivery transactionally, then performs provider I/O outside the database transaction.
- Same-request replay returns the durable delivery without sending twice; changed payload, stale state, non-active winner, missing recap/evidence, unknown label, closed/unconfirmed window, timeout, and uncertain provider outcome fail safely.
- The Twilio adapter sends bounded recap content through the configured WhatsApp Sandbox sender, maps only safe provider-neutral results, and keeps credentials, `whatsapp:` addresses, Message SIDs, raw forms, and provider errors out of public contracts and logs.
- A signed `application/x-www-form-urlencoded` status callback is verified against the exact public URL and all received parameters before typed delegation. Duplicate or reordered callbacks are durable and non-regressive.
- `accepted`, `queued`, and `sent` remain unverified. `failed` and `undelivered` remain explicit failures. Only `delivered` plus playable evidence atomically promotes the recap to `VERIFIED`; a later `read` may be retained as delivery detail but is not required by the gate.
- The control tower uses the generated client and shows confirmation, submitting, queued/sent, delivered/verified, failed/undelivered, replay, and simulated fallback states without exposing contact or provider identifiers.
- Mocked cross-layer checks pass, followed by one separately authorized Sandbox delivery to an opted-in synthetic participant and visible callback-confirmed status.

## HTTP contract gate

- `POST /v1/calls/{call_id}/recap-deliveries` (`send_whatsapp_recap`): demo auth, explicit allowed origin, mutation rate limit, correlation ID, and required `Idempotency-Key`; request contains `recap_id`, `expected_operation_version`, allowlisted `recipient_label`, `sandbox_opt_in_confirmed: true`, and `customer_service_window_confirmed: true`; returns `202` with `RecapDeliveryResponse` for a new reservation or exact replay.
- `GET /v1/recap-deliveries/{delivery_id}` (`get_recap_delivery`): returns the durable bounded projection without provider I/O.
- `GET /v1/operations/{operation_id}` continues to expose the recap lifecycle and delivery projection needed by the control tower; any accepted schema extension is generated rather than copied into TypeScript.
- `POST /v1/messaging/twilio/status` is provider ingress and excluded from public OpenAPI. It verifies `X-Twilio-Signature`, expected account/message binding, and form bounds before delegation; valid duplicate callbacks return `204` only after durable processing, while invalid signatures/bindings fail closed and retryable persistence failures return non-success.
- Public success data contains application UUIDs, normalized `RESERVED | SUBMITTED | SENT | DELIVERED | FAILED | UNDELIVERED` status, recap lifecycle, safe failure category, and timestamps. It contains no phone number, Message SID, raw recap body, signature, credential, or provider payload.
- Stable safe errors cover `401`, `403`, `404`, `409`, `422`, `429`, `502`, `503`, and `504`; provider details and private participant data never enter the response.

## Application contract gate

- New provider-neutral package: `yuno_backend.volta.delivery`.
- Public symbols include `SendRecapDeliveryCommand`, `RecapDelivery`, `RecapDeliveryStatus`, `RecapDeliveryGateway`, `RecapDeliveryRepository`, `SendRecapDeliveryService`, `RecordRecapDeliveryStatusService`, typed send/status results, and bounded safe exceptions.
- `SendRecapDeliveryService.reserve(...)` accepts typed application IDs, version, recipient label, confirmations, idempotency fingerprint, correlation, clock, repositories, and gateway boundary. It returns a durable reservation/replay and never accepts an address or provider payload.
- Provider submission occurs after commit through the injected gateway. Definitive provider results are finalized in a new transaction; ambiguous timeout/connection outcomes stay explicit and must not be retried with a new logical identity.
- `RecordRecapDeliveryStatusService.record(...)` accepts a normalized signed-ingress event with an opaque provider correlation, stable deduplication key, normalized status, and receipt time. It deduplicates and applies monotonic state changes, promotes the recap only for `DELIVERED` with evidence, and appends safe correlated audit events.
- Add `VERIFIED` to `RecapDisclosureState`; existing constructors and deterministic fallback continue to create `SIMULATED`. Persistence stores the delivery, fingerprint, private provider correlation, deduplication keys, normalized state, safe failure category, timestamps, and audit facts through a reversible migration.
- Twilio mapping lives in `yuno_backend.integrations.twilio.messaging`; FastAPI and Pydantic do not enter backend/core, and Twilio status strings do not enter domain models outside the adapter normalization boundary.

## Security, provider assumptions, and fallback

- Official Twilio documentation checked on 2026-08-30 confirms: every Sandbox participant must send the join message; that inbound message opens the 24-hour customer-service window; free-form content outside the window requires an approved template; status callbacks are form posts whose fields may evolve; and the supported SDK validator should validate the exact URL and all parameters.
- The address map and Sandbox sender are server-only configuration. Public responses, logs, fixtures, screenshots, generated files, and Git contain labels and synthetic canaries only.
- One authorized provider trial requires a named synthetic participant, explicit opt-in/window confirmation, expected cost, public callback endpoint, retained redacted evidence, and cleanup. Phase start itself authorizes no delivery or provider-account mutation.
- Fallback: preserve and visibly label the existing `SIMULATED` recap and playable audio evidence. Never claim `VERIFIED` from an API acceptance, queued/sent state, polling assumption, screenshot alone, or failed callback.

## One-writer ownership

| Path/artifact | Sole writer | Notes |
| --- | --- | --- |
| `backend/**`, backend migration | `rmcosta-lab` | Domain, application, persistence, and Twilio messaging adapter; implemented before API consumers. |
| `api/**`, `api/openapi.json` | `rmcosta-lab` | Pydantic source, thin routes, signed callback ingress, wiring, and OpenAPI export. |
| `frontend/**`, generated Orval output | `rmcosta-lab` | Generated client first, then control-tower presentation and browser checks. |
| This phase specification directory | `rmcosta-lab` | Planning and validation evidence. |
| Python/frontend manifests and lockfiles | `rmcosta-lab` only if required | No dependency change is planned; the existing Twilio SDK validator/client is preferred. |
| Shared project specs | none planned | Any broad decision discovered later pauses affected work and routes through `manage-shared-specs`. |

## Current official references

- [Twilio WhatsApp Sandbox](https://www.twilio.com/docs/whatsapp/sandbox)
- [Twilio outbound message status callbacks](https://www.twilio.com/docs/messaging/guides/track-outbound-message-status)
- [Twilio outbound status transitions](https://www.twilio.com/docs/messaging/guides/outbound-message-status-in-status-callbacks)
- [Twilio Message resource](https://www.twilio.com/docs/messaging/api/message-resource)
- [Twilio webhook security](https://www.twilio.com/docs/usage/webhooks/webhooks-security)
