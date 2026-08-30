# Phase 18 implementation plan

1. **Refresh provider facts and freeze provider-neutral contracts**
   - Re-read the Phase 03 PASS dossier and current official Twilio call-resource, authentication, status-callback, geographic-permission, retry, and privacy documentation.
   - Define immutable request/result/status values, the gateway and durable attempt-repository protocols, and the safe exception vocabulary before provider mapping begins.
   - Add architecture tests proving that `yuno_backend.volta.telephony` imports no HTTPX, Twilio SDK, FastAPI, Pydantic API schema, SQLAlchemy implementation, OpenAI, Yuno, or frontend type.

2. **Implement authorization, allowlist, and durable idempotency guards**
   - Validate bounded operation/call identifiers, idempotency key, human actor/timestamp, disclosure readiness, recording mode, and consent policy before network I/O.
   - Resolve only a synthetic destination label through an injected server-side allowlist whose private number never appears in representations or diagnostics.
   - Atomically reserve and fingerprint each logical attempt in a short transaction. Replay the stored same-request result, reject a different-request conflict, block an existing in-flight reservation from dispatching, and record known failures or uncertain outcomes in a separate short transaction after network I/O.
   - Never hold a database transaction, row lock, or unit of work open while waiting for Twilio.
   - Reuse the existing persistence boundary where it safely fits; otherwise add the smallest reversible migration and repository implementation, with rollback and round-trip tests.

3. **Implement the bounded Twilio outbound mapping**
   - Build immutable redacted config and an async HTTPX adapter restricted to the official HTTPS account call endpoint, bounded response size, and bounded timeouts.
   - Map only the accepted outbound form fields, callback subscriptions, and disclosure/consent-controlled flow URL; keep full phone numbers and Basic-auth material confined to request construction.
   - Parse the provider call identifier and accepted initial status into provider-neutral values without returning raw payloads, HTTP concepts, or provider exceptions.

4. **Make retry, uncertainty, and lifecycle behavior deterministic**
   - Retry only a documented, provably pre-dispatch transient failure under a small bounded policy. A timeout or connection loss after dispatch becomes `OutboundCallOutcomeUncertain` and never triggers a second create request automatically.
   - Normalize allowlisted lifecycle states and make duplicate/out-of-order observations monotonic; terminal state cannot regress.
   - Translate authentication, permission, rate-limit, invalid-response, timeout, and provider failures into safe typed errors with bounded diagnostic fields.

5. **Test and prepare the integration handoff**
   - Cover zero-I/O guard failures, exact request mapping, one-call idempotency, concurrent duplicates, fingerprint conflicts, provider errors, retry boundaries, uncertain outcomes, malformed/oversized responses, statuses, redaction, and cleanup with injected transports.
   - Run focused Ruff/pytest during iteration, then `make python-check`, migration checks when applicable, `git diff --check`, a secret/privacy scan, and complete diff review.
   - Do not run a live Twilio call. Preserve the fake gateway for Phase 19 and the browser/text/recorded fallback.

6. **Resolve the authorized temporary prerequisite wait**
   - Phase 17 remains ACTIVE even though the owner explicitly authorized this isolated Phase 18 start. Do not claim that Phase 18 is READY under the ordinary roadmap state model.
   - Before opening Phase 18 for review or merging it, require Phase 17 to be DONE, refresh from the merged `main`, inspect overlapping backend/shared files, resolve integration changes, and repeat the deterministic gate.

## Ownership and sequencing

- The coordinator is `rmcosta-lab`. For the explicitly requested parallel implementation, ownership is split into non-overlapping backend paths:
  - core worker: `backend/src/yuno_backend/volta/telephony/**` and `backend/tests/volta/telephony/**`;
  - Twilio worker: `backend/src/yuno_backend/integrations/twilio/**` and `backend/tests/volta/integrations/twilio/**`;
  - persistence worker: the Phase 18 changes in `backend/src/yuno_backend/volta/persistence/**`, `backend/migrations/**`, and matching persistence tests;
  - coordinator: this phase directory, integration-only fixes, and final validation evidence.
- No worker owns `backend/pyproject.toml` or `uv.lock`; HTTPX is already a direct dependency, and any discovered dependency change returns to the coordinator before either file is edited.
- The phase coordinator owns only this specification directory during planning and its validation evidence during implementation.
- The core contract worker lands first. The Twilio and persistence workers then run in parallel against those frozen symbols; guard and idempotency behavior land before provider dispatch, and failure/lifecycle mapping lands before integration handoff.
- There is no frontend or API workstream, OpenAPI/Orval generation, browser validation, public deployment, or parallel writer inside this phase.
- Before editing persistence, exports, the manifest, or lockfile, refresh open phase/specification pull requests and coordinate any overlapping writer.
- No shared spec change is planned. The early-start exception is documented here and does not remove or weaken the Phase 17 dependency.
- No deployment, production access, live call, participant contact, recording, account mutation, Yuno operation, payment, financial mutation, or unrelated remote change is authorized.
