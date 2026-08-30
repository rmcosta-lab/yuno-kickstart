# Fase 15 — Expose evidence and recovery routes

## Coordination

- Priority: P0 API integration for the complete browser recovery journey.
- Branch: `phase/15-expose-evidence-recovery-routes`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fases 12, 14, 24, and 25. They were merged by pull requests #16, #14, #18, and #21 with their gate evidence recorded. Fase 25 was introduced by merged specs pull request #19 and now supplies the durable application facade consumed here.
- Conflicts with: none.
- Roadmap gate: FastAPI implements the accepted P0 contracts for evidence, simulated recaps, briefs, notifications, inbound recovery simulations, mandate replacement, escalation, and audit retrieval; API tests cover authorization, idempotency, missing evidence, stale state, and safe errors without changing the committed contract or generated client.

## Objective and terminal user-visible outcome

Expose the already accepted evidence and recovery HTTP surface through thin FastAPI integration so the later recovery frontend can play agreement evidence, run the deterministic good and bad recovery scripts, acknowledge notifications, replace a mandate after escalation, and inspect the correlated audit timeline. This phase adds no screen. Its terminal observable result is that the existing generated client receives durable backend results rather than `501 CONTRACT_NOT_IMPLEMENTED` for every Fase 15 operation, while evidence and audit operations already wired by Fase 10 retain their accepted behavior.

## Included scope

- Keep the existing Fase 04 Pydantic request/response types, paths, operation IDs, statuses, headers, and safe error schemas unchanged.
- Wire and test these accepted operations: `attach_commitment_evidence`, `create_simulated_recap`, `create_call_brief`, `start_inbound_simulation`, `replace_mandate`, `create_escalation`, `acknowledge_notification`, and `get_operation_audit`.
- Extend the existing `VoltaTextContractService` transport adapter, dependency construction, response projection, and safe exception translation; routers remain generic and thin.
- Delegate mutations to the typed Fase 14/24 backend services and preserve the Fase 10 evidence-reservation/commitment sequence.
- Enforce the accepted bearer authorization, mutation rate limit, `Idempotency-Key` replay/conflict semantics, optimistic operation-version checks, and safe request/correlation headers.
- Add focused adapter, route, error-mapping, PostgreSQL integration, and unchanged-contract tests.
- Prove that audit retrieval returns the accepted bounded artifact histories and never leaks recording bytes, filesystem paths, raw transcripts, provider payloads, contact details, or internal exception text.

## Excluded scope

- Pydantic model, route, status, operation-ID, OpenAPI, Orval, or generated-client changes.
- Frontend behavior, browser testing, backend domain rules, backend persistence changes, migrations, provider calls, real audio recording, real inbound PSTN, or notification delivery.
- OpenAI, Twilio, Yuno, payment, deployment, production access, remote database mutation, or real participant data.
- A `VERIFIED` recap, SMS/email delivery, or any claim that simulated delivery is challenge-verified.
- Direct SQLAlchemy sessions, repository queries, domain decisions, or transaction orchestration in routers or API projection code.
- Shared mission, stack, roadmap, or challenge-plan changes in this branch.

## HTTP contract gate

All operations require the configured demo bearer token. Every `POST` requires the existing printable 8–128 character `Idempotency-Key`; mutation responses preserve `Idempotency-Replayed: true` only for an identical durable replay. Every response preserves `X-Request-ID`.

| Method and route | Operation ID | Request | Success | Required semantics |
| --- | --- | --- | --- | --- |
| `POST /v1/calls/{call_id}/evidence` | `attach_commitment_evidence` | `CreateCommitmentEvidenceRequest` | `201 CommitmentEvidenceResponse` | Preserve the Fase 10 private-playable evidence reservation with `audio_start_ms`, item ID, event ID, call ownership, version check, and idempotent replay. |
| `POST /v1/calls/{call_id}/recaps` | `create_simulated_recap` | `CreateSimulatedRecapRequest` | `201 WrittenRecapResponse` | Generate one recap for the named commitment, return channel `SIMULATED`, and never imply external delivery. |
| `POST /v1/calls/{call_id}/briefs` | `create_call_brief` | `CreateCallBriefRequest` | `201 CallBriefResponse` | Persist and return only the accepted bounded structured brief for a commitment owned by the call. |
| `POST /v1/operations/{operation_id}/inbound-simulations` | `start_inbound_simulation` | `StartInboundSimulationRequest` | `201 RecoverySimulationResponse` | Run only `MANDATE_SAFE` or `OUT_OF_MANDATE`, preserve one active winner, and return either the replacement result or open escalation. |
| `POST /v1/operations/{operation_id}/mandates` | `replace_mandate` | `ReplaceMandateRequest` | `201 OperationResponse` | Create and activate immutable mandate version `current + 1`, resolve the named same-operation escalation, and return the updated aggregate. |
| `POST /v1/calls/{call_id}/escalations` | `create_escalation` | `CreateEscalationRequest` | `201 EscalationResponse` | Persist bounded conflict context for the call without changing a commitment. |
| `POST /v1/notifications/{notification_id}/acknowledgements` | `acknowledge_notification` | `AcknowledgeNotificationRequest` | `200 CoordinatorNotificationResponse` | Persist the first actor/timestamp; identical retries return the stored notification and a different actor conflicts. |
| `GET /v1/operations/{operation_id}/audit` | `get_operation_audit` | UUID path, optional opaque cursor, limit 1–100 | `200 AuditTimelineResponse` | Return ordered safe events plus quote, commitment, recap, brief, recovery, escalation, and notification histories with a bounded opaque cursor. |

