# Phase 23 implementation plan

1. **Freeze provider-neutral contracts and current provider facts**
   - Refresh the official OpenAI WebSocket, conversations/tools, VAD, and server-event schemas before implementing mappings; preserve the Phase 02 account-verified `gpt-realtime-2.1` model unless a separately recorded access fact requires configuration only.
   - Define immutable audio/session/tool/output/event values, the gateway/connection protocols, and the safe exception vocabulary before the adapter depends on them.
   - Prove with architecture tests that the provider-neutral package imports no OpenAI/WebSocket transport, FastAPI, Pydantic API schema, database, Twilio, or frontend type.

2. **Implement the bounded OpenAI WebSocket mapping**
   - Add `websockets` as a direct backend dependency and regenerate `uv.lock` with the manifest/lockfile pair owned by the backend writer.
   - Build immutable redacted provider config and inject the connector for tests; accept only secure provider URLs, positive deadlines, and bounded message sizes.
   - Map the typed request to the documented authorization/safety headers with a privacy-preserving 64-character digest and one `session.update` for English PCM16/24 kHz audio, server VAD, instructions, voice, and allowlisted tools.
   - Wait for `session.updated` before exposing a ready connection and map Base64 audio input/output without retaining chunks.

3. **Map lifecycle, evidence, and tool correlation**
   - Parse allowlisted lifecycle, speech, audio-delta, tool-call, response-complete, response-cancelled, rate/error, and disconnect conditions into the public event/exception vocabulary.
   - Validate JSON type, size, identifiers, non-negative offsets, tool name, and object arguments; ignore only documented non-application/unknown event types.
   - Send a validated `RealtimeToolOutput` as `conversation.item.create` with the original `call_id`, then `response.create`, preserving caller event IDs and ordering.
   - Expose provider-neutral playback truncation and map only a received assistant audio item/content index plus played offset to `conversation.item.truncate` for later WebSocket interruption handling.
   - Keep tool execution outside the adapter so Phase 08 services remain the only operational authority.

4. **Make lifecycle and failure behavior deterministic**
   - Bound connection establishment, session acknowledgement, event receipt, and close; translate authentication, unavailable model, rate limit, provider error, timeout, malformed event, and disconnect into safe typed exceptions.
   - Do not retry an established session or silently reconnect. Guarantee explicit close and async-context cleanup without orphaned sockets or tasks.
   - Allowlist diagnostic fields and prove credentials, safety identifiers, instructions, tool inputs/results, audio, transcripts, raw JSON, and provider close reasons cannot enter logs, exceptions, or representations.

5. **Test beside the behavior and close evidence**
   - Add protocol/value/architecture tests under `backend/tests/volta/realtime/**` and injected-transport tests under `backend/tests/volta/integrations/openai/**`.
   - Cover exact session/audio mapping, event order, unknown/malformed/oversized events, tool/output correlation, duplicate output rejection, provider errors, timeouts, cancellation, disconnects, and cleanup.
   - Add a separately marked credential-gated synthetic test using ignored audio; retain only safe correlation metadata and delete the artifact after the run.
   - Run focused Ruff/pytest during iteration, then `make python-check`, the separately invoked credentialed test when credentials are available, `git diff --check`, a secret/privacy scan, and a complete diff review.

## Ownership and sequencing

- One backend writer owns `backend/src/yuno_backend/volta/realtime/**`, `backend/src/yuno_backend/integrations/openai/realtime.py`, their tests/exports, `backend/pyproject.toml`, and `uv.lock`.
- The phase coordinator owns only this specification directory during planning and validation evidence updates during implementation.
- Provider-neutral contracts land before mapping and tests depend on them; manifest and lockfile change together before importing `websockets`.
- There is no frontend or API workstream, no OpenAPI/Orval generation, no browser check, no database migration, and no parallel writer inside this phase.
- Before editing the manifest/lockfile or OpenAI package exports, refresh open phase/specification pull requests and coordinate if another active branch touches them. Refresh `origin/main` before publication and before Phase 12 consumes the contract.
- No shared mission, stack, roadmap, or challenge-plan change is planned; no other phase depends on a new decision before this phase can merge, and no temporary prerequisite wait remains.
- No deployment, production access, browser credential mint, live phone call, real participant contact, Yuno operation, payment, financial mutation, or unrelated remote change is authorized.
