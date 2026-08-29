# Fase 05 — Implement operation and mandate rules

## Coordination

- Priority: P0 backend foundation.
- Branch: `phase/05-implement-mandate-core`.
- Owner: `rmcosta-lab`.
- Tracking Issue: none requested.
- Depends on: Fase 04, merged by pull request #5 at `3e45529`.
- Conflicts with: none.
- Roadmap gate: backend-only tests prove source-prompt retention, versioned extraction-policy references, draft validation, explicit approval, immutable mandate versions, and deterministic price, currency, pickup-window, condition, and authority checks without importing FastAPI or a database implementation.

## Objective and terminal outcome

Give later API, persistence, negotiation, and OpenAI phases one provider-neutral Python contract for turning an extracted intake proposal into a validated draft, approving it into an operation with immutable mandate version 1, and checking proposed actions deterministically against that mandate.

The target user remains the operations coordinator, but this backend-only phase adds no screen or working HTTP journey. Its terminal observable result is a deterministic test suite and stable public application boundary that later phases can wire without importing Pydantic transport models.

## Included scope

- Frozen domain entities and value objects for route, pickup window, money, proposed operation/mandate data, intake draft, mandate, operation, validation issue, authority action, and mandate decision.
- Retention of the original source prompt with a non-empty versioned extraction-policy reference; source prompts are excluded from object representations and logs.
- Semantic validation that produces structured issues and makes invalid drafts ineligible for approval without creating authority.
- Explicit approval of exactly the expected draft version into one operation and immutable mandate version 1, with injected identifiers and an aware UTC clock.
- Deterministic mandate evaluation for amount, currency, pickup window, conditions, action authority, and active mandate version.
- Typed application commands, services, repository/unit-of-work protocols, public domain exceptions, and deterministic in-memory fakes confined to tests.

## Excluded scope

- FastAPI, Pydantic API schemas, HTTP status mapping, authorization, CORS, OpenAPI, Orval, or frontend work.
- SQLAlchemy models, migrations, PostgreSQL access, transaction implementations, or durable idempotency; Fase 06 owns persistence.
- Carrier selection, quotes, commitments, winner transitions, recovery, evidence, notifications, or audit persistence; Fases 08 and 14 own those rules.
- OpenAI extraction, Realtime, Twilio, Yuno, payment behavior, provider calls, deployment, production access, and live mutations.
- Editing the accepted mission, stack, roadmap, challenge plan, manifests, or lockfiles.

## Domain decisions

- Add the Volta core under `backend/src/yuno_backend/volta/mandates/`; the existing payment bootstrap remains untouched and no FastAPI or API schema enters this package.
- Use frozen, slotted dataclasses and enums for domain state. Use `UUID` identifiers, aware UTC `datetime`, `date` pickup bounds, `Decimal` money with explicit currency, and tuples for immutable condition collections.
- The HTTP layer will later convert integer minor units to exact `Decimal` values at the boundary; binary floating point is forbidden.
- `IntakeDraft` retains `source_prompt`, `requested_language`, `extraction_policy_version`, the extracted proposal, structured validation issues, eligibility, version, and timestamps. The prompt uses `repr=False` and must never appear in exceptions or logs.
- Draft validation is deterministic and side-effect free. It checks required route endpoints, ordered pickup dates, non-negative price, accepted P0 currency `MXN`, bounded/non-empty conditions, and a supported requested language. Validation issues contain safe field and reason codes, not submitted values.
- Approval requires an eligible draft and an exact expected draft version. It creates a new `Operation` at version 1 and a new immutable `Mandate` at version 1; it never mutates the draft proposal or makes an invalid draft authoritative.
- An approved mandate grants only explicit `NEGOTIATE` and `COMMIT` actions for its operation and version. `MandatePolicy.evaluate(...)` returns an allow/deny decision with stable reason codes for action authority, mandate version, amount, currency, pickup window, and conditions.
- Later phases may extend aggregates additively, but must not weaken immutable mandate history or move deterministic authority into prompts, providers, API DTOs, or browser callbacks.

## HTTP contract handoff

No HTTP contract changes in this phase. The accepted Fase 04 routes remain authoritative:

- `POST /v1/operation-drafts` will eventually combine server-side extraction with `CreateIntakeDraftService`; Fase 05 accepts a typed extracted proposal and does not call a model.
- `POST /v1/operations` will map `ApproveOperationRequest` to `ApproveOperationCommand` and map the returned domain operation to `OperationResponse` in Fase 10.
- Transport errors remain outside the core. Fase 10 will translate stale draft, missing draft, invalid approval, and conflict exceptions to the accepted safe `404`, `409`, and `422` envelopes.

No Pydantic model is imported or reused as a domain entity, and this phase does not regenerate OpenAPI or Orval.

## Application contract gate

Public modules and symbols to implement:

