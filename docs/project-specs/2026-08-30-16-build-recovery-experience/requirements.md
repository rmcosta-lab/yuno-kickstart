# Fase 16 — Build evidence, recovery, and audit screens

## Coordination

- Priority: P0 complete-browser-journey experience.
- Branch: `phase/16-build-recovery-experience`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fases 09 and 15, merged with gate evidence in pull requests #7 and #22.
- Conflicts with: none.
- Roadmap gate: play the agreement turn at its stored offset; distinguish evidence lifecycle and
  operational disposition; run deterministic good and bad recoveries; show notifications and
  escalation context; support mandate replacement; and render the correlated audit timeline with
  loading and failure states.
- Shared clarification: this phase now owns the smallest cross-layer authenticated audio-retrieval
  slice required by the unchanged playback gate. The reason and boundary are recorded in
  [`evidence-audio-playback.md`](../../decisions/evidence-audio-playback.md).

## Objective and user-visible outcome

Give the operations coordinator one truthful control-tower journey from agreement evidence through
autonomous recovery or human escalation. The coordinator can hear the private agreement artifact
from the stored offset, inspect its recap and brief, run the reproducible mandate-safe and
out-of-mandate simulations, acknowledge the resulting notification, replace a mandate after an
escalation, and audit every correlated fact without the browser deciding operational state.

The terminal result is an authoritative refreshed operation and audit view with exactly one active
winner, retained superseded history, an explicitly `SIMULATED` recap, and either a mandate-safe
notification or an open/resolved human escalation. It is not a verified written commitment, real
inbound call, booking, or provider delivery.

## Included scope

- Add an authenticated binary audio contract keyed only by `evidence_id`, backed by the existing
  private `EvidenceStorage` protocol and response-capped at 25 MiB of validated RIFF/WAVE bytes.
- Add the provider-neutral backend retrieval service, thin FastAPI route, typed safe errors,
  OpenAPI declaration, binary-safe shared fetch mutator, Orval client, and focused tests for the
  new contract.
- Remove `recording_reference` from `CommitmentEvidenceResponse` and every nested browser-facing
  operation/audit response. Preserve it only in backend/persistence state, and prove existing
  frontend code has no consumer before accepting the compatibility-narrowing contract change.
- Replace the fixture shells at `/evidence`, `/recovery`, `/escalation`, and `/audit` with a narrow
  live feature using generated query and mutation hooks.
- Render lifecycle `CANDIDATE` or `SIMULATED` separately from disposition `ACTIVE` or `SUPERSEDED`;
  never derive either state from price, timestamps, recap presence, or client-side workflow.
- Fetch authorized audio into an in-memory Blob URL, seek to `audio_start_ms / 1000`, expose
  accessible playback controls, and revoke the URL after use.
- Display recap content as `SIMULATED`, structured call briefs, notification acknowledgement,
  escalation context, and mandate-replacement inputs.
- Consume recap and brief artifacts only through existing operation/audit reads. Creating recap or
  brief artifacts is not a Fase 16 user action.
- Run `MANDATE_SAFE` and `OUT_OF_MANDATE` inbound simulations using the current server version and
  active commitment, then invalidate/refetch operation and audit state after every mutation.
- Present the eight bounded audit collections with the backend's exact timestamp, artifact UUID,
  and source-kind tie-break order. Group only events, recoveries, escalations, and notifications
  that directly expose a server correlation ID; keep other artifacts standalone with source
  labels. Support opaque cursor pagination without inventing missing transitions.

## Excluded scope

- Public/static evidence assets, browser interpretation of `recording_reference`, signed
  object-storage URLs, Range requests, transcoding, a production storage provider, or an audio
  upload/recording flow.
- Changes to negotiation, mandate, recovery, winner-selection, audit, or idempotency rules.
- New migrations, database queries in FastAPI, raw transcripts, real participant data, provider
  payloads, real inbound PSTN, Twilio, OpenAI event changes, Yuno, or payments.
- `VERIFIED` recap delivery, SMS/email, live carrier contact, deployment, production access, or any
  financial/external mutation.
- Broad control-tower redesign, new frontend dependency, or unrelated shared-spec change.

## Assumptions, risks, and fallback

- Assumption: Fase 15 operation/audit behavior remains the source of truth. This phase makes exactly
  two HTTP contract changes: additive audio retrieval and removal of the private storage reference
  from browser-facing evidence responses.
