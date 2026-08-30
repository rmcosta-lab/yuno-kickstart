# Fase 16 — Plan

## Task groups in dependency order

1. **Freeze playback and display contracts**
   - Confirm the additive binary OpenAPI declaration, exact safe `404`/`413` codes and messages,
     25 MiB bound, headers, mutator parsing behavior, and `EvidenceAudio` application symbols before
     dependent work.
   - Inventory the generated Fase 15 fields used for lifecycle, disposition, recovery, mandate,
     notification, escalation, audit pagination, and correlation.
   - Search every consumer of `CommitmentEvidenceResponse.recording_reference`; freeze its removal
     from public responses only after proving no application behavior depends on it.
   - Record presentation invariants: state comes from responses, `SIMULATED` is not `VERIFIED`, and
     timestamp sorting never creates a domain transition.

2. **Implement provider-neutral audio retrieval**
   - Add `yuno_backend.volta.evidence.playback` using the existing repository and storage ports.
   - Load the evidence reference in a short unit of work, close/rollback it, retrieve outside the
     database transaction, validate RIFF/WAVE and length, and return no reference.
   - Unit-test success, missing evidence/blob, invalid reference/media, oversize data, storage
     failure, and the no-open-transaction invariant with in-memory fakes.

3. **Expose and generate the audio contract**
   - Remove `recording_reference` from public evidence responses while preserving backend storage
     state and the existing evidence-ingestion input; add the thin authenticated route and adapter
     construction, explicit `audio/wav` binary schema, no-store/nosniff headers, safe typed errors,
     and request correlation.
   - Test authorization before retrieval, UUID validation, safe 404/413/500 translation, response
     bytes/headers, redacted logs, and no reference/path/filename leakage.
   - Update `voltaFetch` so declared `audio/*` successes use `Response.blob()` while JSON success
     and error handling remains unchanged; cover both paths without decoding bytes as text.
   - Run API tests, `make generate`, review OpenAPI, mutator, and Orval diffs, and freeze the
     generated Blob client before frontend integration.

4. **Build the evidence experience**
   - Replace `/evidence` fixtures with an authoritative operation/audit query and generated binary
     fetch under the existing demo-auth/live-operation boundary.
   - Imperatively fetch audio outside TanStack Query, create, seek, expose, and revoke a Blob URL,
     clear the Blob reference on replacement/unmount, and display existing recap/brief plus exact
     evidence metadata, lifecycle, disposition, loading, denied, unavailable, retry, and success
     states.
   - Never render or log the opaque recording reference; it remains only in evidence-ingestion
     input and backend/persistence state after public response redaction.

5. **Build good and bad recovery flows**
   - Replace `/recovery` fixtures with explicit `MANDATE_SAFE` and `OUT_OF_MANDATE` actions using
     server version and active commitment fields.
   - Allocate stable logical idempotency keys, disable duplicate submissions, render only returned
     before/after facts, and invalidate/refetch operation and audit on settlement.
   - Display notification acknowledgement with the first stored actor/timestamp and safe conflicts.

6. **Build escalation and mandate replacement**
   - Replace `/escalation` fixtures with conflict, attempted-alternative, recommendation,
     correlation, and resolution context from the response.
   - Use React Hook Form and Zod for the replacement terms and approval actor; include the named
     escalation and current operation version; refetch instead of locally closing the escalation.
   - Preserve focus and form values on safe errors while requiring a fresh submit after stale state.

7. **Build the correlated audit view**
   - Replace `/audit` fixtures with deterministic presentation items from all eight artifact arrays.
   - Order by the backend comparator `(timestamp, artifact UUID, source kind)`. Group/display
     correlation IDs only for events, recoveries, escalations, and notifications that directly
     expose them; keep quotes, commitments, recaps, and briefs standalone. Append opaque cursor
     pages without duplicates and expose load-more/error states.
   - Keep active/superseded, open/resolved, and lifecycle labels verbatim from generated models.

