# Fase 21 — Validation

Keep every criterion unchecked until its exact safe evidence is recorded. Provider/final-trial facts
are not inferred from implemented code, and private fallback evidence never includes its locator.

## Coordination and artifact scope

- [ ] Fase 17 remains DONE with pull request #25 and its Realtime waiver visible; Fase 21 has no
  competing branch/PR or newly active bidirectional conflict before publication.
- [ ] The final diff contains only the phase spec, README, `docs/submission/**`, `docs/architecture.md`,
  and any directly required factual decision-log reconciliation.
- [ ] One-writer ownership and open pull requests touching shared public docs are refreshed before
  edits and publication; merged PR #29's README deployment guidance is preserved, and no unrecorded
  shared decision or temporary prerequisite appeared.
- [ ] Code, `frontend/public`, generated artifacts, contracts, migrations, manifests/locks,
  `.env.example`, mission, stack, roadmap, and other phase specs remain unchanged.

## Consistent public story

- [ ] Presentation, README, architecture, decision log, timed script, and fallback guide use the same
  problem, user, canonical operation, mandate, evidence lifecycle, architecture, and known gaps.
- [ ] `CANDIDATE`, `SIMULATED`, `VERIFIED`, `ACTIVE`, and `SUPERSEDED` are used correctly; browser
  audio is not called PSTN, and synthetic negotiation is not called a real booking.
- [ ] Every success/status claim traces to source, an accepted decision, or merged validation; Fase
  17's waiver and unproved P0.1 outcomes remain visible and are not marked green.
- [ ] README includes clean setup, architecture, deterministic demo, synthetic test data, security
  notes, private evidence handling, fallbacks, and known limitations.
- [ ] The canonical decision log retains alternatives, rationale, consequences, and sources without
  silently changing the mission, stack, roadmap gate, or challenge choice.

## Presentation, diagram, and timed demo

- [ ] `docs/submission/presentation.md` explains the phone-process problem, explicit mandate,
  deterministic authority, demo journey, architecture, evidence, known gap, and fallback.
- [ ] The primary presentation/demo path completes within five minutes in two consecutive rehearsals;
  segment timings and the fallback switch are recorded, and optional material is clearly separable.
- [ ] The architecture Mermaid renders and distinguishes P0 browser WebRTC/text from P0.1 Twilio
  HTTPS/WSS, while keeping tool actions and state changes behind FastAPI and the typed core.
- [ ] The demo script names expected visible results and stop/fallback conditions for provider,
  microphone, network, evidence playback, or timing failure without improvising a false success.
- [ ] All relative links, anchors, headings, tables, code fences, and Mermaid labels render and
  navigate correctly at normal desktop and mobile review widths.

## Clean-environment reproduction

- [ ] A temporary clean checkout of the published phase head follows README setup with documented
  prerequisites, an isolated PostgreSQL database, synthetic values, fresh browser state, and no
  provider credential or private recording copied into the checkout.
- [ ] The documented deterministic text/browser journey reaches one active commitment, private
  timestamp evidence behavior, a `SIMULATED` recap, brief, recovery/escalation, and audit outcome;
  exact safe commands and results are recorded.
- [ ] `make check` passes from the clean checkout, or an exact pre-existing/environment limitation is
  recorded without representing the repository as green.
- [ ] HTTP examples match committed `api/openapi.json`; no Pydantic, OpenAPI, Orval, application
  import/public-symbol, status, error, authorization, or idempotency behavior changed.

## Private fallback, privacy, and security

- [ ] The authorized operator can play the existing private Fase 17 fallback and confirms it tells
  the same bounded synthetic story; access, retention, deletion owner, and cleanup state are recorded
  without a locator, participant detail, transcript, screenshot, audio, or private metadata.
- [ ] Text mode remains the public no-provider fallback; unavailable live PSTN/Realtime evidence is
  explicitly reported and the private recording is never substituted for a successful P0.1 claim.
- [ ] Tracked/untracked content and introduced history contain no standard/ephemeral credential,
  authorization value, database URL, real E.164 number, real participant data, raw provider payload,
  transcript, media, recording, screenshot, private storage reference, or local private path.
- [ ] `.env`, private audio/video, browser artifacts, and provider diagnostics remain ignored/outside
  Git; no deployment, provider mutation, call, recording, external message, Yuno/payment action, or
  financial mutation occurred.

## Commands and final evidence

- [ ] `uv run ruff check .` passes.
- [ ] `uv run pytest` passes with exact counts and credentialed deselections/skips recorded.
- [ ] `pnpm --dir frontend lint` passes with zero warnings.
- [ ] `pnpm --dir frontend build` passes.
- [ ] `make check` passes from the repository root and from the clean-reproduction context.
- [ ] `git diff --check` passes.
- [ ] Link/fence/Mermaid review, complete tracked/untracked diff review, generated-artifact stability
  review, and targeted secret/privacy/phone/media/path scans pass with manually reviewed hits.
- [ ] Final evidence records versions, commands, clean-setup result, rehearsal timings, fallback
  readiness, exact skipped checks, remaining P0.1 gaps, and the truthful release verdict.
