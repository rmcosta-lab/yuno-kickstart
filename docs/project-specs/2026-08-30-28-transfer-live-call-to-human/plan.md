# Phase 28 plan — Transfer a live call to the human coordinator

## Task groups

1. **Refresh state and current provider contracts**
   - Refresh `origin/main`, Phase 20 evidence, remote Phase 28 refs/PRs, and overlapping telephony/API/frontend/shared-file work before implementation.
   - Read current official Twilio Call update, `<Conference>`, Participants, request-signature, callback, trial/account, regional calling, number, and recording/compliance documentation. Freeze only fields needed for one bounded sandbox handoff.
   - Inspect the existing outbound-call status, media bridge, operation projection, audit service, and Phase 20 live-session control. Confirm how inbound Phase 26 calls bind to the same provider-neutral call-session identifier without making Phase 26 a dependency.

2. **Freeze backend and HTTP contracts before parallel work**
   - Define the provider-neutral command, context, status/event, result, repository, gateway, service, authority-fence, safe-error, fingerprint, and monotonic transition contracts from `requirements.md`.
   - Define Pydantic POST/read projections, stable operation IDs, `202`/`200` semantics, safe errors, and the signed callback event vocabulary. Add contract tests before provider or UI wiring.
   - Decide the smallest reversible persistence change for durable reservation, AI authority, callback deduplication, and audit. Do not keep a database transaction open during provider I/O.

3. **Implement deterministic handoff authority and persistence**
   - Atomically validate the live call and current status version, resolve bounded transcript-free context, reserve or replay one logical handoff, persist the request fingerprint, revoke AI speech/commitment authority, and append the requested audit event.
   - Persist monotonic `CONNECTING`, `JOINED`, `FAILED_SAFE`, and `TIMED_OUT_SAFE` outcomes plus stable callback identifiers. Enforce one active handoff and exact same-key replay.
   - Test stale call, missing context, duplicate request, changed payload, duplicate/reordered callback, rollback, audit correlation, and the race between reservation and AI speech/tool execution.

4. **Add the Twilio handoff adapter**
   - Map the provider-neutral handoff to an in-progress Call update that moves the existing remote leg to a server-owned conference, then add only the configured allowlisted coordinator participant.
   - Keep account credentials, E.164 values, Call/Conference/Participant SIDs, REST form fields, TwiML, and provider responses inside the adapter/configuration boundary. Reuse the injected HTTP transport and existing redaction/error vocabulary where possible.
   - Handle definitive failure, timeout, connection loss, uncertain outcome, and same-request retry without dialing a second coordinator. Unit-test with synthetic identifiers and injected transport only.

5. **Wire API ingress, media fencing, and callback processing**
   - Add thin demo-authorized POST/read routes, origin/rate/idempotency controls, dependency wiring, and stable safe-error mapping.
   - Verify the raw Twilio form signature and expected account/call/conference/participant binding before parsing and delegation. Return success only after durable duplicate-safe status processing.
   - Gate media-bridge output and commitment-capable tool dispatch on the durable authority fence; drop/clear pending model audio when reservation succeeds and keep read-only context available.
   - Add focused API, signature, callback, uncertain-outcome, media/tool race, redaction, and zero-provider-I/O tests.

6. **Regenerate contracts and build the control-tower flow**
   - Run API contract tests, export OpenAPI, run Orval, and inspect all generated changes before editing consumers.
   - Reuse the live-session card to present mandate, quotes, structured brief, and normalized call status; add the explicit accessible takeover confirmation and generated POST/read flow.
   - Render honest processing, joined, stale, failed-safe, timed-out-safe, duplicate-disabled, and fallback states. Preserve browser voice and text fallback without implying PSTN success.
   - Add focused frontend and browser coverage for keyboard/focus, live announcements, mobile/desktop layout, duplicate prevention, context redaction, success, timeout, and failure.

7. **Integrate and validate deterministic gates**
   - Exercise the full fake-provider journey: active call, context display, explicit takeover, AI fence, remote-leg conference transition, coordinator join callback, generated-client refresh, and audit outcome.
   - Exercise redirect-success/participant-failure, timeout, duplicate action/callback, stale status, callback tampering, AI audio/tool race, and safe retry/termination choices.
   - Run focused checks while iterating, then `make check`, `make generate`, browser smoke with console/network inspection, `git diff --check`, and complete generated/privacy/secret/phone/transcript/provider-payload review.

