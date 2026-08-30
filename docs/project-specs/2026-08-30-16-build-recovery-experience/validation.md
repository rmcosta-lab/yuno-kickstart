# Fase 16 — Validation

Record exact commands, environment, commit SHA, and browser evidence before review. Provider or
credentialed trials are not part of this phase.

## Playback backend and API

- [x] `uv run ruff check .` passes from the repository root.
- [x] `uv run pytest` passes, including focused evidence retrieval, storage failure, transaction
      lifetime, binary route, auth ordering, safe error, size/media, header, and redaction tests.
- [x] An authorized UUID fetch returns byte-identical bounded RIFF/WAVE content as `audio/wav` with
      `private, no-store`, `no-cache`, `nosniff`, request ID, and no filename/reference/path metadata.
- [x] Missing evidence/blob, invalid media/reference, oversize data, and unexpected storage failure
      map to the accepted safe status/schema without existence details, bytes, paths, or exception text.
- [x] Missing/unplayable evidence returns `404 RESOURCE_NOT_FOUND` with `Evidence audio is
unavailable.`; oversize evidence returns `413 EVIDENCE_AUDIO_TOO_LARGE` with `Evidence audio
exceeds the demo playback limit.`; both omit `resource_id`.
- [x] Storage retrieval occurs after the database unit of work is closed; API code performs no
      repository query and backend code imports no FastAPI/Pydantic type.
- [x] The 25 MiB rule is reported as a trusted-P0 response cap; tests do not claim the eager
      `retrieve -> bytes` port prevents read-time allocation above the cap.

## Contract generation

- [x] API contract tests pass after adding `commitment_id` to `CallBriefResponse`.
- [x] `make generate` updates `api/openapi.json` and `frontend/src/lib/api/generated/**` from source;
      the new stable operation ID is `get_evidence_audio` and its success content is binary
      `audio/wav`.
- [x] A clean second `make generate` produces no diff after the review corrections.
- [x] Generated files contain a typed authenticated Blob-returning client; no generated file or
      transport DTO was hand-edited or copied into frontend code.
- [x] `CommitmentEvidenceResponse` and nested operation/audit responses no longer expose
      `recording_reference`; a repository-wide search proves no current frontend behavior depended on
      the removed response field, while backend persistence and evidence-ingestion input retain it.
- [x] Focused coverage proves `voltaFetch` returns byte-preserving Blob data for `audio/*` success,
      still parses JSON success and typed `ApiErrorResponse`, and retains auth/request-ID behavior.

## Frontend behavior

- [x] `pnpm --dir frontend lint` passes with zero warnings after the review corrections.
- [x] `pnpm --dir frontend typecheck` passes in strict mode after the review corrections.
- [x] `pnpm --dir frontend build` passes after the review corrections.
- [x] `pnpm --dir frontend test:e2e` passes the corrected recovery experience and existing Chromium
      suites without committing the synthetic audio artifact.
- [x] The player loads an authorized Blob, seeks to `audio_start_ms / 1000` within normal browser
      media timing tolerance, exposes keyboard-operable controls, and revokes its Blob URL after
      replacement/unmount. Audio is fetched imperatively and no Blob remains in TanStack Query cache.
- [x] Evidence independently labels lifecycle (`CANDIDATE`/`SIMULATED`) and disposition
      (`ACTIVE`/`SUPERSEDED`); no achieved state is labeled `VERIFIED`.
- [x] The good simulation leaves exactly one active winner, retains a superseded commitment, and
      shows the returned notification; acknowledgement preserves the stored actor/timestamp.
- [x] The bad simulation preserves the commitment and shows an open escalation. Mandate replacement
      names that escalation, returns the incremented immutable version, and updates the view only after
      authoritative refetch.
- [x] Audit load-more combines all bounded artifact collections without duplicates, retains source
      labels, uses `(timestamp, artifact UUID, source kind)` tie-breaks, displays correlation only for
      artifacts that directly expose it, and never invents state or causal ordering.

## Browser, accessibility, and failure evidence

- [x] Playwright first completes the corrected canonical evidence/recovery/escalation/audit flow at desktop
      and approximately 390 px mobile width; screenshots contain synthetic data only.
- [x] Console and network inspection after the corrected flow shows no runtime error, failed unexpected
      request, authorization/reference/path leak, duplicate mutation, unrevoked Blob URL, or cached
      audio Blob.
- [x] A browser journey exercises evidence, both recovery outcomes, mandate replacement, and audit
      through the local FastAPI API against durable PostgreSQL state without intercepting application
      requests.
- [x] Loading, empty, denied, audio-unavailable, retryable failure, stale `409`, mutation-in-flight,
      pagination failure, and success states are reproducible and preserve the last authoritative view.
- [x] Keyboard navigation, visible focus, headings/forms/lists, audio controls, status announcements,
      touch targets, contrast, long-text wrapping, and non-color state cues pass review.