8. **Integrate, polish, and verify**
   - Exercise the canonical evidence → good recovery → notification → bad recovery → escalation →
     mandate replacement → audit journey against the local API/PostgreSQL stack.
   - Add focused Playwright coverage using synthetic WAV bytes written to ignored private storage;
     seed existing recap/brief prerequisites through setup APIs rather than adding creation controls;
     no audio artifact enters Git.
   - Run full Python/frontend/generation checks, browser verification in Playwright-first and
     console/network-inspection-second order, mobile/desktop/accessibility checks, and final
     generated/diff/secret/private-data review.

## Parallel workstreams and ownership

- The backend writer owns group 2 after group 1 freezes the application contract.
- The API writer owns the route, error schema, and `api/openapi.json`. The frontend writer owns the
  Orval output and shared fetch mutator. Frontend integration waits for their reviewed
  OpenAPI/generation/parsing checkpoint.
- The frontend writer may prepare presentation-only composition for groups 4–7 after group 1, but
  owns no copied DTO and does not wire audio before the generated client is frozen.
- The phase coordinator is the only writer for phase specs, roadmap clarification, and the playback
  decision. Layer workers request shared edits through the coordinator.
- No two writers touch the same shared component, generated directory, manifest, lockfile, or test
  fixture. One coordinator integrates all workstreams and verifies the end-to-end journey.

## Contract and generation checkpoints

- Checkpoint 1: backend symbols, binary route, headers, errors, and size/media rules are
  decision-complete before implementation diverges.
- Checkpoint 1 also records a clean repository-wide compatibility search before removing the public
  response field; evidence ingestion and backend persistence retain the reference.
- Checkpoint 2: backend unit tests and API contract tests pass before `make generate`.
- Checkpoint 3: the API writer regenerates and freezes OpenAPI; the frontend writer then regenerates
  Orval once, uses generated Blob behavior, and never hand-edits generated files.
- Checkpoint 4: every accepted mutation invalidates/refetches operation and audit queries and
  preserves one idempotency key for an identical logical retry.
- Checkpoint 5 (satisfied): the complete production-build browser journey proved the playback offset,
  both recovery outcomes, notification acknowledgement, stale conflict recovery, named escalation
  resolution, and mixed audit against the local FastAPI API and durable PostgreSQL state without
  intercepting application requests.

## Tests near changed behavior

- Backend unit tests live beside evidence application tests and use injected repositories/storage.
- API tests cover binary content/schema/headers, exact safe errors, wiring, and no leakage;
  add PostgreSQL integration only where required to prove ID-to-artifact resolution.
- Focused fetch/E2E coverage proves byte-preserving Blob success and unchanged JSON success/error,
  authorization, and request-ID behavior for the shared mutator.
- Frontend E2E tests seed deterministic evidence/recap/brief prerequisites, then exercise loading,
  playback, mutations, pagination, stale/error recovery, keyboard/focus, and responsive states. Do
  not add a test dependency.
- Credentialed OpenAI/Twilio tests, Yuno/payment tests, webhooks, RLS, provider sandbox calls, and
  production storage trials are not applicable.

## Shared decision and refresh points

- This branch carries the directly required roadmap clarification and
  `docs/decisions/evidence-audio-playback.md`. The outcome and gate are unchanged; implementation
  scope expands only enough to make playback possible without violating private storage.
- Fases 17 and 20 consume the resulting browser journey. Neither has an active branch or pull
  request at claim time; mention the clarification in the Fase 16 pull-request body and refresh
  remote state before publication and before merging generated/shared files.
- If another pull request begins touching the roadmap, generated contract, demo-auth boundary, or
  shared control-tower components, coordinate one writer and refresh this branch before continuing.

## Authorization boundaries

No deployment, production access, provider call, real recording, remote migration, live telephony,
financial mutation, Issue creation, merge, or unrelated remote change is authorized. The start
workflow publishes only this planning commit; implementation follows `implement-phase`.

## Temporary waits

None after the approved scope clarification. Fases 09 and 15 are merged, there are no conflicts or
open pull requests, the existing `EvidenceStorage.retrieve` port supports the application service,
and the binary contract decision is recorded before implementation.
