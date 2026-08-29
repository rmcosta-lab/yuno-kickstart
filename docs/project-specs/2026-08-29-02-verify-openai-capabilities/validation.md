# Fase 02 validation

Keep every criterion unchecked until its redacted evidence is recorded. Raw secrets, authorization headers, full provider payloads, personal data, and private audio must never be committed.

## Official contract and account access

- [ ] Record the consultation date and direct official OpenAI URL for Structured Outputs, Realtime model capabilities, client secrets, WebRTC, WebSocket, tool outputs, interruptions, and voice activity events.
- [ ] Record the project account's accessible extraction and Realtime model IDs; distinguish catalog availability from credentialed account access.
- [ ] Record account tier or safe observed rate-limit fields, regional/browser constraints, latency samples, and any spend/quota blocker without exposing identifiers or credentials.
- [ ] Confirm the selected interfaces use the current GA shapes and no obsolete beta header or event name.

## Structured extraction

- [ ] A credentialed Responses API probe returns the canonical synthetic intake as the strict JSON Schema.
- [ ] Independent validation rejects extra fields, invented facts, wrong price/currency/window values, and malformed output.
- [ ] Authentication, unavailable-model, rate-limit, timeout, and invalid-response failures produce safe categories and nonzero exits.
- [ ] Record the selected account-available extraction model and deterministic text fallback.

## Realtime server WebSocket

- [ ] A credentialed server WebSocket session reaches the selected account-available Realtime model and closes cleanly.
- [ ] Spanish audio input and output succeed, with safe timing and terminal event evidence.
- [ ] One `input_audio_buffer.speech_started` event records reproducible `audio_start_ms`, item ID, and event ID correlation to a private artifact.
- [ ] Timeout, provider `error`, disconnect, and rate-limit events are handled without logging a standard or ephemeral credential.

## Realtime browser WebRTC

- [ ] The server mints a narrowly scoped, short-lived client secret; the standard API key is absent from browser source, storage, console, network logs, screenshots, and committed files.
- [ ] A supported browser establishes and tears down the current GA WebRTC call with microphone and audio playback.
- [ ] Spanish speech succeeds and one Portuguese or English interruption resumes coherently.
- [ ] Barge-in interrupts active model audio and the recorded cancellation/truncation behavior is reproducible.
- [ ] Permission denial and connection failure expose a textual error and preserve the deterministic text fallback.
- [ ] The isolated harness is keyboard-operable and does not depend on color alone for status.

## Tool-call roundtrip

- [ ] The model emits the fixed synthetic tool call with schema-valid arguments.
- [ ] The harness returns `function_call_output` with the original `call_id`, requests continuation, and receives a response that uses the result.
- [ ] Invalid tool arguments and provider failures do not execute an unsafe or product-state mutation.

## Security and evidence handling

- [ ] Fixtures contain only synthetic operation, person, carrier, route, rate, and contact data.
- [ ] Redaction review finds no API key, client secret, authorization header, raw provider payload, private audio, or personal data in Git, logs, errors, screenshots, or reports.
- [ ] Any private audio location, access boundary, retention deadline, and deletion result are recorded outside public artifacts.
- [ ] The final report names every unmet gate item and does not present a fallback or documented capability as a passed credentialed test.

## Repository checks

- [ ] `uv run ruff check .` passes; attach the command result.
- [ ] `uv run pytest` passes, including isolated deterministic harness tests; attach the command result.
- [ ] `pnpm lint` from `frontend/` is marked not applicable unless the phase changes frontend code; if it does, the command passes and the scope change is recorded first.
- [ ] `pnpm build` from `frontend/` is marked not applicable unless the phase changes frontend code; if it does, the command passes and the scope change is recorded first.
- [ ] `git diff --check` passes and the staged diff contains only authorized phase artifacts.
- [ ] A final secret/privacy review passes before publication.

## Gate decision

- [ ] **PASS:** every roadmap capability is backed by current official documentation and credentialed evidence, limits and fallbacks are recorded, and Fases 11 and 13 may depend on the merged result.
- [ ] **BLOCKED:** list the concrete account, quota, environment, privacy, or provider-contract blocker; keep dependent Realtime implementation blocked without weakening the gate.
