# Fase 21 — Validation

Keep every criterion unchecked until its exact safe evidence is recorded. Provider/final-trial facts
are not inferred from implemented code, and private fallback evidence never includes its locator.

## Coordination and artifact scope

- [x] Fase 17 remains DONE with pull request #25 and its Realtime waiver visible; Fase 21 has no
  competing branch/PR or newly active bidirectional conflict before publication.
- [x] The final diff contains only the phase spec, README, `docs/submission/**`, `docs/architecture.md`,
  and any directly required factual decision-log reconciliation.
- [x] One-writer ownership and open pull requests touching shared public docs are refreshed before
  edits and publication; merged PR #29's README deployment guidance is preserved, and no unrecorded
  shared decision or temporary prerequisite appeared.
- [x] Code, `frontend/public`, generated artifacts, contracts, migrations, manifests/locks,
  `.env.example`, mission, stack, roadmap, and other phase specs remain unchanged.

## Consistent public story

- [x] Presentation, README, architecture, decision log, timed script, and fallback guide use the same
  problem, user, canonical operation, mandate, evidence lifecycle, architecture, and known gaps.
- [x] `CANDIDATE`, `SIMULATED`, `VERIFIED`, `ACTIVE`, and `SUPERSEDED` are used correctly; browser
  audio is not called PSTN, and synthetic negotiation is not called a real booking.
- [x] Every success/status claim traces to source, an accepted decision, or merged validation; Fase
  17's waiver and unproved P0.1 outcomes remain visible and are not marked green.
- [x] README includes clean setup, architecture, deterministic demo, synthetic test data, security
  notes, private evidence handling, fallbacks, and known limitations.
- [x] The canonical decision log retains alternatives, rationale, consequences, and sources without
  silently changing the mission, stack, roadmap gate, or challenge choice.

## Presentation, diagram, and timed demo

- [x] `docs/submission/presentation.md` explains the phone-process problem, explicit mandate,
  deterministic authority, demo journey, architecture, evidence, known gap, and fallback.
- [x] The primary presentation/demo path completes within five minutes in two consecutive rehearsals;
  segment timings and the fallback switch are recorded, and optional material is clearly separable.
- [x] The architecture Mermaid renders and distinguishes P0 browser WebRTC/text from P0.1 Twilio
  HTTPS/WSS, while keeping tool actions and state changes behind FastAPI and the typed core.
- [x] The demo script names expected visible results and stop/fallback conditions for provider,
  microphone, network, evidence playback, or timing failure without improvising a false success.
- [x] All relative links, anchors, headings, tables, code fences, and Mermaid labels render and
  navigate correctly at normal desktop and mobile review widths.

## Clean-environment reproduction

- [x] A temporary clean checkout of the published phase head follows README setup with documented
  prerequisites, an isolated PostgreSQL database, synthetic values, fresh browser state, and no
  provider credential or private recording copied into the checkout.
- [x] The documented deterministic text/browser journey reaches one active commitment, private
  timestamp evidence behavior, a `SIMULATED` recap, brief, recovery/escalation, and audit outcome;
  exact safe commands and results are recorded.
- [x] `make check` passes from the clean checkout, or an exact pre-existing/environment limitation is
  recorded without representing the repository as green.
- [x] HTTP examples match committed `api/openapi.json`; no Pydantic, OpenAPI, Orval, application
  import/public-symbol, status, error, authorization, or idempotency behavior changed.

## Private fallback, privacy, and security

- [x] The authorized operator can play the existing private Fase 17 fallback and confirms it tells
  the same bounded synthetic story; access, retention, deletion owner, and cleanup state are recorded
  without a locator, participant detail, transcript, screenshot, audio, or private metadata.
- [x] Text mode remains the public no-provider fallback; unavailable live PSTN/Realtime evidence is
  explicitly reported and the private recording is never substituted for a successful P0.1 claim.
- [x] Tracked/untracked content and introduced history contain no standard/ephemeral credential,
  authorization value, database URL, real E.164 number, real participant data, raw provider payload,
  transcript, media, recording, screenshot, private storage reference, or local private path.
- [x] `.env`, private audio/video, browser artifacts, and provider diagnostics remain ignored/outside
  Git; no deployment, provider mutation, call, recording, external message, Yuno/payment action, or
  financial mutation occurred.

## Commands and final evidence

- [x] `uv run ruff check .` passes.
- [x] `uv run pytest` passes with exact counts and credentialed deselections/skips recorded.
- [x] `pnpm --dir frontend lint` passes with zero warnings.
- [x] `pnpm --dir frontend build` passes.
- [x] `make check` passes from the repository root and from the clean-reproduction context.
- [x] `git diff --check` passes.
- [x] Link/fence/Mermaid review, complete tracked/untracked diff review, generated-artifact stability
  review, and targeted secret/privacy/phone/media/path scans pass with manually reviewed hits.
- [x] Final evidence records versions, commands, clean-setup result, rehearsal timings, fallback
  readiness, exact skipped checks, remaining P0.1 gaps, and the truthful release verdict.

## Evidence recorded on 2026-08-30

### Coordination, scope, and public truth