The accepted public mappings remain:

- `401 AUTHENTICATION_REQUIRED` or `AUTHENTICATION_INVALID` before delegation.
- `403 ACTION_NOT_AUTHORIZED` when the authenticated actor lacks authority.
- `404 RESOURCE_NOT_FOUND` for missing operation, call, commitment, escalation, notification, or evidence without lookup details.
- `409 STALE_OPERATION_VERSION` with only the safe current version; `IDEMPOTENCY_KEY_REUSED`, `STATE_CONFLICT`, or `MANDATE_CONFLICT` for incompatible replay or transition.
- `422 VALIDATION_ERROR` for the existing Pydantic boundary, without submitted values.
- `429 RATE_LIMITED` with the safe retry header.
- `500 INTERNAL_ERROR` with request ID only for unexpected or persistence failures.
- `501 CONTRACT_NOT_IMPLEMENTED` remains possible only while an operation is deliberately unwired; the final gate requires all eight Fase 15 operations to be integrated.

## Application contract gate

The API adapter may translate validated transport values and project backend results, but it may not own recovery rules, database queries, or transactions.

| Import path | Public symbols used by Fase 15 | Construction and typed behavior |
| --- | --- | --- |
| `yuno_backend.volta.text_slice` | `TextNegotiationApplication`, `AttachCommitmentEvidenceInput`, `AuditProjection`, `MutationOutcome` | Existing application-scoped facade constructed with a unit-of-work factory, extractor, carrier catalog, clock, ID generator, private evidence storage, and policy version. The existing evidence reservation and base audit behavior remain authoritative. |
| `yuno_backend.volta.evidence.commands` | `GenerateBriefCommand`, `GenerateRecapCommand`, `RecordEvidenceCommand` | Frozen UUID/version/correlation inputs. The accepted pre-commitment evidence route continues through the text-slice reservation rather than changing the Fase 04 sequence. |
| `yuno_backend.volta.evidence.services` | `GenerateBriefService.generate(...) -> CallBrief`, `GenerateRecapService.generate(...) -> Recap`, `RecordEvidenceService.record(...) -> AgreementEvidence` | Constructed with a fresh `OperationUnitOfWork`, `Clock`, and `IdGenerator`; each mutation commits once or rolls back. |
| `yuno_backend.volta.recovery.commands` | `SimulateInboundRecoveryCommand`, `ReplaceMandateCommand`, `CreateEscalationCommand`, `AcknowledgeNotificationCommand` | Frozen provider-neutral UUIDs, versions, `Money`, `PickupWindow`, `QuoteTerms`, bounded context, actor, and correlation ID. |
| `yuno_backend.volta.recovery.services` | `SimulateInboundRecoveryService.simulate(...) -> RecoveryAttempt`, `ReplaceMandateService.replace(...) -> Operation`, `CreateEscalationService.create(...) -> PostContactEscalation`, `AcknowledgeNotificationService.acknowledge(...) -> Notification` | Constructed with a fresh unit of work, clock, ID generator, and `MandatePolicy` where required; domain services own every state transition and transaction. |
| `yuno_backend.volta.recovery.models` | `RecoveryAttempt`, `PostContactEscalation`, `Notification`, `RecoveryDecision`, `RecoveryDecisionState` | Frozen durable results projected to the existing response DTOs without importing FastAPI/Pydantic into backend code. |
| `yuno_backend.volta.recovery.errors`, `yuno_backend.volta.negotiations.errors`, `yuno_backend.volta.persistence.errors` | Safe missing-resource, stale-version, conflict, blocked-operation, already-recorded/resolved/acknowledged, and persistence exceptions | Central translation emits only the accepted public status/code/message and safe identifiers/current version; no exception string is returned directly. |
| `yuno_backend.volta.persistence.unit_of_work` | `SqlAlchemyOperationUnitOfWork` | Constructed from the existing async session factory. It remains private to backend application/service construction; routers never access its repositories. |

