# Fase 14 — Preserve evidence and enforce recovery rules

## Coordination

- Priority: P0 backend evidence and recovery foundation.
- Branch: `phase/14-implement-evidence-recovery-core`.
- Owner: `joaovitorpsouza11` (GitHub login to be confirmed at push time; contact via the session user email `joaovitorpsouza11@gmail.com` if no tracking Issue exists).
- Tracking Issue: none requested.
- Depends on: Fase 08, merged by pull request #12, with its required validation evidence recorded.
- Conflicts with: none.
- Roadmap gate: backend-only tests persist provider-neutral call sessions, playable recording references with `audio_start_ms`, item and event identifiers, briefs, and recaps labeled `SIMULATED`; they also prove one mandate-safe renegotiation or reconfirmed replacement with an atomic winner transition and notification, plus one out-of-mandate escalation that resumes only after a new immutable mandate version.

## Objective and terminal outcome

Give Volta a deterministic, provider-neutral evidence and recovery core so an operations coordinator can trust the recorded agreement and see exactly one active winner survive a renegotiation or an escalation. This phase adds no HTTP or frontend surface. Its terminal observable result is a backend test suite that persists a playable recording reference (`audio_start_ms`, item ID, event ID) plus a call brief and a `SIMULATED` recap for an existing Fase 08 commitment, then proves one mandate-safe replacement keeps exactly one active commitment with full history and a notification, and one out-of-mandate attempt escalates and stays blocked until a new immutable mandate version resumes it.

## Included scope

- A provider-neutral `volta.evidence` package: frozen values for call-session recording references, agreement-turn evidence (`recording_reference`, `audio_start_ms`, `item_id`, `event_id`), call briefs, and recaps whose disclosure state is always `SIMULATED` in this phase.
- Selection of the private evidence-storage mechanism used in development (a filesystem-backed adapter behind a provider-neutral protocol, outside Git and outside PostgreSQL binary columns) and documentation of its access and deletion behavior.
- A provider-neutral `volta.recovery` package: frozen values and application services for a mandate-safe renegotiation/replacement path and an out-of-mandate escalation path, both keyed to an existing Fase 08 commitment and operation.
- Application services: `RecordEvidenceService` (attaches evidence to a `CANDIDATE`/`ACTIVE` commitment), `GenerateBriefService`, `GenerateRecapService` (always `SIMULATED`), `SimulateInboundRecoveryService` (mandate-safe replacement or out-of-mandate escalation), and `ResumeAfterEscalationService` (accepts a new immutable mandate version to unblock a previously escalated operation).
- Typed exceptions for missing commitment/evidence, invalid disposition, out-of-mandate recovery terms, and an operation still blocked by an unresolved escalation.
- Additive Alembic migration and private SQLAlchemy mappings/repositories for evidence references, briefs, recaps, recovery attempts, and post-contact escalations, extending the Fase 06/08 schema and unit of work.
- Deterministic in-memory tests plus isolated PostgreSQL tests for round trips, the atomic winner-replacement transaction, notification recording, escalation blocking, and resumption after a new mandate version.
- Safe, allowlisted audit events for evidence recorded, brief generated, recap generated, recovery replacement applied, post-contact escalation raised, and escalation resumed.

## Excluded scope

- FastAPI wiring, Pydantic schema edits, HTTP error translation, authorization, CORS, OpenAPI/Orval regeneration, frontend behavior, or browser testing (owned by Fase 15).
- Real audio recording, real Realtime/Twilio adapters, real notification delivery (SMS/email), Yuno, payments, or any production/remote mutation.
- Carrier selection, quote recording, and initial commitment creation, which remain owned by Fase 08 and are only consumed here.
- A `VERIFIED` recap state, real inbound PSTN handling, or any capability the mission defers to P2.
- Changes to mission, technology stack, roadmap, challenge plan, manifests, lockfiles, `.env.example`, Docker Compose, or existing API/generated artifacts.

## Domain and deterministic policy decisions

