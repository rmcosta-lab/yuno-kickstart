# Volta implementation roadmap

This roadmap is a dependency graph of small outcomes. Phase numbers are stable identifiers, not implicit dependencies. A phase starts only after every declared dependency is merged with its gate evidence recorded.

The graph separates frontend, application programming interface (API), backend, and provider work when stable contracts allow independent delivery. Cross-layer phases remain only where the team must prove an integrated journey.

Four phases can start independently: the control tower shell, OpenAI feasibility, Twilio feasibility, and the core P0 HTTP contracts. Phase 04 is the only initial writer for `api/openapi.json` and `frontend/src/lib/api/generated/**`; frontend implementation phases consume generated types but never edit them. Later Realtime and telephony contract changes are serialized through their API phases.

Provider feasibility phases record evidence and decisions without editing shared manifests, `.env.example`, or application wiring concurrently. P0.1 implementation waits for the complete P0 browser gate, but the early Twilio phase exposes account, compliance, and hosting risks before they threaten the submission.

OpenAI product implementation is split by capability. Structured intake extraction can begin after the mandate boundary is stable, while Realtime event and tool integration waits for the negotiation core. Phase 12 integrates both adapters only after the integrated text slice passes.

See [`mission.md`](mission.md) for product outcomes and [`tech-stack.md`](tech-stack.md) for accepted technology boundaries.

### Fase 01 — Structure the control tower shell

Slug: structure-control-tower

Depends on: none

Conflicts with: none

Gate: The frontend renders a responsive control tower shell with synthetic presentation-only fixtures for intake, mandate review, carrier sessions, comparison, evidence, recovery, escalation, and audit; loading, empty, and error states pass `make frontend-check` plus browser console, network, and responsive smoke tests.

This frontend-only phase owns routes, layout, navigation, reusable visual primitives, and view-level state. It does not edit generated API files, copy HTTP data transfer objects, call providers, or implement business rules.

### Fase 02 — Verify OpenAI Realtime and extraction access

Slug: verify-openai-capabilities

Depends on: none

Conflicts with: none

Gate: Official current documentation and credentialed smoke tests confirm an account-available model for structured extraction, an account-available Realtime voice model, ephemeral client credentials, browser Web Real-Time Communication (WebRTC), server WebSocket events, one tool-call result roundtrip, English audio with natural pacing, barge-in, and reproducible `audio_start_ms` plus item ID evidence; limits and fallbacks are recorded.

This provider-feasibility phase uses synthetic content and keeps standard credentials server-side. It does not implement product behavior or change shared application configuration.

### Fase 03 — Verify Twilio outbound-call feasibility

Slug: verify-twilio-outbound

Depends on: none

Conflicts with: none

Gate: Official current documentation and an explicitly authorized smoke test confirm account and trial restrictions, number and destination rules, request signatures, status events, artificial intelligence disclosure, recording consent, and one bidirectional Media Stream reaching a secure WebSocket endpoint; a compatible public hosting choice and fallback are recorded.

This provider-feasibility phase contacts only an allowlisted test participant after explicit human action. It does not implement negotiation, contact a real carrier, or change shared application configuration.

### Fase 04 — Define the core P0 HTTP contracts

Slug: define-p0-http-contracts

Depends on: none

Conflicts with: none

Gate: Pydantic contracts define intake drafts, operation approval and retrieval, negotiation start, carrier sessions, quotes, candidate commitments, evidence, simulated recaps, briefs, recovery simulations, mandate replacement, escalation, notification, and audit under `/v1`; authorization, idempotency, stale-state, and safe-error semantics have API tests, and OpenAPI plus Orval generation passes.

This contract phase owns Pydantic HTTP models, `api/openapi.json`, and generated frontend artifacts. It defines no domain rule and implements no provider call.

### Fase 05 — Implement operation and mandate rules

Slug: implement-mandate-core

Depends on: 04

Conflicts with: none

Gate: Backend-only tests prove source-prompt retention, versioned extraction-policy references, draft validation, explicit approval, immutable mandate versions, and deterministic checks for price, currency, pickup window, conditions, and authority without importing FastAPI or a database implementation.

