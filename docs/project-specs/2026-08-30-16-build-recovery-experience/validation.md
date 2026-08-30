# Fase 16 — Validation

Record exact commands, environment, commit SHA, and browser evidence before review. Provider or
credentialed trials are not part of this phase.

## Playback backend and API

- [ ] `uv run ruff check .` passes from the repository root.
- [ ] `uv run pytest` passes, including focused evidence retrieval, storage failure, transaction
      lifetime, binary route, auth ordering, safe error, size/media, header, and redaction tests.
- [ ] An authorized UUID fetch returns byte-identical bounded RIFF/WAVE content as `audio/wav` with
      `private, no-store`, `no-cache`, `nosniff`, request ID, and no filename/reference/path metadata.
- [ ] Missing evidence/blob, invalid media/reference, oversize data, and unexpected storage failure
      map to the accepted safe status/schema without existence details, bytes, paths, or exception text.
- [ ] Missing/unplayable evidence returns `404 RESOURCE_NOT_FOUND` with `Evidence audio is
unavailable.`; oversize evidence returns `413 EVIDENCE_AUDIO_TOO_LARGE` with `Evidence audio
exceeds the demo playback limit.`; both omit `resource_id`.
- [ ] Storage retrieval occurs after the database unit of work is closed; API code performs no
      repository query and backend code imports no FastAPI/Pydantic type.
- [ ] The 25 MiB rule is reported as a trusted-P0 response cap; tests do not claim the eager
      `retrieve -> bytes` port prevents read-time allocation above the cap.

## Contract generation

- [ ] API contract tests pass before generation.
- [ ] `make generate` updates `api/openapi.json` and `frontend/src/lib/api/generated/**` from source;
      the new stable operation ID is `get_evidence_audio` and its success content is binary
      `audio/wav`.
- [ ] A clean second `make generate` produces no diff.
- [ ] Generated files contain a typed authenticated Blob-returning client; no generated file or
      transport DTO was hand-edited or copied into frontend code.
- [ ] `CommitmentEvidenceResponse` and nested operation/audit responses no longer expose
      `recording_reference`; a repository-wide search proves no current frontend behavior depended on
      the removed response field, while backend persistence and evidence-ingestion input retain it.
- [ ] Focused coverage proves `voltaFetch` returns byte-preserving Blob data for `audio/*` success,
      still parses JSON success and typed `ApiErrorResponse`, and retains auth/request-ID behavior.

## Frontend behavior

- [ ] `pnpm --dir frontend lint` passes with zero warnings.
- [ ] `pnpm --dir frontend typecheck` passes in strict mode.
- [ ] `pnpm --dir frontend build` passes.
- [ ] `pnpm --dir frontend test:e2e` passes the focused recovery experience and existing Chromium
      suites without committing the synthetic audio artifact.
- [ ] The player loads an authorized Blob, seeks to `audio_start_ms / 1000` within normal browser
      media timing tolerance, exposes keyboard-operable controls, and revokes its Blob URL after
      replacement/unmount. Audio is fetched imperatively and no Blob remains in TanStack Query cache.
- [ ] Evidence independently labels lifecycle (`CANDIDATE`/`SIMULATED`) and disposition
      (`ACTIVE`/`SUPERSEDED`); no achieved state is labeled `VERIFIED`.
- [ ] The good simulation leaves exactly one active winner, retains a superseded commitment, and
      shows the returned notification; acknowledgement preserves the stored actor/timestamp.
- [ ] The bad simulation preserves the commitment and shows an open escalation. Mandate replacement
      names that escalation, returns the incremented immutable version, and updates the view only after
      authoritative refetch.
- [ ] Audit load-more combines all bounded artifact collections without duplicates, retains source
      labels, uses `(timestamp, artifact UUID, source kind)` tie-breaks, displays correlation only for
      artifacts that directly expose it, and never invents state or causal ordering.

## Browser, accessibility, and failure evidence

- [ ] Playwright first completes the canonical evidence/recovery/escalation/audit flow at desktop
      and approximately 390 px mobile width; screenshots contain synthetic data only.
- [ ] Console and network inspection after the flow shows no runtime error, failed unexpected
      request, authorization/reference/path leak, duplicate mutation, unrevoked Blob URL, or cached
      audio Blob.
- [ ] Loading, empty, denied, audio-unavailable, retryable failure, stale `409`, mutation-in-flight,
      pagination failure, and success states are reproducible and preserve the last authoritative view.
- [ ] Keyboard navigation, visible focus, headings/forms/lists, audio controls, status announcements,
      touch targets, contrast, long-text wrapping, and non-color state cues pass review.
- [ ] Refreshing or retrying never fabricates a recovery result and never changes a mutation's
      idempotency key unless the user starts a genuinely new logical action.

## Security and scope

- [ ] No bearer token, `recording_reference`, filesystem path, raw audio, Blob URL, transcript,
      provider payload, real phone/name, secret, or private participant data appears in logs,
      user-visible text/URLs, persistent storage, history, screenshots, exceptions, or the Git diff.
      The transient in-memory `<audio src="blob:...">` is allowed only during playback and is revoked.
- [ ] Audio remains outside Git and PostgreSQL binary columns; no public/static asset, signed URL,
      Range support, storage provider, migration, deployment, or production configuration was added.
- [ ] OpenAI, Twilio, Yuno, payments, webhooks, RLS, CORS changes, live calls, and remote mutations are
      absent or explicitly reported as not applicable.
- [ ] P0 tests prove existing bearer authentication and safe lookup behavior. They do not claim a
      per-evidence ownership check; generic `403` remains reserved for a future authority boundary.

## Final repository gate

- [ ] `make check` passes after generation and focused iteration.
- [ ] `git diff --check` passes.
- [ ] Final `git diff` review confirms only approved Fase 16 implementation, generated artifacts,
      tests, phase specs, roadmap clarification, and playback decision are present.
- [ ] The Fase 16 pull-request body notifies the future Fases 17 and 20 of the additive playback
      contract and records command/browser evidence plus any skipped or credential-dependent check.
