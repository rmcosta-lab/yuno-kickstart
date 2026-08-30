# Phase 18 validation

## Planning and coordination

- [ ] Requirements, contracts, ownership, risks, fallback, and exclusions still match the unchanged Phase 18 roadmap gate.
- [ ] Phase 03 remains DONE with its PASS evidence and no competing Phase 18 branch or pull request exists.
- [ ] The owner-authorized early start and the temporary Phase 17 prerequisite wait remain explicit; Phase 18 is not represented as ordinarily READY while Phase 17 is ACTIVE.
- [ ] Before review or merge, Phase 17 is DONE, `main` is refreshed, integration differences are reconciled, and the complete deterministic gate is repeated.
- [ ] Only the phase specification and approved backend source/tests/exports, optional migration/persistence files, and paired manifest/lockfile changes enter the phase.

## Provider-neutral contract and guards

- [ ] Public import paths, symbols, construction, typed inputs/outputs, and safe exceptions match `requirements.md`.
- [ ] Architecture tests prove `yuno_backend.volta.telephony` imports no provider transport, FastAPI, Pydantic API schema, SQLAlchemy implementation, OpenAI, Yuno, or frontend type.
- [ ] Missing human authorization, unknown destination label, disclosure/consent mismatch, unsafe config, or conflicting idempotency replay fails before network I/O.
- [ ] Full phone numbers, credentials, headers, raw payloads, audio, recordings, transcripts, and participant data are absent from public values, representations, errors, logs, fixtures, and evidence.

## Idempotency and persistence

- [ ] One logical idempotency key and canonical fingerprint map to at most one Twilio call under retries and concurrency.
- [ ] Same-key/same-request replay returns the recorded normalized result; same-key/different-request raises a safe conflict.
- [ ] A post-dispatch timeout or connection loss records a typed uncertain outcome and does not automatically issue another provider mutation.
- [ ] When persistence changes, migration upgrade/downgrade, PostgreSQL round trip, uniqueness, locking, rollback, and restart replay tests pass; no remote migration is applied.

## Twilio adapter and lifecycle

- [ ] Current official Twilio documentation is cited for call creation, authentication, statuses, retry behavior, disclosure/consent obligations, and sensitive fields.
- [ ] Tests prove the exact official HTTPS destination, bounded timeouts/response size, accepted form mapping, callback subscriptions, and private allowlist resolution.
- [ ] Success, authentication/permission failure, rate limit, provider rejection, malformed/oversized response, timeout, connection failure, and cleanup map to the accepted safe results or exceptions.
- [ ] Provider identifiers and accepted statuses normalize correctly; duplicate, unknown, and out-of-order events cannot regress a terminal state.
- [ ] Mock transports prove retry boundaries and no live Twilio request, phone call, recording, or participant contact occurs.

## Deterministic checks

- [ ] `uv run ruff check .` from `backend/` passes.
- [ ] `uv run pytest tests` from `backend/` passes.
- [ ] Focused telephony and Twilio adapter tests pass.
- [ ] `make python-check` passes from the repository root.
- [ ] `git diff --check` passes.
- [ ] Complete diff, ignored-file, secret/privacy, dependency, and generated-artifact review finds no unrelated or sensitive content.

## Not applicable

- [ ] API tests, `make generate`, OpenAPI/Orval, CORS, webhook ingress/signature verification, WebSocket/Media Streams, frontend lint/build, and browser checks are recorded as not applicable.
- [ ] Live Twilio sandbox/PSTN trials, deployment, production access, account changes, recordings, Yuno, payments, and financial mutations are recorded as not authorized and not executed.
