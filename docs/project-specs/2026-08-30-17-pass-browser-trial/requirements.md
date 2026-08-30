# Fase 17 — Pass the complete P0 browser trial

## Coordination

- Priority: P0 complete-browser checkpoint and prerequisite for Fases 18 and 21.
- Branch: `phase/17-pass-browser-trial`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fases 10, 13, and 16, merged with gate evidence in pull requests #15, #20, and #23.
- Conflicts with: none.
- Roadmap gate: a clean environment completes the canonical English browser journey and the
  no-eligible-carrier, contradiction, English interruption, permission-denial, reconnect,
  good-recovery, and bad-escalation scenarios; `make check`, browser console and network
  inspection, secret review, every private recording offset, and a reproducible recorded fallback
  pass.
- Priority source: the roadmap identifies this cross-layer gate as completion of P0 before product
  telephony implementation begins.

## Objective and user-visible outcome

Prove that an operations coordinator can run Volta's complete browser checkpoint from a clean
environment: enter and approve the canonical English request, start deterministic carrier
workflows, use browser voice or the truthful text fallback, select exactly one mandate-safe winner,
inspect playable evidence and the simulated recap, complete a mandate-safe recovery, escalate an
out-of-mandate recovery, and audit the resulting state.

The terminal result is one reproducible, recorded P0 browser demonstration with authoritative
PostgreSQL state, exactly one active commitment, retained superseded history, validated private
agreement-turn playback, a `SIMULATED` recap, and visible recovery or escalation evidence. It is
not a PSTN call, carrier booking, provider-delivered written commitment, or `VERIFIED` commitment.

## Included scope

- Define and execute one clean-environment trial harness for the canonical Manzanillo-to-Guadalajara
  English journey through the generated client, FastAPI BFF, typed backend services, PostgreSQL,
  private local evidence storage, and the existing browser Realtime boundary.
- Exercise the required failure and adversarial matrix: no eligible carrier, a contradictory or
  out-of-mandate quote, English barge-in, microphone permission denial, playback failure,
  disconnect/reconnect, mandate-safe recovery, and out-of-mandate escalation.
- Verify every stored `audio_start_ms` against its private playable RIFF/WAVE artifact and confirm
  that the browser receives audio only through the authenticated evidence route.
- Add or extend the smallest deterministic Playwright coverage and reproducible trial fixtures
  needed to run the complete story from a clean checkout without relying on stale local state.
- Run the separately credential-gated OpenAI Realtime trial and human qualitative checks when the
  operator explicitly authorizes provider use and the required server credential/private synthetic
  audio are available.
- Produce a private recorded fallback and a safe evidence record containing commands, versions,
  scenario outcomes, console/network results, and known provider limitations without credentials,
  participant data, SDP, transcripts, raw audio, or private storage references.
- Correct only integration defects exposed by the trial, preserving the accepted layer contracts,
  domain authority, generated-client ownership, and provider boundaries.

## Excluded scope

- Twilio, public switched telephone network (PSTN), real inbound or outbound calls, real carrier
  contact, real rates, bookings, provider-delivered recap, SMS, email, or `VERIFIED` commitments.
- New product capability, broad redesign, new architecture, model-controlled carrier selection,
  browser-owned mandate/winner decisions, or weakening any accepted gate.
- Deployment, public hosting, production access, remote database mutation, production recording,
  real participant data, Yuno, payments, or financial mutations.
- Pydantic, OpenAPI, Orval, migration, manifest, lockfile, `.env.example`, provider-policy, or global
  specification changes unless the trial proves a concrete blocking defect and the coordinator
  records the revised ownership and regeneration/communication checkpoint first.
- Committing recordings, credentials, authorization values, private evidence files, screenshots
  containing secrets, raw provider events, transcripts, or local environment files.

## Assumptions, risks, and fallback

- Assumption: the merged contracts from Fases 10, 13, and 16 are sufficient. The phase consumes the
  current HTTP and application boundaries and expects no contract generation or migration.
- Assumption: a clean local environment can run PostgreSQL, the FastAPI BFF, the production Next.js
  build, private temporary evidence storage, and pinned Playwright Chromium.
- Risk: the credentialed Fase 13 combined run was not consistently green because the model did not
  always issue `create_candidate_commitment` within 60 seconds. Mitigation: keep deterministic
  tool/contract assertions separate from the qualitative provider observation, record all retries
  and timeouts honestly, and never convert provider nondeterminism into a false pass.
- Risk: the final `server_vad.threshold = 0.85` calibration was accepted after `0.7` remained too
  sensitive to ambient noise, without a later complete human retest. Mitigation: repeat natural
  pacing, ambient-noise resistance, English barge-in, coherent continuation, stop, and reconnect in
  the complete trial.
- Risk: stale fixture state, idempotency keys, ports, browser storage, or database rows make a run
  appear reproducible. Mitigation: provision an isolated database and evidence root, create fresh
  logical mutation keys, clear browser state, and preserve a one-command setup/teardown record.
