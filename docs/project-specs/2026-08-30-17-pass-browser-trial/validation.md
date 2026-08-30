# Fase 17 — Validation

Keep every criterion unchecked until its exact safe evidence is recorded. Provider-credentialed
evidence and the private fallback remain separate from deterministic repository checks.

## Coordination and clean environment

- [x] Fases 10, 13, and 16 remain merged with their required gate evidence; no competing Fase 17
  branch/PR, closed-unmerged review, or newly active bidirectional conflict exists.
- [ ] The trial starts from the published Fase 17 head with a clean tracked/untracked worktree,
  isolated PostgreSQL database, empty private evidence root, fresh browser profile/state, and no
  reused logical mutation key.
- [x] Exact Python, Node, pnpm, PostgreSQL, Chromium, browser, and optional OpenAI model versions are
  recorded without credentials or private paths.
- [x] Requirements, exclusions, ownership, fallback, and the unchanged roadmap gate still match;
  no unrecorded shared decision or temporary prerequisite appeared.

## Canonical browser journey

- [x] The canonical English prompt creates a schema-validated draft with source and policy version;
  explicit approval creates one operation and immutable mandate for Thursday and at most MXN 9,000.
- [x] Deterministic eligibility and fixed ranking select the three canonical synthetic carriers and
  create concurrent workflow sessions without model discretion.
- [x] Quote changes and one contradictory/out-of-mandate statement remain auditable; invalid terms
  are rejected and cannot become an eligible quote or commitment.
- [x] Exactly one evidence-backed `CANDIDATE` is `ACTIVE`; later replacement leaves exactly one
  active winner and preserves every `SUPERSEDED` commitment.
- [x] The recap is labeled `SIMULATED`, the structured brief is visible, and no UI or evidence claims
  real carrier contact, PSTN, booking, provider delivery, or `VERIFIED` commitment.
- [x] Operation reload and the bounded audit timeline preserve deterministic ordering, correlations,
  versions, quotes, evidence, recap, brief, recovery, escalation, and notification facts without
  client-authored transitions.

## Required failure and recovery matrix

- [x] No eligible carrier creates exactly one auditable pre-contact escalation before any session,
  quote, commitment, Realtime connection, or provider action begins.
- [x] Contradiction, stale version, duplicate replay, changed idempotency fingerprint, and
  out-of-mandate requests return their accepted safe behavior and leave durable state consistent.
- [x] Microphone permission denial, unavailable/blocked playback, credential/provider failure, clean
  and forced disconnect, and reconnect are distinct accessible states with text fallback available.
- [x] Reconnect mints a fresh credential/session, closes the prior peer/channel/tracks/listeners,
  reconciles uncertain mutation state, and never replays it under a new provider call identifier.
- [x] Mandate-safe recovery either renegotiates or reconfirms before atomic replacement, creates one
  auditable notification, and preserves exactly one active winner.
- [x] Bad recovery preserves the commitment, records attempted alternatives and safe context, opens
  human escalation, and resumes only after a new immutable mandate version resolves it.

## Evidence audio and fallback recording

- [x] Every evidence UUID in the trial resolves only through authenticated
  `GET /v1/evidence/{evidence_id}/audio` to valid bounded RIFF/WAVE bytes with private/no-store/nosniff
  headers and no public storage reference.
- [x] Playback begins at each stored `audio_start_ms` within recorded normal browser timing tolerance;
  item/event identifiers correlate to the agreeing turn without claiming word-level accuracy.
- [x] Missing, invalid, oversized, denied, and unsupported audio fail safely while evidence metadata,
  recap, brief, recovery, escalation, and audit views remain usable.
- [x] The complete P0 fallback recording is reproducible by an authorized operator, private and
  outside Git, uses only synthetic data, and tells the same truthful bounded browser story.
- [x] Recording access, retention, deletion owner, and cleanup result are recorded safely without a
  local/private path, raw audio, transcript, participant data, or storage reference in Git.

## Separately authorized English Realtime trial

- [x] Provider use was explicitly authorized and used only a server-side standard key, in-memory
  ephemeral credential, synthetic operation data, and private synthetic audio.
- [ ] One English WebRTC session establishes with natural pacing; ambient noise at the accepted
  `server_vad.threshold = 0.85` does not cause the earlier false interruption behavior.
- [ ] One English barge-in produces observable interruption handling and a coherent continuation.
- [ ] `record_quote` and `create_candidate_commitment` each reach the exact generated BFF operation,
  return a bounded safe output with the original provider call ID, and refresh authoritative state.
- [x] Explicit Stop releases microphone/playback/connection resources; forced disconnect and fresh
  reconnect do not overlap sessions or duplicate a mutation.
- [x] Account/model limits, latency, timeout/retry outcomes, provider nondeterminism, browser/model
  versions, and any skipped credentialed criterion are reported without weakening the gate.

## API, backend, PostgreSQL, and contracts

