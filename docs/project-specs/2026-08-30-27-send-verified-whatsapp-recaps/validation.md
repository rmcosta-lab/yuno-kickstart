# Fase 27 validation — Send and verify WhatsApp recaps

## Planning and coordination

- [ ] Requirements, exclusions, contracts, ownership, risks, gate, and fallback still match refreshed `origin/main`.
- [ ] Fases 19 and 25 remain DONE; no competing Phase 27 branch/PR or newly declared conflict exists.
- [ ] Only approved phase-spec, backend, API, frontend, generated, migration, and configuration-inventory paths enter the phase.

## Current provider evidence

- [ ] Current official Sandbox join, 24-hour window/template, Message resource, callback status, webhook signature, trial/account, retry, timeout, and error guidance is recorded.
- [ ] Provider fields and mappings are frozen from official references; evolving callback parameters remain compatible with supported SDK signature validation.
- [ ] No provider-account, sender, template, destination, or live-delivery mutation occurs without separate explicit authorization.

## Backend/core and persistence

- [ ] Provider-neutral commands, models, statuses, gateway, repositories, services, results, and safe exceptions match `requirements.md` and import no FastAPI/Pydantic/Twilio payload.
- [ ] Reservation validates active winner, recap, operation version, allowlisted label, opt-in/window confirmations, and playable evidence before provider I/O.
- [ ] Fingerprinted idempotency makes exact replay side-effect free; changed payload, races, stale state, missing recap/evidence, and unknown label fail safely.
- [ ] No transaction stays open across network I/O; definitive and ambiguous provider outcomes persist truthfully and safely.
- [ ] Duplicate/out-of-order callback events deduplicate durably, never regress state, and append safe correlated audit events.
- [ ] Only `DELIVERED` plus playable evidence atomically changes the recap from `SIMULATED` to `VERIFIED`; rollback preserves the prior state.
- [ ] PostgreSQL tests cover constraints, indexes, round trips, restart replay, rollback, and migration upgrade/downgrade/upgrade.

## Twilio adapter and callback ingress

- [ ] The adapter sends one bounded WhatsApp Message only to the configured allowlisted label and supplies the exact status-callback URL.
- [ ] Credentials, addresses, Message SIDs, status strings, raw forms, and provider errors remain inside adapter/private persistence boundaries.
- [ ] Injected tests cover accepted send, definitive failure, timeout, connection loss, malformed response, uncertain outcome, duplicate prevention, and redaction.
- [ ] The callback verifies `X-Twilio-Signature` with the supported SDK, exact public URL, and every received form parameter before typed parsing/delegation.
- [ ] Missing/tampered signatures, wrong account/message binding, malformed/oversized fields, and unknown deliveries fail closed.
- [ ] Valid duplicate callbacks return success only after durable replay; persistence failure returns non-success so Twilio can retry.

## HTTP, OpenAPI, and frontend

- [ ] Public POST/GET contracts enforce auth, origin, rate limit, idempotency, explicit confirmation, stable operation IDs, and declared safe errors without private/provider fields.
- [ ] API contract tests pass before `api/openapi.json` export; `make generate` reproduces OpenAPI and Orval output.
- [ ] The frontend uses only generated hooks/types and sends no address or provider identifier.
- [ ] Confirmation, submitting, submitted, sent, delivered/verified, failed/undelivered, replay, and simulated fallback states are truthful and accessible.
- [ ] Keyboard/focus, live status announcements, disabled states, color-independent meaning, long content, and mobile/desktop layout pass focused checks.
- [ ] Browser console and network inspection show no runtime error, duplicate mutation, address, provider ID/payload, signature, credential, or recording reference.

## Cross-layer and security

- [ ] Fake-provider integration passes active winner → reservation → send → signed reordered callbacks → durable `VERIFIED` → refreshed operation/audit projection.
- [ ] Deterministic tests cover stale/missing evidence, same and changed idempotency, callback duplicate/reorder/tampering, failure, timeout, uncertain outcome, and provider-unavailable fallback.
- [ ] FastAPI remains thin, backend owns authority/state/audit, Twilio mapping stays in the adapter, and React owns presentation/explicit action only.
- [ ] Secret/contact/provider-payload scans confirm no address, Message SID, credential, signature, raw recap/form, private participant data, or recording reference entered Git, logs, errors, screenshots, or generated public artifacts.

## Required deterministic commands

- [ ] `uv run ruff check .`
- [ ] `uv run pytest`
- [ ] `make python-check`
- [ ] `make generate`
- [ ] `pnpm lint` from `frontend/`
- [ ] `pnpm typecheck` from `frontend/`
- [ ] `pnpm build` from `frontend/`
- [ ] `make check`
- [ ] Focused browser tests plus desktop/mobile smoke, console, and network inspection.
- [ ] `git diff --check`, complete diff/untracked review, and secret/contact/provider-payload scan.

## Authorized Sandbox delivery

- [ ] A separately authorized synthetic participant has joined the Twilio Sandbox and opened the 24-hour customer-service window; endpoint, cost, retained evidence, and cleanup are recorded.
- [ ] One real Sandbox send reaches signed callback-confirmed `DELIVERED`, the active winner's evidence plays at `audio_start_ms`, and the control tower visibly shows `VERIFIED`.
- [ ] Restrictions, latency, callback sequence, failures, redacted evidence, and cleanup are reported separately; an unavailable provider leaves this criterion unchecked and uses `SIMULATED` fallback.

## Explicitly not authorized by phase start

- [ ] No deployment, production access, account/sender/template change, participant contact, WhatsApp delivery, PSTN call, recording, Yuno/payment operation, financial mutation, or unrelated remote mutation was performed during planning.

## Official references refreshed on 2026-08-30

- [Twilio WhatsApp Sandbox](https://www.twilio.com/docs/whatsapp/sandbox)
- [Track outbound message status](https://www.twilio.com/docs/messaging/guides/track-outbound-message-status)
- [Outbound status transitions](https://www.twilio.com/docs/messaging/guides/outbound-message-status-in-status-callbacks)
- [Twilio Message resource](https://www.twilio.com/docs/messaging/api/message-resource)
- [Twilio webhook security](https://www.twilio.com/docs/usage/webhooks/webhooks-security)
