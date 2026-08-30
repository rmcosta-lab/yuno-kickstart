# Fase 14 — Plan

## Task groups (dependency order)

1. **Evidence domain values** — `volta/evidence/models.py`, `volta/evidence/errors.py`. Frozen `AgreementEvidence`, `CallBrief`, `Recap`, `RecapDisclosureState`. Unit tests for construction and validation only, no persistence.
2. **Recovery domain values** — `volta/recovery/models.py`, `volta/recovery/commands.py`, `volta/recovery/errors.py`. Frozen `RecoveryAttempt`, `RecoveryOutcome`, `PostContactEscalation`, `Notification`. Depends on group 1 only for shared error/base patterns, not on evidence models.
3. **Ports** — `volta/evidence/repositories.py` (`EvidenceRepository`, `BriefRepository`, `RecapRepository`, `EvidenceStorage`) and `volta/recovery/repositories.py` (`RecoveryAttemptRepository`, `PostContactEscalationRepository`, `NotificationRepository`), plus the `OperationUnitOfWork` protocol extension. Contract decision point: confirm exact repository method signatures before parallel service/persistence work starts.
4. **Filesystem evidence-storage adapter** — a `volta/evidence/storage/filesystem.py` (or similar) implementing `EvidenceStorage` for local development, writing outside Git and outside PostgreSQL binary columns, with documented access/deletion behavior. In-memory fake for unit tests.
5. **Application services** — `RecordEvidenceService`, `GenerateBriefService`, `GenerateRecapService` in `volta/evidence/services.py`; `SimulateInboundRecoveryService`, `ResumeAfterEscalationService` in `volta/recovery/services.py`. Reuse Fase 05 `MandatePolicy` and the Fase 08 atomic winner-transition pattern.
6. **In-memory repository fakes and deterministic unit tests** for all services: idempotent evidence attach, brief/recap generation, mandate-safe replacement (atomic supersede + notification), out-of-mandate escalation (block, then resume with a strictly greater mandate version), stale-version rejection.
7. **One additive Alembic migration** for `volta_agreement_evidence`, `volta_call_briefs`, `volta_recaps`, `volta_recovery_attempts`, `volta_post_contact_escalations`, `volta_notifications` (exact names finalized here), extending `backend/migrations/versions/`. Include upgrade/downgrade and constraints (one evidence row per commitment, at most one unresolved escalation per operation, FKs to operation/commitment).
8. **SQLAlchemy mappers and repositories** in `volta/persistence/tables.py`, `mappers.py`, `repositories.py`; extend `SqlAlchemyOperationUnitOfWork` with the new repositories, following the exact pattern used for Fase 08's negotiation repositories.
9. **Audit event wiring** — add allowlisted metadata schemas to `audit/models.py`'s `_METADATA_SCHEMA_BY_EVENT` for `EVIDENCE_RECORDED`, `BRIEF_GENERATED`, `RECAP_GENERATED`, `RECOVERY_REPLACEMENT_APPLIED`, `POST_CONTACT_ESCALATED`, `ESCALATION_RESUMED`; emit events from the application services inside the same transaction as the mutation.
10. **Isolated PostgreSQL integration tests** — round trips, migration upgrade/downgrade/re-upgrade, constraint violations, concurrent replacement attempts, rollback preserving prior state.
11. **Final checks** — `uv run ruff check .`, `uv run pytest`, `make python-check`, `git diff --check`, diff review for secrets/scope.

## Ownership and workstreams

- Single backend writer for this phase (no parallel frontend/API workstream authorized). Task groups 1–2 and 3–4 can proceed in parallel internally since they touch disjoint new files; groups 5+ are sequential because services depend on finalized ports.
- No shared stack, roadmap, or manifest change is anticipated. If a new dependency (e.g. for filesystem path handling) seems needed, treat it as a coordinated decision rather than adding it silently.

## Checkpoints

- After group 3 (ports defined): confirm the `OperationUnitOfWork` protocol extension does not break Fase 08's existing `negotiations`/`quotes`/`commitments` repository attributes.
- After group 7 (migration drafted): re-run `alembic upgrade head` / `downgrade -1` / `upgrade head` locally before writing dependent repository code.
- Before finishing: refresh `git fetch origin main` and re-check declared conflicts (none) and dependency status (Fase 08 remains merged) since no other roadmap phase should have started concurrently against these same paths.

## Temporary waits

None identified. Fase 08 is already merged; no prerequisite phase must land before this one proceeds.

## Explicitly out of authorization

No deployment, production access, live financial mutation (not applicable — no Yuno in this project), or unrelated remote change. No FastAPI, Pydantic, OpenAPI, Orval, or frontend edit.
