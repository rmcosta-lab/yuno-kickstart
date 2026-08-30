# Fase 27 plan — Send and verify WhatsApp recaps

## Task groups

1. **Freeze provider and application semantics**
   - Refresh official Sandbox, WhatsApp window/template, Message resource, status-callback, signature, retry, timeout, and trial-account documentation.
   - Freeze the provider-neutral state machine, monotonic callback rules, idempotency fingerprint, evidence prerequisite, public projections, safe errors, and configuration inventory before dependent work.

2. **Implement backend authority and persistence**
   - Add the `yuno_backend.volta.delivery` models, commands, protocols, services, errors, repositories, and audit outcomes defined in `requirements.md`.
   - Extend recap disclosure with `VERIFIED` while preserving `SIMULATED` as the default/fallback.
   - Add one reversible migration and PostgreSQL repositories for reservation/replay, private provider correlation, callback deduplication, monotonic state, verification, and rollback.
   - Test active-winner/evidence checks, same-request replay, fingerprint conflict, stale version, missing evidence, callback duplicate/reorder, atomic promotion, uncertain outcome, and redaction before provider code depends on them.

3. **Implement the Twilio WhatsApp adapter**
   - Add the configured Sandbox sender and label-to-address allowlist without exposing addresses beyond the adapter/configuration boundary.
   - Submit one bounded Message resource with a status-callback URL and normalize accepted/definitive/ambiguous outcomes.
   - Use injected transport/SDK boundaries to test authentication, mapping, timeout, connection loss, malformed response, provider failure, recipient allowlist, retry safety, and secret/contact redaction.

4. **Expose typed HTTP and callback boundaries**
   - Add Pydantic send/read projections, stable operation IDs, auth/origin/rate/idempotency checks, safe error translation, and dependency wiring.
   - Reuse the supported Twilio SDK validator for exact-URL, evolving-form signature validation before bounded parsing and account/message binding.
   - Keep the provider callback out of public OpenAPI and return success only after durable duplicate-safe processing.
   - Add focused API contract, signature, invalid binding, callback reorder/duplicate, provider-failure, and no-provider-I/O tests.

5. **Regenerate contracts and add the control-tower flow**
   - Run API tests and export `api/openapi.json`; then regenerate Orval and review the complete generated diff before editing consumers.
   - Add an accessible explicit confirmation using only generated hooks/types and a configured participant label.
   - Render honest submitting, submitted, sent, delivered/verified, failed/undelivered, replay, polling/refresh, and simulated-fallback states at mobile and desktop widths.

6. **Integrate and validate deterministically**
   - Exercise a fake-provider journey from active winner and evidence through send, signed reordered callbacks, durable `VERIFIED`, refreshed operation projection, and audit timeline.
   - Exercise stale/missing evidence, duplicate and changed idempotency, invalid signature/binding, timeout/uncertain result, failed/undelivered, and provider-unavailable fallback.
   - Run `make generate`, `make check`, focused browser interaction checks, desktop/mobile smoke, console/network inspection, `git diff --check`, and secret/contact/provider-payload scans.

7. **Run the Sandbox gate only with separate authorization**
   - Confirm the synthetic participant joined the Sandbox and refreshed the 24-hour window; record authorization, public HTTPS callback, expected cost, retained redacted evidence, and cleanup before sending.
   - Prove one delivery reaches callback-confirmed `DELIVERED`, the evidence remains playable at `audio_start_ms`, and the control tower shows `VERIFIED` without exposing private identifiers.
   - If provider access fails, leave the live criterion unchecked and demonstrate the declared `SIMULATED` fallback without claiming external delivery.

## Ownership and checkpoints

- Coordinator and sole phase owner: `rmcosta-lab`.
- One writer owns each layer sequentially: `rmcosta-lab` for `backend/**`, then `api/**` and `api/openapi.json`, then `frontend/**` and generated Orval output. The same owner avoids cross-worktree overlap; each checkpoint lands before the next layer consumes it.
- The phase spec directory is coordinator-owned. No shared project-spec edit, manifest, or lockfile change is planned.
- **Application checkpoint:** provider-neutral authority, persistence, migration, idempotency, callback ordering, evidence, and safe errors pass before adapter/API work.
- **Provider checkpoint:** current official fields and signature behavior are recorded before adapter/callback mapping is accepted.
- **HTTP checkpoint:** contract tests pass before OpenAPI export; OpenAPI is the only source for Orval generation.
- **Generation checkpoint:** generated diffs are reviewed before frontend integration; no handwritten TypeScript DTO is allowed.
- **Browser checkpoint:** focused interaction coverage precedes mobile/desktop smoke and console/network inspection.
- **Live checkpoint:** Sandbox evidence is separately authorized and reported; deterministic validation does not imply a real delivery.

## Guardrails

- No deployment, production access, provider-account/sender/template mutation, participant contact, WhatsApp delivery, PSTN call, recording, Yuno/payment operation, or unrelated remote change is authorized by this plan.
- Do not keep a database transaction open across Twilio I/O, retry an ambiguous send with a new logical identity, regress callback state, or promote from `accepted`, `queued`, `sent`, or `read` without prior `delivered` evidence.
- Do not expose or log addresses, Message SIDs, credentials, signatures, raw recap content/forms/provider payloads, private participant data, or recording references.
- Do not move winner/evidence/verification authority into FastAPI, React, provider responses, or callbacks; those boundaries validate/map and delegate only.
- A new broad shared decision pauses affected work, records the impact, and routes through `manage-shared-specs`; implementation itself should use `implement-phase`.
