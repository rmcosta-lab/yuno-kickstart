# Fase 20 plan — Add outbound-call controls and status

## Task groups

1. **Freeze the consumed contract and presentation mapping**
   - Confirm Fases 16 and 19 remain merged, refresh the Phase 20 branch/PR state, and verify the generated `useCreateOutboundCall` signature and merged operation/session models.
   - Freeze the deterministic lowest-rank session selection, fixed `synthetic-carrier-one` label, coordinator actor, recording-disabled literals, idempotency lifetime, and honest four-state mapping before React work.
   - Record that the create response is a snapshot, not a subscription; do not add polling or infer later callback status.

2. **Build the narrow telephony control**
   - Create `frontend/src/features/telephony/` with a small Client Component and index export, using the existing generated hook and UI primitives.
   - Render the selected synthetic carrier, unchecked confirmation, explanatory privacy/call-copy, explicit `Start demo call` button, accessible state announcement, and concise safe failure guidance.
   - Disable missing-session, unchecked, and pending submissions. Preserve one key for an identical uncertain retry and avoid persisting or logging request/result material.

3. **Compose without disturbing fallbacks**
   - Add the control to the live sessions experience beside the existing browser voice simulator and text path, passing only authoritative `OperationResponse` data.
   - Keep Server Component boundaries, Realtime state, tool dispatch, operation refresh, browser voice, and typed text unchanged.
   - Confirm simulated preview mode performs no outbound request and does not present a real-call control as operational.

4. **Add focused behavioral coverage**
   - Add `frontend/tests/e2e/outbound-call-controls.spec.ts` using the existing Playwright harness and intercepted safe API fixtures.
   - Prove unchecked and missing-session guards, exactly one generated request, safe body/header literals, double-submit prevention, four-state rendering, safe HTTP failure, absence of phone/provider details, and visible browser/text fallbacks.
   - Keep the test deterministic and credential-free; no Twilio call, public endpoint, or provider account is used.

5. **Run frontend and rendered gates**
   - Run the focused Playwright test, then `pnpm lint`, `pnpm typecheck`, `pnpm build`, and the root `make frontend-check` target when equivalent or broader.
   - Run the live desktop flow in Chromium: verify keyboard/focus, consent gating, pending/success/failure fixtures, and fallbacks; inspect console and network after the journey.
   - Review the full diff, `git diff --check`, generated/manifests unchanged, and targeted scans for phone numbers, credentials, provider IDs/payloads, authorization, raw errors, audio, and participant data.

## Ownership and sequencing

- Coordinator and sole phase owner: `rmcosta-lab`.
- The consumed generated contract and state projection are frozen before component and test work.
- One writer owns `frontend/src/features/telephony/**`; the same writer makes the small composition edit in `frontend/src/features/negotiation/negotiation-experience.tsx` and owns the focused E2E file.
- No writer exists for generated files, manifests/lockfiles, API, backend, migrations, configuration, provider adapters, shared specs, or external systems.
- If implementation discovers that later provider status is required to meet the intended result, stop and route the missing HTTP contract through a separate coordinated API phase; do not handwrite a client or expand this branch silently.

## Contract and integration checkpoints

- **Generated-client checkpoint:** import and call only merged Orval symbols; no copied transport types or direct `fetch`.
- **Authority checkpoint:** selected operation/session IDs come from the authoritative operation response; the destination label and actor are bounded demo constants, and the checkbox never becomes domain authority.
- **Idempotency checkpoint:** one logical pending/uncertain attempt owns one key; no parallel mutation and no key reuse after completion or session change.
- **Truthfulness checkpoint:** `starting`, `live`, `ended`, and `failed` map only from mutation state, response enum, or caught safe error. No live-observation or PSTN-success claim exceeds the returned snapshot.
- **Fallback checkpoint:** browser voice and text remain visible and unchanged before the PSTN control is accepted.
- **Rendered checkpoint:** the focused test passes before desktop Playwright flow; Chrome console/network inspection follows the exercised journey.
- **Publication checkpoint:** refresh Phase 20, dependency, conflict, and overlapping frontend PR state before implementation publication.

## Shared files and branch refresh

- No mission, stack, roadmap, challenge-plan, OpenAPI, generated-client, manifest, lockfile, or environment change is planned.
- Refresh open pull requests touching `frontend/src/features/negotiation/**`, `frontend/tests/e2e/**`, or shared frontend primitives before implementation and before publication. Coordinate rather than overwrite overlapping work.
- No temporary prerequisite wait exists: Fases 16 and 19 are merged and no conflict is declared.

## Guardrails

- No deployment, production access, account/number/permission mutation, participant contact, PSTN call, recording, Yuno operation, payment, financial mutation, or unrelated remote change is authorized.
- Do not expose or log phone numbers, allowlist mappings, provider call IDs, raw error bodies, credentials, signatures, authorization headers, idempotency keys, audio, transcripts, or participant data.
- Do not add automatic retry, polling, a status stream, multi-call behavior, detailed diagnostics, inbound calling, takeover, or evidence/audit scope.
- Do not edit generated files or describe browser voice as telephony. A mocked browser test proves UI behavior, not a credentialed provider trial.
