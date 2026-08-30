# Volta technology stack

This document records shared technology and provider decisions for Volta. The repository constitution in [`AGENTS.md`](../../AGENTS.md) remains the default. The challenge-specific choices and exceptions below follow [`challenge-plan.md`](../decisions/challenge-plan.md).

The repository's application programming interface (API) remains a backend for frontend (BFF). All artificial intelligence (AI) and provider access stay inside the boundaries defined below.

## Decision principles

- Preserve the existing frontend, HTTP boundary, and plain-Python core.
- Keep deterministic operational authority in the backend, not in model prompts or browser callbacks.
- Prove the complete browser journey before depending on real telephony for the demo.
- Isolate external providers behind narrow adapters and avoid infrastructure that does not advance an observable gate.
- Treat provider access, account limits, and model availability as facts to verify during the relevant phase.

## Accepted stack

| Area | Decision | Reason |
| --- | --- | --- |
| Frontend | Next.js App Router, React, and strict TypeScript | Uses the existing application and keeps rendering, browser state, and interaction in one boundary. |
| Interface | Tailwind CSS, shadcn/Base UI primitives, React Hook Form, and Zod | Reuses the repository baseline for a polished control tower and validated forms. |
| Browser data | Orval-generated `fetch` client with TanStack Query | Keeps FastAPI OpenAPI as the contract source and prevents handwritten TypeScript data transfer objects. |
| API/BFF | Python 3.13, FastAPI, Pydantic, and structured logging | Defines typed `/v1` HTTP contracts, validation, authorization boundaries, error translation, and WebSocket ingress. |
| Backend/core | Plain Python application services and provider protocols | Keeps mandate, selection, negotiation, commitment, recovery, and audit rules independent of FastAPI and providers. |
| Persistence | PostgreSQL with SQLAlchemy asyncio and `asyncpg` | Matches the current repository and supports transactional winner replacement and auditable state. |
| Browser voice | OpenAI Realtime over Web Real-Time Communication (WebRTC) | Supports low-latency speech, interruptions, events, and tool calls without routing browser audio through the API. |
| Server AI | OpenAI API for schema-validated intake extraction | Keeps the prompt policy and standard API credentials server-side; deterministic validation follows every extraction. |
| Telephony | Twilio Programmable Voice and bidirectional Media Streams behind an adapter | Defines the minimum P0.1 inbound and outbound public switched telephone network (PSTN) path while keeping telephony out of domain rules. |
| Written recap | Twilio Programmable Messaging for WhatsApp behind a provider-neutral delivery adapter | Avoids the unavailable A2P 10DLC path while proving one real recap to an allowlisted, opted-in Sandbox participant; simulated delivery remains the deterministic fallback. |
| Local runtime | Docker Compose for PostgreSQL, `uv` for Python, and `pnpm` for the frontend | Reuses the checked-in development workflow and keeps local setup small. |

Dependency versions remain in manifests and lockfiles rather than this document.

## Frontend boundary

The frontend owns the control tower, forms, browser session state, microphone and playback controls, Realtime WebRTC lifecycle, visible fallbacks, and user-initiated actions. It calls application behavior only through the generated FastAPI client.

The direct browser-to-OpenAI Realtime connection is the accepted challenge exception. Before creating it, the frontend requests a short-lived, narrowly configured client credential from FastAPI. The standard `OPENAI_API_KEY` never reaches browser code, storage, logs, errors, screenshots, or generated artifacts.

The browser forwards Realtime tool requests to typed `/v1` endpoints. It returns only the backend result to the Realtime session, preserving the original tool-call identifier. A browser callback never creates or changes a commitment by itself.

## Application programming interface and backend-for-frontend boundary

FastAPI owns:

- Pydantic request and response models for every HTTP contract;
- versioned `/v1` routes and the committed OpenAPI document;
- demo authorization, explicit Cross-Origin Resource Sharing (CORS) origins, rate limits, correlation IDs, and safe error translation;
- minting narrowly scoped Realtime client credentials without caching them;
- Twilio request verification, inbound voice, call-status, WhatsApp delivery-status webhook ingress, live-handoff controls, and the server WebSocket boundary for Media Streams;
- dependency wiring from HTTP or WebSocket ingress to typed core services.

FastAPI remains thin. It does not own carrier ranking, mandate decisions, quote eligibility, winner transitions, persistence queries, or provider payload mapping. Application HTTP contracts are regenerated with `make generate` after a Pydantic change.

## Backend/core boundary

The backend owns:

- immutable mandate versions and deterministic checks for price, currency, pickup window, conditions, and authority;
- carrier eligibility, fixed ranking, negotiation state, quote validity, and the atomic active-winner transition;
- commitment evidence, recap state, call briefs, notifications, escalations, and append-only audit events;
- repositories, transactions, and migrations;
- provider-neutral Realtime, telephony, recording, and written-delivery protocols;
- provider adapters containing external URLs, headers, payload models, event mapping, retries, and redaction.

The backend package never imports FastAPI. Provider mutations must be explicit, idempotent where retry is possible, and correlated to the operation and call session.

## Data and evidence

PostgreSQL is the source of durable operation and audit state. Schema changes use versioned migrations; the persistence phase may select the smallest migration runner compatible with the existing SQLAlchemy setup before the first schema is committed.