- [x] Refreshing or retrying never fabricates a recovery result, discards preserved form values, or
      changes a mutation's
      idempotency key unless the user starts a genuinely new logical action.

## Security and scope

- [x] No bearer token, `recording_reference`, filesystem path, raw audio, Blob URL, transcript,
      provider payload, real phone/name, secret, or private participant data appears in logs,
      user-visible text/URLs, persistent storage, history, screenshots, exceptions, or the Git diff.
      The transient in-memory `<audio src="blob:...">` is allowed only during playback and is revoked.
- [x] Audio remains outside Git and PostgreSQL binary columns; no public/static asset, signed URL,
      Range support, storage provider, migration, deployment, or production configuration was added.
- [x] OpenAI, Twilio, Yuno, payments, webhooks, RLS, CORS changes, live calls, and remote mutations are
      absent or explicitly reported as not applicable.
- [x] P0 tests prove existing bearer authentication and safe lookup behavior. They do not claim a
      per-evidence ownership check; generic `403` remains reserved for a future authority boundary.

## Final repository gate

- [x] `make check` passes after the review corrections.
- [x] `git diff --check` passes after the review corrections.
- [x] Final `git diff` review confirms only approved Fase 16 implementation, generated artifacts,
      tests, phase specs, roadmap clarification, and playback decision are present.
- [x] The Fase 16 pull-request body notifies the future Fases 17 and 20 of the additive playback
      contract and records command/browser evidence plus any skipped or credential-dependent check.

## Recorded evidence

- Worktree under validation: `phase/16-build-recovery-experience`; the exact publication SHA and PR
  URL are recorded in the pull request after the validated tree is committed.
- Deterministic generation: two successive
  `UV_CACHE_DIR=/private/tmp/yuno-phase16-uv-cache make generate` runs produced the same OpenAPI/Orval
  diff SHA-256, `6b8e863c6ff2de65ef37ae4cb55143f28c5f45de9bb60ac798e1dd31af89cb45`.
- Repository gate with isolated local PostgreSQL:
  `UV_CACHE_DIR=/private/tmp/yuno-phase16-uv-cache TEST_DATABASE_URL=<redacted-loopback-url> make check`
  passed with 516 Python tests, 2 credential/provider deselections, Ruff, frontend lint, strict
  typecheck, and the 13-page production build. The existing Starlette/httpx deprecation warning is
  unchanged.
- Real application composition:
  `TEST_DATABASE_URL=<redacted-loopback-url> uv run pytest api/tests/test_volta_text_postgres.py -q`
  passed. It resolves the evidence UUID through isolated PostgreSQL and the shared private filesystem
  storage, checks byte-identical WAV and response headers, removes the artifact, and checks the safe
  redacted `404`.
- Browser evidence: `PLAYWRIGHT_SKIP_WEB_SERVER=1 pnpm --dir frontend test:e2e` passed 6 Chromium
  tests against the production build outside the filesystem/
  MachPort sandbox. The focused recovery journey also passed independently after exercising desktop
  and 390 x 844 layouts, Blob seek/revocation, safe retry identity, authoritative refetch, validation,
  all eight audit sources, pagination, and the exact comparator. Audio was generated only in memory.
- A second real browser journey used the production Next.js build, the local FastAPI API, bearer
  authentication, migrated local PostgreSQL, and private filesystem evidence without intercepting
  application requests. It created a commitment, rendered its recap and brief, played its WAV from
  the 0.250-second offset, applied a mandate-safe replacement, exposed the unavailable-audio fallback,
  acknowledged the notification, escalated an out-of-mandate replacement, reproduced a stale `409`
  while preserving entered values, resolved the named escalation at immutable mandate v2, and rendered
  all eight audit sources. Browser console inspection returned no entries.
- The rejected-token refetch retained the last authoritative audit while showing the distinct
  authorization error; reconnecting restored the live query. The existing Playwright suite separately
  covers loading, empty, mutation-in-flight, retryable failure, pagination failure/retry/success,
  keyboard/focus behavior, long text, desktop, and 390 x 844 responsive presentation.
- The final post-correction gate
  `UV_CACHE_DIR=/private/tmp/yuno-phase16-finish-cache TEST_DATABASE_URL=<redacted-loopback-url> make check`
  passed with 516 Python tests, 2 credential/provider deselections, Ruff, frontend lint, strict
  typecheck, and the 13-page production build. A clean subsequent `make generate` completed without
  changing generated output, and `git diff --check` passed.
- The synthetic 1-second WAV remains outside Git under private temporary evidence storage for future
  local tests at the user's request. No provider credential, external call, deployment, payment,
  production access, remote migration, or remote application mutation was used.
- Post-review corrections include commitment-scoped recap/brief rendering, retained authoritative
  data after refetch failure, distinct authentication failures, preserved stale-conflict form state,
  associated field errors, a resolved-escalation summary, truthful winner fixtures, and reconciled
  Volta setup guidance. No new test case or new deep review was added or run.
