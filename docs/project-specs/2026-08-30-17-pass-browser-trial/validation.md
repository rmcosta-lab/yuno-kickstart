# Fase 17 — Validation

Keep every criterion unchecked until its exact safe evidence is recorded. Provider-credentialed
evidence and the private fallback remain separate from deterministic repository checks.

## Coordination and clean environment

- [ ] Fases 10, 13, and 16 remain merged with their required gate evidence; no competing Fase 17
  branch/PR, closed-unmerged review, or newly active bidirectional conflict exists.
- [ ] The trial starts from the published Fase 17 head with a clean tracked/untracked worktree,
  isolated PostgreSQL database, empty private evidence root, fresh browser profile/state, and no
  reused logical mutation key.
- [ ] Exact Python, Node, pnpm, PostgreSQL, Chromium, browser, and optional OpenAI model versions are
  recorded without credentials or private paths.
- [ ] Requirements, exclusions, ownership, fallback, and the unchanged roadmap gate still match;
  no unrecorded shared decision or temporary prerequisite appeared.

## Canonical browser journey

- [ ] The canonical English prompt creates a schema-validated draft with source and policy version;
  explicit approval creates one operation and immutable mandate for Thursday and at most MXN 9,000.
- [ ] Deterministic eligibility and fixed ranking select the three canonical synthetic carriers and
  create concurrent workflow sessions without model discretion.
- [ ] Quote changes and one contradictory/out-of-mandate statement remain auditable; invalid terms
  are rejected and cannot become an eligible quote or commitment.
- [ ] Exactly one evidence-backed `CANDIDATE` is `ACTIVE`; later replacement leaves exactly one
  active winner and preserves every `SUPERSEDED` commitment.
- [ ] The recap is labeled `SIMULATED`, the structured brief is visible, and no UI or evidence claims
  real carrier contact, PSTN, booking, provider delivery, or `VERIFIED` commitment.
- [ ] Operation reload and the bounded audit timeline preserve deterministic ordering, correlations,
  versions, quotes, evidence, recap, brief, recovery, escalation, and notification facts without
  client-authored transitions.

## Required failure and recovery matrix

- [ ] No eligible carrier creates exactly one auditable pre-contact escalation before any session,
  quote, commitment, Realtime connection, or provider action begins.
- [ ] Contradiction, stale version, duplicate replay, changed idempotency fingerprint, and
  out-of-mandate requests return their accepted safe behavior and leave durable state consistent.
- [ ] Microphone permission denial, unavailable/blocked playback, credential/provider failure, clean
  and forced disconnect, and reconnect are distinct accessible states with text fallback available.
- [ ] Reconnect mints a fresh credential/session, closes the prior peer/channel/tracks/listeners,
  reconciles uncertain mutation state, and never replays it under a new provider call identifier.
- [ ] Mandate-safe recovery either renegotiates or reconfirms before atomic replacement, creates one
  auditable notification, and preserves exactly one active winner.
- [ ] Bad recovery preserves the commitment, records attempted alternatives and safe context, opens
  human escalation, and resumes only after a new immutable mandate version resolves it.

## Evidence audio and fallback recording

- [ ] Every evidence UUID in the trial resolves only through authenticated
  `GET /v1/evidence/{evidence_id}/audio` to valid bounded RIFF/WAVE bytes with private/no-store/nosniff
  headers and no public storage reference.
- [ ] Playback begins at each stored `audio_start_ms` within recorded normal browser timing tolerance;
  item/event identifiers correlate to the agreeing turn without claiming word-level accuracy.
- [ ] Missing, invalid, oversized, denied, and unsupported audio fail safely while evidence metadata,
  recap, brief, recovery, escalation, and audit views remain usable.
- [ ] The complete P0 fallback recording is reproducible by an authorized operator, private and
  outside Git, uses only synthetic data, and tells the same truthful bounded browser story.
- [ ] Recording access, retention, deletion owner, and cleanup result are recorded safely without a
  local/private path, raw audio, transcript, participant data, or storage reference in Git.

## Separately authorized English Realtime trial

- [ ] Provider use was explicitly authorized and used only a server-side standard key, in-memory
  ephemeral credential, synthetic operation data, and private synthetic audio.
