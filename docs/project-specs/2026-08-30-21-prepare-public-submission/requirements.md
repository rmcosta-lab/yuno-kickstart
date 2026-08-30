# Fase 21 — Prepare the public submission package

## Coordination and gate

- Priority: P1 submission reliability and polish; prerequisite for the final P0.1 trial.
- Branch: `phase/21-prepare-public-submission`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fase 17, DONE in merged pull request #25 with its recorded Realtime waiver visible.
- Conflicts with: none.
- Roadmap gate: the presentation, public repository guide, architecture diagram, decision log,
  timed demo script, and private recorded fallback tell one consistent story and work from a clean
  environment; privacy and secret scans confirm that no credential, real participant data, or
  private audio entered Git.

## Objective and audience

Give judges, reviewers, and a clean-environment operator one truthful, English-first public package
that explains Volta's drayage problem, bounded mandate, browser P0 proof, P0.1 telephony architecture,
evidence, limitations, and fallback. The terminal user-visible result is a repository whose guide can
be followed from a clean checkout and a five-minute primary presentation/demo script whose claims can
be traced to merged validation evidence.

The package must distinguish demonstrated behavior from planned or credential-gated behavior. At
phase start, the complete deterministic browser story is accepted with Fase 17's recorded qualitative
Realtime/tool-call waiver; Twilio media code is merged, but three overlapping outbound calls, inbound
recovery, and live human takeover remain final-trial outcomes and must not be presented as completed.

## Included scope

- Make `README.md` the concise public repository guide: problem and value, truthful capability/status
  summary, prerequisites, clean setup, deterministic demo steps and synthetic data, architecture,
  validation, security/privacy, fallbacks, and known limitations.
- Add `docs/submission/presentation.md` as the canonical slide-by-slide English presentation source,
  with speaker cues, evidence references, and a five-minute core narrative that can lose optional
  detail without losing the proof.
- Add `docs/submission/demo-script.md` with timestamped operator actions, expected visible outcomes,
  preflight, branch points for live browser/PSTN availability, and explicit transitions to the
  private fallback.
- Add `docs/submission/recorded-fallback.md` with safe reproduction, access, retention, deletion, and
  playback-check instructions. It records no private path, object reference, participant detail,
  transcript, screenshot, audio, or credential.
- Refine `docs/architecture.md` around one Mermaid diagram that visibly separates the P0 browser
  WebRTC/text harness from the P0.1 Twilio HTTPS/WSS media bridge while preserving FastAPI and
  plain-Python authority boundaries.
- Review and, only where needed for final factual consistency, update the canonical decision log in
  `docs/decisions/challenge-plan.md`; retain alternatives, consequences, accepted gaps, and sources.
- Cross-link all six public artifacts and reconcile terminology against the mission, stack, roadmap,
  committed OpenAPI, merged phase validation, and current repository behavior.
- Rehearse the package from a clean temporary checkout with synthetic data, an isolated local
  PostgreSQL database, and no provider credential; run the private fallback only under its existing
  authorized access and keep it outside Git.

## Excluded scope

- Product code, `frontend/public/**`, screenshots, generated API files, Pydantic contracts, backend
  symbols, migrations, manifests/lockfiles, `.env.example`, fixtures, tests, deployment, or hosting.
- Creating or committing a slide binary, video, recording, audio sample, transcript, real phone
  number, participant identity, provider payload, authorization value, or private storage reference.
- A new Twilio/OpenAI call, public endpoint, provider-account change, production access, remote
  migration, real-carrier contact, external message, Yuno/payment action, or financial mutation.
- Claiming `VERIFIED` recap delivery, a real booking, production readiness, completed P0.1 trial
  outcomes, or a provider result not supported by merged validation evidence.
- Reopening architecture, stack, roadmap, challenge choice, or other broad shared decisions. A newly
  required decision is routed through `manage-shared-specs` rather than hidden in submission prose.

## Acceptance criteria

1. The README's clean setup works without a provider key and reaches the deterministic text/browser
   story using only documented prerequisites, synthetic fixtures, and server-owned state.
2. Presentation, README, architecture, decision log, demo script, and fallback instructions use one
   glossary and status matrix: `CANDIDATE`/`SIMULATED` are not `VERIFIED`, browser is not PSTN,
   synthetic carriers are not real bookings, and planned P0.1 evidence is not a completed trial.
3. The presentation and demo script fit a five-minute core run in two consecutive timed rehearsals;
   optional architecture/questions material is separately labeled and the fallback branch does not
   require improvisation.
