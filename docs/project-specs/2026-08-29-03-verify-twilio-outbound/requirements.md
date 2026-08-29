# Phase 03 requirements — Verify Twilio outbound-call feasibility

## Objective and outcome

- De-risk Volta's P0.1 outbound public switched telephone network (PSTN) path before product telephony implementation begins.
- Serve the hackathon team and demo operator by producing a current, reproducible PASS or BLOCKED feasibility verdict for Twilio Programmable Voice and bidirectional Media Streams.
- Finish with safe evidence for account and trial restrictions, number and destination rules, request verification, status callbacks, artificial intelligence (AI) disclosure, recording consent, secure WebSocket media in both directions, a compatible hosting choice, and a fallback.
- This is an early P0.1 risk-reduction phase. It does not change the complete-browser P0 priority.

## Scope

Included:

- Consult current official Twilio sources and record each source URL, title, access date, relevant account mode or region, and conclusion.
- Inspect the available Twilio account without exposing credentials and record the restrictions that affect an authorized outbound demo call.
- Define a synthetic destination label and keep the real allowlisted phone number outside Git, logs, screenshots, and evidence artifacts.
- Validate the official request-verification procedure against the exact public callback URL used by the smoke test.
- Observe safe call-status evidence and one Twilio bidirectional Media Stream reaching a Transport Layer Security (TLS)-valid secure WebSocket endpoint in both directions.
- Use a deterministic loopback, tone, or other non-product media response for the feasibility proof; Phase 03 does not depend on OpenAI access or negotiation behavior.
- Record the required AI disclosure and recording-consent procedure for the authorized participant, including the point at which recording may begin.
- Select a public hosting approach compatible with Hypertext Transfer Protocol Secure (HTTPS), secure WebSockets, secret isolation, and Twilio callbacks, plus a documented fallback.

Excluded:

- Product negotiation, mandate, quote, commitment, evidence, or audit behavior.
- Calls to a real carrier, real booking activity, production traffic, real inbound PSTN, Short Message Service, email, or direct Session Initiation Protocol.
- Frontend, API/BFF, backend/core, OpenAPI, Orval, database, migration, `.env.example`, manifest, lockfile, or shared application wiring changes.
- Selecting or integrating the OpenAI Realtime model; Phase 02 and later phases own those decisions.
- Provisioning hosting, buying a number, changing account settings, placing a call, or recording audio without the operator's explicit implementation-time authorization.
- Committing credentials, full phone numbers, raw provider payloads, private audio, participant personal data, or authentication material.

## Coordination and gate

- Branch: `phase/03-verify-twilio-outbound`
- Planning directory: `docs/project-specs/2026-08-29-03-verify-twilio-outbound/`
- Owner and team contact: `rmcosta-lab`
- Tracking Issue: none requested
- Depends on: none
- Conflicts with: none
- Roadmap gate, unchanged: Official current documentation and an explicitly authorized smoke test confirm account and trial restrictions, number and destination rules, request signatures, status events, artificial intelligence disclosure, recording consent, and one bidirectional Media Stream reaching a secure WebSocket endpoint; a compatible public hosting choice and fallback are recorded.

## Assumptions, risks, and fallback

- The operator can access a Twilio account, an eligible originating number, and an allowlisted test participant; the phase must record a blocker rather than infer access.
- The current account mode, destination geography, number capabilities, regional rules, and provider policies may differ from remembered or tutorial behavior and must be verified from official sources and account evidence.
- Callback verification can fail when a proxy or tunnel changes the public scheme, host, path, port, or parameters. The evidence must name the exact externally visible URL used for verification without including secrets.
- Trial announcements, verified-destination limits, geographic permissions, or number availability may prevent a representative final call.
- A tunnel may prove transport reachability but may not satisfy stable P0.1 hosting needs. The final finding must distinguish smoke-test reachability from the selected compatible hosting approach.
- If account access, an authorized destination, or secure hosting is unavailable, record a BLOCKED verdict with the smallest next action. Browser voice, text mode, and the private recorded demo remain the presentation fallback, but P0.1 stays explicitly unmet.
- If current evidence invalidates an accepted shared stack decision, stop and route the decision through `manage-shared-specs`; do not edit shared specifications silently in this phase.