This phase defines provider-neutral entities, value objects, application services, and repository protocols.

### Fase 06 — Persist operations, mandates, and audit events

Slug: persist-operation-state

Depends on: 05

Conflicts with: none

Gate: Versioned migrations and backend repository tests persist and reload the intake source, policy version, operation, immutable mandate, status history, and correlated append-only audit events in PostgreSQL; rollback and duplicate-operation cases preserve a consistent state.

This backend-only phase selects the migration runner and implements transactions without exposing database models through the API.

### Fase 07 — Build intake and mandate approval screens

Slug: build-intake-experience

Depends on: 01, 04

Conflicts with: none

Gate: Using the generated client types and an injected test boundary, the frontend submits the canonical prompt, renders the source and policy version, displays editable validation feedback, requires explicit approval, and handles loading, empty, error, retry, and success states without embedding mandate rules.

This frontend-only phase may use synthetic responses that conform to generated types. It does not edit generated files.

### Fase 08 — Implement selection, quotes, and commitments

Slug: implement-negotiation-core

Depends on: 05, 06

Conflicts with: none

Gate: Backend-only tests prove deterministic route and availability filtering, fixed ranking, selection of one to three synthetic carriers, pre-contact escalation when none is eligible, idempotent quote recording, stale-mandate and out-of-mandate rejection, quote comparison, exactly one active winner, superseded history, and atomic retry-safe transitions.

The model never chooses carriers, validates a quote, or changes commitment state. This phase extends the existing repositories and audit services without FastAPI concerns.

### Fase 09 — Build negotiation and comparison screens

Slug: build-negotiation-experience

Depends on: 01, 04

Conflicts with: none

Gate: Using generated client types and injected conforming responses, the frontend renders one to three workflow sessions, quote changes, mandate violations, no-eligible-carrier escalation, comparison, one active winner, loading, reconnect, terminal, and retry states; frontend checks and browser smoke tests pass.

This frontend-only phase does not edit generated files, rank carriers, validate quotes, or decide commitment eligibility.

### Fase 10 — Pass the integrated text negotiation slice

Slug: pass-text-negotiation

Depends on: 06, 07, 08, 09

Conflicts with: none

Gate: FastAPI routes delegate the accepted intake, operation, negotiation, quote, commitment, and audit-state contracts to typed backend services, and the generated client completes the canonical prompt-to-winner journey in text mode against PostgreSQL; no-eligible-carrier, validation correction, duplicate mutation, stale mandate, and out-of-mandate paths pass API tests, `make generate`, `make check`, and browser console and network inspection.

This is the first cross-layer integration phase. It owns API dependency wiring and fixes only integration defects in the already-owned backend and frontend implementations.

### Fase 11 — Implement the OpenAI extraction adapter

Slug: implement-openai-extraction-adapter

Depends on: 02, 05

Conflicts with: none

Gate: A backend adapter implements schema-validated intake extraction behind a provider-neutral protocol; mocked tests cover strict output validation, provider errors, timeouts, retries, and redaction, while a separately marked credentialed test reproduces the accepted Phase 02 extraction capability without exposing a standard credential.

This backend-only phase keeps OpenAI URLs, headers, payloads, and responses outside the domain and API layers. It does not configure a Realtime session or map Realtime events. The deterministic extractor remains available for local tests and fallback demonstrations.

### Fase 12 — Expose the Realtime session boundary

Slug: expose-realtime-boundary

Depends on: 10, 11, 23

Conflicts with: none

Gate: FastAPI wires structured extraction to the OpenAI adapter and exposes a tested `/v1` Realtime client-secret contract that authorizes the demo identity, validates allowed origins, rate limits requests, supplies a privacy-preserving safety identifier, disables caching, and returns a narrowly scoped short-lived credential; OpenAPI and Orval regenerate, and logs and errors contain no standard or ephemeral secret.

This API phase is the sole writer for the Realtime contract and generated client update. It does not create an active browser call.

