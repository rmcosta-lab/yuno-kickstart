# Fase 14 — Validation

## Backend quality and tests

- [ ] `uv run ruff check .` (from `backend/`)
- [ ] `uv run pytest` (from `backend/`), including new `tests/volta/evidence/**` and `tests/volta/recovery/**`
- [ ] Focused PostgreSQL-backed integration tests for evidence and recovery repositories (isolated, separately marked as in Fase 06/08)
- [ ] `make python-check` (repository root)

## Domain and application behavior

- [ ] Evidence attach is idempotent for a `CANDIDATE`/`ACTIVE` commitment; a second call returns the stored record without a new row
- [ ] Evidence attach to a missing or `SUPERSEDED` commitment fails with a safe typed error
- [ ] Generated `CallBrief` and `Recap` round-trip from PostgreSQL with identical fields; `Recap.disclosure_state` is always `SIMULATED`
- [ ] Mandate-safe recovery: exactly one new active commitment, prior commitment `SUPERSEDED` with timestamp and link, one notification recorded, full history preserved
- [ ] Out-of-mandate recovery: no commitment mutation, one `PostContactEscalation` created, subsequent recovery attempts rejected with `OperationBlockedByEscalation`
- [ ] Escalation resumes only when `ResumeAfterEscalationService` receives a strictly greater mandate version than the one recorded at escalation time; resuming performs no commitment mutation by itself
- [ ] Stale expected operation version raises `StaleOperationVersion` and writes nothing, for both evidence and recovery mutations
- [ ] Concurrent/injected-failure attempts at replacement cannot produce two active commitments (mirrors Fase 08's winner-transition tests)

## Migration and persistence

- [ ] Alembic `upgrade head`, `downgrade -1`, `upgrade head` succeed against the local PostgreSQL instance
- [ ] Constraints reject: a second evidence row for the same commitment, a second unresolved `PostContactEscalation` for the same operation, and broken operation/commitment foreign keys
- [ ] Rollback on a failed mutation leaves the prior durable state unchanged

## Audit and security

- [ ] New audit event types (`EVIDENCE_RECORDED`, `BRIEF_GENERATED`, `RECAP_GENERATED`, `RECOVERY_REPLACEMENT_APPLIED`, `POST_CONTACT_ESCALATED`, `ESCALATION_RESUMED`) are allowlisted with bounded, safe metadata only
- [ ] No raw recording path, transcript fragment, contact detail, or provider payload appears in audit metadata, logs, exceptions, or test fixtures
- [ ] Diff review confirms no secret, personal data, unrelated change, or API/generated-file change

## Explicitly not applicable to this phase

- OpenAPI/Orval generation (no HTTP contract change)
- Browser/frontend smoke tests (no frontend change)
- Yuno sandbox/webhook checks (Yuno is not used by this project)
- Twilio/Realtime credentialed checks (out of scope for this phase)

## Final gate check

- [ ] `git diff --check`
- [ ] Roadmap gate reproduced: backend-only tests persist provider-neutral call sessions, playable recording references with `audio_start_ms`, item and event identifiers, briefs, and recaps labeled `SIMULATED`; one mandate-safe renegotiation/replacement with atomic winner transition and notification; one out-of-mandate escalation that resumes only after a new immutable mandate version
