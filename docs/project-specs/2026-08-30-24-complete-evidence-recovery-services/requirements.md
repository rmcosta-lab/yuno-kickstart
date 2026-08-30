# Fase 24 — Complete evidence and recovery backend services

## Coordination

- Priority: P0 backend prerequisite for Fase 15.
- Branch: `phase/24-complete-evidence-recovery-services`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fase 14, merged by pull request #14 with its gate evidence recorded.
- Conflicts with: none.
- Roadmap gate: backend-only tests prove mandate replacement, explicit escalation, and idempotent notification acknowledgement, including PostgreSQL round trips, stale-version handling, audit events, rollback, no FastAPI import, and no HTTP-contract change.

## Objective and terminal outcome

Complete the typed backend application boundary that Fase 15 needs for the three accepted recovery mutations. The terminal backend-observable result is an immutable replacement mandate that resolves its post-contact escalation, an explicit escalation that stores bounded structured context without changing a commitment, and a notification acknowledgement that preserves its first actor and UTC timestamp across retries.

## Included scope

- `ReplaceMandateCommand` and `ReplaceMandateService` for one locked operation transaction that validates the expected operation version, creates mandate version `current + 1`, activates it, resolves the named open post-contact escalation, returns the updated `Operation`, and appends safe coordinator audit events.
- `CreateEscalationCommand` and `CreateEscalationService` for an existing call session. The service resolves the call to its operation, verifies the expected operation version, persists bounded `conflict`, `attempted_alternatives`, and `recommended_action` context, changes no commitment, transitions the operation to `ESCALATED`, and returns the `PostContactEscalation`.
- `AcknowledgeNotificationCommand` and `AcknowledgeNotificationService` for an existing notification. The first acknowledgement stores a bounded actor and aware UTC timestamp; an identical retry returns the stored notification without a second state transition or audit event.
- Additive recovery models needed by the accepted response boundary: structured escalation context and notification recovery-decision state, correlation, acknowledgement actor, and acknowledgement timestamp.
- Repository-port and SQLAlchemy changes for inserting and activating immutable mandates, updating notifications, resolving call sessions, and round-tripping the extended recovery values.
- One additive, reversible Alembic migration for the new recovery context and acknowledgement columns plus constraints and indexes demonstrated by the queries.
- Safe typed exceptions for missing resources, stale versions, wrong-operation relationships, conflicting acknowledgement, invalid or already-resolved escalation state, and invalid bounded context.
- Deterministic unit tests and isolated PostgreSQL tests for success, replay, stale state, missing/mismatched resources, constraints, migration reversal, and rollback.
- Allowlisted audit events for mandate replacement, explicit escalation creation, and notification acknowledgement.

## Excluded scope

- FastAPI wiring, Pydantic schema changes, HTTP error translation, authorization, CORS, rate limiting, route tests, OpenAPI/Orval generation, frontend behavior, or browser testing; Fase 15 owns these integrations.
- Changes to the accepted `/v1` route, request, response, status, or error semantics.
- Recovery simulation, evidence recording, recap generation, brief generation, atomic winner replacement, or escalation blocking already completed by Fase 14 except for the smallest compatible extensions required by these three services.
- Provider calls, OpenAI, Twilio, Yuno, payments, real notifications, deployment, production access, or remote database mutation.
- Mission, technology stack, roadmap, challenge-plan, manifest, lockfile, `.env.example`, or Docker Compose changes.

## Domain and transaction decisions