### Fase 13 — Add browser voice and tool roundtrips

Slug: add-browser-voice

Depends on: 09, 12

Conflicts with: none

Gate: The frontend establishes and tears down an English Realtime WebRTC session with natural pacing, handles microphone and playback permissions, barge-in, reconnect, and text fallback, forwards every tool request to typed `/v1` routes, returns the result with the original call identifier, and exposes no standard credential in source, storage, console, or network logs.

This frontend-only phase reuses the negotiation UI and never mutates commitment state from a browser callback.

### Fase 14 — Preserve evidence and enforce recovery rules

Slug: implement-evidence-recovery-core

Depends on: 08

Conflicts with: none

Gate: Backend-only tests persist provider-neutral call sessions, playable recording references with `audio_start_ms`, item and event identifiers, briefs, and recaps labeled `SIMULATED`; they also prove one mandate-safe renegotiation or reconfirmed replacement with an atomic winner transition and notification, plus one out-of-mandate escalation that resumes only after a new immutable mandate version.

This phase records the selected private evidence-storage mechanism, access rules, and deletion behavior. Both recovery paths preserve superseded commitments and append safe correlated audit events.

### Fase 15 — Expose evidence and recovery routes

Slug: expose-evidence-recovery-routes

Depends on: 12, 14, 24, 25

Conflicts with: none

Gate: FastAPI implements the accepted P0 contracts for evidence, simulated recaps, briefs, notifications, inbound recovery simulations, mandate replacement, escalation, and audit retrieval; API tests cover authorization, idempotency, missing evidence, stale state, and safe errors without changing the committed contract or generated client.

This API-only phase delegates every decision and transaction to typed backend services.

### Fase 16 — Build evidence, recovery, and audit screens

Slug: build-recovery-experience

Depends on: 09, 15

Conflicts with: none

Gate: The frontend plays the agreement turn at the stored offset, distinguishes `CANDIDATE`, `SIMULATED`, active, and superseded states, runs reproducible good and bad inbound simulations, shows notifications and escalation context, supports human mandate replacement, and renders the complete correlated audit timeline with loading and failure states.

This cross-layer phase adds the smallest authenticated evidence-audio retrieval contract and
backend storage-resolution service required by the playback gate, regenerates the client, and
then builds the frontend experience. Browser-facing evidence responses no longer contain the
opaque storage reference, and the browser does not infer operational state.

### Fase 17 — Pass the complete P0 browser trial

Slug: pass-browser-trial

Depends on: 10, 13, 16

Conflicts with: none

Gate: A clean environment completes the canonical English browser journey and the no-eligible-carrier, contradiction, English interruption, permission-denial, reconnect, good-recovery, and bad-escalation scenarios; `make check`, browser console and network inspection, secret review, and every private recording offset pass, and a recorded fallback is reproducible.

This cross-layer gate completes P0 before product telephony implementation begins.

### Fase 18 — Implement the Twilio outbound adapter

Slug: implement-twilio-adapter

Depends on: 03, 17

Conflicts with: none

Gate: A backend provider adapter creates an idempotent outbound call only after explicit human authorization, enforces the destination allowlist, maps provider call identifiers and terminal status, requires disclosure and consent flags, and passes mocked retry, timeout, duplicate-event, redaction, and failure tests without importing FastAPI.

This backend-only phase contains Twilio call-creation URLs, headers, and payload mapping.

### Fase 19 — Bridge Twilio media through FastAPI

Slug: bridge-twilio-media

Depends on: 12, 18

Conflicts with: none

Gate: FastAPI defines and regenerates the minimum telephony contract for one explicitly authorized call to one allowlisted test destination. The call establishes one secure Twilio Media Stream, exchanges bidirectional audio with OpenAI Realtime, delegates at least one tool action to the existing backend services, and terminates without exposing credentials or creating duplicate commitments. Focused API and WebSocket tests and one reproducible authorized sandbox call pass.

