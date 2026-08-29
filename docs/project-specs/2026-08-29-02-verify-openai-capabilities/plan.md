# Phase 02 implementation plan

## Ordered work

1. **Refresh facts and access**
   - Re-read the official sources in `requirements.md` and record consultation dates.
   - Confirm the executing environment has the repository skill identifiers, authenticated GitHub access, an ignored `OPENAI_API_KEY`, microphone/playback access, and a supported browser.
   - Query account-visible models and record access, region, quota, and rate-limit blockers without printing credentials.

2. **Freeze synthetic probe contracts**
   - Define one canonical English intake fixture and strict extraction schema.
   - Define one harmless local tool and its typed input/output fixture.
   - Define the redacted result record: model ID, transport, timestamps, safe event IDs, status, latency, observed limit, and failure category.
   - Decide the private temporary audio location and deletion deadline before recording.

3. **Prove structured extraction**
   - Probe candidate account-visible text models with the Responses API and strict JSON Schema.
   - Validate the response independently against the fixture, including explicit missing values and rejection of invented constraints.
   - Select the smallest reliable account-available model for later adapter work and record the fallback.

4. **Prove the server Realtime path**
   - Open a GA Realtime WebSocket session with an account-available voice model.
   - Exercise session setup, English input/output, safe event capture, timeout/close behavior, and rate-limit reporting.
   - Correlate `input_audio_buffer.speech_started` with `audio_start_ms`, item ID, event ID, and the private artifact.

5. **Prove the browser Realtime path**
   - Mint a scoped short-lived client secret on the server and establish the documented browser WebRTC flow.
   - Verify microphone permission, playback, explicit teardown, permission denial, and text fallback.
   - Perform an English turn, one English interruption, and a barge-in while model audio is playing.

6. **Prove the tool roundtrip**
   - Receive the fixed synthetic tool call, validate and execute it locally, and send `function_call_output` with the original `call_id`.
   - Send the documented continuation event and confirm the next model response incorporates the tool result.
   - Record malformed arguments and provider-error behavior without adding product business rules.

7. **Review and publish evidence**
   - Update `validation.md` with redacted evidence links, observed limits, model choices, failures, and fallbacks.
   - Delete temporary secrets and expired/private test artifacts according to the recorded deadline.
   - Run the applicable lint/tests and phase diff/secret review, then submit through `finish-phase` when every roadmap gate item passes.

## Ownership and integration checkpoints

- `ThallesCansi` is the sole writer for the phase spec directory and `experiments/openai-capabilities/**`.
- There are no parallel frontend, API, or backend product workstreams in this feasibility phase.
- No OpenAPI/Orval generation is expected because no Pydantic contract changes. If implementation discovers that a product contract is necessary, stop and route that work to the appropriate later phase instead of expanding this one.
- No manifest or lockfile edit is planned. The team changed the primary demo language from Spanish to English during validation. Because this affects active and future phases, the coordinator routed the shared-spec update through dedicated pull request #2 from the current default branch.
- Phases 11 and 13 must consume the merged evidence rather than assumptions and refresh from the default branch after this phase merges.
- No deployment, production access, live financial mutation, real-carrier contact, or unrelated remote change is authorized.

## Resolved waits

- OpenAI account access, a supported operator browser, and a safe ignored artifact location were available for the credentialed probes.
- No provider documentation or GA event-shape change blocked the selected interfaces.
- Shared-spec pull request #2 merged as `8f1685e`, making English the authoritative project gate before phase submission.