- Replacement is an immutable append: the existing mandate row remains unchanged, the new mandate receives version `current + 1`, and the operation's active-mandate reference changes in the same transaction.
- The replacement command must name the currently unresolved escalation for the same operation. Resolving a missing, foreign, or already-resolved escalation fails safely and writes nothing.
- Replacement increments the operation version once, records one status entry, resolves the escalation at the same clock instant, and emits coordinator-attributed `MANDATE_REPLACED` and `ESCALATION_RESOLVED` audit events with allowlisted metadata only.
- Explicit escalation resolves `call_id` through the existing negotiation repository, stores only bounded printable context accepted by Fase 04, never stores raw transcript/provider payload/contact data, and never creates, supersedes, or activates a commitment.
- At most one unresolved post-contact escalation remains allowed per operation. A duplicate equivalent request is handled by the API idempotency boundary in Fase 15; a competing open escalation returns a safe conflict.
- A notification is immutable except for one-way acknowledgement fields. Repeating acknowledgement with the same actor returns the stored value. A later different actor cannot overwrite the first acknowledgement.
- Every service locks the operation or relevant mutation scope, checks the expected operation version before writing, commits exactly once, and rolls back completely on every exception.

## HTTP contract gate

No HTTP contract change is authorized. The backend services must be directly adaptable to the accepted Fase 04 contracts without transport types:

| Existing route | Accepted success | Backend input/output |
| --- | --- | --- |
| `POST /v1/operations/{operation_id}/mandates` | `201 OperationResponse` | `ReplaceMandateCommand` to updated `Operation` |
| `POST /v1/calls/{call_id}/escalations` | `201 EscalationResponse` | `CreateEscalationCommand` to `PostContactEscalation` |
| `POST /v1/notifications/{notification_id}/acknowledgements` | `200 CoordinatorNotificationResponse` | `AcknowledgeNotificationCommand` to updated `Notification` |

Fase 15 remains responsible for bearer authorization, `Idempotency-Key`, Pydantic-to-domain conversion, `403/404/409` translation, response projection, and route tests. `api/openapi.json` and `frontend/src/lib/api/generated/**` remain untouched here.

## Application contract gate

| Import path | Public symbols | Construction and typed behavior |
| --- | --- | --- |
| `yuno_backend.volta.recovery.commands` | `ReplaceMandateCommand`, `CreateEscalationCommand`, `AcknowledgeNotificationCommand` | Frozen inputs composed only of UUIDs, versions, domain `Money`/`PickupWindow`, bounded tuples/strings, approval actor, and correlation ID; no Pydantic or HTTP values. |
| `yuno_backend.volta.recovery.models` | `EscalationContext`, `RecoveryDecisionState`, `RecoveryDecision`, extended `PostContactEscalation`, extended `Notification` | Frozen provider-neutral results with aware UTC timestamps. Escalation context is bounded; notification acknowledgement fields are both set or both absent. |
| `yuno_backend.volta.recovery.services` | `ReplaceMandateService.replace(command) -> Operation`, `CreateEscalationService.create(command) -> PostContactEscalation`, `AcknowledgeNotificationService.acknowledge(command) -> Notification` | Constructed with `OperationUnitOfWork`, `Clock`, and `IdGenerator`; replacement also reuses mandate validation rules. Each mutation commits once or rolls back fully. |
| `yuno_backend.volta.recovery.repositories` | Extended `NotificationRepository.update(...)` and `OperationUnitOfWork` | Async persistence-neutral ports; the inherited negotiation repository resolves `call_id`; no SQLAlchemy/session type crosses the boundary. |
| `yuno_backend.volta.mandates.repositories` | Extended `OperationRepository.replace_mandate(operation)` | Atomically inserts the new immutable mandate, changes `active_mandate_id`, updates operation version/status, and inserts the latest status history entry. |
| `yuno_backend.volta.recovery.errors` | `NotificationNotFound`, `NotificationAlreadyAcknowledged`, `EscalationAlreadyResolved`, `EscalationContextConflict`, plus existing `EscalationNotFound`, `OperationBlockedByEscalation`, `StaleOperationVersion` and call/operation lookup errors | Stable safe codes and identifiers/version context only; no submitted text, provider payload, or secret in messages. |
| `yuno_backend.volta.persistence.repositories` and `.unit_of_work` | Additive SQLAlchemy implementations of the extended ports | Constructed from the existing async session factory and returning domain values only. |