This hackathon-scoped API phase owns the minimum telephony contract and generated client update. Backend adapters and services retain provider mapping and operational rules. Later telephony integration and final-trial phases own complete status handling, reconnection, multi-call hardening, and exhaustive retry and signature tests.

### Fase 20 — Add outbound-call controls and status

Slug: add-outbound-call-controls

Depends on: 16, 19

Conflicts with: none

Gate: Using the generated client, the frontend requires a consent checkbox and an explicit `Start demo call` action for one allowlisted destination label. It displays `starting`, `live`, `ended`, or `failed` and provides browser-voice and text fallbacks. It exposes no real phone number, credential, or raw provider payload. One focused frontend test and one desktop browser smoke test pass.

This hackathon-scoped frontend phase consumes only the generated telephony contract. Later telephony integration and final-trial phases own separate provider and network diagnostics, advanced retry and reconnection, and a detailed call timeline. They also own deep evidence and audit integration, responsive coverage, intermediate states, and error-specific visuals.

### Fase 21 — Prepare the public submission package

Slug: prepare-public-submission

Depends on: 17

Conflicts with: none

Gate: The presentation, public repository guide, architecture diagram, decision log, timed demo script, and private recorded fallback tell one consistent story and work from a clean environment; privacy and secret scans confirm that no credentials, real participant data, or private audio entered Git.

This documentation and demo-assets phase can run in parallel with P0.1 implementation. It distinguishes the P0 browser harness from P0.1 telephony and states every known gap.

### Fase 22 — Pass the final P0.1 telephony trial

Slug: pass-final-telephony-trial

Depends on: 20, 21, 26, 27, 28

Conflicts with: none

Gate: An authorized rehearsal exercises the canonical three-carrier fixture through three overlapping outbound public switched telephone network (PSTN) sessions. It completes one mandate-safe inbound recovery call, delivers the final active winner's recap through Twilio WhatsApp, and transfers one live call to the coordinator without disconnecting the remote participant or losing structured context. The delivered recap promotes the winner to `VERIFIED` only when playable timestamp evidence exists. Browser voice, text, simulated recap, and a private recording remain ready as fallbacks, and all five submission artifacts fit the allotted time.

The cross-layer trial reports account and Sandbox restrictions, call and WhatsApp delivery outcomes, overlap, latency, handoff continuity, disconnects, and every remaining challenge gap. It never presents API submission, simulated delivery, or workflow-only concurrency as challenge-verified evidence.

### Fase 23 — Implement the OpenAI Realtime adapter

Slug: implement-openai-realtime-adapter

Depends on: 02, 08

Conflicts with: none

Gate: A backend adapter implements narrow Realtime session configuration and event mapping behind provider-neutral protocols; mocked tests cover session configuration, tool-call and tool-output correlation, provider events, disconnects, timeouts, and redaction, while a separately marked credentialed test reproduces the accepted Phase 02 server WebSocket roundtrip and correlated `audio_start_ms` plus item ID evidence without exposing a standard credential.

This backend-only phase keeps OpenAI URLs, headers, payloads, events, and responses outside the domain and API layers. It does not mint browser credentials, expose an HTTP contract, or allow model events to bypass the deterministic negotiation services.

### Fase 24 — Complete evidence and recovery backend services

Slug: complete-evidence-recovery-services

Depends on: 14

Conflicts with: none

Gate: Backend-only tests prove three outcomes: mandate replacement resolves its post-contact escalation and creates an immutable mandate version; explicit escalation preserves safe structured context without changing a commitment; notification acknowledgement records the actor and timestamp idempotently. PostgreSQL round trips, stale-version handling, audit events, and rollback preserve consistent state. The backend imports no FastAPI types and changes no HTTP contract.

This supporting backend phase defines the typed commands, services, results, and safe exceptions required by the accepted mandate-replacement, escalation-creation, and notification-acknowledgement contracts. It extends the Fase 14 persistence boundary. It does not implement routes, change Pydantic models, regenerate OpenAPI or Orval, or add frontend behavior.

### Fase 25 — Complete the evidence and recovery application facade

