# Phase 23 — Implement the OpenAI Realtime adapter

## Objective and terminal outcome

- **Objective:** provide the backend with a narrow, provider-neutral asynchronous Realtime connection that maps OpenAI server WebSocket sessions, audio, tool calls, tool outputs, and evidence events without granting operational authority to model events.
- **Target user:** the operations coordinator who will later use browser voice and authorized telephony while the same deterministic negotiation services remain authoritative.
- **User-visible outcome:** this backend-only phase adds no screen or HTTP route; its terminal result is a tested adapter that Phases 12 and 19 can compose into the browser-credential and telephony boundaries.
- **Priority:** P0, because the Realtime boundary blocks browser voice and the later P0.1 media bridge.

## Scope

### Included

- Provider-neutral immutable session, tool, tool-output, audio, lifecycle, and evidence event values under `yuno_backend.volta.realtime`.
- Provider-neutral `RealtimeGateway` and `RealtimeConnection` protocols plus a safe exception vocabulary.
- An OpenAI server WebSocket adapter under `yuno_backend.integrations.openai` using the Phase 02 account-verified `gpt-realtime-2.1` default, with the model configurable.
- Narrow `session.update` mapping for English audio, PCM16 mono at 24 kHz, server VAD, a selected voice, fixed instructions, and allowlisted function tools.
- Bidirectional audio chunk mapping, provider-neutral playback truncation for WebSocket interruption, typed tool-call parsing, `function_call_output` using the original `call_id`, the subsequent `response.create`, response audio deltas, lifecycle events, and `input_audio_buffer.speech_started` evidence with event ID, item ID, and `audio_start_ms`.
- Explicit connect/session/event timeouts, message-size bounds, deterministic close behavior, injected connector seams, safe provider error translation, and redacted diagnostics.
- Mocked tests for exact mapping, malformed and unknown events, correlation, provider errors, disconnects, timeouts, cancellation, close behavior, and secret/payload redaction.
- A separately marked credential-gated synthetic server WebSocket test that reproduces the merged Phase 02 tool roundtrip and evidence correlation without retaining raw audio, responses, or credentials.

### Excluded

- FastAPI, HTTP or WebSocket ingress, dependency wiring, authorization, CORS, rate limiting, OpenAPI, Orval, and frontend changes.
- Minting ephemeral browser credentials, creating a WebRTC call, browser media handling, Twilio, telephony bridging, call-status webhooks, recordings, or persistence.
- Executing negotiation tools inside the adapter, changing a quote or commitment, selecting a carrier, or bypassing Phase 08 services.
- Intake extraction behavior, provider-driven retries of an established live session, automatic reconnect, deployment, production access, real carrier or personal data, and Yuno/payment/financial mutations.
- Changes to mission, technology stack, roadmap, challenge plan, or generated artifacts.

## Dependencies, coordination, and gate

- **Depends on:** Phase 02, merged in PR #3 with a credentialed `gpt-realtime-2.1` WebSocket roundtrip and correlated VAD evidence; Phase 08, merged in PR #12 with deterministic negotiation services that remain the only operational authority.
- **Conflicts with:** none.
- **Branch:** `phase/23-implement-openai-realtime-adapter`.
- **Owner:** `ThallesCansi`; no tracking Issue was requested.
- **Roadmap gate:** a backend adapter implements narrow Realtime session configuration and event mapping behind provider-neutral protocols; mocked tests cover session configuration, tool-call and tool-output correlation, provider events, disconnects, timeouts, and redaction, while a separately marked credentialed test reproduces the accepted Phase 02 server WebSocket roundtrip and correlated `audio_start_ms` plus item ID evidence without exposing a standard credential.
- **Fallback:** the adapter remains replaceable through the provider-neutral protocols, text mode continues to use the deterministic Phase 08 services, and provider failure is surfaced honestly rather than represented as a completed voice session.

## Decisions and assumptions