| Import path | Public symbols | Contract |
| --- | --- | --- |
| `yuno_backend.volta.mandates.models` | `Money`, `Route`, `PickupWindow`, `OperationProposal`, `MandateProposal`, `DraftValidationIssue`, `IntakeDraft`, `Mandate`, `Operation`, `MandateAction`, `MandateDecision` | Immutable provider-neutral values and entities; constructors enforce local invariants and expose no transport/provider types. |
| `yuno_backend.volta.mandates.commands` | `CreateIntakeDraftCommand`, `ApproveOperationCommand`, `CheckMandateCommand` | Frozen typed inputs. Create carries source prompt, language, policy version, and extracted proposal; approve carries draft ID/version and actor; check carries operation/mandate version, action, and proposed terms. |
| `yuno_backend.volta.mandates.services` | `CreateIntakeDraftService`, `ApproveOperationService`, `MandatePolicy` | Constructed with the protocols below; async creation/approval return `IntakeDraft`/`Operation`, while policy evaluation is synchronous and returns `MandateDecision`. |
| `yuno_backend.volta.mandates.repositories` | `IntakeDraftRepository`, `OperationRepository`, `OperationUnitOfWork`, `Clock`, `IdGenerator` | Protocols only. Repositories load/add domain entities; the unit of work exposes both repositories and commit/rollback; clock and ID generation are injected for deterministic behavior. |
| `yuno_backend.volta.mandates.errors` | `InvalidDomainValue`, `DraftNotFound`, `StaleDraftVersion`, `DraftNotApprovable`, `OperationAlreadyApproved`, `MandateConflict` | Typed public exceptions with safe IDs, current versions, and reason codes only; no HTTP status, raw prompt, provider payload, or persistence exception. |

Service behavior:

- `CreateIntakeDraftService.create(command) -> IntakeDraft` validates the extracted proposal, assigns deterministic injected IDs/timestamps, stores the source prompt and policy version, starts at draft version 1, and commits through the unit of work.
- `ApproveOperationService.approve(command) -> Operation` loads the draft, checks exact version and eligibility, prevents duplicate approval, creates operation and mandate version 1, records the approval actor/time, and commits once.
- `MandatePolicy.evaluate(mandate, command) -> MandateDecision` is pure and returns every deterministic rejection reason in stable order. `require_allowed(...)` may raise `MandateConflict` using the same safe reasons.

Phase 06 may implement these protocols with SQLAlchemy/PostgreSQL without changing service callers. Phase 10 must record the exact adapter construction and exception-to-HTTP mapping before replacing `CONTRACT_NOT_IMPLEMENTED`.

## Security and provider handoff

- There is no Yuno, OpenAI, Twilio, browser, payment, or database handoff in this phase.
- Use synthetic values in tests. Never include a real prompt, person, carrier contact, credential, provider identifier, or private audio reference.
- Source prompts and approval actors are retained only as required domain values; prompts remain redacted from representations, exceptions, assertions that print failures, and structured logs.
- No external state changes, deployment, remote migration, phone call, or financial operation is authorized.

## Acceptance criteria

- Tests prove the original prompt and extraction-policy version survive draft creation while the prompt is absent from `repr` and exceptions.
- Valid and invalid extracted proposals produce deterministic, structured validation outcomes; only eligible drafts may be approved.
- Approval requires the expected draft version, creates exactly one operation and immutable mandate version 1, and rejects missing, stale, invalid, or already-approved drafts through typed exceptions.
- Attempts to mutate frozen draft, mandate, and operation values fail; later mandate replacement can only create a new version rather than change an existing one.
- Mandate checks accept an in-authority action and reject independently and in combination: wrong action, stale mandate version, excessive amount, wrong currency, pickup outside the approved window, and disallowed conditions.
- Unit tests use injected clock, ID generator, and in-memory repository/unit-of-work fakes and require no live database or provider.
- `backend/src/yuno_backend/volta/**` imports no FastAPI, Pydantic API schema, SQLAlchemy, provider adapter, or database module.
- `uv run ruff check .`, `uv run pytest`, and `make python-check` pass; no unrelated path or dependency change enters the phase.

## Assumptions, risks, and fallback

- Assumption: the merged Fase 04 transport vocabulary and the accepted mission/stack remain stable while this backend contract is implemented.
- Risk: mirroring Pydantic DTOs would couple the core to HTTP. Mitigation: use domain-specific commands and explicit later mappings.
- Risk: semantic validation and mandate evaluation overlap. Mitigation: draft validation decides whether authority may be created; mandate evaluation decides whether a proposed action fits already-approved authority.
- Risk: premature persistence design constrains Fase 06. Mitigation: protocols describe behavior and atomic intent without importing SQLAlchemy or fixing a schema.
- Risk: source prompts leak through diagnostics. Mitigation: redacted representations and tests that scan exceptions/loggable values.
- Fallback: deterministic in-memory fakes and pure policy evaluation keep downstream rule development testable while PostgreSQL and AI extraction are unavailable.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-05-implement-mandate-core/**` | `rmcosta-lab` | Phase coordinator owns requirements, plan, and validation. |
| `backend/src/yuno_backend/volta/mandates/**` | Fase 05 backend writer | Sole implementation owner for new operation/mandate domain and application modules. |
| `backend/tests/volta/mandates/**` | Fase 05 backend writer | Deterministic unit and architecture tests only. |
| `backend/src/yuno_backend/__init__.py` and `backend/src/yuno_backend/volta/**/__init__.py` | Fase 05 backend writer | Export only the accepted public application contract; preserve payment exports. |
| `backend/pyproject.toml`, root `pyproject.toml`, `uv.lock` | No writer expected | No dependency is required; manifest and lockfile changes require a plan update and one coordinator-owned pair. |
| `api/**`, `frontend/**`, `api/openapi.json`, generated clients | No Fase 05 writer | Consume no API DTO and make no transport or UI change. |
| `docs/project-specs/{mission,tech-stack,roadmap}.md`, `docs/decisions/challenge-plan.md` | No Fase 05 writer | No shared decision change is required; route any discovered broad change through `manage-shared-specs`. |
| Existing payment, Yuno integration, and database bootstrap files | No Fase 05 writer | Preserve unchanged; Volta rules live in their own namespace. |