- Assumption: trusted P0 demo evidence is RIFF/WAVE and no larger than 25 MiB. The existing eager
  `EvidenceStorage.retrieve -> bytes` port means this is a response-acceptance cap, not a guarantee
  that read-time memory is bounded. Real/untrusted recordings remain outside this phase.
- Risk: a private storage reference leaks through a response, log, URL, DOM, screenshot, or error.
  Mitigation: public response DTOs remove the field, the audio route accepts only `evidence_id`,
  the backend resolves the reference, responses are `no-store`, and tests assert redaction.
- Risk: mutation retries duplicate recoveries, replacements, or acknowledgements.
  Mitigation: generate one idempotency key per logical submit and reuse it only for an identical
  uncertain retry; always refetch authoritative state.
- Risk: combining eight audit arrays creates a client-authored transition narrative. Mitigation:
  sort only for presentation, retain each artifact type, show correlation IDs only where supplied,
  and never infer lifecycle, disposition, resolution, or winner state.
- Risk: stale operation state makes a recovery or replacement unsafe. Mitigation: disable duplicate
  submits, send the last server version, surface safe `409` conflicts, refetch, and require a fresh
  user action.
- Fallback: when playback is missing, unsupported, oversized, or denied, retain the evidence
  metadata, recap, brief, and audit views and label audio unavailable. When an application mutation
  fails, keep the last authoritative projection and offer a safe refetch/retry without fabricating
  a successful recovery. Text mode remains the demo fallback.

## Acceptance criteria

- An authorized browser fetches an evidence artifact by UUID, receives validated `audio/wav`,
  loads it into a Blob URL, and seeks to the exact stored millisecond offset within normal media
  timing tolerance; unauthorized, missing, invalid, and oversized cases fail safely.
- No `recording_reference`, filesystem path, bearer token, raw audio, provider payload, or real
  participant data appears in user-visible URLs, logs, DOM text, persistent browser storage,
  screenshots, or typed errors. The required transient `blob:` media source exists only in memory
  on the audio element and is revoked after use.
- Evidence cards independently show `CANDIDATE`/`SIMULATED` lifecycle and
  `ACTIVE`/`SUPERSEDED` disposition; `VERIFIED` is not presented as achieved.
- The mandate-safe simulation returns and displays exactly one active commitment plus a
  notification; the prior commitment remains superseded and auditable.
- The out-of-mandate simulation leaves the commitment unchanged and displays an open escalation
  with conflict, attempted alternatives, recommendation, and correlation context.
- The coordinator can acknowledge a notification and replace a mandate for the named escalation;
  returned operation state, immutable version increment, and resolution are shown only after
  authoritative refetch.
- Audit pagination preserves stable item ordering and correlation across events, quotes,
  commitments, recaps, briefs, recoveries, escalations, and notifications without duplicates;
  correlation groups appear only where the response directly carries `correlation_id`.
- Loading, empty, denied, retryable error, stale conflict, audio-unavailable, mutation-in-flight,
  and success states are distinct, keyboard accessible, responsive, and do not rely on color.
- `make generate`, `make check`, focused E2E tests, browser console/network inspection,
  `git diff --check`, and sensitive-data review pass.

## HTTP contract gate

The existing Fase 15 JSON operation behavior remains authoritative; only the nested evidence
response projection is narrowed to remove `recording_reference`:

| Method and route                                            | Generated result                      | UI semantics                                                                                    |
| ----------------------------------------------------------- | ------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `GET /v1/operations/{operation_id}`                         | `200 OperationResponse`               | Current version, mandate, active commitment, escalation, and notifications are server-owned.    |
| `GET /v1/operations/{operation_id}/audit`                   | `200 AuditTimelineResponse`           | Bounded artifact collections plus opaque `next_cursor`; correlation is displayed, not inferred. |
| `POST /v1/operations/{operation_id}/inbound-simulations`    | `201 RecoverySimulationResponse`      | Run only the selected server script and render its returned commitment or escalation.           |
| `POST /v1/operations/{operation_id}/mandates`               | `201 OperationResponse`               | Resolve the named escalation and display the returned immutable mandate version.                |
| `POST /v1/notifications/{notification_id}/acknowledgements` | `200 CoordinatorNotificationResponse` | Display the stored first actor/timestamp; conflicting actors remain `409`.                      |

