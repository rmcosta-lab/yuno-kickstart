# Fase 17 — Implementation plan

## 1. Freeze the accepted trial contract

- Refresh `origin/main`, dependency PRs #15/#20/#23, the Fase 17 branch/PR state, and all declared
  conflicts before implementation.
- Record the exact clean-environment prerequisites: Python 3.13/`uv`, Node/`pnpm`, pinned Chromium,
  PostgreSQL, local demo authorization, private evidence root, and optional server-side OpenAI access.
- Freeze the existing HTTP and application gates in `requirements.md`. No Pydantic, OpenAPI, Orval,
  migration, provider-policy, or dependency change is expected.
- Define fresh synthetic fixture identifiers and isolated database/evidence/browser state. Keep all
  credential values, private paths, raw audio, and provider payloads out of the trial record.

## 2. Build the deterministic complete-journey harness

- Give one browser-trial writer ownership of `frontend/tests/e2e/**` and Playwright configuration.
- Compose or extend existing intake/negotiation, Realtime diagnostic, and recovery coverage into one
  reproducible clean journey rather than copying contracts or domain rules into test code.
- Exercise canonical approval, three eligible sessions, valid and contradictory/out-of-mandate
  quotes, one active evidence-backed candidate, simulated recap, brief, and complete audit reload.
- Add the no-eligible-carrier fixture and assert that it creates a pre-contact escalation before any
  session/provider mutation.
- Exercise authenticated playback for every private evidence artifact and verify the stored
  millisecond offsets, safe unavailable-audio behavior, and absence of public storage references.
- Exercise mandate-safe replacement/notification and bad recovery/escalation/mandate replacement
  with fresh idempotency keys, authoritative refetches, and exactly one active winner.

## 3. Run independent risk workstreams after the deterministic checkpoint

- Frontend/browser writer: permission denial, playback block, keyboard/focus/live-region behavior,
  responsive mobile/desktop layouts, disconnect, fresh reconnect, fallback, and cleanup.
- API/backend verifier: focused existing regression suites for authorization, CORS, rate limiting,
  idempotency, stale versions, transaction rollback, evidence retrieval, recovery, and audit ordering.
- Security/evidence verifier: inspect bundle, DOM, browser storage, console, network, server logs,
  Git diff, ignored private artifacts, and recording handling for credentials or sensitive values.
- These workstreams are read-only against shared/generated files. A failed criterion becomes one
  minimized reproduction owned by the phase coordinator before any code writer is assigned.

## 4. Repair only reproduced integration defects

- Classify each defect at the frontend, API, backend, provider adapter, data, or environment boundary.
- Assign one writer to the smallest owning path and add focused regression coverage beside the fix.
- Keep business decisions in the core, HTTP validation/errors in FastAPI, and browser presentation,
  WebRTC lifecycle, and generated-client use in the frontend.
- If an HTTP contract repair is unavoidable, pause the dependent browser work; update and test
  Pydantic first, run `make generate`, review/freeze OpenAPI, regenerate Orval, and then fix consumers.
- If a migration, dependency, manifest/lock pair, environment inventory, or shared decision becomes
  necessary, revise this plan, identify affected phases/owners, communicate the change, and refresh
  branches before proceeding. No such change is currently planned.

## 5. Run the separately authorized Realtime trial

- Before provider use, confirm explicit operator authorization, server-only credentials, synthetic
  private WAV input, safe artifact settings, account/model access, and cleanup responsibility.
- Run typed quote and commitment tool roundtrips, preserve original provider call identifiers, and
  verify refreshed authoritative context after every mutation.
- Human-check English natural pacing, ambient-noise resistance at the accepted VAD threshold `0.85`,
  one barge-in with coherent continuation, explicit Stop, permission failure, forced disconnect, and
  fresh-session reconnect without mutation replay.
- Record provider nondeterminism, limits, timeouts, retries, browser/model versions, and skipped
  checks exactly. Deterministic local evidence does not masquerade as provider success.

## 6. Produce the private recorded fallback

- Rehearse the same canonical browser story with synthetic data and truthful `SIMULATED`/browser
  labels, including the good and bad recovery outcomes.
- Create a short private recording outside Git with no visible credential, authorization value,
  private storage path/reference, real participant data, raw transcript, or provider payload.
- Document how an authorized operator can reproduce it from the clean setup and record private
  location, access, retention, and deletion responsibility without committing the artifact or path.
- Confirm that text mode can reproduce the operational outcome when live voice/provider access is
  unavailable and that the failure remains visible.

## 7. Final integration and handoff

- Run focused tests near every repaired defect, then `uv run ruff check .`, `uv run pytest`,
  `pnpm --dir frontend lint`, `pnpm --dir frontend typecheck`,
  `pnpm --dir frontend format:check`, `pnpm --dir frontend build`, the deterministic Playwright
  suite, and root `make check` with isolated PostgreSQL.
- Run `make generate` twice only if an HTTP contract changed; otherwise prove OpenAPI/Orval have no
  diff and were not hand-edited.
- Run the browser journey first, then inspect console, network, DOM/storage, runtime errors,
  responsive behavior, accessibility, microphone/connection teardown, and private playback offsets.
- Review the complete tracked/untracked diff, generated artifacts, architecture imports, manifests,
  migrations, environment inventory, and secret/sensitive-data patterns; run `git diff --check`.
- Record exact commands, versions, pass/fail counts, skipped credentialed evidence, known provider
  nondeterminism, fallback reproduction, and residual gaps in `validation.md` before review.

## Coordination and external-change boundaries

- One named writer owns each row of the requirements ownership matrix. Contract decisions and the
  deterministic reproduction freeze before non-overlapping layer fixes run in parallel.
- No deployment, public hosting change, production access, remote migration, real call, external
  message, carrier contact, Yuno/payment action, or financial mutation is authorized by this phase.
- OpenAI provider use and creation of the private fallback recording require the explicit checkpoint
  in sections 5 and 6; credentials and recordings remain outside Git.
- No temporary prerequisite is currently known. If a supporting prerequisite appears, record the
  wait here and resume only after its specification/PR is merged and this branch is refreshed.
