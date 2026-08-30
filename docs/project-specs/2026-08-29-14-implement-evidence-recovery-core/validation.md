# Fase 14 — Validation

## Backend quality and tests

- [x] `uv run ruff check .` (from `backend/`) — all checks passed
- [x] `uv run pytest` (from `backend/`), including new `tests/volta/evidence/**` and `tests/volta/recovery/**` — 157 passed, 23 skipped, 1 deselected, non-Postgres run; Postgres-gated tests skip cleanly without `TEST_DATABASE_URL`
- [x] Focused PostgreSQL-backed integration tests for evidence and recovery repositories (isolated, separately marked as in Fase 06/08) — verified independently against a local `docker compose up -d postgres` instance with `TEST_DATABASE_URL` set: `uv run pytest tests/volta -q` → 172 passed, 1 deselected, container removed afterward
- [x] `make python-check` (repository root) — ruff clean, 277 passed, 23 skipped, 1 deselected (pre-existing credentialed OpenAI test)

## Domain and application behavior

- [x] Evidence attach is idempotent for a `CANDIDATE`/`ACTIVE` commitment; a second call returns the stored record without a new row
- [x] Evidence attach to a missing or `SUPERSEDED` commitment fails with a safe typed error
- [x] Generated `CallBrief` and `Recap` round-trip from PostgreSQL with identical fields; `Recap.disclosure_state` is always `SIMULATED`
- [x] Mandate-safe recovery: exactly one new active commitment, prior commitment `SUPERSEDED` with timestamp and link, one notification recorded, full history preserved
- [x] Out-of-mandate recovery: no commitment mutation, one `PostContactEscalation` created, subsequent recovery attempts rejected with `OperationBlockedByEscalation`
- [x] Escalation resumes only when `ResumeAfterEscalationService` receives a strictly greater mandate version than the one recorded at escalation time; resuming performs no commitment mutation by itself
- [x] Stale expected operation version raises `StaleOperationVersion` and writes nothing, for both evidence and recovery mutations
- [x] Concurrent/injected-failure attempts at replacement cannot produce two active commitments (mirrors Fase 08's winner-transition tests) — added `test_concurrent_recovery_replacement_attempts_leave_exactly_one_active_winner` in `backend/tests/volta/persistence/test_recovery_evidence_repositories.py`, racing two `SimulateInboundRecoveryService.simulate()` calls via `asyncio.gather`; exactly one wins, the other raises `StaleOperationVersion`, and exactly one active commitment survives. `SimulateInboundRecoveryService._replace` was also reordered to acquire `lock_winner_scope` and re-fetch/verify `get_active` before superseding, matching Fase 08's `CreateCommitmentService.create` pattern exactly (deep-review finding, `backend/src/yuno_backend/volta/recovery/services.py`)

## Migration and persistence

- [x] Alembic `upgrade head`, `downgrade -1`, `upgrade head` succeed against the local PostgreSQL instance (verified via `tests/volta/persistence/test_migrations.py`, including a downgrade -1 assertion and full downgrade-to-base/upgrade-to-head cycle)
- [x] Constraints reject: a second evidence row for the same commitment, a second unresolved `PostContactEscalation` for the same operation, and broken operation/commitment foreign keys
- [x] Rollback on a failed mutation leaves the prior durable state unchanged

## Audit and security

- [x] New audit event types (`EVIDENCE_RECORDED`, `BRIEF_GENERATED`, `RECAP_GENERATED`, `RECOVERY_REPLACEMENT_APPLIED`, `POST_CONTACT_ESCALATED`, `ESCALATION_RESUMED`) are allowlisted with bounded, safe metadata only — added to `audit/models.py`'s `_METADATA_SCHEMA_BY_EVENT` (all `{}`) and to the Postgres `ck_volta_audit_events_metadata_schema` check constraint in the Fase 14 migration
- [x] No raw recording path, transcript fragment, contact detail, or provider payload appears in audit metadata, logs, exceptions, or test fixtures — confirmed by diff review and grep
- [x] Diff review confirms no secret, personal data, unrelated change, or API/generated-file change — diff is scoped entirely to `backend/**`; no `api/**`/`frontend/**` files touched; no FastAPI/Pydantic imports in `evidence/**` or `recovery/**` (verified via grep)

## Explicitly not applicable to this phase

- OpenAPI/Orval generation (no HTTP contract change)
- Browser/frontend smoke tests (no frontend change)
- Yuno sandbox/webhook checks (Yuno is not used by this project)
- Twilio/Realtime credentialed checks (out of scope for this phase)

## Final gate check

- [x] `git diff --check` — exit 0, no whitespace errors
- [x] Roadmap gate reproduced: backend-only tests persist provider-neutral call sessions, playable recording references with `audio_start_ms`, item and event identifiers, briefs, and recaps labeled `SIMULATED`; one mandate-safe renegotiation/replacement with atomic winner transition and notification; one out-of-mandate escalation that resumes only after a new immutable mandate version — all reproduced under `tests/volta/evidence/**`, `tests/volta/recovery/**`, and `tests/volta/persistence/test_recovery_evidence_repositories.py`

## Coordinator notes (open items, not blockers)

- No new dependency was added to `pyproject.toml`/`uv.lock`; the filesystem evidence adapter uses only the Python standard library.
- `recovery/errors.py` adds `EscalationNotFound`, one error beyond the six explicitly named in requirements.md's application contract table, needed so `ResumeAfterEscalationService` fails safely on an unknown `escalation_id`. Minimal, safe, and consistent with the existing exception style — flagged here for visibility rather than as a deviation requiring rework.
- `SimulateInboundRecoveryService`'s mandate-safe replacement path synthesizes a new `Quote` from the proposed terms and reuses Fase 08's existing commitment/quote FK chain rather than adding new schema — reduces persistence surface area at the cost of one indirection future readers should be aware of.
- `Commitment.evidence_id` on recovery-created commitments remains an opaque, unpersisted placeholder UUID (same convention as Fase 08), now documented with an inline comment in `recovery/services.py` pointing readers to `AgreementEvidence.commitment_id` as the real, FK'd evidence link.

## Deep review (2026-08-29)

A three-lens deep review (correctness/architecture, security/data, product/scope) ran against the uncommitted Fase 14 diff. Security/data was clean. Two issues were confirmed and fixed:

1. **Concurrency coverage gap** (medium): no Postgres-backed concurrent-replacement test existed for recovery, unlike Fase 08's negotiation suite, despite this checklist claiming equivalent coverage. Fixed — see the "Concurrent/injected-failure attempts" line above. `SimulateInboundRecoveryService._replace` was also reordered to lock-then-verify the active commitment (previously safe only via the outer operation-row lock, now also matching Fase 08's explicit pattern).
2. **Validation record accuracy** (medium): this file previously misstated `uv run pytest`/`make python-check` pass counts (claimed 299 passed; actual was 157 passed/22 skipped from `backend/` and 277 passed/22 skipped from repo root). Corrected above.

One low finding (undocumented `evidence_id` placeholder) was fixed with an inline comment; see the coordinator note above. Full re-verification after fixes: `uv run ruff check .` clean, `make python-check` → 277 passed/23 skipped/1 deselected, `git diff --check` clean, and a fresh `docker compose up -d postgres` run of `tests/volta` → 172 passed (including the new concurrency test), container removed afterward.

## Submission re-verification (2026-08-29)

Before opening the pull request, every gate above was rerun from a clean shell against the uncommitted diff: `uv run ruff check .` clean; `uv run pytest` (backend) → 157 passed, 23 skipped, 1 deselected; `make python-check` (root) → 277 passed, 23 skipped, 1 deselected; `docker compose up -d postgres` + `TEST_DATABASE_URL` `uv run pytest tests/volta` → 172 passed, 1 deselected (including `tests/volta/persistence/test_migrations.py`'s upgrade/downgrade/re-upgrade cycle), container removed afterward; `git diff --check` clean; grep confirmed no FastAPI/Pydantic import in `evidence/**`/`recovery/**` and no raw recording path, transcript, or secret in the diff; `git status` confirmed no `api/**`/`frontend/**` change. All results match the counts already recorded above.