This phase additively defines:

| Method and route                       | Request                                                             | Success                                                                             | Errors and security                                                                                                                                                                                                                                                |
| -------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `GET /v1/evidence/{evidence_id}/audio` | UUID path, existing demo bearer authorization; no storage reference | `200 audio/wav` binary, at most 25 MiB, `private, no-store`, `nosniff`, no filename | Typed `401`/`403`; `404 RESOURCE_NOT_FOUND` with message `Evidence audio is unavailable.`; `413 EVIDENCE_AUDIO_TOO_LARGE` with message `Evidence audio exceeds the demo playback limit.`; standard `500` with request ID only. The `404`/`413` omit `resource_id`. |

FastAPI explicitly declares the binary OpenAPI schema and operation ID `get_evidence_audio`; typed
errors use `ApiErrorResponse`. Orval generates the authenticated Blob-returning client. All POSTs
retain the existing printable 8–128 character `Idempotency-Key` and safe
`401`/`403`/`404`/`409`/`422`/`429`/`500` semantics. The audio route never returns the opaque
reference, supports no Range request in P0, and does not log evidence bytes.
The additive `ApiErrorCode.EVIDENCE_AUDIO_TOO_LARGE` is used only for the bounded `413`; missing,
unsupported, or unreadable evidence is deliberately indistinguishable as the constant safe `404`.
The authenticated demo operator may learn that an artifact exceeds the accepted P0 cap through
`413`; that limited classification is accepted, while the response omits its reference and ID.

`CommitmentEvidenceResponse` loses the public `recording_reference` field before the new client is
generated. The backend `AgreementEvidence.recording_reference`, repository, database, and
create-evidence input remain unchanged; Phase 16 does not redesign evidence ingestion. A
repository-wide consumer search and generated-client compile gate must prove the response-field
removal is compatible with the current application.

## Application contract gate

| Import path                                                | Public symbols and construction                                                                                                                                                                             | Typed behavior                                                                                                                                                                                                                                                                                        |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `yuno_backend.volta.evidence.playback`                     | New `EvidenceAudio`, `RetrieveEvidenceAudioService`, `EvidenceAudioNotFound`, and `EvidenceAudioTooLarge`; construct with an operation unit-of-work factory, `EvidenceStorage`, and the fixed 25 MiB bound. | `retrieve(evidence_id: UUID) -> EvidenceAudio`; load the evidence/reference through a short unit of work, close it, then retrieve bytes outside the transaction; validate RIFF/WAVE and return bytes, `audio/wav`, and length without exposing the reference.                                         |
| `yuno_backend.volta.evidence.repositories`                 | Existing `EvidenceRepository.get` and `EvidenceStorage.retrieve`.                                                                                                                                           | No protocol change is expected; the service composes existing ports and maps storage absence/invalid media to safe typed exceptions.                                                                                                                                                                  |
| `api.app.volta_text_service` or a focused playback adapter | New typed `get_evidence_audio(evidence_id)` transport method constructed with the same backend factory/storage used by evidence writes.                                                                     | Return `EvidenceAudio` to the router; central translation emits only safe typed errors. No repository or storage-path access in FastAPI.                                                                                                                                                              |
| `frontend/src/features/recovery`                           | `RecoveryExperience` client leaf plus presentation-only evidence, recovery, escalation, and audit components; construct from generated hooks and existing demo-auth/live-operation boundaries.              | Inputs/outputs remain generated models; fetch audio imperatively as Blob without TanStack Query caching; mutation state is local, while operation, lifecycle, disposition, recovery, and resolution state remain server-owned. `ApiHttpError<ApiErrorResponse>` is sanitized at the feature boundary. |
| `frontend/src/lib/api/volta-fetch`                         | Existing `voltaFetch<T>` custom mutator, add content-aware success parsing.                                                                                                                                 | Preserve JSON and typed JSON errors; return `Blob` for declared `audio/*` success without a text roundtrip; retain auth/request-ID/error behavior and reject unsupported content safely.                                                                                                              |

The App Router pages stay Server Components and render the smallest interactive leaf. React Hook
Form plus Zod owns the non-trivial mandate-replacement form. One idempotency key is allocated per
logical mutation and retained across identical retries; a fresh action gets a fresh key. No backend
symbol, Pydantic model, raw `Response`, storage reference, or provider payload crosses into React.

## Browser/server and terminal handoff