4. The architecture diagram renders and shows browser WebRTC, generated HTTPS/JSON calls, FastAPI
   provider ingress, the typed core, PostgreSQL, private audio storage, OpenAI Realtime, Twilio Media
   Streams, and where human takeover belongs, without exposing deployment secrets or implying that
   providers own mandate or winner decisions.
5. Every material claim links to repository behavior, an accepted decision, or merged validation;
   Fase 17's waiver and any unproved telephony outcome remain prominent and use no green/pass label.
6. The private fallback can be located and played by the authorized operator using out-of-band access,
   starts cleanly, tells the same bounded story, and has a named retention/deletion owner without any
   private locator or media entering the repository.
7. Relative links, headings, code fences, Mermaid syntax, and commands are reviewed; `make check`,
   `git diff --check`, clean/untracked review, and targeted secret, credential, phone, participant,
   transcript, media, and private-path scans pass or an exact honest limitation is recorded.

## Contract gates

### HTTP contract

No HTTP contract changes. Public docs may describe existing `/v1` behavior only after checking the
committed `api/openapi.json`; they must not publish private headers or imply that a browser callback
changes a commitment. Requests, responses, success statuses, authorization/idempotency requirements,
and safe errors remain exactly as implemented. Any mismatch is documented as a limitation and routed
to the owning future phase instead of changing Pydantic, OpenAPI, or Orval here.

### Application contract

No import path, public symbol, construction rule, typed input/output, or exception changes. The
package describes FastAPI as a thin consumer of existing typed `yuno_backend.volta` services and the
plain-Python core as the sole operational authority. A discovered source/document mismatch is fixed
in prose when the source is authoritative; a code defect is excluded and handed to its owning phase.

### Browser/provider handoff and terminal result

The P0 browser obtains a scoped Realtime credential from FastAPI, connects to OpenAI over WebRTC, and
returns tool requests through typed `/v1` routes; text fallback exercises the same deterministic core.
The P0.1 diagram separately shows Twilio HTTPS/WSS ingress through FastAPI. Neither browser nor Twilio
provider events grant authority. The terminal public result is an auditable synthetic operation with
exactly one active commitment, a recap explicitly labeled `SIMULATED`, a structured brief, playable
private timestamp evidence, recovery/escalation history, and a truthful status for every unavailable
live channel.

## Risks, assumptions, and fallback

- Assumption: the merged Fase 17 deterministic evidence is the minimum factual baseline. Later phase
  evidence may be referenced only after it merges and the submission branch refreshes normally.
- Risk: parallel P0.1 work makes the package stale. Mitigation: keep a small evidence/status table,
  cite merged phase validation, and perform a final refresh/reconciliation before review without
  inventing results.
- Risk: the current README and architecture retain bootstrap/Yuno language. Mitigation: preserve
  useful setup material while making Volta and the accepted no-Yuno decision the public narrative.
- Risk: the private recording or terminal output leaks a credential, phone number, path, participant,
  or audio. Mitigation: use only bounded outcomes in Git, scan tracked and untracked files, and keep
  location/access handling out of band.
- Fallback: when PSTN, Realtime, microphone, or network access is unavailable, run deterministic text
  mode and then the private Fase 17 recording. The script calls the fallback what it is and reports
  the unavailable live evidence; it never substitutes the recording for a successful P0.1 claim.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-21-prepare-public-submission/**` | Phase coordinator `rmcosta-lab` | Sole writer for plan, requirements, validation, and safe evidence. |
| `README.md` | Fase 21 public-guide writer | Public entry point; retain working development and coordination links without exposing internal/private data. |
| `docs/submission/**` | Fase 21 submission writer | Own presentation source, timed script, and safe fallback instructions; Markdown/text only. |
| `docs/architecture.md` | Fase 21 architecture writer | One canonical P0/P0.1 diagram and explanatory boundary text. |
| `docs/decisions/challenge-plan.md` | Fase 21 decision-log writer | Factual reconciliation only; preserve accepted alternatives/consequences and coordinate before editing. |
| Private fallback recording and its locator | No Git writer; authorized operator owns access/retention/deletion | Never copy, stage, name, or reveal the artifact/path in Git or review evidence. |
| `frontend/**`, `api/**`, `backend/**`, `infra/**`, generated files, manifests/locks, migrations, `.env.example`, shared mission/stack/roadmap, other phase specs | No Fase 21 writer | Read-only evidence sources; route a defect or shared decision to its owner. |

Pull request #29 (`ops/hackathon-deploy`) overlapped `README.md` during planning. Its owner was
notified, it merged before the claim, and this branch refreshed onto that accepted deployment
guidance. Fase 21 will preserve it and keep one writer on README during reconciliation. Refresh open
pull requests and notify any newly affected owner before editing another public shared file.
