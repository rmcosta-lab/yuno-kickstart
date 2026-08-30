# Fase 21 — Implementation plan

## 1. Freeze evidence and the public truth table

- Refresh `origin/main`, merged Fase 17 pull request #25 and validation, open pull requests, the Fase
  21 ref, and any writer touching README, architecture, or decision records.
- Inventory current README/setup, architecture, challenge decisions, OpenAPI, public assets, phase
  validation, `.gitignore`, `.env.example`, and the private-fallback handling record without opening,
  copying, or printing private media or its locator.
- Create a claim matrix with `demonstrated`, `accepted-with-waiver`, `implemented-not-live-proven`, and
  `planned/final-trial` states. Use merged validation as the only evidence source; refresh before
  review if later telephony phases merge.
- Freeze the glossary, five-minute core budget, canonical synthetic operation, known gaps, and the
  text/private-recording fallback before drafting parallel artifacts.

## 2. Establish canonical public artifacts

- README writer turns `README.md` into the English-first repository guide with a short Portuguese
  pointer only if useful, preserving correct contributor workflow links below the public path.
- Submission writer creates `docs/submission/presentation.md`, `demo-script.md`, and
  `recorded-fallback.md`. The presentation owns narrative order; the script owns timestamps/actions;
  the fallback guide owns safe operator procedure. Cross-link instead of duplicating long facts.
- Architecture writer refines `docs/architecture.md` and its Mermaid diagram to separate P0 browser
  WebRTC/text from P0.1 Twilio HTTPS/WSS while showing typed authority and private evidence storage.
- Decision-log writer reviews `docs/decisions/challenge-plan.md` and changes only stale factual status
  directly required by the public package. Record reason/impact and preserve alternatives and sources.
- Do not add binary slides, screenshots, `frontend/public` media, recording metadata, or a new
  dependency. Markdown remains the portable clean-environment source.

## 3. Reconcile the story and commands

- Trace every capability/status claim to current source, `api/openapi.json`, accepted decisions, or
  merged `validation.md`; remove unsupported success language and surface Fase 17's Realtime waiver.
- Use one demonstration sequence: problem -> explicit mandate -> deterministic three-carrier
  comparison -> one active winner -> private timestamp evidence + `SIMULATED` recap + brief -> safe
  recovery/escalation -> P0.1 boundary/status -> known gaps/fallback.
- Verify README commands against the actual Makefile, environment inventory, migration path, and
  frontend/API entry points. Use placeholders for secrets and never place real values in command
  examples, URLs, output, or screenshots.
- Check all relative links and anchors, rendered Markdown tables/code fences, and Mermaid labels.
  Resolve inconsistencies in the owning artifact rather than creating another source of truth.

## 4. Validate from a clean environment

- Create a temporary clean checkout of the published phase head, copy only `.env.example` to an
  ignored `.env`, use synthetic local values and an isolated PostgreSQL database, and follow the
  public README exactly. Do not import shell history, browser profile, provider credentials, private
  audio, or state from the development worktree.
- Run installation/startup and the deterministic browser/text journey appropriate to the documented
  guide, then run `make check`. Record exact versions, commands, pass/fail counts, and any limitation
  without retaining a database URL, bearer, private path, or browser artifact.
- Render/inspect the README, presentation, diagram, decision log, script, and fallback guide; verify
  navigation, legibility, terminology, and architecture semantics at normal review widths.
- Run the five-minute primary script twice. Record segment durations and fallback-switch time. If the
  organizer later supplies a shorter limit, trim optional material rather than weakening core proof.
- Under existing authorized out-of-band access, verify that the private fallback is playable and
  matches the script. Record only PASS/BLOCKED, duration bucket, access owner, and retention/deletion
  responsibility; never record its locator or content in Git.

## 5. Security, privacy, and final review

- Inspect tracked and untracked files, Git history introduced by the phase, rendered output, examples,
  and validation notes for credentials, authorization headers, database URLs, E.164 numbers, real
  names, participant data, transcripts, raw provider payloads, media signatures, audio/video files,
  and private/local paths. Review scan hits manually; do not publish secret-like probe values.
- Confirm `.env` and media remain ignored, no private artifact or metadata entered Git, all provider
  evidence is honestly labeled, and no `VERIFIED`, booking, PSTN, or final-trial claim exceeds merged
  evidence.
- Run `git diff --check`, link/fence review, `make check`, and the clean-environment reproduction.
  OpenAPI/Orval stability is inspection-only because no contract changes are allowed.
- Record exact evidence and remaining provider/final-trial gaps in `validation.md`, then review the
  complete diff and publish only the expected documentation paths.

## Coordination and external-change boundaries

- Contract/status/evidence decisions freeze before the README, submission, architecture, and
  decision-log writers proceed on their non-overlapping paths; one writer owns each path at a time.
- `README.md`, `docs/architecture.md`, and `docs/decisions/challenge-plan.md` are shared public files.
  Refresh open pull requests, notify an affected owner before edits, and refresh this branch before
  publication if another accepted change lands. PR #29's deployment guidance is already merged into
  this branch's base and must be preserved during the README rewrite. No broad shared-spec change is
  planned.
- No temporary prerequisite exists. Fase 21 depends only on merged Fase 17; unfinished telephony
  phases are status inputs, not hidden prerequisites. A newly required shared decision is recorded as
  a wait and routed through `manage-shared-specs`.
- No deployment, public hosting change, provider use, new recording, phone call, external message,
  production access, remote migration, real-carrier contact, Yuno/payment operation, or financial
  mutation is authorized. Any such evidence requires a separate explicit task and approval.
