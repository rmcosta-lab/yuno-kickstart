# Phase 19 validation — Bridge Twilio media through FastAPI

## Planning and coordination

- [ ] Requirements, contracts, ownership, risks, fallback, and exclusions match the unchanged Phase 19 roadmap gate.
- [ ] Phase 12 remains DONE; the consumed Phase 18 base and all remote Phase 17/18/19 branches and pull requests are refreshed before implementation and publication.
- [ ] The 2026-08-30 owner decision and its timing remain explicit: Phase 19 was claimed while Phase 17 was ACTIVE, PR #25 merged immediately afterward, Phase 18 remains ACTIVE, and the roadmap is unchanged.
- [ ] Before Phase 19 review/merge, Phase 18 is integrated or explicitly reconciled, the stacked base is refreshed without rewriting Phase 18 history, and the complete deterministic gate is repeated.
- [ ] Only the phase specification, approved API/BFF source/tests/config, generated OpenAPI/Orval artifacts, and explicitly required paired manifest/lock or safe configuration documentation enter the phase.

## Public HTTP contract

- [ ] Demo authorization, allowed origin, rate limit, request correlation, and required `Idempotency-Key` are enforced before outbound provider I/O.
- [ ] Pydantic request/response models expose only the accepted provider-neutral call facts and reject malformed authorization, destination, consent, and recording combinations.
- [ ] Same-request replay and typed authorization, allowlist, state, idempotency, provider, timeout, rate-limit, invalid-response, and uncertain-outcome errors match `requirements.md`.
- [ ] API tests prove `201` new acceptance, `200` replay, safe non-2xx semantics, zero-I/O guards, and no raw provider or participant data.

## Twilio ingress and signature security

- [ ] Current official Twilio documentation is recorded for exact signature verification, external URL reconstruction, Voice/TwiML, status fields/retries, Media Stream upgrade/frames/limits, and disconnect behavior.
- [ ] Correctly signed synthetic voice, consent, status, and WebSocket requests pass; missing, stale, replayed, malformed, oversized, wrong-origin, wrong-path/query, wrong-call, and tampered cases fail closed.
- [ ] Disclosure and applicable explicit consent occur before the stream starts; recording remains disabled unless separately authorized after consent.
- [ ] Duplicate or out-of-order status events apply once, cannot regress a terminal state, and return success only after verified durable processing.
- [ ] Provider routes, logs, errors, fixtures, and evidence contain no full number, signature, credential, authorization header, raw form, raw payload, audio, transcript, or participant detail.

## Media WebSocket and Realtime bridge

- [ ] One expected call/stream binding is required before media acceptance, is bounded and replay-safe, and exposes no standard credential or private destination.
- [ ] `connected`, `start`, `media`, `mark`, `clear`, and `stop` ordering, frame sizes, encodings, queue depth, idle/total timeout, concurrency, and close codes have positive and negative tests.
- [ ] Accepted Twilio input audio reaches the existing provider-neutral Realtime gateway and accepted Realtime output audio/control reaches Twilio with correct backpressure and barge-in behavior.
- [ ] Every Realtime tool request delegates to the same Volta facade used by browser voice, preserves its original `call_id`, and returns a typed output only after deterministic execution.
- [ ] Duplicate tool/frame/event delivery and every Twilio/OpenAI/application/server disconnect path close resources once and cannot duplicate a quote, commitment, recap, brief, recovery, escalation, or terminal state.
- [ ] Bounded queues, timeouts, task cancellation, client/server half-close, provider errors, malformed events, and shutdown pass without leaked tasks, sockets, secrets, or raw media.

## Architecture, contracts, and generation

- [ ] FastAPI routers remain thin and import typed backend application/provider-neutral contracts without owning domain transitions, persistence queries, or provider call mapping.
- [ ] Backend/core imports no FastAPI/Pydantic API schema, and Twilio/OpenAI URLs, headers, raw payloads, and provider event parsing remain in their accepted adapter/ingress boundaries.
- [ ] API contract tests pass before generation; `make generate` updates `api/openapi.json` and `frontend/src/lib/api/generated/**` only from Pydantic/OpenAPI sources.
- [ ] Generated artifacts are not hand-edited, expose only the browser-consumed outbound-call contract, and pass generated-client tests plus frontend typecheck/build.

## Deterministic checks

- [ ] Focused API, signature, WebSocket, bridge, disconnect, idempotency, and redaction pytest suites pass.
- [ ] `uv run ruff check .` passes for affected Python paths.
- [ ] `uv run pytest` passes for the affected API/backend environment.
- [ ] `make python-check` passes from the repository root.
- [ ] `make generate` passes and its complete generated diff is reviewed.
- [ ] `pnpm lint` passes from `frontend/`.
- [ ] `pnpm build` passes from `frontend/`.
- [ ] `git diff --check`, complete diff/untracked review, and secret/privacy/phone/audio/raw-payload scans pass.

## Authorized sandbox evidence

- [ ] A separate explicit authorization records the synthetic participant label, destination country, origin class, public HTTPS/WSS endpoint, disclosure, consent/recording behavior, expected cost/duration, evidence limits, retention, and cleanup before any call or deployment.
- [ ] One authorized sandbox run proves signed status ingress, accepted secure Media Stream, inbound and outbound audio/events, one correlated tool roundtrip through deterministic services, terminal/disconnect cleanup, and no duplicate commitment.
- [ ] Account restrictions, call result, latency, disconnects, redacted evidence, endpoint cleanup, and any unmet provider gate are reported separately from deterministic repository checks.

## Explicitly not authorized by phase start

- [ ] No production deployment/access, account/number/permission change, real-carrier contact, unapproved PSTN call, recording, Yuno operation, payment, financial mutation, or unrelated remote mutation occurred.