One backend-facing application facade must expose the complete durable operation/audit projection for recaps, briefs, recoveries, post-contact escalations, and notifications. The API must not fill this boundary with direct repository queries. Merged Fase 25 pull request #21 completed this public facade, durable replay, deterministic recovery fixtures, and paged audit projection; Fase 15 refreshed from that `origin/main` and consumes those typed symbols without backend changes.

## Browser/server, AI, and provider handoff

The browser handoff remains the already generated Orval client over HTTPS/JSON. Fase 16 will consume these operations; no generated file changes here. Browser voice may call the same typed operations, but no Realtime event or callback changes operational state without a successful backend result. There is no Yuno/payment handoff, no Twilio or live inbound call, and no provider mutation in this phase.

## Acceptance criteria

- All eight accepted operations delegate to typed backend behavior and no longer return the default `501` in the configured PostgreSQL application.
- Identical mutation retries return the stored status/body and replay header; a different normalized request under the same key returns `409 IDEMPOTENCY_KEY_REUSED` and changes no state.
- Authorization runs before application delegation; rate limiting and request IDs retain the accepted behavior.
- Missing evidence/artifacts/resources, stale versions, blocked recovery, mandate conflict, already-resolved escalation, and conflicting acknowledgement map to safe `404`/`409` responses without internal details.
- Mandate-safe simulation leaves exactly one active commitment and one notification; out-of-mandate simulation leaves the commitment unchanged and returns one open escalation.
- Replacement creates a new immutable mandate and resolves only the named same-operation escalation. Acknowledgement preserves the first actor and timestamp across retries.
- Audit retrieval returns bounded, correlated, durable artifact histories and omits raw evidence bytes/paths, transcripts, contact details, provider payloads, secrets, and internal exceptions.
- Route, Pydantic, OpenAPI, and generated-client snapshots remain byte-for-byte unchanged; no handwritten TypeScript DTO is introduced.
- Focused API tests, PostgreSQL integration tests, `make python-check`, `git diff --check`, and diff/secret review pass.

## Assumptions, risks, and fallback

- Assumption: the Fase 04 HTTP contract remains accepted and Fases 12, 14, 24, and 25 remain merged; Fase 25 supplies the required backend facade without changing that HTTP contract.
- Risk: standalone backend mutation services are wired directly while durable replay/projection is incomplete. Mitigation: use one application facade and a unit-of-work factory; do not put repository access or transition logic in FastAPI.
- Risk: Fase 14 recap/brief values do not by themselves expose every accepted response field. Mitigation: prove a durable backend projection before wiring; do not synthesize or retain request-only success in API memory.
- Risk: error translation leaks bounded-but-sensitive escalation context or recording references. Mitigation: explicit exception allowlist and safe constant public messages.
- Risk: replay repeats an already committed mutation. Mitigation: durable fingerprint/result storage and PostgreSQL replay/concurrency tests for every POST.
- Fallback: keep the existing Fase 10 evidence and base-audit routes working, leave incomplete operations at honest `501`, preserve durable state, and add the smallest supporting backend phase when the required query/idempotency facade is absent. Never bypass the boundary with API-owned SQL or fabricated success.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-15-expose-evidence-recovery-routes/**` | Fase 15 coordinator (`rmcosta-lab`) | Own requirements, plan, validation, and any temporary-wait record. |
| `api/app/volta_text_service.py`, API application-adapter modules, dependency wiring | Fase 15 API writer (`rmcosta-lab`) | Sole writer for transport conversion, backend construction, result projection, and safe error mapping. |
| `api/app/routers/contracts.py`, `api/app/contract_service.py`, `api/app/main.py` | Fase 15 API writer only if required | Preserve the accepted contract; edits may only wire behavior or central translation without schema/operation changes. |
| `api/tests/**` | Fase 15 API writer (`rmcosta-lab`) | Focused adapter, route, authorization, replay, safe-error, unchanged-contract, and PostgreSQL tests. |
| `api/app/schemas/**`, `api/openapi.json`, `frontend/src/lib/api/generated/**` | No Fase 15 writer | Must remain byte-for-byte unchanged. |
| `backend/**`, `frontend/**`, manifests/lockfiles, migrations | No Fase 15 writer | Out of scope; a missing backend boundary requires a supporting phase, not an opportunistic edit. |
| `docs/project-specs/{mission,tech-stack,roadmap}.md`, `docs/decisions/challenge-plan.md` | No Fase 15 writer | No shared change is carried. Use `manage-shared-specs` if the temporary wait requires a new prerequisite. |