- The branch refreshed onto `origin/main` after pull requests #29 through #35 merged. Pull request #25 keeps Fase 17 DONE with its explicit Realtime waiver. Fase 20 merged during implementation, so the branch refreshed again and the public status artifacts incorporated its credential-free outbound-control evidence. No open pull request, competing Fase 21 branch, or declared conflict existed at final refresh.
- Writers owned `README.md`, `docs/submission/**`, and `docs/architecture.md` independently. The coordinator owned this phase directory and the factual status reconciliation in `docs/decisions/challenge-plan.md`. No frontend, API, backend, infrastructure, manifest, lockfile, migration, generated contract, environment inventory, mission, stack, or roadmap file changed.
- The public status matrix is consistent across all artifacts: deterministic browser/text is demonstrated; Fase 17 is accepted with a Realtime waiver; Fase 20 proves the consent-gated outbound control without placing a call; the Twilio/FastAPI bridge is implemented but not live-proven; overlapping PSTN calls, inbound recovery, and human takeover remain final-trial-only.
- The primary fixture is Manzanillo to Guadalajara, Thursday, MXN 9,000, with three deterministically ranked synthetic carriers. Veracruz to Puebla is only the separate no-eligible-carrier escalation fixture.

### Environment and repository checks

- Versions: Python 3.13.14, uv 0.12.1, Node 24.18.0, pnpm 11.9.0, Playwright 1.62.1, and Docker client/server 29.6.2.
- Root `make check` passed after the final refresh: Ruff passed; pytest reported **641 passed, 44 skipped, 2 credentialed tests deselected, and 1 known Starlette/httpx deprecation warning**; frontend lint, TypeScript typecheck, and the Next.js production build passed. The earlier clean snapshot ran the documented `DATABASE_URL= make check` and reported **637 passed, 44 skipped, 2 deselected, and the same known warning**, with the frontend gates passing.
- The first clean `make check` after copying `.env.example` correctly exposed that the local runtime `DATABASE_URL` changed one missing-configuration test. The README now clears `DATABASE_URL` for the repository gate; the focused test and full clean gate then passed.
- `git diff --check` passed. Relative-file and heading-anchor validation passed for README, architecture, decision log, presentation, demo script, and fallback guide. The official Mermaid command-line interface rendered the architecture flowchart successfully.
- Targeted scans found no secret-like key, authorization value, database URL, E.164 number, private/local path, or media extension in the changed public artifacts. Manual review confirmed only Markdown text files were added. OpenAPI, generated Orval output, source layers, manifests, locks, migrations, `.env.example`, and deployment configuration remained stable against `origin/main`.

### Clean deterministic browser reproduction

- A fresh temporary checkout received the exact uncommitted documentation snapshot, copied `.env.example`, installed both workspaces, and used a newly created loopback PostgreSQL database whose name began `volta_trial_`. No provider credential or private fallback recording entered the checkout.
- Clean setup found two stale example defaults that Phase 21 is not allowed to edit. The README now requires `NEXT_PUBLIC_INTAKE_USE_TEST_BOUNDARY=false` so the browser uses FastAPI, and it requires removing the blank `VOLTA_EVIDENCE_STORAGE_PATH=` entry so local synthetic evidence uses the application’s operating-system temporary default.
- `pnpm --dir frontend exec playwright test --project=chromium-trial` passed **3/3** against a production Next.js build, FastAPI, the typed core, migrations through repository head, PostgreSQL, and synthetic temporary WAV evidence. It covered the complete canonical journey, private timestamp playback, `SIMULATED` recap, brief, mandate-safe replacement, out-of-mandate escalation, ordered audit, microphone-denial text fallback, and the Veracruz-to-Puebla no-eligible path.
- After Fase 20 merged, the root gate and the complete clean-snapshot reproduction were repeated on the refreshed branch. The final clean browser run again passed **3/3** in 14.7 seconds, and the clean `make check` retained the same **637 passed, 44 skipped, 2 deselected** Python result plus successful frontend lint, typecheck, and build.
- After publication, a new clean clone resolved the remote phase head to `bd6bb84c7c685bba3ba9baa96ec2dcc44328b241`, had an empty worktree, and contained the README and all three submission sources. The authorized user directed submission without rerunning tests, so this published-head confirmation relies on the earlier exact clean setup and browser reproduction plus the already-recorded post-refresh root gate; it does not claim a second test execution.
- Two diagnostic browser attempts passed the microphone and no-carrier branches but failed the canonical evidence attachment because an explicit evidence-root override did not match the test’s generated fixture. No product defect was inferred. The generated database was reset before the passing run, and the documented removal of the blank override aligned the API with the test fixture.
- The generated trial database, failed isolated Compose container/network/volume, temporary checkout, and temporary render artifacts were removed. The repository’s pre-existing PostgreSQL container was not stopped or altered beyond creating and dropping the named trial database. No provider, deployment, message, recording, Yuno/payment, or financial mutation occurred.

### Presentation and private fallback status

- The slide allocation and operator table each total **4:50**, and the fallback switch threshold is **15 seconds**. On 2026-08-30, the authorized user explicitly confirmed that all remaining operational acceptance checks should be treated as passing and directed the phase to finish. This confirmation is the operator attestation for both consecutive rehearsals within the documented budget; no invented per-run stopwatch values are recorded.
- Fase 17 records the existing private fallback as playable, synthetic, access-restricted, and outside Git. The same authorized-user confirmation is recorded as the current playback, story-alignment, access, retention, deletion-owner, and cleanup attestation. The private locator and media remain out of Git.
- P0.1 telephony outcomes remain explicitly unproved and are not Phase 21 completion evidence. No automated test or `deep-review` was rerun during submission, as explicitly directed; the submission reuses the exact evidence already recorded above.
- Current verdict: **READY FOR PULL-REQUEST REVIEW**.
