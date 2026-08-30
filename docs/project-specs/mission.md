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
- **P0.1, minimum telephony path**: The same rules and tools support three overlapping outbound calls, one inbound recovery, and one live coordinator takeover before submission. The browser remains the development harness and demo fallback, and written-recap delivery remains explicitly simulated.

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

P0.1 runs three overlapping outbound negotiations over the public switched telephone network (PSTN), one authorized inbound recovery, and one live coordinator takeover. Every call includes artificial intelligence (AI) disclosure and recording consent. The final winner retains a recap labeled `SIMULATED`; the hackathon does not claim external written delivery or `VERIFIED` evidence.

## Success signals

P0 is successful when the browser journey is reproducible in English, survives an English barge-in, and demonstrates all of the following:

- one to three eligible carriers selected without model discretion;
- concurrent workflow sessions with an auditable quote comparison;
- no candidate agreement outside the approved price, currency, pickup window, conditions, or mandate version;
- exactly one active winner, with superseded decisions retained;
- a playable agreement-turn artifact linked by `audio_start_ms`, item ID, and event ID;
- a recap labeled `SIMULATED`, plus a structured call brief and audit trail;
- one autonomous mandate-safe recovery and one human escalation;
- browser voice, text fallback, barge-in handling, and visible prior context for takeover.

The final submission is successful when the P0 evidence remains reproducible and Volta completes the minimum P0.1 path. An authorized rehearsal must prove:

- three overlapping outbound calls
- one mandate-safe inbound recovery
- one recap explicitly labeled `SIMULATED` and linked to playable timestamp evidence
- one coordinator takeover that does not disconnect the remote participant

Browser voice, text, and a private recording remain ready as fallbacks.

## Included scope

P0 and P0.1 include only the capabilities required for the accepted demo:

- A Next.js control tower for intake, mandate approval, carrier sessions, quote comparison, recovery, escalation, and audit.
- A versioned server-side extraction policy followed by explicit coordinator approval and deterministic backend enforcement.
- A synthetic carrier registry with route coverage, declared availability, and fixed priority.
- Typed `/v1` FastAPI contracts generated into the frontend client.
- A plain-Python core for mandate, selection, negotiation, commitment, replacement, notification, escalation, and audit rules.
- PostgreSQL persistence for operational and audit state.
- OpenAI Realtime browser voice over Web Real-Time Communication (WebRTC), with scoped server-issued client credentials and typed tool roundtrips.
- Twilio inbound and outbound Voice with bidirectional Media Streams through a provider adapter and FastAPI WebSocket bridge for P0.1.
- A simulated written recap for the active winner, with no external delivery claim.
- One live coordinator takeover that preserves the remote call and prevents further AI commitments.
- Private demo audio outside Git, synthetic fixtures, consent, redacted logs, and an agreed deletion window.

## Work excluded from the prototype

The prototype excludes production operations and unrelated integrations:

- Real carrier bookings, live rates, transportation-management-system integration, or any production operation.
- Yuno, payments, payment credentials, or financial mutations.
- Short Message Service (SMS), email, other external recap delivery, direct Session Initiation Protocol (SIP), real-carrier integration, or production contact-center routing.
- Telephony scale, routing, and resilience beyond the three authorized outbound calls, one inbound recovery, and one live takeover required by the demo.
- Production-grade identity, multi-tenancy, compliance, retention, billing, analytics, or high availability.
- A prompt-policy administration interface or model-controlled carrier selection.
- Detection of another voice agent or production fraud controls.

## Priorities after P0

### P1: submission reliability and polish

P1 turns the working browser checkpoint into a reliable final submission:

- Complete and rehearse the minimum P0.1 telephony journey, including the mandatory outcomes from Phases 26 and 28.
- Harden loading, error, reconnect, and provider-failure states.
- Present audit evidence, privacy boundaries, and known gaps so judges can inspect them.
- Finish the public setup guide, architecture diagram, presentation, and recorded fallback.
- Run the English, natural-pacing, noise, interruption, and disconnect trial matrix.

### P2: future sophistication

P2 remains outside the hackathon-critical path:

- Add the first external recap channel and production delivery policies.
- Add general inbound routing, a coordinator queue, and multi-party transfer policies.
- Scale beyond the three overlapping demo calls and harden multi-call recovery.
- Add production authorization, retention controls, analytics, and external transportation integrations only after the prototype proves its value.

## Assumptions to verify

The plan depends on these assumptions:

- The Volta drayage case remains the selected challenge unless an explicit shared decision replaces it.
- The team can obtain OpenAI Realtime access and provision Twilio Voice for every authorized participant early enough to complete P0.1.
- The team confirmed English as the primary trial and demo language on 2026-08-29.
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