Winner replacement must be transactional so an operation never exposes two active commitments. Provider event identifiers and application idempotency keys support deduplication and safe retry. Audit records contain safe structured metadata rather than raw provider payloads.

Playable demo audio is private and remains outside Git and PostgreSQL binary columns. The evidence phase must select a private object-storage mechanism and document access and deletion behavior. Local ignored storage is acceptable only for development. Store the recording reference, `audio_start_ms`, item ID, and event ID with the commitment evidence.

## OpenAI and model decisions

- A versioned server policy extracts an operation and mandate draft into a schema-validated structure.
- Coordinator approval, not extraction, creates operational authority.
- OpenAI Realtime handles speech, interruption events, and tool calls; the Python core validates every tool action before state changes.
- The model named in the challenge plan is an initial candidate, not an unchecked runtime assumption. The OpenAI capability phase records the models available to the project account and any limits before implementation depends on them.
- Start with low reasoning effort and measure mandate accuracy and response latency against the fixed trial matrix before changing the configuration.
- Deterministic text mode exercises the same API contracts when speech is unavailable.

## Twilio telephony and messaging decisions

P0.1 uses Twilio for three overlapping outbound calls, one inbound recovery, one WhatsApp recap, and one live coordinator takeover. A human must explicitly start outbound dialing, and every participant must be allowlisted and authorized. Volta discloses that it is an AI system at the beginning of each call and obtains consent before recording. The recap proof uses a Twilio Sandbox participant who has explicitly joined and opened the 24-hour customer-service window; production sender onboarding and custom template approval remain outside the hackathon gate.

FastAPI terminates the public HTTPS and secure-WebSocket ingress. The Twilio adapters own call creation, WhatsApp submission, live-call updates, and provider-specific event mapping. The Realtime adapter owns the server-side OpenAI event stream. These adapters delegate tools and state changes to the same core services used by browser voice and text mode.

Each provider phase must verify current Twilio signatures, trial and Sandbox restrictions, regional rules, number requirements, WhatsApp session and template rules, callback status semantics, recording obligations, and retry behavior against official documentation. Short Message Service (SMS), email, a second recap channel, direct Session Initiation Protocol (SIP), production WhatsApp onboarding, production contact-center routing, and telephony scale beyond the fixed demo are not selected technologies.

## Yuno decision

Volta does not use Yuno, the Yuno Web SDK, or any payment flow. The selected Nauta challenge has no payment outcome, and adding one would increase scope without supporting the demo. Existing payment adapters remain unused and no Yuno credential is required for Volta.

## Testing and verification

Every layer has a deterministic local gate and a separately reported provider trial:

| Concern | Approach |
| --- | --- |
| Python quality | Ruff, public type hints, pytest, and pytest-asyncio through `make python-check`. |
| Domain rules | Deterministic unit tests for mandates, selection, quote validity, idempotency, winner replacement, recovery, and escalation. |
| API contracts | FastAPI tests, committed OpenAPI output, `make generate`, and frontend type checking/build. |
| Frontend | ESLint, TypeScript, production build, component-level interaction tests where valuable, and browser smoke tests. |
| Rendered journey | Browser checks for responsive layout, console errors, network failures, permission denial, loading, reconnect, and fallback states. |
| AI and voice | Mocked event tests plus a separate credentialed matrix for English, natural pacing, noise, contradiction, barge-in, and disconnects. |
| Telephony | Mocked adapters and signature tests, followed by separately marked calls to authorized test destinations. |
| WhatsApp recap | Mocked idempotency, signature, and out-of-order status tests, followed by one separately marked delivery to an allowlisted, opted-in Sandbox participant. |
| Security | Secret and personal-data diff review, origin and authorization tests, redacted-log checks, and recording-access review. |

`make check` is the repository-wide handoff gate for cross-layer code. Credentialed provider trials are reported separately because they require account access, authorized participants, and explicit scope.

## Deployment requirements

Local development uses the existing Next.js and FastAPI processes with PostgreSQL in Docker Compose. The team has not selected a public hosting provider yet.

The Twilio feasibility phase must record a deployment choice before P0.1 depends on it. The target must support:

- Hypertext Transfer Protocol Secure (HTTPS) for the control tower and API;
- stable, secure WebSockets for the Twilio media bridge;
- server-only secret management and explicit allowed origins;
- PostgreSQL connectivity and versioned migrations;
- private, expiring access to audio evidence;
- structured logs with correlation IDs and credential redaction.

A separate network service between FastAPI and the Python core, Kubernetes, Kafka, Redis, Celery, a service mesh, or event sourcing is not part of the accepted stack.

## Accepted deviations from the repository baseline

Three challenge-specific deviations are accepted:

1. **Browser-to-Realtime WebRTC:** the browser connects directly to OpenAI using a scoped ephemeral credential minted by FastAPI. All operational tools still pass through the BFF and deterministic core.
2. **Twilio media bridge:** P0.1 adds a FastAPI WebSocket for bidirectional call audio. This is transport ingress, not a second business service.
3. **No payment integration:** the repository includes Yuno-oriented bootstrap code, but Volta does not activate it for this challenge.

No other architecture or security boundary changes are accepted by this baseline. A future deviation requires an explicit decision record.
