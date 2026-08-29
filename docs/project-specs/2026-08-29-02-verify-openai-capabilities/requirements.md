# Phase 02 — Verify OpenAI Realtime and extraction access

## Outcome and priority

- **Objective:** retire the OpenAI access and Realtime feasibility risks before product code depends on them.
- **Target user:** the Volta implementation team and demo coordinator.
- **User-visible outcome:** a redacted, reproducible capability report identifies an account-available structured-extraction model and Realtime voice model, proves the required browser and server flows with synthetic English content, and records limits and fallbacks.
- **Priority:** P0 risk-reduction gate for Phases 11 and 13.

## Scope

Included:

- Current official OpenAI documentation for Structured Outputs, Realtime models, client secrets, WebRTC, WebSocket, tools, interruptions, and voice activity events.
- Credentialed probes for one schema-constrained extraction and the complete Realtime gate.
- A minimal isolated smoke harness under `experiments/openai-capabilities/**` and redacted evidence in this phase directory.
- Account-specific model availability, rate-limit observations, latency, browser permissions, English behavior, natural voice pacing, and deterministic fallback decisions.

Excluded:

- Product routes, domain behavior, provider adapters, persistence, generated OpenAPI/Orval files, application wiring, deployment, and changes to shared manifests, lockfiles, or `.env.example`.
- Production data, real carrier details, phone calls, recordings committed to Git, or any Yuno/payment work.
- Treating documented model availability as proof of access; the project account must pass the credentialed probes.

## Coordination

- **Branch:** `phase/02-verify-openai-capabilities`
- **Owner:** `ThallesCansi`
- **Tracking Issue:** none requested
- **Depends on:** none
- **Conflicts with:** none
- **Roadmap gate:** official current documentation and credentialed smoke tests confirm an account-available extraction model, an account-available Realtime voice model, ephemeral client credentials, browser WebRTC, server WebSocket events, one tool-call result roundtrip, English audio with natural pacing, barge-in, and reproducible `audio_start_ms` plus item ID evidence; limits and fallbacks are recorded.

## Decisions, assumptions, risks, and fallback

- Use the current GA Realtime interface. The official docs currently identify `gpt-realtime-2.1` as a Realtime model with audio input/output and function calling, but the probe selects it only if the project account confirms access.
- Use WebRTC for the browser probe and WebSocket for the server probe. A standard API key remains server-side; a short-lived client secret may exist only in browser memory for the probe session.
- Use a fixed synthetic English drayage fixture and one short English interruption. No prompt or audio contains a real person, carrier, shipment, or contact detail.
- Record sanitized event names, IDs needed by the gate, timings, statuses, model IDs, and limits. Never record authorization headers, standard or ephemeral secrets, full provider payloads, or raw/private audio in Git.
- Main risks are unavailable models, quota or regional restrictions, microphone/browser denial, non-reproducible interruption behavior, and missing evidence correlation.
- If Realtime access is unavailable, retain deterministic text mode and a recorded browser fallback as the demo path, record the exact account blocker, and do not claim the Phase 02 gate or unblock dependent Realtime implementation.

## Acceptance criteria

- One model available to the project account returns a strict schema-conforming extraction of the canonical synthetic intake, with missing facts represented explicitly rather than invented.
- An account-available Realtime voice model completes both a browser WebRTC session and a server WebSocket session using the current GA event shapes.
- The browser obtains a scoped, short-lived client secret without exposing the standard API key and completes English audio input/output at a calm, conversational pace.
- A synthetic tool request is executed locally, returned as `function_call_output` with the original `call_id`, and followed by a model response.
- The operator interrupts model audio; the harness captures the cancellation/truncation behavior and the conversation continues coherently.
- A caller turn produces a reproducible `input_audio_buffer.speech_started` event whose `audio_start_ms`, item ID, and event ID correlate to the private test artifact during validation; only its redacted digest and metadata remain after scheduled deletion.
- The report records model IDs, transport choices, observed limits and latency, failures, browser requirements, redaction review, and fallback status without exposing secrets or personal data.

## Contract gates

### Provider HTTP and event boundary

This phase creates no repository `/v1` application route. Its isolated probes verify the current official provider boundaries without freezing their payloads into product code:

- a Responses API request with a strict JSON Schema must return a successful, schema-valid extraction; authentication/authorization, unavailable-model, rate-limit, timeout, and invalid-response failures are categorized and redacted;
- the server creates a narrowly scoped short-lived Realtime client secret, and the browser establishes the documented WebRTC call without receiving the standard key;
- the trusted server opens the documented Realtime WebSocket connection and records only the safe event fields required by the gate;
- all unexpected HTTP statuses and Realtime `error` events fail the probe with a typed local category and safe diagnostic summary.

Exact request and event shapes must be re-read from the official documentation during implementation rather than copied from this planning document.

### Application boundary

No production application service, import path, public symbol, or exception contract is introduced. The smoke harness is a disposable provider-feasibility boundary with typed local inputs (synthetic fixture and selected model IDs), typed redacted results, explicit nonzero failure exits, and no imports from FastAPI or Volta domain modules. Phase 11 will define the reusable provider-neutral protocols and adapter exceptions after this gate passes.

### Browser/server handoff and terminal result

The server exchanges its standard credential for a scoped client secret; the browser keeps that secret in memory only, establishes WebRTC, and sends/receives Realtime events over the data channel. Tool calls cross only the synthetic harness boundary, and tool output preserves the original `call_id`. The terminal result is a reviewed capability matrix in `validation.md`, not an application state change.

## Layer and quality decisions

- **Frontend:** no product UI; only an isolated browser harness with explicit microphone start/stop, connection status, and text fallback controls.
- **API/BFF:** no FastAPI route or OpenAPI change.
- **Backend/core:** no domain or application behavior; the server probe must not import FastAPI.
- **Data:** no database or durable operational state. Private audio, if retained temporarily, stays outside Git with a documented deletion time.
- **OpenAI:** official documentation and credentialed probes are both required; neither substitutes for the other.
- **Security:** server-only standard key, ephemeral browser credential, synthetic data, redacted logs, no caching or committed recordings.
- **Visual/accessibility:** product visual design is not applicable; the harness must remain keyboard-operable and expose textual connection/error state for the test operator.

## One-writer ownership

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-02-verify-openai-capabilities/**` | `ThallesCansi` | Phase decisions and redacted evidence only |
| `experiments/openai-capabilities/**` | `ThallesCansi` | Isolated synthetic smoke harness only |
| Private audio and raw provider traces | `ThallesCansi` | Outside Git; retain only for the agreed test window |
| `.env` | local operator | Ignored, never staged or displayed |
| `.env.example`, application paths, generated files, manifests, and lockfiles | no phase writer | Excluded from this phase |
| Shared mission, stack, roadmap, and challenge decision | no phase writer | No change required |

## Official sources to refresh during implementation

- [Realtime and audio](https://developers.openai.com/api/docs/guides/realtime)
- [Realtime WebRTC](https://developers.openai.com/api/docs/guides/realtime-webrtc)
- [Realtime WebSocket](https://developers.openai.com/api/docs/guides/realtime-websocket)
- [Realtime conversations and tool outputs](https://developers.openai.com/api/docs/guides/realtime-conversations)
- [GPT-Realtime-2.1 model](https://developers.openai.com/api/docs/models/gpt-realtime-2.1)
- [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