- [x] Authentication and explicit CORS run before delegation; rate limits, no-store credentials,
  request IDs, safe errors, and redacted structured logs behave as accepted.
- [x] Typed API delegation covers intake, approval, negotiation, quotes, commitment, evidence audio,
  recap, brief, recovery, mandate replacement, escalation, notification, operation, and audit reads.
- [x] Backend tests preserve deterministic mandate/ranking/quote/winner/recovery rules, fingerprinted
  idempotency, transactional rollback, append-only audit, and FastAPI-free public boundaries.
- [x] The isolated PostgreSQL database migrates to repository head and round-trips every canonical
  artifact; repeated/restarted mutations preserve identity and do not duplicate state or audit.
- [x] `api/openapi.json` and `frontend/src/lib/api/generated/**` remain unchanged and unedited. If a
  proven contract repair occurred, API tests pass and two `make generate` runs are deterministic
  before frontend consumers pass.

## Browser, visual, accessibility, and security

- [x] Playwright exercises the complete user flow first; subsequent browser inspection finds no
  unexpected console warning/error, runtime/hydration failure, or failed network request.
- [x] Network traffic is limited to expected Next.js/BFF calls and the explicitly authorized
  Realtime exchange; expected methods/statuses/request IDs are recorded with authorization redacted.
- [x] Desktop and mobile widths have no horizontal overflow or clipped actions; loading, empty,
  denied, stale, retry, fallback, in-flight, recovery, escalation, and terminal states remain clear.
- [ ] Keyboard order, focus visibility, landmarks/headings, labels/descriptions, live announcements,
  contrast, non-color cues, touch targets, audio controls, and text wrapping pass.
- [x] The standard key, ephemeral secret, demo bearer, authorization header, database URL, private
  reference/path, SDP, transcript, raw event/tool/provider payload, real contact data, and audio are
  absent from source, bundle, DOM, storage, console, network evidence, logs, screenshots, fixtures,
  exceptions, generated artifacts, the fallback record, and Git.
- [x] No Yuno/payment behavior, Twilio/PSTN call, real carrier contact, deployment, production access,
  remote migration, external message, or financial mutation was performed or claimed.

## Commands and final evidence

- [x] `uv run ruff check .` passes.
- [x] `uv run pytest` passes with the required isolated PostgreSQL configuration; exact counts and
  credentialed deselections/skips are recorded.
- [x] `pnpm --dir frontend lint` passes with zero warnings.
- [x] `pnpm --dir frontend typecheck` passes.
- [x] `pnpm --dir frontend format:check` passes.
- [x] `pnpm --dir frontend build` passes.
- [x] `pnpm --dir frontend test:e2e` passes the deterministic Chromium suite.
- [ ] `pnpm --dir frontend test:e2e:realtime` passes when separately authorized, or every skipped or
  nondeterministic result is explicitly recorded without being reported as green.
- [x] `make check` passes from the repository root against isolated PostgreSQL.
- [x] Focused tests beside every integration repair pass and their exact commands/results are recorded.
- [x] `git diff --check`, complete tracked/untracked diff review, generated-artifact review,
  architecture-import review, manifest/lock/migration review, secret/sensitive-data scan, and
  one-writer ownership review pass.
- [x] The final evidence records the reproducible clean command sequence, scenario matrix, console
  and network inspection, offset results, private fallback status, known provider limitations, and
  any residual P0 gap.

## Evidence recorded on 2026-08-30

### Environment and coordination

- Branch `phase/17-pass-browser-trial` started aligned with its published planning commit. Dependency
  pull requests #15, #20, and #23 were merged, no Fase 17 pull request or competing branch existed,
  and the roadmap declared no conflict. The final implementation remains an uncommitted phase diff,
  so the clean-published-head criterion above remains unchecked.
- Versions: Python 3.13.14, uv 0.12.1, Node 24.18.0, pnpm 11.9.0, PostgreSQL
  17.11, Playwright 1.62.1 with pinned Chromium revision 1234, in-app Chrome Browser inspection, and
  OpenAI Realtime model `gpt-realtime-2.1`.
- Each real trial used a newly created loopback PostgreSQL database named with the safe
  `volta_trial_` prefix and migrated through revision `20260830_25`. Its exact private evidence file
  was mode `0600`; logical mutation keys and browser contexts were fresh. Trial databases and copied
  synthetic WAVs were removed individually after use.

### Deterministic browser and repair evidence

- `chromium-trial` against a production Next.js build, FastAPI, backend services, and PostgreSQL:
  **3 passed**. It covered the complete canonical operation, one rejected above-cap quote, original
  evidence playback at 250 ms, simulated recap, brief, safe rendered 404 with the audit still usable,
  mandate-safe replacement, notification acknowledgement, out-of-mandate escalation, immutable
  mandate replacement, recovery playback at its stored 1840 ms offset, final audit, permission denial
  with usable text fallback, and the
  Veracruz-to-Puebla no-eligible pre-contact escalation. The recovery evidence returned authenticated
  `200 audio/wav` with private/no-store headers after the fixture repair.