- Current official OpenAI documentation defines server-to-server WebSocket as the appropriate trusted-server transport; the standard API key is sent only by the backend and never enters public values, exceptions, logs, fixtures, or evidence.
- The adapter uses `websockets.asyncio.client.connect`, already resolved in `uv.lock`, as a direct backend dependency. The gateway owns each connection only for its async-context lifetime; tests inject a connector rather than opening a network socket.
- `OpenAIRealtimeConfig` owns provider facts: secure base URL, configurable model, redacted API key, connect/close/event timeouts, and maximum message size. `RealtimeSessionRequest` owns application facts: redacted instructions, language, voice, PCM format, VAD choice, safety identifier, and allowlisted tools.
- The accepted session baseline is English, PCM16 mono at 24 kHz, output modality `audio`, `server_vad`, `create_response: true`, and `interrupt_response: true`. Any implementation change to these facts must remain explicit and tested.
- Tool arguments and outputs cross the provider-neutral boundary as bounded JSON objects, never raw JSON strings. The adapter validates object shape and size before emitting a request or sending a result.
- `RealtimeToolCallRequested` carries provider event ID, item ID, original `call_id`, tool name, and parsed arguments. `RealtimeToolOutput` carries caller-generated event IDs, the same `call_id`, and a bounded result; sending it emits `conversation.item.create` and then `response.create` in order.
- `RealtimeSpeechStarted` carries event ID, item ID, and non-negative `audio_start_ms`. `RealtimePlaybackTruncation` carries a received assistant item ID, content index, and played `audio_end_ms` so a later WebSocket bridge can remove unplayed audio after barge-in. Other mapped values cover session readiness, speech stop, output-audio delta, response completion/cancellation, and safe provider errors. Known non-application events may be ignored; malformed mapped events fail closed with a typed error.
- The adapter never invokes Phase 08 services. A caller receives a typed tool request, invokes the appropriate deterministic service, and only then returns its typed result. Model speech or provider events cannot directly mutate operation state.
- No established-session mutation is retried automatically. Connect failure, timeout, or disconnect raises a typed safe error; the caller decides whether a new logical session may be created.
- Safe diagnostics may retain failure category, model ID, event type, provider request/event ID, close code, and duration. They exclude authorization values, safety identifiers, instructions, tool arguments/results, audio bytes, transcripts, and raw provider payloads.
- Current contract references: [Realtime WebSocket](https://developers.openai.com/api/docs/guides/realtime-websocket), [Realtime conversations and tool outputs](https://developers.openai.com/api/docs/guides/realtime-conversations), and [Realtime VAD](https://developers.openai.com/api/docs/guides/realtime-vad).

## HTTP contract gate

Phase 23 changes no HTTP contract and does not regenerate OpenAPI or Orval.

- Phase 12 remains the sole owner of `POST /v1/realtime/client-secrets`, its authorization, origin/rate-limit controls, cache policy, Pydantic models, and generated client.
- Phase 19 remains the sole owner of FastAPI telephony HTTP/WebSocket ingress and Twilio event verification.
- No standard key, provider event, raw payload, close reason, audio bytes, or OpenAI exception may cross an HTTP boundary.

## Application contract gate

| Import path | Public symbols | Construction, typed inputs/outputs, and exceptions |
| --- | --- | --- |
| `yuno_backend.volta.realtime.models` | `PcmAudioFormat`, `RealtimeToolDefinition`, `RealtimeSessionRequest`, `RealtimeToolOutput`, `RealtimePlaybackTruncation`, `RealtimeSessionReady`, `RealtimeSpeechStarted`, `RealtimeSpeechStopped`, `RealtimeAudioDelta`, `RealtimeToolCallRequested`, `RealtimeResponseCompleted`, `RealtimeResponseCancelled`, `RealtimeEvent` | Frozen values validate PCM format, bounded identifiers, privacy-preserving safety digests, tool names/schema objects, non-negative offsets, redacted instructions/audio/results, and the discriminated event union. Provider strings and raw JSON are not exposed. |
| `yuno_backend.volta.realtime.gateway` | `RealtimeConnection`, `RealtimeGateway` | `RealtimeGateway.connect(request) -> AsyncContextManager[RealtimeConnection]`. A connection exposes `send_audio(chunk: bytes) -> None`, `truncate_playback(truncation: RealtimePlaybackTruncation) -> None`, `send_tool_output(output: RealtimeToolOutput) -> None`, `events() -> AsyncIterator[RealtimeEvent]`, and `close() -> None`; all methods are async except the iterator/context construction. |
| `yuno_backend.volta.realtime.errors` | `RealtimeError`, `RealtimeAuthenticationError`, `RealtimeModelUnavailableError`, `RealtimeRateLimitError`, `RealtimeConnectionError`, `RealtimeTimeoutError`, `RealtimeDisconnectedError`, `InvalidRealtimeEvent`, `RealtimeProviderError` | Provider-neutral safe exceptions expose only allowlisted diagnostic metadata and never include credentials, instructions, tool data, audio, transcripts, or raw messages. |
| `yuno_backend.integrations.openai.realtime` | `OpenAIRealtimeConfig`, `OpenAIRealtimeGateway` | Constructed with immutable redacted config and an optional injected WebSocket connector. `connect(request)` owns one server WebSocket context, sends the narrow session update, and returns a protocol-compatible connection or raises only public Realtime exceptions. |

Phases 12 and 19 depend only on the provider-neutral contracts for application composition. OpenAI URLs, headers, Base64, JSON event names, close codes, and request/response mapping remain inside the integration module. The provider-neutral package imports no `websockets`, FastAPI, Pydantic API schema, SQLAlchemy, Twilio, or OpenAI SDK type.

## Browser/server handoff and terminal result

- For the future browser path, Phase 12 mints a scoped client secret and Phase 13 creates WebRTC; Phase 23 does not handle or expose that secret. Shared session intent may be constructed from the provider-neutral request, but browser provider mapping remains outside this adapter.
- For the future telephony path, Phase 19 passes provider-neutral PCM chunks into `RealtimeConnection`, consumes typed audio/tool/evidence events, calls deterministic services, and returns `RealtimeToolOutput` with the original `call_id`.
- The terminal result of Phase 23 is a verified backend contract and adapter. It creates no operation, call, quote, commitment, recording, notification, or user-visible success state by itself.

## Acceptance criteria

- The exact session request maps to the documented GA OpenAI WebSocket URL, bearer and privacy-preserving safety headers, and one narrow `session.update`; secrets and redacted fields are absent from object representations.
- A synthetic PCM stream yields typed lifecycle, audio, tool, and speech-evidence events with stable order and bounded values.
- A caller can truncate only a received assistant audio item at a validated played-audio offset, mapped exactly to `conversation.item.truncate` for later WebSocket barge-in composition.
- A valid function call is emitted once with parsed object arguments; its typed result sends `function_call_output` with the original `call_id` followed by `response.create`.
- Unknown non-application events do not break forward compatibility, while invalid JSON, oversized messages, malformed mapped events, invalid tool arguments, provider `error` events, and unexpected binary messages fail safely.
- Connect timeout, session-update timeout, receive timeout, clean/unclean disconnect, cancellation, explicit close, and context exit have deterministic tests and never leave reader tasks or sockets open.
- No model event invokes or bypasses carrier selection, mandate validation, quote recording, or commitment transitions.
- The credentialed test uses synthetic ignored audio, is skipped without explicit credentials, retains only redacted pass/fail/correlation metadata, and reproduces tool output plus `audio_start_ms`, item ID, and event ID evidence.
- `uv run ruff check .`, `uv run pytest`, focused backend tests, `make python-check`, and `git diff --check` pass; API, frontend, browser, database, Twilio, Yuno, and payment checks remain not applicable.

## Risks and security

- **Provider drift:** refresh official event/session schemas during implementation, isolate mapping, bound unknown events, and fail closed for malformed mapped events.
- **Tool confusion or duplicate output:** validate allowlisted names and JSON objects, preserve `call_id`, send one output per call, and leave idempotent domain mutation to Phase 08 services.
- **Leaked voice content or credentials:** redact representations and exceptions, never log raw events/audio/instructions/tool data, keep `.env` ignored, and retain only safe correlation evidence.
- **Hung or orphaned sessions:** enforce connect/session/receive/close deadlines and structured async-context cleanup.
- **False success after disconnect:** surface a typed disconnect and require the caller to decide whether a new session is authorized; never infer completion from a closed socket.
- **Account/model failure:** retain configurable model selection and deterministic text fallback, and report the credentialed gate separately.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-23-implement-openai-realtime-adapter/**` | `ThallesCansi` | Phase coordinator owns requirements, plan, and validation evidence. |
| `backend/src/yuno_backend/volta/realtime/**` | Phase 23 backend writer | Sole owner of provider-neutral values, protocols, and exceptions. |
| `backend/src/yuno_backend/integrations/openai/realtime.py` and package exports | Phase 23 backend writer | Sole owner of OpenAI WebSocket/session/event mapping and public adapter exports. |
| `backend/tests/volta/realtime/**` and `backend/tests/volta/integrations/openai/test_realtime*.py` | Phase 23 backend writer | Protocol, mapping, lifecycle, redaction, and separately marked credentialed tests. |
| `backend/pyproject.toml` and `uv.lock` | Phase 23 backend writer | Add `websockets` as one direct runtime dependency and update the paired lockfile atomically. |
| Root `pyproject.toml`, `.env.example` | No writer expected | The existing `openai_credentialed` marker and `OPENAI_API_KEY` inventory are sufficient; any change requires a recorded plan update. |
| `api/**`, `frontend/**`, `api/openapi.json`, generated clients | No Phase 23 writer | No transport, UI, or generated contract change. |
| Phase 08 negotiation modules and persistence | No Phase 23 writer | Consume public services only in later integration; do not modify deterministic authority. |
| Shared mission, stack, roadmap, and challenge decision | No Phase 23 writer | A broad discovered decision routes through `manage-shared-specs`; this phase carries none. |
