# Phase 19 plan — Bridge Twilio media through FastAPI

## Task groups

1. **Refresh the stacked base and freeze contracts**
   - Confirm Phase 18 remains at or ahead of recorded base `5600aa9470db4da1c5885fc48eb38a43996f00e1`, inspect any new Phase 18 changes, and freeze the provider-neutral outbound-call imports consumed by this phase.
   - Re-read Phase 03 PASS evidence and current official Twilio signature, Voice/TwiML, status callback, bidirectional Media Streams, framing/limits, and disconnect documentation plus official OpenAI Realtime server-WebSocket documentation.
   - Freeze the smallest provider-specific fields and lifecycle needed for one call; explicitly leave complete status, reconnect, multi-call, and exhaustive signature/retry coverage to later phases.

2. **Define public and provider ingress contracts first**
   - Add Pydantic outbound-call request/response/error models and thin `/v1/operations/{operation_id}/outbound-calls` routing using the repository's existing demo authorization, request correlation, idempotency header, rate limiting, and safe error envelope.
   - Define the minimal verified Twilio voice/consent and terminal-status routes plus the non-OpenAPI media-WebSocket protocol, external-origin reconstruction, single-stream limits, and safe close behavior.
   - Add focused contract tests and representative missing/tampered/unauthorized cases before wiring any real adapter. Use injected fakes and synthetic forms/frames only.

3. **Wire Phase 18 outbound calling and the minimum terminal status**
   - Map the application request exactly to `OutboundCallRequest` and inject the Phase 18 gateway/store without exposing Twilio configuration or provider payloads through Pydantic models.
   - Accept same-request durable replay under the same `201` response without a replay marker, and map idempotency conflict, authorization/allowlist, provider, rate-limit, timeout, invalid-response, and uncertain-outcome semantics into the frozen HTTP envelope.
   - Verify the provider request, normalize the terminal observation needed by the demo, and apply it duplicate-safely through the backend boundary before returning success. Defer the complete status matrix and retry policy.

4. **Implement consent-gated TwiML and stream authorization**
   - Generate only the minimal disclosure/consent flow established by current official behavior. Recording stays disabled unless the separately authorized request explicitly selects after-consent recording.
   - Mint a bounded one-call stream binding with no phone number or standard credential, validate the expected provider call/stream IDs, and reject representative replay, mismatch, or over-capacity input.
   - Keep all Twilio form, XML, and frame mapping inside `api/app/telephony/**`; application services receive only normalized typed commands.

5. **Build the bounded bidirectional bridge**
   - Create one Realtime connection for the accepted stream using the existing `RealtimeGateway`; forward inbound audio and map output audio with bounded queues, timeouts, and backpressure sufficient for the reproducible call.
   - Route every Realtime tool request through the same Volta application facade used by browser voice, preserve the original `call_id`, and return a typed `RealtimeToolOutput` only after deterministic completion.
   - Use one structured-concurrency lifetime for both transport directions. On Twilio, OpenAI, tool, timeout, or shutdown failure, cancel peers, close once, persist a safe monotonic outcome, and never synthesize a commitment or successful call.

6. **Regenerate and integrate contracts**
   - Export `api/openapi.json`, run Orval, inspect the generated diff, and update only the smallest Phase 20-facing typed client surface required by the outbound-call route.
   - Run API and generated-client tests, then frontend lint/typecheck/build to prove the new generated surface does not break existing consumers. No Phase 20 interface is implemented here.

7. **Validate deterministic and credentialed gates separately**
   - Run focused Ruff/pytest while iterating, then `make python-check`, `make generate`, the applicable frontend check/build, `git diff --check`, and complete secret/privacy/generated-artifact review.
   - Exercise the minimum callback/stream flow, bidirectional audio, one tool correlation, duplicate delivery, one forced disconnect, and cleanup with fakes.
   - Run a sandbox call only after a separate authorization names the participant label, country, origin class, public endpoint, disclosure/consent/recording behavior, expected cost, duration, retention, and cleanup. Without that authorization, leave the sandbox criterion unchecked and do not deploy or dial.