- Risk: the private fallback recording or diagnostics leak credentials, participant data, SDP,
  transcripts, raw tool/provider payloads, or storage references. Mitigation: use synthetic data,
  disable retained provider test artifacts, keep recordings outside Git, review console/network and
  the final diff, and record only bounded safe identifiers and results.
- Fallback: browser text mode exercises the same typed BFF and deterministic core if microphone,
  playback, Realtime access, or provider behavior fails. A private short recording demonstrates the
  complete browser operation when the live environment is unavailable. Failures remain visible and
  are never described as PSTN contact, provider success, or a verified written commitment.

## Acceptance criteria

- From a clean checkout and isolated PostgreSQL database, the generated client completes canonical
  intake, explicit approval, selection of the three eligible synthetic carriers, quote comparison,
  one evidence-backed active `CANDIDATE`, `SIMULATED` recap, brief, and complete audit projection.
- A no-eligible-carrier fixture creates one pre-contact escalation and no carrier session, quote,
  commitment, provider connection, or browser-authored operational state.
- A contradictory or out-of-mandate statement is visible, rejected by deterministic backend rules,
  and absent from eligible comparison and active commitment state.
- A separately authorized English browser-voice run demonstrates natural pacing, ambient-noise
  resistance, one coherent barge-in recovery, typed quote and commitment tool roundtrips with their
  original provider call identifiers, explicit Stop, and a fresh-session reconnect without replay.
- Permission denial, unavailable/blocked playback, credential or provider failure, disconnect, and
  reconnect remain accessible, recoverable, non-color-only states with the text path always usable.
- Mandate-safe recovery preserves exactly one active winner, supersedes prior history atomically,
  and creates an auditable notification; bad recovery preserves the current commitment and opens a
  human escalation until a new immutable mandate resolves it.
- Every evidence item used by the journey resolves through the authenticated route to private valid
  RIFF/WAVE bytes and begins playback at its stored `audio_start_ms` within normal media timing
  tolerance; unavailable or invalid audio fails safely while recap, brief, and audit remain usable.
- Browser console contains no unexpected warning/error, network inspection shows only expected BFF,
  Next.js, and explicitly authorized Realtime traffic, and no standard/ephemeral credential or
  private recording reference appears in source, bundle, DOM, storage, console, screenshots, logs,
  errors, or Git.
- The fallback recording can be reproduced from the documented clean setup, remains private and
  outside Git, and tells the same bounded P0 story as the live browser journey.
- `make check`, focused Playwright suites, generated-artifact stability review, `git diff --check`,
  secret/privacy review, responsive browser checks, and the complete ownership/diff review pass.

## HTTP contract gate

This phase consumes the accepted contract without changing it. The trial must prove these groups
through the generated client and the existing safe status/error semantics:

| Boundary | Required behavior |
| --- | --- |
| `POST /v1/operation-drafts`, `POST /v1/operations`, `GET /v1/operations/{operation_id}` | Structured draft, explicit approval, immutable mandate, authoritative reload; expected `201`/`200` and safe `401`/`403`/`404`/`409`/`422`/`429`/`500` errors. |
| `POST /v1/operations/{operation_id}/negotiations`, `POST /v1/calls/{call_id}/quotes`, `POST /v1/calls/{call_id}/commitments` | Deterministic selection, quote validation, fingerprinted idempotency, stale-state rejection, and exactly one active winner; mutations return `201` or a declared safe error. |
| `POST /v1/realtime/client-secrets` | Existing demo authorization, allowed origin, rate limit, no-store short-lived credential, fixed server session policy, and no standard/ephemeral secret leakage. |
| `GET /v1/evidence/{evidence_id}/audio` | Authenticated `200 audio/wav`, private/no-store/nosniff, server-resolved reference, bounded bytes; safe constant `404`, bounded `413`, and no opaque reference in URL or response. |
| `POST /v1/operations/{operation_id}/inbound-simulations`, `POST /v1/operations/{operation_id}/mandates`, `POST /v1/notifications/{notification_id}/acknowledgements` | Server-owned good/bad recovery, version-safe mandate replacement, and idempotent acknowledgement with accepted `200`/`201` and safe stale/conflict errors. |
| `GET /v1/operations/{operation_id}/audit` | Bounded deterministic projections and opaque pagination without browser-invented transitions or leaked private fields. |

Operation IDs, Pydantic models, `api/openapi.json`, and generated Orval artifacts remain unchanged. If
a contract defect is proven, the coordinator pauses dependent browser work, assigns one API writer,
updates/tests Pydantic first, runs `make generate` twice, reviews the artifacts, and then assigns the
frontend consumer update.

## Application contract gate