## Acceptance criteria

1. A findings artifact maps every roadmap-gate claim to official Twilio documentation and safe observed evidence, with uncertainties labeled.
2. The findings state the account mode, relevant trial restrictions, eligible originating-number requirements, destination verification or geographic-permission constraints, and the impact on the canonical three-participant rehearsal without exposing private account data.
3. An explicitly authorized human action initiates the only smoke call to a pre-approved allowlisted participant; the evidence records authorization, synthetic participant label, disclosure, consent outcome, and timestamps without a full phone number or private audio.
4. The exact callback request used in the test passes the official Twilio request-verification procedure, and a negative tampering case fails safely.
5. Safe status evidence demonstrates the observed call lifecycle and identifiers needed for later adapter design without treating raw provider fields as application contracts.
6. A secure WebSocket endpoint receives Twilio stream lifecycle and media traffic and sends a deterministic media response back to the authorized call. Evidence includes safe timestamps or redacted identifiers, not raw audio or complete provider payloads.
7. The findings select a compatible public hosting approach and record HTTPS, secure-WebSocket, callback, secret-management, operational, and fallback considerations. Phase 03 does not deploy it.
8. The verdict is PASS only when every unchanged roadmap-gate claim is evidenced. Otherwise it is BLOCKED, names the unmet claim, and preserves the browser/text/recorded fallback without implying telephony success.
9. Repository review confirms that no credential, full phone number, private audio, participant personal data, or unrelated change entered Git.

## Contract and layer decisions

- HTTP contract gate: not applicable. Phase 03 adds no `/v1` route, Pydantic request or response, status code, or application error semantic. Provider callback observations inform Phase 19 but do not define its contract.
- Application contract gate: not applicable. Phase 03 adds no importable product module, public symbol, typed application input or output, or domain exception. Any disposable feasibility harness remains outside the application packages.
- Provider boundary: Twilio PSTN and callback traffic may reach only the explicitly authorized feasibility endpoint. The test must not import or invoke Volta domain services.
- Browser/server handoff: not applicable. There is no browser payment, Yuno, or product Realtime handoff in this phase.
- Terminal user-visible result: a PASS or BLOCKED feasibility dossier for the team, not an application screen or a claimed carrier commitment.
- Data: safe documentation evidence only; no PostgreSQL or private-audio persistence.
- Yuno and payments: not applicable and excluded.
- Visual and accessibility: no product user interface changes. Evidence must remain readable and redact private data.

## One-writer ownership

| Path or resource | Writer | Decision |
| --- | --- | --- |
| `docs/project-specs/2026-08-29-03-verify-twilio-outbound/**` | `rmcosta-lab` | Phase plan, findings, redacted evidence index, and final verdict |
| `scripts/twilio_feasibility/**`, only if a reproducible disposable harness is necessary | `rmcosta-lab` | Non-product harness only; no application imports and no committed secrets |
| `frontend/**` | none | Excluded |
| `api/**` and `api/openapi.json` | none | Excluded |
| `backend/**` | none | Excluded |
| `frontend/src/lib/api/generated/**` | none | Excluded; never edit generated files |
| Python and frontend manifests and lockfiles; `.env.example` | none | Excluded by the roadmap phase boundary |
| `mission.md`, `tech-stack.md`, `roadmap.md`, and `challenge-plan.md` | none | No shared-spec edit; route invalidated decisions through `manage-shared-specs` |
| Twilio account, phone number, callback endpoint, and hosting account | `rmcosta-lab` as test operator | Read-only inspection until separate explicit authorization for each external mutation or call |