- `AgreementEvidence` binds one `commitment_id` to a `recording_reference` (opaque private-storage pointer), a non-negative `audio_start_ms`, a non-empty `item_id`, and a non-empty `event_id`. Evidence may be attached only to a commitment in `CANDIDATE` or `ACTIVE` disposition; attaching evidence twice for the same commitment is idempotent and returns the stored record instead of creating a duplicate.
- `CallBrief` is a frozen, bounded summary (route, carrier, agreed terms reference, mandate version, generated timestamp) built only from already-persisted safe fields; it never re-derives or stores raw transcript, prompt, or contact text.
- `Recap` always carries `disclosure_state = "SIMULATED"` in this phase; the domain type has no branch that can mark it otherwise, so a future delivery-provider phase must add a new state rather than flip a flag here.
- `RecoveryAttempt` records whether an inbound event is mandate-safe (replacement/reconfirmation within the active mandate's price, currency, pickup window, and conditions) or out-of-mandate. A mandate-safe attempt creates a new commitment for the same operation, atomically supersedes the previous active commitment (reusing the Fase 08 winner-transition guarantees), and records exactly one notification for the coordinator. An out-of-mandate attempt creates a `PostContactEscalation`, changes no commitment, and blocks further recovery attempts on that operation until resumed.
- `PostContactEscalation` (distinct from the Fase 08 `PreContactEscalation`) stores a safe reason code, the operation version and mandate version at escalation time, and a resolved/unresolved state. It resolves only when `ResumeAfterEscalationService` receives a new immutable mandate version greater than the one active at escalation time; resuming does not itself create a commitment, it only clears the block so a subsequent mandate-safe recovery attempt may proceed.
- Every recovery mutation is scoped to the operation's optimistic version, mirroring Fase 08: a stale expected version raises `StaleOperationVersion` and writes nothing.

## HTTP contract gate

No HTTP contract changes are authorized. Fase 15 will map these services to new or existing Fase 04 contracts for evidence, recap, brief, notification, recovery simulation, mandate replacement, escalation, and audit retrieval. `api/openapi.json` and `frontend/src/lib/api/generated/**` remain untouched by this phase.

## Application contract gate

| Import path | Public symbols | Typed behavior |
| --- | --- | --- |
| `yuno_backend.volta.evidence.models` | `AgreementEvidence`, `CallBrief`, `Recap`, `RecapDisclosureState` | Frozen provider-neutral values using UUIDs, non-negative millisecond offsets, and aware UTC timestamps. |
| `yuno_backend.volta.evidence.repositories` | `EvidenceRepository`, `BriefRepository`, `RecapRepository`, `EvidenceStorage` | Async ports; `EvidenceStorage` is the private-storage protocol implemented by a filesystem adapter for development. |
| `yuno_backend.volta.evidence.services` | `RecordEvidenceService.record(...) -> AgreementEvidence`, `GenerateBriefService.generate(...) -> CallBrief`, `GenerateRecapService.generate(...) -> Recap` | Constructed with the unit of work, clock, and ID generator; every mutation commits once or rolls back completely. |
| `yuno_backend.volta.recovery.models` | `RecoveryAttempt`, `RecoveryOutcome`, `PostContactEscalation`, `Notification` | Frozen provider-neutral values; `RecoveryOutcome` is `REPLACED` or `ESCALATED`. |
| `yuno_backend.volta.recovery.commands` | `SimulateInboundRecoveryCommand`, `ResumeAfterEscalationCommand` | Frozen typed inputs with expected operation version, proposed terms or new mandate version, and a correlation UUID. |
| `yuno_backend.volta.recovery.repositories` | `RecoveryAttemptRepository`, `PostContactEscalationRepository`, `NotificationRepository`, and extended `OperationUnitOfWork` | Async ports; no SQLAlchemy/session type crosses the boundary. |
| `yuno_backend.volta.recovery.services` | `SimulateInboundRecoveryService.simulate(...) -> RecoveryAttempt`, `ResumeAfterEscalationService.resume(...) -> PostContactEscalation` | Reuses `MandatePolicy` from Fase 05 and the atomic winner-transition pattern from Fase 08. |
| `yuno_backend.volta.recovery.errors` | `CommitmentNotFound`, `EvidenceAlreadyRecorded` (idempotent no-op path), `InvalidCommitmentDisposition`, `OperationBlockedByEscalation`, `MandateVersionNotAdvanced`, `StaleOperationVersion` | Safe exceptions exposing stable codes and UUID/version context only. |
| `yuno_backend.volta.persistence.repositories` and `.unit_of_work` | Additive SQLAlchemy evidence/recovery repositories and the extended `SqlAlchemyOperationUnitOfWork` | Constructed from the existing async session factory; locks and persists one logical mutation transaction and returns only domain values. |

Public package exports are explicit; evidence and recovery domain/application modules import neither FastAPI nor SQLAlchemy.

## Yuno browser/server handoff and terminal user-visible result

This phase produces no browser-visible result by itself. Its terminal, backend-observable result is: a persisted `AgreementEvidence` reloadable with the exact `audio_start_ms`/`item_id`/`event_id`, a generated `CallBrief`, a `Recap` labeled `SIMULATED`, one successful mandate-safe replacement leaving exactly one active commitment with superseded history and a recorded notification, and one out-of-mandate escalation that blocks recovery until `ResumeAfterEscalationService` accepts a new mandate version.

## Persistence, atomicity, and audit decisions

- Extend the existing migration chain with one additive, reversible migration under private lowercase `volta_` tables (e.g. `volta_agreement_evidence`, `volta_call_briefs`, `volta_recaps`, `volta_recovery_attempts`, `volta_post_contact_escalations`, `volta_notifications`); exact names are fixed before code depends on them.
- Unique constraints: one evidence record per commitment, at most one unresolved `PostContactEscalation` per operation, and foreign keys tying evidence/briefs/recaps/recovery rows to their operation and commitment.
- Reuse the Fase 08 locked operation/active-winner transaction pattern for mandate-safe replacement so no partial state or two active commitments can appear.
- Append safe audit events for evidence recorded, brief generated, recap generated, recovery replacement applied, post-contact escalation raised, and escalation resumed; metadata stays allowlisted and bounded, with no raw recording path, transcript, contact detail, or provider payload copied into metadata.
- No database transaction remains open across storage or provider work; the filesystem evidence-storage adapter is called and awaited before the persistence transaction begins or after it commits, never inside it.

## Acceptance criteria

- Evidence can be attached only to a `CANDIDATE`/`ACTIVE` commitment; attaching it again is idempotent; attaching it to a missing or superseded commitment fails safely.
- A generated brief and a `SIMULATED` recap reload identically from PostgreSQL and never carry a disclosure state other than `SIMULATED` in this phase.
- One mandate-safe recovery attempt atomically supersedes the prior active commitment, creates exactly one new active commitment, preserves full history, and records exactly one notification; concurrent or partial failures cannot create two active commitments.
- One out-of-mandate recovery attempt changes no commitment, creates one `PostContactEscalation`, and further recovery attempts on that operation are rejected with `OperationBlockedByEscalation` until `ResumeAfterEscalationService` accepts a new, strictly greater mandate version.
- PostgreSQL upgrade, downgrade, and re-upgrade succeed; repositories round-trip every evidence/recovery value; constraints reject broken relationships and invalid values; rollback preserves the prior durable state.
- `uv run ruff check .`, `uv run pytest`, focused PostgreSQL-backed tests, `make python-check`, and `git diff --check` pass. Diff review confirms no secret, personal contact, raw evidence path, provider payload, unrelated change, API/generated change, or external mutation.

## Assumptions, risks, and fallback

- Assumption: the merged Fase 08 negotiation/commitment contract and the Fase 05/06 mandate and persistence boundaries remain the baseline; this phase only extends them additively.
- Risk: evidence storage design overreaches into a real object-storage provider before one is selected for deployment. Mitigation: a filesystem-backed adapter behind a narrow `EvidenceStorage` protocol keeps the interface stable for a later provider swap.
- Risk: recovery logic duplicates or diverges from the Fase 08 atomic winner-transition guarantee. Mitigation: reuse the same locked-transaction repository pattern and add permutation/concurrency tests mirroring Fase 08's.
- Risk: escalation resumption silently reactivates a stale mandate. Mitigation: `ResumeAfterEscalationService` requires a strictly greater mandate version than the one recorded at escalation time and performs no commitment mutation itself.
- Risk: audit metadata leaks a recording path or transcript fragment. Mitigation: event-specific allowlists identical in spirit to Fase 08's, with redaction review in tests.
- Fallback: keep the deterministic in-memory repositories and filesystem evidence adapter fully testable without PostgreSQL so Fase 15/17 integration issues can be isolated to the persistence layer.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-14-implement-evidence-recovery-core/**` | Fase 14 coordinator | Owns requirements, plan, and validation evidence. |
| `backend/src/yuno_backend/volta/evidence/**` | Fase 14 backend writer | Sole writer for evidence domain values, ports, services, errors, and exports. |
| `backend/src/yuno_backend/volta/recovery/**` | Fase 14 backend writer | Sole writer for recovery domain values, ports, services, errors, and exports. |
| `backend/src/yuno_backend/volta/{negotiations,mandates,audit,persistence}/**` | Fase 14 backend writer | Additive extensions only; preserve Fases 05/06/08 contracts and exports. |
| `backend/migrations/**` | Fase 14 backend writer | Sole writer for one additive reversible migration and its constraints/indexes. |
| `backend/tests/volta/{evidence,recovery,negotiations,mandates,audit,persistence}/**` | Fase 14 backend writer | Deterministic unit and isolated PostgreSQL integration tests. |
| `backend/pyproject.toml`, `uv.lock`, root `Makefile` | No planned Fase 14 writer | Existing dependencies and commands are sufficient; treat any discovered need as a coordinated manifest/lockfile decision. |
| `api/**`, `frontend/**`, `api/openapi.json`, generated clients | No Fase 14 writer | No HTTP, generated contract, or UI change is authorized. |
| Shared mission, stack, roadmap, challenge plan, deployment and provider files | No Fase 14 writer | No shared decision is required; route a broad discovery through `manage-shared-specs`. |