| Import path | Public boundary consumed by the trial | Required behavior |
| --- | --- | --- |
| `api.app.volta_text_service` | `VoltaTextContractService` from `create_volta_text_contract_service(...)` | Thin transport adapter delegates every accepted operation to typed services, returns public projections, and maps safe exceptions without business rules or database queries in FastAPI. |
| `yuno_backend.volta.text_slice` and existing mandate/negotiation/recovery modules | Existing typed commands, application facade, services, projections, repositories, and safe exceptions | PostgreSQL-backed intake, mandate, selection, quotes, commitment, recap, brief, recovery, escalation, notification, and audit behavior remains deterministic, transactional, idempotent, and FastAPI-free. |
| `yuno_backend.volta.evidence.playback` | `RetrieveEvidenceAudioService`, `EvidenceAudio`, `EvidenceAudioNotFound`, `EvidenceAudioTooLarge` | Resolve an evidence UUID to validated bounded private audio without exposing the storage reference or holding a database transaction across storage retrieval. |
| `frontend/src/features/realtime` | `BrowserVoiceExperience`, `connectBrowserRealtime`, and the typed tool dispatcher | One explicit WebRTC lifecycle, allowlisted events, safe tool output, original provider call-ID correlation, uncertain-mutation reconciliation, fresh reconnect, and deterministic cleanup. |
| `frontend/src/features/recovery` and generated API client | `RecoveryExperience`, evidence player, audit projection, and generated hooks/functions | Render server-owned lifecycle/disposition, play private audio from the stored offset, run/refresh recovery and escalation, and never infer operational state. |

No public symbol or construction pattern changes are planned. A proven integration defect may be
fixed only at its owning layer with focused tests and without moving domain authority across the
existing boundaries.

## Browser/server handoff and terminal result

The browser calls only this repository's FastAPI BFF through the generated client, except for the
accepted Realtime WebRTC connection created with a memory-only server-issued ephemeral credential.
Every operational Realtime tool request returns through the BFF and deterministic Python core with
the original provider correlation. Private audio is fetched only from the authenticated BFF route
into a revocable in-memory Blob URL. PostgreSQL and backend services remain the durable source of
mandate, winner, recovery, escalation, notification, and audit state.

The terminal browser result is the authoritative operation/audit projection with exactly one active
winner and either a completed mandate-safe recovery notification or a preserved commitment plus
human escalation. The private recording is supporting evidence, not durable operational authority.

## Layer, data, security, visual, and accessibility decisions

- Frontend: preserve the established control tower and smallest client boundaries; extend test
  orchestration before product UI and keep text fallback available throughout.
- API/BFF: preserve Pydantic/OpenAPI/error/auth/CORS/rate-limit behavior and thin delegation.
- Backend/core/data: preserve deterministic rules, atomic winner transitions, durable idempotency,
  isolated PostgreSQL state, safe audit data, and private evidence references outside public DTOs.
- OpenAI: provider use is separately credential-gated and synthetic; record nondeterminism rather
  than hiding it. No Twilio, Yuno, or payment handoff exists in this phase.
- Security: synthetic names/rates/audio only; secrets remain server-side or ephemeral in memory;
  recordings stay private, ignored, access-controlled, and outside Git.
- Visual: verify truthful labels, lifecycle/disposition separation, recoverable errors, loading and
  terminal states at mobile and desktop widths; do not add decorative redesign work.
- Accessibility: keyboard flow, visible focus, semantic landmarks/forms/timelines, sufficient
  contrast, non-color cues, restrained live regions, native or equivalent audio controls, touch
  targets, text wrapping, and no horizontal overflow are part of the gate.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-17-pass-browser-trial/**` | Phase coordinator `rmcosta-lab` | Own requirements, plan, validation, and final safe evidence. |
| `frontend/tests/e2e/**`, `frontend/playwright.config.ts` | Fase 17 browser-trial writer | Own deterministic and credential-gated orchestration; retain secret-safe artifact settings. |
| `frontend/src/features/{realtime,recovery,negotiation}/**` and affected control-tower pages/components | One Fase 17 frontend writer, only after a reproduced defect | Apply the smallest integration fix; preserve generated types and server-owned state. |
| `api/**` excluding generated OpenAPI | One Fase 17 API writer, only after a reproduced transport/wiring defect | Preserve thin delegation and accepted contracts; coordinate before any Pydantic change. |
| `backend/**` | One Fase 17 backend writer, only after a reproduced core/persistence/provider-adapter defect | Preserve FastAPI-free authority and add focused regression coverage. |
| `api/openapi.json`, `frontend/src/lib/api/generated/**` | One API contract writer then one frontend generation writer, only if contract repair is unavoidable | Test Pydantic first, generate in order, never hand-edit, and freeze the checkpoint before consumer fixes. |
| `frontend/package.json`, `pnpm-lock.yaml`, Python manifests/locks, migrations, `.env.example` | No expected writer | Existing stack is sufficient; revise the plan and assign one writer per manifest/lock pair or migration only for a proven blocker. |
| Mission, tech stack, roadmap, challenge plan, decision records, other phase specs | No Fase 17 writer | No shared decision change is planned; route a newly required decision through the owning workflow. |
| Private audio, fallback recording, browser/provider diagnostics containing sensitive values | No Git writer | Keep outside Git with restrictive access and the agreed deletion/retention handling. |

The phase coordinator freezes a reproduced defect and assigns exactly one writer to its path before
parallel work begins. Shared/generated files remain read-only until that checkpoint.
