# Phase 23 validation

## Planning and scope

- [ ] Requirements, application contracts, ownership, risks, fallback, and exclusions still match the Phase 23 roadmap gate.
- [ ] Phase 02 PR #3 and Phase 08 PR #12 remain merged with their required evidence, and no active declared conflict or competing Phase 23 branch/PR exists.
- [ ] Only the phase specification, approved backend source/tests/exports, `backend/pyproject.toml`, and paired `uv.lock` changes enter the phase.
- [ ] FastAPI, HTTP/WebSocket ingress, OpenAPI/Orval, frontend, persistence, Twilio, Yuno, payment, deployment, and production work remain absent.

## Provider-neutral backend contract

- [ ] `RealtimeGateway.connect` and the `RealtimeConnection` async lifecycle match the frozen public import paths and typed signatures.
- [ ] Session, tool, output, audio, lifecycle, and evidence values are immutable, bounded, redacted, and provider-neutral.
- [ ] Exceptions expose only the accepted safe metadata and never carry credentials, instructions, tool data, audio, transcripts, raw JSON, or provider exception text.
- [ ] Architecture tests prove `yuno_backend.volta.realtime` imports no `websockets`, OpenAI SDK, FastAPI, Pydantic API schema, SQLAlchemy, Twilio, or frontend code.
- [ ] The adapter emits typed tool requests only; no provider event invokes or bypasses Phase 08 carrier, quote, mandate, or commitment services.

## OpenAI WebSocket adapter

- [ ] Current official OpenAI WebSocket, conversations/tools, VAD, and server-event documentation is refreshed and linked in the final evidence.
- [ ] `backend/pyproject.toml` declares the selected `websockets` runtime dependency and `uv.lock` is regenerated atomically without unrelated dependency churn.
- [ ] Tests prove the secure URL, bearer/safety headers, configurable model, English PCM16 mono 24 kHz session, server VAD, voice, instructions, and allowlisted tool mapping.
- [ ] Audio append/output deltas, session readiness, speech start/stop, response completion/cancellation, and safe provider failures map exactly to typed values.
- [ ] `RealtimeSpeechStarted` preserves event ID, item ID, and non-negative `audio_start_ms` without retaining audio content.
- [ ] Tool arguments are bounded parsed objects; output preserves the original `call_id` and sends `conversation.item.create` before `response.create` exactly once.
- [ ] Unknown non-application events are safely ignored, while invalid JSON, oversized/binary messages, malformed mapped events, invalid tool data, and provider `error` events fail closed.

## Lifecycle, reliability, and redaction

- [ ] Connect, session-update, receive, cancellation, explicit close, context exit, clean disconnect, and unclean disconnect tests are deterministic and leave no socket or reader task open.
- [ ] No established session is retried or reconnected implicitly; every failure has a safe typed terminal result for the caller.
- [ ] Object `repr`, exceptions, captured logs, diagnostics, and test failures contain no API key, authorization header, safety identifier, instructions, tool arguments/results, audio, transcript, full payload, or raw close reason.
- [ ] Synthetic fixtures use no real carrier, participant, rate, operation, or personal data.

## Deterministic checks

- [ ] `uv run ruff check .`
- [ ] `uv run pytest`
- [ ] `uv run pytest backend/tests/volta/realtime backend/tests/volta/integrations/openai -m 'not openai_credentialed'`
- [ ] `make python-check`
- [ ] `git diff --check`
- [ ] Complete staged diff and secret/privacy review show no unrelated file, credential, ignored `.env`, raw audio, or generated evidence.

## Separately marked OpenAI trial

- [ ] `uv run pytest -m openai_credentialed backend/tests/volta/integrations/openai/test_realtime_credentialed.py` is run only with explicit local credentials and synthetic ignored audio, or is reported as skipped/unavailable rather than passed.
- [ ] The trial reproduces the Phase 02 `gpt-realtime-2.1` server WebSocket tool call/output roundtrip, receives a completed continuation, and correlates `audio_start_ms`, item ID, and event ID.
- [ ] The standard credential remains server-side; retained evidence contains only model ID, safe correlation IDs, timings, artifact digest/size/duration, and pass/fail category.
- [ ] Temporary audio/evidence is ignored, private, and deleted after the agreed test window; no external state or operational mutation occurs.

## Not applicable

- [ ] API tests, `make generate`, Orval, frontend lint/build, and browser console/network/responsive checks are recorded as not applicable because Phase 23 changes no API or frontend contract.
- [ ] Database migration, PostgreSQL, Supabase/RLS, webhook, CORS, authorization, idempotent financial mutation, Yuno sandbox, Twilio, and phone checks are recorded as not applicable.