- [ ] One English WebRTC session establishes with natural pacing; ambient noise at the accepted
  `server_vad.threshold = 0.85` does not cause the earlier false interruption behavior.
- [ ] One English barge-in produces observable interruption handling and a coherent continuation.
- [ ] `record_quote` and `create_candidate_commitment` each reach the exact generated BFF operation,
  return a bounded safe output with the original provider call ID, and refresh authoritative state.
- [ ] Explicit Stop releases microphone/playback/connection resources; forced disconnect and fresh
  reconnect do not overlap sessions or duplicate a mutation.
- [ ] Account/model limits, latency, timeout/retry outcomes, provider nondeterminism, browser/model
  versions, and any skipped credentialed criterion are reported without weakening the gate.

## API, backend, PostgreSQL, and contracts

- [ ] Authentication and explicit CORS run before delegation; rate limits, no-store credentials,
  request IDs, safe errors, and redacted structured logs behave as accepted.
- [ ] Typed API delegation covers intake, approval, negotiation, quotes, commitment, evidence audio,
  recap, brief, recovery, mandate replacement, escalation, notification, operation, and audit reads.
- [ ] Backend tests preserve deterministic mandate/ranking/quote/winner/recovery rules, fingerprinted
  idempotency, transactional rollback, append-only audit, and FastAPI-free public boundaries.
- [ ] The isolated PostgreSQL database migrates to repository head and round-trips every canonical
  artifact; repeated/restarted mutations preserve identity and do not duplicate state or audit.
- [ ] `api/openapi.json` and `frontend/src/lib/api/generated/**` remain unchanged and unedited. If a
  proven contract repair occurred, API tests pass and two `make generate` runs are deterministic
  before frontend consumers pass.

## Browser, visual, accessibility, and security

- [ ] Playwright exercises the complete user flow first; subsequent browser inspection finds no
  unexpected console warning/error, runtime/hydration failure, or failed network request.
- [ ] Network traffic is limited to expected Next.js/BFF calls and the explicitly authorized
  Realtime exchange; expected methods/statuses/request IDs are recorded with authorization redacted.
- [ ] Desktop and mobile widths have no horizontal overflow or clipped actions; loading, empty,
  denied, stale, retry, fallback, in-flight, recovery, escalation, and terminal states remain clear.
- [ ] Keyboard order, focus visibility, landmarks/headings, labels/descriptions, live announcements,
  contrast, non-color cues, touch targets, audio controls, and text wrapping pass.
- [ ] The standard key, ephemeral secret, demo bearer, authorization header, database URL, private
  reference/path, SDP, transcript, raw event/tool/provider payload, real contact data, and audio are
  absent from source, bundle, DOM, storage, console, network evidence, logs, screenshots, fixtures,
  exceptions, generated artifacts, the fallback record, and Git.
- [ ] No Yuno/payment behavior, Twilio/PSTN call, real carrier contact, deployment, production access,
  remote migration, external message, or financial mutation was performed or claimed.

## Commands and final evidence

- [ ] `uv run ruff check .` passes.
- [ ] `uv run pytest` passes with the required isolated PostgreSQL configuration; exact counts and
  credentialed deselections/skips are recorded.
- [ ] `pnpm --dir frontend lint` passes with zero warnings.
- [ ] `pnpm --dir frontend typecheck` passes.
- [ ] `pnpm --dir frontend format:check` passes.
- [ ] `pnpm --dir frontend build` passes.
- [ ] `pnpm --dir frontend test:e2e` passes the deterministic Chromium suite.
- [ ] `pnpm --dir frontend test:e2e:realtime` passes when separately authorized, or every skipped or
  nondeterministic result is explicitly recorded without being reported as green.
- [ ] `make check` passes from the repository root against isolated PostgreSQL.
- [ ] Focused tests beside every integration repair pass and their exact commands/results are recorded.
- [ ] `git diff --check`, complete tracked/untracked diff review, generated-artifact review,
  architecture-import review, manifest/lock/migration review, secret/sensitive-data scan, and
  one-writer ownership review pass.
- [ ] The final evidence records the reproducible clean command sequence, scenario matrix, console
  and network inspection, offset results, private fallback status, known provider limitations, and
  any residual P0 gap.
