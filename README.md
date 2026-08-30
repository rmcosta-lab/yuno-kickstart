# Volta: mandate-safe drayage coordination

Volta is an artificial intelligence (AI) voice-agent prototype for drayage operations. It turns synthetic carrier negotiations into bounded, auditable commitments. This repository includes a complete deterministic browser and text journey, plus separately reported browser-voice and telephony work.

## Why Volta exists

Drayage coordinators compare quotes and manage changes across phone conversations. Those facts can remain outside the operation record, which makes it hard to prove terms or recover safely.

Volta gives the coordinator control before, during, and after a negotiation:

- The coordinator reviews and approves an immutable mandate
- Deterministic rules select synthetic carriers and enforce price, route, pickup window, and conditions
- PostgreSQL records quotes, evidence, commitments, recoveries, escalations, and an append-only audit history
- The operation keeps exactly one active commitment while preserving superseded decisions

The prototype never contacts or books a real carrier. It uses no Yuno or payment flow.

## Current capability status

The public story uses four evidence states. A test-validated implementation is not presented as live provider proof.

| State | Capability | Evidence and remaining gap |
| --- | --- | --- |
| Demonstrated | Deterministic browser and text journey | Intake, approval, three synthetic sessions, quote comparison, one active `CANDIDATE`, private timestamp evidence, `SIMULATED` recap, brief, recovery, escalation, and audit passed the [Phase 17 trial](docs/project-specs/2026-08-30-17-pass-browser-trial/validation.md) |
| Accepted with waiver | Browser voice over OpenAI Realtime | Credential, stop, disconnect, and reconnect behavior ran. The complete two-tool provider roundtrip and qualitative voice checks did not pass, so browser voice is not a fully verified result |
| Implemented, not live-proven | Consent-gated outbound control and Twilio Media Streams bridge | The control’s generated request, idempotent retry, `starting`/`live`/`ended`/`failed` states, and fallbacks passed credential-free browser checks in [Phase 20](docs/project-specs/2026-08-30-20-add-outbound-call-controls/validation.md). Deterministic route, signature, media, tool, and disconnect tests passed in [Phase 19](docs/project-specs/2026-08-30-19-bridge-twilio-media/validation.md). No authorized sandbox call proved the complete live path |
| Final-trial only | Three overlapping public switched telephone network (PSTN) calls, inbound recovery, and live coordinator takeover | These remain required trial outcomes. This repository does not claim that they succeeded |

`CANDIDATE` and `SIMULATED` describe evidence lifecycle. `ACTIVE` and `SUPERSEDED` describe commitment disposition. `VERIFIED` remains unavailable because the prototype does not deliver an external written recap.

## Run the provider-free demo

The local path uses deterministic extraction, three synthetic carriers, PostgreSQL, and the real FastAPI boundary. It needs no OpenAI, Twilio, Yuno, or payment credential.

### Install prerequisites

Install these tools:

- Python 3.13, selected by `.python-version`
- [uv](https://docs.astral.sh/uv/)
- Node.js 20.9 or later
- [pnpm](https://pnpm.io/) 11.9.0
- Docker with Docker Compose

### Configure the local environment

Copy the safe inventory and install both workspaces:

```bash
cp .env.example .env
make install
```

Keep every provider field empty. Remove the blank `VOLTA_EVIDENCE_STORAGE_PATH=` line so local synthetic evidence uses the application’s operating-system temporary default. In `.env`, keep `VOLTA_EXTRACTION_MODE=deterministic` and set a local-only bearer:

```dotenv
VOLTA_DEMO_BEARER_TOKEN=your_local_demo_bearer_here
NEXT_PUBLIC_INTAKE_USE_TEST_BOUNDARY=false
```

The boundary override sends intake and mandate actions through the local FastAPI service instead of the early frontend fixture. Do not reuse the example bearer in a shared or deployed environment.

### Start PostgreSQL and migrate the schema

Start the database, then apply the versioned migrations:

```bash
make postgres-up
uv run alembic -c backend/alembic.ini upgrade head
```

### Start the API and frontend

Run each service in a separate terminal:

```bash
make dev-api
```

```bash
make dev-frontend
```

Open the control tower at `http://localhost:3000`. FastAPI documentation is available at `http://localhost:8000/docs`.

If the Next.js watcher reports `EMFILE`, use polling for that session:

```bash
WATCHPACK_POLLING=true make dev-frontend
```

## Follow the deterministic story

Use this primary synthetic operation:

```text
Find ground transport for Thursday from the port of Manzanillo to our
warehouse in Guadalajara for at most MXN 9,000. One 40-foot dry container,
standard handling conditions.
```

Enter the local bearer when the control tower requests it. The browser keeps it in memory for the current tab.

1. Open **Intake**, choose **Use canonical prompt**, and submit the request
2. Open **Mandate** and approve the Thursday, MXN 9,000 authority boundary
3. Open **Sessions** and start the negotiation. Confirm that fixed ranking selects three synthetic carriers
4. Open **Comparison** and use text fallback to record MXN 8,500, MXN 9,500, and MXN 8,750 quotes. Confirm that the above-cap quote is rejected
5. Create one evidence-backed candidate from an eligible quote. Confirm that exactly one commitment is `ACTIVE`
6. Open **Evidence** and inspect the private timestamp link, `SIMULATED` recap, and structured brief
7. Open **Recovery** and run the mandate-safe simulation. Confirm atomic replacement, one `SUPERSEDED` commitment, and one notification
8. Run the out-of-mandate simulation. Confirm that the active commitment remains unchanged and an escalation opens
9. Open **Audit** and inspect the ordered record of every decision

Evidence playback requires an authorized private synthetic audio artifact outside Git. If it is unavailable, keep the evidence metadata, recap, and brief visible, then use the documented fallback.

For the separate no-eligible-carrier case, submit this fixture:

```text
Find transport Thursday from Veracruz to Puebla for at most MXN 9,000,
one 40-foot dry container, standard handling.
```

Starting its negotiation creates one pre-contact escalation and no carrier session, quote, or commitment.

## Understand the architecture

The browser calls FastAPI through the generated OpenAPI client. FastAPI delegates typed work to a provider-neutral Python core. Only the core may approve operational state changes, and PostgreSQL stores durable state.

Browser voice is a scoped Web Real-Time Communication (WebRTC) exception. The browser requests a short-lived credential from FastAPI, then connects directly to OpenAI Realtime. The separate telephony path terminates Twilio HTTPS and secure WebSocket ingress at FastAPI before using the same typed core.

Read the [architecture guide](docs/architecture.md) for the full boundary diagram. The [mission](docs/project-specs/mission.md), [technology decisions](docs/project-specs/tech-stack.md), and [challenge decision log](docs/decisions/challenge-plan.md) explain the product and provider choices.

## Use the submission materials and fallbacks

The public package keeps one five-minute narrative across these artifacts:

- [Presentation source](docs/submission/presentation.md)
- [Timed demo script](docs/submission/demo-script.md)
- [Recorded fallback procedure](docs/submission/recorded-fallback.md)

Use deterministic text mode when PSTN, OpenAI Realtime, the microphone, or the network is unavailable. An authorized operator may then use the private recording. Its location, media, participant details, and transcript stay outside Git. A fallback never counts as successful PSTN or Realtime evidence.

## Validate changes

Run the repository gate before handing off code:

```bash
DATABASE_URL= make check
```

Clearing `DATABASE_URL` for this command keeps the missing-configuration test isolated from the local runtime value in `.env`. The gate runs Ruff, pytest, frontend linting, TypeScript checks, and the production frontend build. Regenerate the OpenAPI document and Orval client after changing a Pydantic contract:

```bash
make generate
```

Rendered frontend changes also require browser, console, network, accessibility, and responsive checks. The [HTTP API guide](docs/api.md) describes contract ownership.

## Protect security and privacy

Use synthetic routes, carriers, rates, calls, and participants. Never commit or log provider credentials, bearer values, authorization headers, database URLs, real phone numbers, raw provider payloads, transcripts, or audio.

Standard OpenAI and Twilio credentials remain server-side. The browser receives only a narrowly scoped, short-lived Realtime credential. Store demo audio in private storage outside Git and PostgreSQL binary columns, disclose recording to authorized participants, and delete it under the agreed retention policy.

Volta does not use Yuno, payment credentials, or payment operations. Keep all provider and financial mutations inside a separately authorized task.

## Review known limitations

This hackathon prototype has explicit limits:

- It proves synthetic coordination, not a real booking, live rate, or production operation
- Browser Realtime retains the Phase 17 waiver described in the status table
- The Twilio bridge lacks a complete authorized live sandbox result
- Three-call concurrency, inbound PSTN recovery, and takeover await the final trial
- Written recap delivery remains `SIMULATED`; `VERIFIED` is unreachable
- Full accessibility sign-off remains incomplete
- Local filesystem evidence and the single-instance deployment topology are for the synthetic demo, not production scale
- Production identity, multi-tenancy, compliance, high availability, and transportation-system integration remain out of scope

For hackathon hosting, follow the preserved [Vercel and Render deployment guide](docs/deployment.md). That topology publishes the browser journey; it does not prove the pending live telephony outcomes.

## Contribute within the repository boundaries

Read [AGENTS.md](AGENTS.md) before changing the repository. Layer-specific instructions define ownership for `frontend/`, `api/`, and `backend/`.

Use the [roadmap](docs/project-specs/roadmap.md) for phase dependencies and gates. The [development tooling guide](docs/development-tooling.md) covers project-scoped skills, Model Context Protocol servers, authentication, and browser verification. Branches and pull requests are the coordination mechanism; do not edit generated clients or publish unsupported provider claims.