- `pnpm --dir frontend test:e2e`: **6 passed** after the lifecycle repair. The suite covers diagnostic
  failure states, cleanup, text fallback, private Blob playback transport, and 390-by-844 responsive
  fit. A separate in-app Chrome inspection loaded `/intake`, keyboard/click selected the canonical
  prompt, found a semantic page structure, rendered without clipping at desktop width, and reported
  no console/runtime logs.
- Reproduced repair 1: recovery referenced textual `.webm` bytes, so authenticated recovery playback
  failed with 404. The backend now atomically materializes a deterministic three-second mono PCM WAV,
  mode `0600`, whose duration exceeds the stored 1840 ms offset. Focused backend/evidence/recovery
  regression command: **51 passed**.
- Reproduced repair 2: the asynchronous clean-close status overwrote `FALLBACK`. Voice callbacks,
  tool dispatch, and reconciliation are now generation-bound, and stale sessions cannot overwrite a
  fallback or newer session. The permission/fallback focused browser test passed, as did the complete
  trial and default suite.
- Reproduced test-isolation repair: ambient `DATABASE_URL` no longer changes the fake contract route
  test. Its focused run passed both with the normal environment and with a synthetic nonempty ambient
  URL.

### Provider-credentialed checkpoint

- The user explicitly authorized provider use. The standard key stayed server-side; the browser
  received only short-lived memory-only client credentials and used private synthetic audio. The
  first attempt never reached the provider because Next dev exhausted local file watchers (`EMFILE`).
  A production-server retry initially used the prior isolated-port build and was stopped before the
  provider. Both infrastructure failures were corrected without changing product criteria.
- Three valid provider executions reached OpenAI. The main scenario emitted `record_quote` but did
  not emit `create_candidate_commitment` within the fixed 60-second wait in all three runs. The final
  run therefore remained **1 failed, 1 passed**: forced disconnect, reconciliation, fresh credential,
  reconnect, no quote replay, and explicit clean Stop passed; the two-tool roundtrip failed only at
  the missing commitment call. The known model nondeterminism is not reported as green.
- Natural English pacing, ambient-noise resistance, and coherent spoken barge-in require a human
  listener and were not falsely inferred from the synthetic automated run. Those criteria and the
  complete two-tool provider criterion remain unchecked and block a full Fase 17 PASS.
- Playwright screenshots, traces, and video were disabled for provider tests. Generated failure
  context, copied synthetic audio, and private provider-test artifacts were deleted after recording
  only bounded outcomes; no credential, SDP, transcript, raw event, or provider payload was retained.

### Private fallback recording and cleanup

- With separate explicit authorization, the canonical deterministic test produced a 4.84-second
  WebM recording (approximately 511 KiB) outside Git. It passed 1/1 against an isolated database and
  shows only synthetic operation UI, including the good and bad recovery outcome. Start and terminal
  frames were visually inspected: no bearer value or private storage reference was visible.
- The retained recording and containing directories are restricted to the current user (`0600` file,
  `0700` directories). Its private path is intentionally omitted here. The user owns retention and
  deletion; temporary extracted frames, runner config, database, copied WAV, and test-result metadata
  were permanently removed and are not recoverable from the workspace.
- Reproduction: create a fresh loopback database whose name begins `volta_trial_`, migrate to head,
  run API and production frontend on isolated loopback ports with a synthetic demo bearer, and run the
  canonical `chromium-trial` test with Playwright video enabled to an access-restricted directory
  outside the repository. Never commit the output or pass a real participant recording.

### Final commands and review

- `make check` with the local PostgreSQL test URL: Ruff passed; pytest **517 passed, 2 credentialed
  tests deselected, 0 skipped, 1 known Starlette/httpx deprecation warning**; frontend lint,
  typecheck, and production build passed.
- `pnpm --dir frontend format:check`, `git diff --check`, focused API/backend tests, full frontend
  checks, and the deterministic Playwright suites passed. `api/openapi.json`, generated Orval files,
  manifests, lockfiles, migrations, and `.env.example` have no diff. Review found no FastAPI import
  in backend, browser-owned operational transition, credential value, private recording path,
  provider payload, Yuno/payment action, remote mutation, deployment, or real carrier contact.
- Residual gate: this is **NOT A FULL TECHNICAL PASS** because the human qualitative voice
  observations were not performed and the credentialed model did not issue the commitment tool call
  within the accepted timeout. Deterministic text fallback and the complete P0 operational story are
  reproducibly green.
- Explicit hackathon disposition: on 2026-08-30 the user accepted the recorded Realtime limitation,
  retained the truthful deterministic fallback as the demo path, and authorized Fase 17 to be
  submitted and merged so dependent phases can proceed. The unchecked voice criteria above remain
  visible and are not represented as passed; this is an explicit delivery waiver, not a weakened or
  fabricated validation result.
- Final release verdict: **ACCEPTED FOR HACKATHON WITH RECORDED REALTIME WAIVER**.
