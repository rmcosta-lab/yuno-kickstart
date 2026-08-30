# Fase 26 — Plan

## Task groups

1. **Freeze current contracts and official provider behavior**
   - Reconfirm merged Fase 15 recovery/evidence contracts and Fase 19 signed Twilio ingress, stream binding, frame lifecycle, Realtime bridge, and browser projections.
   - Read current official Twilio voice webhook, request validation, TwiML `<Gather>`, `<Connect><Stream>`, custom parameter, and Media Stream message documentation. Record the exact configured URL/form validation and consent/stream ordering used.
   - Freeze the provider-only routes, provider-neutral inputs/results/errors, caller-correlation eligibility, statuses, evidence bounds, and deterministic brief facts before implementation.

2. **Add durable inbound correlation and attempt state**
   - Define the provider-neutral inbound models/application protocol and safe exception vocabulary under backend telephony.
   - Add the smallest migration and repositories for explicit opaque caller-to-operation bindings and inbound attempts/events, including unique active-operation/provider-call constraints, consent timestamp, status, stream consumption, completion fingerprint/result, and safe correlation IDs.
   - Prove zero, one, and multiple eligible bindings; stale/ineligible operation, missing/duplicate active commitment, open escalation, concurrent attempt, identical replay, and changed replay behavior with repository/application tests.

3. **Build the transactional recovery completion facade**
   - Accept a consented attempt plus bounded post-consent audio and fixed driver-delay metadata; stage playable audio through the private `EvidenceStorage` boundary without logging it.
   - In one database unit of work, lock the operation/attempt, invoke `SimulateInboundRecoveryService.simulate_in_transaction` with current mandate-safe deterministic terms and staged evidence, then invoke `GenerateBriefService.generate_in_transaction` for the resulting commitment.
   - Persist completion status/result and the safe audit correlation in the same commit. On failure, roll back state and remove staged evidence; on identical retry return the durable result without storing or mutating again.

4. **Implement signed inbound voice and consent ingress**
   - Extend the existing raw bounded form reader to validate the configured full URL and every received pair with the supported Twilio request validator before typed access.
   - Implement `/v1/telephony/twilio/inbound/voice`: account/destination/allowlist checks, one backend correlation, durable attempt reservation, AI/recording disclosure, DTMF consent gather, and safe hangup behavior.
   - Implement `/v1/telephony/twilio/inbound/consent`: reverify the request, bind it to the same call, durably record explicit consent, and return one `<Connect><Stream>` with only the existing WSS URL and opaque single-use binding.

5. **Extend the existing bridge for consented evidence and completion**
   - Reuse the Fase 19 WebSocket signature, account/call/stream/media-format checks, one-stream capacity, bounded queues, frame sizes, duration, backpressure, and Realtime lifetime.
   - Capture only bounded post-consent inbound audio in the playable private format and retain no raw transcript/provider body. Preserve normal output audio and safe barge-in behavior.
   - On the fixed driver-delay tool/completion signal and orderly stop, submit one typed completion to the backend facade. On refusal, malformed frames, insufficient audio, disconnect, timeout, OpenAI/tool/storage/database failure, cancel peers once, persist a safe non-success status, and never claim a recovery.

6. **Integrate existing application and frontend projections**
   - Construct the inbound facade from the existing session/UoW, private evidence storage, recovery fixture catalog, clock/IDs, and telephony runtime; keep FastAPI and Twilio mappings out of backend/core.
   - Verify existing `get_operation`, `get_operation_audit`, and evidence playback return the new status/commitment/recovery/evidence/brief/notification/audit result without a new public DTO.
   - Run `make generate` after API tests and require no semantic OpenAPI or Orval change. Use the current frontend generated hooks and refresh flow; do not edit frontend source unless verification exposes a scoped defect.

7. **Exercise deterministic and browser journeys**
   - Add focused valid and negative HTTP/WebSocket tests for signatures, added form fields, proxy/origin mismatch, allowlist/correlation ambiguity, consent refusal/replay, stream mismatch/replay, duplicate frames/events, concurrency, disconnect, redaction, and cleanup.
   - Add backend unit/PostgreSQL tests proving exactly one mandate-safe replacement, operation version/status, brief, evidence artifact and timestamp, notification, inbound attempt status, audit events, replay, rollback, and out-of-mandate rejection.
   - Run the complete synthetic inbound transport-to-persistence journey, then browser-smoke Recovery, Evidence playback, and Audit at desktop and mobile widths; inspect console and network errors.