All public exports are explicit. Recovery, mandate, and application modules import neither FastAPI nor Pydantic.

## Acceptance criteria

- Replacing a mandate under a locked operation creates exactly one immutable next version, activates it, resolves exactly the named open escalation, advances operation state once, and persists the actor and approval timestamp.
- Missing, foreign, resolved, or stale replacement input raises a safe typed exception and leaves the active mandate, escalation, operation version, status history, and audit trail unchanged.
- Explicit escalation round-trips its bounded conflict, attempted alternatives, recommended action, call/operation/commitment context, correlation ID, and timestamps while leaving every commitment byte-for-byte unchanged.
- Notification acknowledgement stores the first actor and timestamp; same-actor retries return the stored value without another operation transition or audit event; a different actor cannot overwrite it.
- PostgreSQL migration upgrade, downgrade, and re-upgrade pass; repositories round-trip every new field; constraints reject partial acknowledgement state, invalid relationships, and unsafe bounds; injected failures roll back all writes.
- `uv run ruff check .`, `uv run pytest`, focused PostgreSQL-backed tests, `make python-check`, and `git diff --check` pass. Diff review confirms no FastAPI/Pydantic import in backend application code, no API/generated/frontend change, no secret/personal/provider payload, and no unrelated edit.

## Risks and fallback

- Risk: changing `OperationRepository.update` for mandate activation could silently overwrite history. Mitigation: introduce an explicit `replace_mandate` port and test old and new mandate rows after rollback and replay.
- Risk: enriching the Fase 14 recovery models breaks existing construction sites. Mitigation: update all in-memory and SQLAlchemy mappers together and retain frozen invariants with focused contract tests.
- Risk: explicit escalation context stores sensitive conversation text. Mitigation: bounded printable values, no raw transcript/contact/provider fields, safe exception messages, and redaction-oriented diff/tests.
- Risk: acknowledgement retries create multiple versions or audit events. Mitigation: lock, compare the stored actor, and treat an identical acknowledgement as a read-only replay.
- Fallback: preserve the merged Fase 14 services and schema unchanged if the new application contract cannot satisfy atomicity; keep Fase 15 paused and split the unresolved persistence decision through `manage-shared-specs` rather than exposing an incomplete backend boundary.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-24-complete-evidence-recovery-services/**` | Fase 24 coordinator (`rmcosta-lab`) | Owns requirements, plan, and validation evidence. |
| `backend/src/yuno_backend/volta/recovery/**` | Fase 24 backend writer (`rmcosta-lab`) | Sole writer for commands, models, ports, services, errors, and exports. |
| `backend/src/yuno_backend/volta/mandates/repositories.py` | Fase 24 backend writer (`rmcosta-lab`) | Additive operation-repository contract only. |
| `backend/src/yuno_backend/volta/{audit,persistence}/**` | Fase 24 backend writer (`rmcosta-lab`) | Smallest additive audit, mapper, repository, table, and unit-of-work changes. |
| `backend/migrations/**` | Fase 24 backend writer (`rmcosta-lab`) | Sole writer for one additive reversible migration. |
| `backend/tests/volta/{recovery,mandates,audit,persistence}/**` | Fase 24 backend writer (`rmcosta-lab`) | Deterministic and isolated PostgreSQL validation. |
| `backend/pyproject.toml`, `uv.lock`, root `Makefile` | No planned writer | Existing dependencies and commands are sufficient; coordinate any discovered need. |
| `api/**`, `frontend/**`, `api/openapi.json`, generated clients | No Fase 24 writer | No HTTP or browser change is authorized. |
| Shared mission, stack, roadmap, challenge plan, provider and deployment files | No Fase 24 writer | No shared decision is planned; route a broad discovery through `manage-shared-specs`. |