All application JSON and audio bytes pass through this repository's authenticated FastAPI BFF.
There is no direct browser-to-storage provider, Yuno, Twilio, or new OpenAI handoff. The browser
keeps audio only in a revocable Blob URL, seeks using the server-provided offset, and treats the
browser callback as presentation only. Durable recovery and audit state comes from PostgreSQL
through the backend application facade and is refreshed after every accepted mutation.

## Layer, security, visual, and accessibility decisions

- Frontend: preserve the Volta control-tower visual system, Server Components by default, narrow
  client ownership, generated TanStack Query hooks, semantic timelines, and explicit query states.
- API/BFF: one thin authenticated binary route, response DTO redaction, explicit OpenAPI content
  schema and headers, safe typed errors, request IDs, and no caching or reference leakage. P0 uses
  the existing global demo bearer; `403` remains reserved by the generic contract rather than
  claiming per-evidence row authorization.
- Backend/core: provider-neutral retrieval orchestration only; no FastAPI import, new domain rule,
  migration, or provider selection.
- Data/providers/AI/Yuno: unchanged. Audio stays outside Git and PostgreSQL binary columns.
- Security: synthetic demo data only; never log bodies, authorization, references, paths, Blob
  URLs, transcripts, contact details, or raw context. A transient in-memory `blob:` element source
  is permitted for playback and must be revoked after use.
- Visual: prioritize evidence provenance, before/after recovery, escalation action, and audit
  correlation over decorative chrome. Lifecycle and disposition use separate text labels.
- Accessibility: native audio controls or equivalent keyboard-operable controls, visible focus,
  semantic forms/headings/lists, labeled status, meaningful `aria-live`, non-color cues, long-text
  wrapping, and mobile/desktop layouts without clipped actions.

## One-writer ownership

| Path or artifact                                                                                                                   | Writer                                                                     | Rule                                                                                                                                     |
| ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/project-specs/2026-08-30-16-build-recovery-experience/**`                                                                    | Phase coordinator `rmcosta-lab`                                            | Own requirements, plan, and validation.                                                                                                  |
| `docs/project-specs/roadmap.md`, `docs/decisions/evidence-audio-playback.md`                                                       | Phase coordinator `rmcosta-lab`                                            | Sole writer for the approved scope clarification and decision; notify Fases 17/20 through the eventual PR body.                          |
| `backend/src/yuno_backend/volta/evidence/playback.py`, focused exports and `backend/tests/volta/evidence/**`                       | Fase 16 backend writer                                                     | Own only audio retrieval orchestration and tests; preserve storage/persistence contracts.                                                |
| `api/app/schemas/**`, focused playback router/adapter/wiring, `api/tests/**`                                                       | Fase 16 API writer                                                         | Own response-field redaction, the additive route, explicit binary schema, safe errors, wiring, compatibility search, and contract tests. |
| `api/openapi.json`, `frontend/src/lib/api/generated/**`                                                                            | Fase 16 API contract writer                                                | Generated together only after source/API tests; never hand-edit.                                                                         |
| `frontend/src/app/(control-tower)/{evidence,recovery,escalation,audit}/**`, `frontend/src/features/recovery/**`, focused E2E tests | Fase 16 frontend writer                                                    | Own page composition, generated-hook orchestration, forms, player, and presentation.                                                     |
| `frontend/src/components/control-tower/**`                                                                                         | Fase 16 frontend writer only where required                                | Preserve existing consumers; no broad redesign.                                                                                          |
| `frontend/src/lib/{demo-auth,live-operation-handoff}.tsx`                                                                          | Prefer read-only; Fase 16 frontend writer only if a missing seam is proven | Coordinate a narrow compatible change and preserve Fases 10/13 behavior.                                                                 |
| `frontend/src/lib/api/volta-fetch.ts`, focused fetch/E2E coverage                                                                  | Fase 16 frontend contract writer                                           | Sole writer for binary success parsing; preserve JSON/error/auth/request-ID behavior for every existing generated operation.             |
| Manifests/lockfiles, migrations, `.env.example`, all other shared specs, provider adapters                                         | No Fase 16 writer                                                          | No dependency, schema, configuration, or provider change is planned.                                                                     |

One named writer owns each row even when implementation workstreams run in parallel. Contract and
backend service symbols freeze before API and frontend work begin; generated artifacts have only
the API contract writer.
