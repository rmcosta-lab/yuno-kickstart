# Volta project mission

Volta is a real-time voice agent for coordinating drayage negotiations. This mission turns the accepted challenge direction in [`challenge-plan.md`](../decisions/challenge-plan.md) into the shared product baseline for implementation.

## Ground-transport coordination problem

Ground-transport coordination depends on phone conversations whose quotes, conditions, and changes remain outside the operation record. A coordinator cannot reliably compare several negotiations, prove what was agreed, or recover from a failed carrier without repeating manual work and risking an unauthorized commitment.

## Operations coordinator

The primary user is an operations coordinator at an importer or freight forwarder. The coordinator describes the transport need, approves the authority that Volta may exercise, starts negotiations, resolves escalations, and audits the result.

Carrier dispatchers and drivers are conversation participants, not product operators. The hackathon uses authorized people acting from a pre-registered, synthetic carrier fixture; it does not contact real carriers.

## Mandate-safe, auditable coordination

Volta turns messy carrier conversations into mandate-safe, auditable commitments that update the shipment operation.

## Delivery commitment

The project commits to both checkpoints:

- **P0, complete browser journey**: A deterministic simulator proves the full intake, negotiation, recovery, escalation, and audit journey with browser voice and text fallback.
- **P0.1, real outbound telephony**: The same rules and tools support authorized outbound calls through Twilio before the final submission. The browser remains the development harness and demo fallback.

The project does not describe browser audio as telephony or a displayed recap as a verified written commitment.

## P0 journey

The browser checkpoint follows one approved operation from intake through recovery:

1. The coordinator describes the canonical Manzanillo-to-Guadalajara transport request in natural language.
2. Volta extracts an operation draft and a structured mandate under a versioned server policy.
3. The coordinator reviews and approves the draft. Approval creates the active operation and an immutable mandate version.
4. Deterministic rules select up to three eligible synthetic carriers by route, availability, and fixed priority. No eligible carrier produces an escalation before any call starts.
5. Volta manages the selected negotiations, records quotes, rejects terms outside the mandate, compares valid options, and selects exactly one active winner.
6. The control tower shows the agreement evidence, a clearly simulated recap, the call brief, and the append-only audit trail.
7. A mandate-safe inbound recovery updates or replaces the winner atomically and notifies the coordinator. An out-of-mandate recovery preserves state and escalates for a human decision.

P0.1 repeats the outbound negotiation over at least one real, authorized public switched telephone network (PSTN) call with artificial intelligence (AI) disclosure and recording consent.

## Success signals

P0 is successful when the browser journey is reproducible in Spanish, survives a mixed-language interruption, and demonstrates all of the following:

- one to three eligible carriers selected without model discretion;
- concurrent workflow sessions with an auditable quote comparison;
- no candidate agreement outside the approved price, currency, pickup window, conditions, or mandate version;
- exactly one active winner, with superseded decisions retained;
- a playable agreement-turn artifact linked by `audio_start_ms`, item ID, and event ID;
- a recap labeled `SIMULATED`, plus a structured call brief and audit trail;
- one autonomous mandate-safe recovery and one human escalation;
- browser voice, text fallback, barge-in handling, and visible prior context for takeover.

The final submission is successful when the P0 evidence remains reproducible and Volta also completes at least one live outbound PSTN negotiation with an authorized participant. A rehearsal must exercise the canonical three-carrier fixture, preserve evidence from every selected session, and retain browser voice, text, and recorded fallbacks.

## Included scope

P0 and P0.1 include only the capabilities required for the accepted demo:

- A Next.js control tower for intake, mandate approval, carrier sessions, quote comparison, recovery, escalation, and audit.
- A versioned server-side extraction policy followed by explicit coordinator approval and deterministic backend enforcement.
- A synthetic carrier registry with route coverage, declared availability, and fixed priority.
- Typed `/v1` FastAPI contracts generated into the frontend client.
- A plain-Python core for mandate, selection, negotiation, commitment, replacement, notification, escalation, and audit rules.
- PostgreSQL persistence for operational and audit state.
- OpenAI Realtime browser voice over Web Real-Time Communication (WebRTC), with scoped server-issued client credentials and typed tool roundtrips.
- Twilio outbound Voice and bidirectional Media Streams through a provider adapter and FastAPI WebSocket bridge for P0.1.
- Private demo audio outside Git, synthetic fixtures, consent, redacted logs, and an agreed deletion window.

## Work excluded from the prototype

The prototype excludes production operations and unrelated integrations:

- Real carrier bookings, live rates, transportation-management-system integration, or any production operation.
- Yuno, payments, payment credentials, or financial mutations.
- Real inbound PSTN calls, direct Session Initiation Protocol (SIP), Short Message Service (SMS), email, or a production recap-delivery provider.
- A claim of literal simultaneous audio across three carrier calls.
- Production-grade identity, multi-tenancy, compliance, retention, billing, analytics, or high availability.
- A prompt-policy administration interface or model-controlled carrier selection.
- Detection of another voice agent or production fraud controls.

## Priorities after P0

### P1: submission reliability and polish

P1 turns the working browser checkpoint into a reliable final submission:

- Complete and rehearse the P0.1 outbound telephony journey.
- Harden loading, error, reconnect, and provider-failure states.
- Present audit evidence, privacy boundaries, and known gaps so judges can inspect them.
- Finish the public setup guide, architecture diagram, presentation, and recorded fallback.
- Run the Spanish, mixed-language, noise, interruption, and disconnect trial matrix.

### P2: future sophistication

P2 remains outside the hackathon-critical path:

- Deliver written recaps through an accepted SMS or email provider so eligible commitments can become `VERIFIED`.
- Add real inbound telephony and in-call human transfer.
- Evaluate literal multi-call audio overlap only if the operational and demo value justifies the complexity.
- Add production authorization, retention controls, analytics, and external transportation integrations only after the prototype proves its value.

## Assumptions to verify

The plan depends on these assumptions:

- The Volta drayage case remains the selected challenge unless an explicit shared decision replaces it.
- The team can obtain OpenAI Realtime access and provision Twilio for authorized destinations early enough to complete P0.1.
- Spanish is the primary trial language; the judges' expected language will be confirmed before the final rehearsal.
- Team members or judges can act as carrier dispatchers and consent to AI disclosure and private demo recording.
- Synthetic names, phone numbers, rates, and routes are sufficient to demonstrate the workflow.
- A deployment target can provide HTTPS, secure WebSockets, server-only secrets, PostgreSQL connectivity, and private audio access.

## Risks to the demo

The phase gates must expose these risks before they threaten the final trial:

- Realtime or Twilio access, account limits, destination restrictions, or hosting constraints may block the PSTN path.
- Prompt extraction or speech recognition may omit, invent, or mistranscribe a constraint.
- Model speech may diverge from persisted state or attempt an out-of-mandate action.
- Concurrent sessions or recovery may create multiple active winners or reuse a stale quote.
- Audio evidence may not remain playable at the stored turn offset.
- Public demo credentials, recordings, or participant data may leak.
- The team may spend too much time on telephony or polish before the complete P0 journey works.

## Fallback when live services fail

Browser voice and text exercise the same typed tools and deterministic core when PSTN or browser audio fails. A private recording demonstrates the complete operation when the live environment is unavailable. Provider failures must remain visible and must not be represented as a successful real-phone trial; without the authorized PSTN evidence, P0 can still be demonstrated, but the final P0.1 success signal remains unmet.