Slug: complete-evidence-recovery-application

Depends on: 10, 24

Conflicts with: none

Gate: Backend-only tests expose one provider-neutral application facade for the accepted recap, brief, inbound-recovery, mandate-replacement, escalation, notification-acknowledgement, operation, and audit behaviors; every mutation has atomic fingerprinted idempotency and durable replay, PostgreSQL persists every accepted response fact, complete bounded projections round-trip in deterministic order, and missing evidence, stale state, rollback, and safe exceptions pass without importing FastAPI or changing the HTTP contract.

This supporting backend phase closes the application and persistence gap discovered when Fase 15 began integration. It persists the accepted structured recap and brief facts, owns the deterministic good and bad recovery scripts, resolves the evidence semantics for a replacement commitment, and publishes complete operation and audit projections for recaps, briefs, recoveries, post-contact escalations, and notifications. It may add the smallest reversible migration and backend repository/query extensions required by those outcomes. It does not implement FastAPI routes, change Pydantic models, regenerate OpenAPI or Orval, add frontend behavior, call a provider, or perform a remote migration.

### Fase 26 — Accept and process inbound Twilio calls

Slug: accept-inbound-twilio-calls

Depends on: 15, 19

Conflicts with: none

Gate: A signed Twilio voice webhook answers one authorized real inbound PSTN call. Fail-closed server-owned correlation resolves the allowlisted synthetic caller and exactly one active operation. The call applies artificial intelligence disclosure and recording consent before opening the existing bidirectional Media Stream. One driver-delay scenario uses the browser's deterministic recovery services, completes one mandate-safe update, and persists its status, brief, playable timestamp evidence, and audit events. Focused tests reject invalid signatures, ambiguous correlation, duplicate events, and out-of-mandate changes. One authorized sandbox call proves the accepted path.

This cross-layer telephony phase replaces the simulated inbound transport without duplicating recovery rules. Provider request parsing, signature verification, TwiML, and media ingress stay in FastAPI; operation correlation, mandate decisions, persistence, and audit stay in backend services, and the existing control tower renders only typed application state.

### Fase 27 — Send and verify WhatsApp recaps

Slug: send-verified-whatsapp-recaps

Depends on: 19, 25

Conflicts with: none

Gate: A provider-neutral delivery service idempotently sends the final active winner's bounded recap through Twilio Programmable Messaging for WhatsApp to one allowlisted synthetic participant who explicitly joined the Sandbox and opened the 24-hour customer-service window. Signed asynchronous status callbacks persist provider-neutral delivery state despite duplicates or out-of-order arrival, and only `delivered` plus playable `audio_start_ms` evidence promotes the agreement to `VERIFIED`. Focused adapter, API, generated-client, and control-tower tests cover invalid signatures, retry, timeout, missing evidence, safe errors, and redaction. One authorized Sandbox delivery and visible status prove the accepted path.

This vertical evidence phase owns the external recap adapter, callback ingress, durable verification transition, and visible delivery status. It keeps contact details out of public contracts and logs, preserves `SIMULATED` as the deterministic fallback, and treats an accepted or queued API response as unverified. Production sender onboarding and custom template approval are follow-up work, not hidden prerequisites for the Sandbox gate.

### Fase 28 — Transfer a live call to the human coordinator

Slug: transfer-live-call-to-human

Depends on: 20

Conflicts with: none

Gate: During one authorized inbound or outbound PSTN call, an explicit takeover action presents the coordinator with the current mandate, quotes, transcript-free structured context, and call status. The action joins the coordinator to the same live conversation without disconnecting the remote participant, prevents the artificial intelligence agent from speaking or committing after handoff, and records the takeover outcome in the audit trail. Focused tests cover failure, timeout, duplicate action, and redaction. One authorized sandbox handoff proves the accepted path.

This cross-layer phase keeps provider call-update or conference mapping in the telephony adapter, verified ingress and control actions in FastAPI, human controls in the frontend, and all commitment authority in the backend. A failed handoff leaves the call in an explicit safe state and never fabricates human participation.