8. **Run the provider gate only with separate authorization**
   - Before deployment or a call, obtain explicit authorization naming the synthetic remote/coordinator labels, destination countries, origin class, public endpoints, disclosure/recording behavior, expected cost/duration, evidence retained, deletion/cleanup, and account restrictions.
   - Prove that the remote participant remains connected while the coordinator joins the same conference, AI speech and commitment tools remain fenced, callbacks persist once, and the audit/control tower show `JOINED` truthfully.
   - Report latency, participant continuity, restrictions, failures, redacted evidence, and cleanup separately. If access or compliance blocks the trial, leave the sandbox criterion unchecked and use the declared fallback without claiming the gate.

## Ownership and sequencing

- Coordinator and sole phase owner: `rmcosta-lab`.
- Backend/application contracts and persistence semantics land before adapter, API, or frontend work depends on them.
- Implementation ownership exception recorded before delegation: the backend worker is the sole writer for `backend/**`; the API worker is the sole writer for `api/**`, including Pydantic schemas and generated `api/openapi.json`; the frontend worker is the sole writer for `frontend/**`, including generated Orval output. This operational split specializes the phase-start ownership table without changing its team owner.
- The coordinator is the sole writer for this phase specification directory and any explicitly approved shared or integration file outside those three roots. No worker edits `validation.md`.
- The API worker owns the OpenAPI source/export checkpoint. After API contract tests and `api/openapi.json` are ready, the coordinator notifies the frontend worker, which alone runs Orval and updates generated consumers; it never hand-copies the Pydantic contract.
- No manifest or lockfile change is planned. Workers must stop and request coordinator ownership before touching `pyproject.toml`, `uv.lock`, `frontend/package.json`, or `pnpm-lock.yaml`; any demonstrably required manifest and its lockfile will have one coordinator-assigned writer.
- Provider-specific fields never enter backend models or browser types. Frontend context uses bounded application projections, not a raw transcript or provider payload.
- No shared mission, tech-stack, roadmap, or challenge-plan edit is planned. If implementation discovers a broad decision that another phase needs, pause the affected work and route it through `manage-shared-specs`.

## Contract and integration checkpoints

- **Readiness checkpoint:** Phase 20 remains merged with gate evidence; Phase 28 still has one remote branch and no competing/open/closed-unmerged PR requiring recovery.
- **Provider-doc checkpoint:** current official Call update, conference participant, callback/signature, account, regional, number, and recording requirements are recorded before adapter code is accepted.
- **Authority checkpoint:** reservation, idempotency, audit, and AI fence pass deterministic backend tests before any provider mutation can run.
- **HTTP checkpoint:** Pydantic models, stable operation IDs, auth/origin/rate/idempotency/error semantics, and callback tests pass before `make generate`.
- **Generation checkpoint:** OpenAPI and Orval regenerate once from accepted source contracts; complete generated diffs are reviewed before frontend integration.
- **Continuity checkpoint:** fake-provider integration proves remote-leg continuity, callback-confirmed coordinator join, no post-reservation AI speech/commitment, and honest safe failure states.
- **Browser checkpoint:** focused interaction tests pass before desktop/mobile browser smoke and console/network inspection.
- **Provider checkpoint:** sandbox evidence requires separate authorization and is reported independently from deterministic checks.

## Guardrails

- No deployment, production access, provider-account/number/permission mutation, participant contact, PSTN call, recording, Yuno operation, payment, financial mutation, or unrelated remote change is authorized by this plan.
- Do not log, persist in public projections, or commit raw audio, transcript, E.164 values, credentials, signatures, authorization headers, raw forms, provider payloads, or private participant data.
- Do not declare `JOINED` from an HTTP provider response, stream disconnect, conference creation, or coordinator dial attempt. Require verified durable participant-join evidence and proof that the remote leg remains present.
- Do not automatically resume AI speech or commitment authority after failure/timeout, retry an uncertain provider mutation with a new logical identity, or allow two active handoffs for one call.
- Do not move mandate, quote, commitment, recovery, or audit authority into FastAPI, React, TwiML, or provider callbacks.