8. **Run final checks and the separately authorized sandbox gate**
   - Run focused checks, `make check`, `make generate`, browser verification, `git diff --check`, migration review, complete diff/untracked review, and targeted secret/number/audio/signature/provider-payload scans.
   - Only after explicit authorization records the synthetic participant, country, public endpoint, disclosure/consent text, recording purpose, cost/duration, retention, and cleanup, configure the Twilio sandbox number and place one inbound call.
   - Record redacted proof of signed webhook acceptance, consent before stream, bidirectional audio, driver-delay completion, persisted/UI evidence, and cleanup. Without authorization or credentials, leave this item unchecked and retain the browser recovery fallback.

## Ownership and dependency order

- Coordinator: `rmcosta-lab`. The backend writer owns backend telephony/application/persistence/migration/tests; the API writer owns `api/app/telephony/**`, router/wiring/config, and transport tests. The frontend writer owns verification only unless a scoped rendering defect is proven.
- Groups 1–2 freeze contracts and durable ownership before transport work. Group 3 must pass with fakes before provider ingress may trigger it.
- Groups 3 and 4 can proceed in parallel after the inbound application protocol is frozen; group 5 consumes both. The coordinator alone reconciles their shared telephony contract.
- Migration and repository changes have one backend writer. `api/openapi.json` and Orval output have one generated checkpoint owner. Manifest and `uv.lock` changes move as one pair only if required.
- Group 6 is the integration checkpoint; group 7 proves deterministic end to end; group 8 is the final constitutional and separately authorized provider gate.
- No shared specification, new UI, Twilio account/number, deployment, remote migration, live call, recording, Yuno operation, payment, or unrelated remote change is authorized by this plan.

## Contract and integration checkpoints

- **Official behavior:** supported request validation uses the exact configured URL and all form fields; AI/recording disclosure and durable consent occur before `<Connect><Stream>`.
- **Correlation:** one opaque caller binding resolves exactly one eligible operation and active commitment under lock. Zero/multiple candidates, open escalation, and concurrent attempt fail before stream or model/storage I/O.
- **Persistence:** inbound attempt/event identifiers and database constraints make voice, consent, stream, completion, and retries duplicate-safe.
- **Recovery:** one completion calls existing mandate/recovery/evidence/brief services; Twilio and OpenAI never choose terms or bypass deterministic policy.
- **Evidence:** only bounded post-consent audio is privately playable; rollback removes staged storage and no raw data enters database projections or logs.
- **Transport:** the Phase 19 binding, Media Stream protocol, Realtime tool correlation, timeouts, cancellation, and safe close behavior remain intact.
- **Public contract:** existing operation/audit/evidence routes are sufficient; OpenAPI/Orval generation is clean and frontend source needs no parallel DTO.
- **Browser:** the current Recovery, Evidence, and Audit surfaces render the durable terminal result and evidence playback with no console/network failure.
- **Provider:** deterministic evidence and a sandbox call are reported separately; repository tests never imply that a real call occurred.

## Shared changes, communication, and temporary waits

- No shared mission, tech stack, roadmap, or challenge-plan change is planned. If implementation proves that a new global consent/retention decision or supporting prerequisite is required, pause the affected group and route it through `manage-shared-specs`; do not silently broaden this phase.
- Before any manifest/lock, generated artifact, `.env.example`, or shared setup-document edit, refresh open pull requests touching that file and notify the affected owner.
- No prerequisite wait exists at planning time: Fases 15 and 19 are merged and no declared conflict is active.
- Sandbox validation waits on separate explicit authority plus credentials/public HTTPS/WSS endpoint. That wait does not authorize deployment, number changes, caller enrollment, recording, or dialing.

## Guardrails and fallback

- Never log/store raw Twilio forms, signatures, auth tokens, E.164 values, raw provider payloads, raw transcripts, standard OpenAI credentials, stream bindings, or unbounded audio.
- Never infer authorization from caller ID or a provider SID, select the first operation, allow pre-consent evidence, create a second active attempt, or retry an uncertain completion with new identifiers.
- Never return recovery success until the evidence, replacement/status, brief, notification, attempt result, and audit facts are durably committed and retrievable.
- If secure correlation, playable storage cleanup, provider behavior, consent language, public ingress, or authorized sandbox access cannot satisfy the gate, preserve the existing browser voice/text recovery and recorded fallback, report the unmet criterion, and do not call or fabricate evidence.
