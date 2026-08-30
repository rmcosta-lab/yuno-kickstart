# Phase 18 validation

Validated on 2026-08-30.

## Planning and coordination

- [x] Requirements, contracts, ownership, risks, fallback, and exclusions still match the unchanged Phase 18 roadmap gate.
- [x] Phase 03 remains DONE with its PASS evidence and no competing Phase 18 branch or pull request exists.
- [x] The owner-authorized early start and the temporary Phase 17 prerequisite wait remain explicit; Phase 18 is not represented as ordinarily READY while Phase 17 is ACTIVE.
- [ ] Before review or merge, Phase 17 is DONE, `main` is refreshed, integration differences are reconciled, and the complete deterministic gate is repeated.
- [x] Only the phase specification and approved backend source/tests/exports, migration/persistence files, and evidence changes enter the phase.

## Provider-neutral contract and guards

- [x] Public import paths, symbols, construction, typed inputs/outputs, and safe exceptions match `requirements.md`.
- [x] Architecture tests prove `yuno_backend.volta.telephony` imports no provider transport, FastAPI, Pydantic API schema, SQLAlchemy implementation, OpenAI, Yuno, or frontend type.
- [x] Missing human authorization, unknown destination label, disclosure/consent mismatch, unsafe config, or conflicting idempotency replay fails before network I/O.
- [x] Full phone numbers, credentials, headers, raw payloads, audio, recordings, transcripts, and participant data are absent from public values, representations, errors, logs, fixtures, and evidence.

## Idempotency and persistence

- [x] One logical idempotency key and canonical fingerprint map to at most one Twilio call under retries and concurrency.
- [x] Same-key/same-request replay returns the recorded normalized result; same-key/different-request raises a safe conflict.
- [x] A post-dispatch timeout or connection loss records a typed uncertain outcome and does not automatically issue another provider mutation.
- [x] Migration upgrade/downgrade, PostgreSQL round trip, uniqueness, locking, rollback, and restart replay tests pass; no remote migration was applied.

## Twilio adapter and lifecycle

- [x] Current official Twilio documentation was consulted for call creation, authentication, statuses, retry behavior, disclosure/consent obligations, and sensitive fields.
- [x] Tests prove the exact official HTTPS destination, bounded timeouts/response size, accepted form mapping, callback subscriptions, and private allowlist resolution.
- [x] Success, authentication/permission failure, rate limit, provider rejection, malformed/oversized response, timeout, connection failure, and cleanup map to the accepted safe results or exceptions.
- [x] Provider identifiers and accepted statuses normalize correctly; duplicate, unknown, and out-of-order events cannot regress a terminal state.
- [x] Mock transports prove retry boundaries and no live Twilio request, phone call, recording, or participant contact occurs.

Official references:

- <https://www.twilio.com/docs/voice/api/call-resource>
- <https://www.twilio.com/docs/usage/rest-api-best-practices>
- <https://www.twilio.com/docs/usage/requests-to-twilio>
- <https://www.python-httpx.org/advanced/timeouts/>
- <https://www.python-httpx.org/exceptions/>
- <https://www.python-httpx.org/advanced/transports/>

## Deterministic checks

- [x] Ruff passes through `UV_CACHE_DIR=/private/tmp/yuno-phase18-uv-cache make python-check`.
- [x] The backend suite passes through `make python-check`: 592 passed, 44 skipped, 2 deselected.
- [x] The focused suite passes without a database: 115 passed, 7 skipped because `TEST_DATABASE_URL` was absent.
- [x] Persistence and migration tests pass against isolated local PostgreSQL: 11 passed.
- [x] `make python-check` passes from the repository root.
- [x] `git diff --check` passes.
- [x] Complete diff, ignored-file, secret/privacy, dependency, and generated-artifact review finds no unrelated or sensitive content.

## Not applicable and not executed

- [x] API tests, `make generate`, OpenAPI/Orval, CORS, webhook ingress/signature verification, WebSocket/Media Streams, frontend lint/build, and browser checks are not applicable.
- [x] Live Twilio sandbox/PSTN trials, deployment, production access, account changes, recordings, Yuno, payments, and financial mutations were not authorized and were not executed.

## Remaining gate

Implementation validation is complete. Review and merge remain blocked until Phase 17 is DONE; then refresh from `main`, reconcile any integration differences, and repeat the full deterministic gate.