8. **Reconcile the stacked branch before review**
   - The owner-authorized decision allowed the Phase 19 claim to proceed while Phase 17 was still ACTIVE; PR #25 merged immediately afterward. A second explicit owner decision during `implement-phase` authorizes stacked implementation while Phase 18 remains ACTIVE. Preserve both decisions without representing Phase 18 as DONE.
   - Before Phase 19 review/merge, require Phase 18's consumed contracts to be integrated or explicitly reconciled, refresh the appropriate base, remove no Phase 18 history, inspect overlapping API/shared-file pull requests, and repeat the complete deterministic gate.

## Ownership and sequencing

- Coordinator and sole phase owner: `rmcosta-lab`.
- Contract decisions and security limits land before dependent bridge work. The outbound/status work and media-bridge work may proceed independently only after the shared API-local command and error vocabulary is frozen.
- One writer owns `api/app/telephony/**`, related routers/schemas/security/config, and matching API tests. The same coordinator owns generated `api/openapi.json` and `frontend/src/lib/api/generated/**` during the single generation checkpoint.
- Phase 18 backend telephony/Twilio paths have no Phase 19 writer. Any required correction is coordinated back to Phase 18 before editing those paths.
- No frontend UI, backend domain-rule, shared mission/stack/roadmap/challenge-plan, deployment, or provider-account workstream exists in this phase.
- If a verifier or runtime dependency is demonstrably required, the coordinator owns `api/pyproject.toml` and `uv.lock` as one pair and refreshes overlapping pull requests first.
- If safe configuration names change, `.env.example` and the smallest relevant setup documentation move together; values remain empty or safe and contain no origin/account/number/secret.

## Contract and integration checkpoints

- **Phase 18 checkpoint:** freeze and test consumed telephony symbols before Pydantic mapping or dependency wiring.
- **Security checkpoint:** request verification, stream binding, single-stream limits, and focused negative tests pass before bridge acceptance can reach OpenAI.
- **Application checkpoint:** fake transport tool calls reach the existing Volta facade and replay safely before audio plumbing is considered complete.
- **Contract correction checkpoint:** Phase 18 exposes `OutboundCall`, not a dispatch/replay wrapper; the public Phase 19 response therefore uses one honest `201` accepted result and no `replayed` field or header.
- **Generation checkpoint:** Pydantic models and API tests pass before `make generate`; generated artifacts are reviewed before frontend verification.
- **Stack reconciliation checkpoint:** Phase 18 lands or is explicitly reconciled before Phase 19 review. The phase-local early-start decision does not change the roadmap dependency graph.
- **Implementation exception checkpoint:** local API/generated-client implementation may proceed on the stacked Phase 18 history by explicit owner authorization; review and merge remain gated on Phase 18 integration or an explicit reconciliation decision.
- **Submission exception checkpoint:** an explicit owner decision authorizes committing, synchronizing, pushing, and opening the Phase 19 pull request with Phase 18 and sandbox evidence still pending. The PR must remain visibly blocked and no fresh tests or `deep-review` are run for this submission.
- **Provider checkpoint:** sandbox evidence is separately authorized and reported; deterministic checks never imply that a real call occurred.

## Guardrails

- No deployment, production access, account/number/permission mutation, live call, participant contact, recording, Yuno operation, payment, financial mutation, or unrelated remote change is authorized by this plan.
- Do not log or persist raw audio, transcript, telephone number, signature, authorization header, raw form/frame, provider payload, standard OpenAI credential, or private participant data.
- Do not return success before the minimum verified terminal processing, allow a model/provider event to bypass deterministic services, or retry an ambiguous provider mutation.
- Do not absorb later-phase complete status, reconnect, multi-call, exhaustive signature/retry, or detailed diagnostic scope into this hackathon slice.
- Represent Phase 17 as DONE only through merged PR #25, keep Phase 18 ACTIVE until its own gate and merge complete, and do not weaken either gate or rewrite their history. Phase 19 is deliberately stacked on Phase 18 and must be reported that way until reconciled.
