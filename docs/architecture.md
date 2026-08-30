# How Volta separates browser and phone-call paths

Volta uses one typed Python core for both its browser proof and its phone-call evolution. This page explains each transport, authority boundary, storage boundary, and validation status.

## Read the architecture and its evidence status

The diagram separates demonstrated behavior from code that still needs live provider proof. Browser application requests use generated HTTPS and JavaScript Object Notation (JSON). Browser audio uses Web Real-Time Communication (WebRTC). Twilio uses HTTPS callbacks and a WebSocket Secure (WSS) media stream. FastAPI owns the application programming interface (API) and provider ingress. Labels in brackets describe the submission evidence.

```mermaid
flowchart LR
    subgraph p0["P0 browser harness"]
        direction TB
        operator["Coordinator or simulated dispatcher"]
        browser["Next.js control tower<br/>Text path: demonstrated<br/>WebRTC path: accepted with waiver"]
        operator --> browser
    end

    subgraph app["Volta application boundaries"]
        direction TB
        api["FastAPI API and provider ingress<br/>Pydantic contracts, auth, validation"]
        core["Plain-Python core<br/>Mandates, eligibility, negotiation,<br/>commitments, recovery, audit"]
        postgres[("PostgreSQL<br/>Operational state and opaque evidence references")]
        audio[("Private audio storage<br/>Recording bytes outside Git and PostgreSQL")]
        api -->|"Typed Python calls"| core
        core -->|"Transactions and repositories"| postgres
        core -->|"Provider-neutral storage port"| audio
    end

    realtime["OpenAI Realtime<br/>WebRTC and server WebSocket"]

    subgraph p01["P0.1 Twilio phone path"]
        direction TB
        participant["Authorized participant<br/>Public switched telephone network"]
        twilio["Twilio Programmable Voice<br/>Media Streams"]
        takeover["Human coordinator takeover<br/>Final-trial-only outcome"]
        participant <-->|"Phone audio"| twilio
        takeover -.->|"Join the same remote leg"| twilio
    end

    browser <-->|"HTTPS and JSON<br/>Generated Orval client"| api
    browser <-->|"WebRTC audio and events<br/>Phase 17 waiver"| realtime
    twilio -->|"Signed HTTPS voice, consent,<br/>and status callbacks"| api
    twilio <-->|"Signed WSS Media Stream<br/>Implemented, not live-proven"| api
    api <-->|"Server WebSocket audio,<br/>events, and tool results"| realtime
    takeover -.->|"Verified takeover action<br/>Final-trial-only"| api
```

The evidence labels have these meanings:

- **Demonstrated**: The deterministic browser and text journey passed through the generated client, FastAPI, the core, PostgreSQL, and private audio playback
- **Accepted with waiver**: Browser WebRTC reached OpenAI Realtime, but the model did not complete the required two-tool roundtrip. The team did not perform qualitative voice checks
- **Implemented, not live-proven**: The signed Twilio HTTPS callbacks and WSS media bridge passed deterministic tests. No authorized Twilio sandbox call proved the complete path
- **Final-trial-only**: Three overlapping phone calls, inbound recovery, and live human takeover have no completed validation claim

See the [Phase 17 validation](project-specs/2026-08-30-17-pass-browser-trial/validation.md) for the explicit Realtime waiver. See the [Phase 19 validation](project-specs/2026-08-30-19-bridge-twilio-media/validation.md) for the unchecked Twilio sandbox evidence.

The [Phase 20 validation](project-specs/2026-08-30-20-add-outbound-call-controls/validation.md) separately proves the consent-gated outbound control, generated request, honest four-state projection, and browser/text fallbacks. That credential-free UI evidence placed no call and does not upgrade the Twilio path to live-proven.

## Keep operational authority in the core

FastAPI translates transport-specific input into typed application calls. It does not select carriers, validate mandates, choose a winner, or mutate commitment state. The core owns those decisions for browser text, browser voice, and Twilio media.

The coordinator approves a structured mandate before negotiation starts. Deterministic core rules then enforce eligibility, price, pickup window, conditions, idempotency, and exactly one active commitment. OpenAI and Twilio transport conversation events, but neither provider grants authority or selects the winner.

Human takeover belongs at the FastAPI and core boundary. A future verified action must preserve the remote phone leg. It must also stop further artificial intelligence (AI) commitment tools atomically. Phase 21 does not claim that final-trial outcome.

## Separate browser and provider ingress

The browser uses generated Orval calls over HTTPS and JSON for application actions. FastAPI’s Pydantic models generate `api/openapi.json`, which generates the TypeScript client under `frontend/src/lib/api/generated/`. Change the Pydantic source first, then run `make generate`; never edit generated files directly.

Browser voice is the narrow provider exception. FastAPI authorizes the request and returns a scoped, short-lived Realtime client secret. The browser keeps it in memory and connects to OpenAI over WebRTC. The standard OpenAI key stays server-side.

Twilio reaches separate provider-ingress routes. FastAPI bounds each form body and verifies signed voice, consent, and terminal-status callbacks before delegation. It also verifies and binds one WSS Media Stream before exchanging bounded audio, events, and tool results with OpenAI Realtime. These provider routes are not browser contracts and do not appear in the generated Orval client.

## Store state and audio on separate boundaries

PostgreSQL stores operations, immutable mandate versions, quotes, commitments, recovery decisions, audit records, evidence metadata, and opaque recording references. Recording bytes never enter PostgreSQL or Git.

The core accesses recording bytes through a provider-neutral private-storage protocol. The local development adapter restricts directories to mode `0700` and files to `0600`; it is not encrypted production storage. A production deployment must replace it before handling real recordings. Authenticated playback returns private, no-store responses without exposing the storage reference.

## Protect credentials and participant data

FastAPI keeps the standard OpenAI key, Twilio credentials, database credentials, signatures, and raw provider payloads away from the browser. Logs and safe errors must exclude authorization values, phone numbers, transcripts, and audio. Twilio callbacks fail closed when signatures, accounts, call bindings, stream bindings, frame limits, or sequence rules do not match.

Volta uses synthetic carriers and operations for the public demo. Private recordings stay outside the repository under explicit access, retention, and deletion controls. Volta does not use Yuno, payments, or payment credentials because the selected Nauta challenge has no payment journey.
