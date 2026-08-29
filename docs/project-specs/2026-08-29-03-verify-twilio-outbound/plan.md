# Phase 03 plan — Verify Twilio outbound-call feasibility

## Task groups

1. **Build the evidence matrix.** Read current official Twilio documentation for outbound calls, account and trial behavior, number and destination eligibility, geographic permissions, request verification, call-status callbacks, bidirectional Media Streams, AI disclosure, recording consent, and applicable regional requirements. Record source metadata and convert every roadmap-gate clause into an evidence row before any live test.
2. **Run the safe account preflight.** Inspect account mode, usable originating-number capability, destination eligibility, and relevant limits without changing account settings. Choose a synthetic participant label, obtain the participant's authorization outside Git, and define an allowlist that contains no committed full number.
3. **Decide the smoke endpoint and hosting candidate.** Select a disposable TLS-valid HTTPS and secure-WebSocket endpoint for the authorized test and separately evaluate the compatible public hosting choice for P0.1. Reconstruct the exact external callback URL used by request verification. Do not provision or deploy anything without explicit authorization.
4. **Prepare a minimal feasibility harness only if needed.** Keep it under `scripts/twilio_feasibility/**`, independent of `frontend`, `api`, and `backend`, and use deterministic media rather than OpenAI or Volta behavior. Avoid manifest, lockfile, and shared-configuration edits; if reproducibility requires one, stop and request a scope decision.
5. **Validate signatures and callbacks before dialing.** Exercise the official request verifier with a representative signed request and a tampered negative case, then prove the endpoint can record redacted stream and status metadata without raw payload logging.
6. **Request authorization and run one smoke call.** Present the exact synthetic participant, destination allowlist, originating account/number class, endpoint, disclosure and consent script, recording behavior, and expected external mutations. Only after explicit approval, initiate one human-triggered call and prove inbound and outbound Media Stream traffic plus safe status evidence.
7. **Publish the feasibility verdict.** Complete the evidence matrix, select the compatible hosting approach and fallback, state PASS or BLOCKED without ambiguity, list the smallest next actions, and explain the impact on Phases 18, 19, 20, and 22.
8. **Perform the documentation and security handoff.** Run proportional checks, inspect the complete diff, confirm redaction, and keep provider trials separately labeled from deterministic repository checks.

## Ordering and checkpoints

- Contract decision before dependent work: the evidence matrix fixes the claims, observed fields, redaction rules, exact callback URL, and PASS/BLOCKED semantics before the smoke endpoint or call is exercised.
- Authorization checkpoint: no purchase, number provisioning, account-setting change, endpoint deployment, call, or recording occurs until its exact target and effect receive explicit authorization.
- Integration checkpoint: Phase 03 records provider observations only. Phase 18 owns the provider-neutral outbound adapter, and Phase 19 owns FastAPI ingress, request verification, WebSocket bridging, and later OpenAPI/Orval generation.
- Shared-decision checkpoint: if official evidence makes the accepted Twilio or hosting direction infeasible, pause and use `manage-shared-specs`. Phases that depend on Phase 03 must refresh after that decision merges.
- Final checkpoint: the verdict cannot be PASS based only on documentation, a one-way stream, an unsigned callback, or an unauthorized call.

## Workstreams and ownership

- Documentation and evidence: `rmcosta-lab` writes only the Phase 03 specification directory.
- Disposable feasibility harness, if required: `rmcosta-lab` owns `scripts/twilio_feasibility/**`; no other phase writes there during the test.
- Frontend workstream: not applicable; no frontend files or generated client files change.
- API/BFF workstream: not applicable; the public callback is a disposable feasibility endpoint, not a product route.
- Backend/core workstream: not applicable; no domain rule, repository, provider adapter, or database code changes.
- Shared files, manifests, lockfiles, and `.env.example`: no writer in this phase.
- External provider operations: `rmcosta-lab` acts only after the separate authorization checkpoint and records safe evidence.

## Generation and test strategy

- OpenAPI and Orval generation are not applicable because the phase changes no Pydantic or browser/server application contract.
- Keep tests next to a committed disposable harness if one is needed. Cover request-verification success and tampering failure, redaction, stream lifecycle handling, deterministic outbound media, and disconnect cleanup.
- Run `uv run ruff check .` and `uv run pytest` only if Python harness or tests are added, followed by the repository's applicable Python handoff target.
- `pnpm lint`, `pnpm build`, browser application testing, database tests, and Yuno checks are not applicable unless the approved scope changes.
- Always run `git diff --check`, review the diff and untracked files, and perform a secret, phone-number, participant-data, raw-payload, and audio-artifact inspection.
- Record the credentialed Twilio smoke test separately from deterministic repository checks. A skipped or blocked provider trial fails the phase gate even when local tests pass.

## Guardrails

- No deployment, production access, live financial mutation, real carrier contact, or unrelated remote change is authorized by this plan.
- Do not record until disclosure has occurred and the participant has consented under the verified procedure.
- Do not commit `.env`, auth tokens, account identifiers, full telephone numbers, call audio, raw callback bodies, or private participant details.
- Do not weaken the gate or describe browser audio, a tunnel-only test, or one-way media as completed P0.1 telephony.
