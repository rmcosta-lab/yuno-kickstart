# Phase 22 validation — Pass the final P0.1 telephony trial

## Planning and coordination

- [x] Phase 22 remains based on current `origin/main`; dependency PRs for 20, 21, 26, and 28 are
      merged with gate evidence, no Phase 22 branch/PR predates this claim, and no bidirectional
      conflict is active.
- [x] Scope, owner, one-writer paths, no-Issue decision, Phase 28 final-SHA caveat, fallback, and the
      separate authorization boundary are recorded without mutable status in the roadmap.
- [ ] Current official Twilio Voice, Media Streams, signature, account/country/capacity, calling and
      recording requirements plus OpenAI Realtime model/account limits are recorded before the live
      run; no endpoint, enum, callback, retry, or consent behavior is guessed.

## Bounded runtime and deterministic tests

- [x] `LiveTelephonyApplication` supports at most three independent active outbound runtime entries
      while preserving the existing `TelephonyApplication`, backend symbols, durable store, and
      constructor boundary.
- [x] Three distinct authorized requests create three calls and voice/media bindings; exact replay
      causes no second provider I/O, changed payload conflicts safely, and a fourth active request is
      rejected before provider I/O.
- [x] Three WebSockets can bridge concurrently; each token is claimed once, each Realtime session,
      audio/tool event, authority fence, disconnect, and terminal cleanup affects only its call, and
      capacity is released in `finally` paths.
- [x] Duplicate, reordered, mismatched, stale, timeout, and terminal status events remain correlated
      and monotonic; no call, commitment, or audit fact can cross session boundaries.
- [x] Focused inbound tests reject invalid signatures and ambiguous callers, deduplicate callbacks,
      and prove the mandate-safe driver-delay recovery, persisted replacement, notification, brief,
      timestamp evidence, and audit state.
- [x] Focused handoff tests prove explicit authorization, bounded context, duplicate-safe request,
      verified callback-only `JOINED`, remote-leg continuity evidence, AI speech/tool fencing,
      timeout/failure safe states, and redaction.
- [ ] Terminal projections prove exactly one `ACTIVE` winner, retained `SUPERSEDED` history,
      idempotent `SIMULATED` recap for the replacement winner, structured brief, playable evidence,
      and correlated audit order.

## Contracts and repository checks

- [ ] `uv run ruff check .` passes from the repository root.
- [ ] `uv run pytest` passes from the repository root with provider tests mocked or explicitly
      deselected when credentialed.
- [ ] `make python-check` passes, including the focused API/WebSocket concurrency suite.
- [ ] `pnpm lint`, `pnpm typecheck`, and `pnpm build` pass from `frontend/`.
- [ ] `make generate` completes and leaves `api/openapi.json` and
      `frontend/src/lib/api/generated/**` without semantic change.
- [ ] `make frontend-check` and `make check` pass on the final implementation/publication SHA; the
      full gate is not inherited from a pre-reconciliation commit.
      `make frontend-check` passed; `make check` remains blocked by the repository-wide Python
      formatting failure recorded below.
- [ ] `git diff --check`, tracked/untracked review, generated-diff review, and scans for secrets,
      E.164 values, participant data, raw audio/transcripts, provider payloads, private paths, and
      recording locators pass.

## Browser and submission preflight

- [ ] The canonical clean fixture and three carrier sessions render through generated types; start,
      live, ended, failed, recovery, handoff, evidence, `SIMULATED` recap, brief, audit, and fallback
      states remain truthful.
- [ ] Desktop and mobile browser passes cover keyboard activation, visible focus, announcements,
      disabled/duplicate action semantics, long content, loading/error recovery, console, network,
      and runtime errors without exposing a number, credential, signature, or provider payload.
- [ ] Presentation, timed demo script, public repository guide, architecture diagram, and decision
      log are internally consistent, distinguish P0 from P0.1, and state every unclosed gap.
- [ ] Two clean-environment dry runs fit the allotted time and prove browser voice, text, and private
      recording fallback switching; none is represented as PSTN evidence.

## Separately authorized credentialed trial

- [ ] A separate authorization record names the synthetic participants/destination labels, public
      ingress and any temporary configuration, disclosure/consent treatment, recording purpose,
      duration/cost bounds, retention/deletion, stop conditions, and cleanup owner before any call.
- [ ] Account checks confirm the configured Twilio project can place and sustain the three authorized
      calls without a disallowed trial announcement/destination restriction and that OpenAI Realtime
      model access and limits match the tested runtime.
- [ ] Three real outbound PSTN calls are simultaneously `live` for one observable shared interval;
      safe timing evidence distinguishes literal overlap from workflow concurrency or sequential
      calls, and all three streams exchange isolated bidirectional audio and correlated tool output.
- [ ] Every outbound participant receives AI disclosure and the approved recording/consent
      treatment before protected processing; no unauthorized destination is contacted or recorded.
- [ ] One authorized live call reaches durable callback-verified `JOINED`; the participant confirms
      the same remote leg remained connected, structured context reaches the coordinator, and the AI
      produces no speech or commitment-capable tool result after the fence.
- [ ] One signed authorized inbound PSTN call correlates fail closed to exactly one active operation,
      applies disclosure/consent, completes the mandate-safe driver-delay recovery, and persists the
      final replacement, notification, brief, playable evidence, and audit facts.
- [ ] The browser terminal state proves exactly one winner, `SIMULATED` recap, playable timestamp,
      structured brief, recovery and handoff continuity; all five artifacts complete in time.
- [ ] Redacted evidence records restrictions, outcomes, overlap, latency, disconnects, handoff
      continuity, gaps, duration/cost, cleanup, and any failure without exposing private material.

## Cleanup, fallback, and verdict

- [ ] Temporary processes/tunnels stop, authorized provider settings are restored, ambiguous
      mutations are reconciled without new idempotency keys, logs/charges are reviewed, and the
      agreed private-audio retention or deletion action is completed.
- [ ] Private audio, locators, credentials, phone numbers, participant data, signatures, and raw
      provider/model payloads remain outside Git and public artifacts.
- [ ] If capacity, account restrictions, participant availability, consent, correlation, recovery,
      evidence, or handoff prevents any required outcome, the browser/text/private-recording fallback
      is shown and Phase 22 is recorded as incomplete rather than challenge-verified.
- [ ] PASS is declared only when the same authorized rehearsal satisfies all unchanged roadmap gate
      clauses and the final public artifacts report no external recap delivery or workflow-only
      concurrency as challenge evidence.

## Executed evidence and current blockers

- `uv run pytest api/tests/test_telephony_routes.py -q`: passed, 76 tests, with one upstream
  Starlette deprecation warning.
- `uv run ruff check api/app/main.py api/app/routers/telephony.py api/app/telephony/bridge.py
  api/app/telephony/service.py api/tests/test_telephony_routes.py`: passed.
- `make frontend-check`: passed lint, typecheck, and production build.
- `git diff --check`: passed before the validation update.
- `make python-check`: blocked before tests by a pre-existing Ruff import-order failure in
  `backend/src/yuno_backend/volta/telephony/__init__.py`, which is outside the Phase 22 diff and
  ownership.
- Safe configuration inspection found server credentials, three outbound labels, and one inbound
  label, but no non-placeholder public HTTPS or secure-WebSocket ingress. No live call, participant
  contact, recording, deployment, provider mutation, or credentialed trial was executed.
- The credentialed overlap, inbound recovery, handoff, browser, timed-artifact, and cleanup gates
  remain unchecked. Phase 22 is not complete and Phase 27 remains blocked by its dependency.
