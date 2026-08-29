# Phase 03 findings — Verify Twilio outbound-call feasibility

## Verdict

**PASS as of 2026-08-29.** The authorized upgraded-account smoke test exercised the exact public HTTPS callbacks and bidirectional WSS boundary, observed the outbound call lifecycle, required in-call DTMF consent, returned deterministic μ-law media, received the matching playback mark, and completed cleanly. The participant confirmed hearing the short tone after pressing `1`. All evidence below is redacted; no full phone number, account or provider identifier, raw callback payload, inbound audio, recording, or transcript is retained.

The decisive account constraint remains: Twilio's current Voice trial strips `<Stream>`, so a free trial cannot satisfy this phase. The operator reported completing the account upgrade and purchasing a Twilio-owned local United States number; read-only Console inspection confirmed the number is active in `US1` with outbound Voice enabled. Brazil low-risk dialing was enabled, high-risk dialing remained disabled, and the operator reported that Twilio's exact-number permission check allowed the private Brazilian destination as low risk. The operator owns that destination and separately authorized two technical calls with recording disabled. The first call reached affirmative consent but exposed a missing WebSocket transport dependency and ended without media; after the dependency, public WSS preflight, and log redaction were corrected, the separately authorized second call satisfied the gate. Neither attempt was retried automatically.

This PASS validates the accepted Twilio outbound callback and Media Stream architecture for the bounded feasibility scope. It removes Phase 03 as a dependency blocker; downstream phases still remain subject to every other roadmap dependency and their own production-grade security, persistence, and deployment gates.

## Gate evidence matrix

| Roadmap-gate claim | Official evidence | Safe observed evidence on 2026-08-29 | Status |
| --- | --- | --- | --- |
| Account and trial restrictions | The current trial lasts 30 days, restricts Voice to verified recipients in the sign-up country, and blocks `<Stream>`. A stable bidirectional-media rehearsal therefore requires an upgraded account. | The operator reported the upgrade; authenticated Console inspection confirmed `US1`, a purchased active number, and Voice enabled. The successful live Stream proves the trial `<Stream>` replacement did not apply. | **PASS** |
| Originating number and destination eligibility | A PSTN `From` value must be an account-owned Twilio number or verified outgoing caller ID. The lower-risk rehearsal choice is an owned number with Voice outbound connectivity. Destination country and exact number class must pass Voice Geo Permissions and the applicable country guidelines. | A Twilio-owned local United States number with Voice enabled originated both authorized calls. Brazil low-risk dialing remained enabled, high-risk remained disabled, and the exact private destination passed Twilio's permission check. No full number entered Git or this dossier. | **PASS** |
| Request signatures | Use a current official SDK with the primary Auth Token, the exact external URL and encoded query, and every received form field; JSON uses the raw body and `bodySHA256`. A proxy must not cause validation against its internal URL. | The disposable boundary reconstructed the configured public origin `https://bangkok-jun-conclude-maker.trycloudflare.com`. A signed synthetic request to the exact `/twilio/status` URL returned `200`, the same signature with a tampered form returned `403`, live Twilio HTTPS callbacks were accepted, and the signed WSS upgrade to `/twilio/media` succeeded. The tunnel was removed after the call. | **PASS** |
| Call-status events | Subscribe explicitly to `initiated`, `ringing`, `answered`, and `completed`. Requests can arrive out of firing order; `completed` can mean a person, interactive voice response system, or voicemail answered. Provider fields remain adapter observations, not Volta contracts. | The successful call emitted redacted `initiated`, `ringing`, `in-progress`, and `completed` observations with sequence numbers `0` through `3`; Twilio represented the requested answered transition as `in-progress`. | **PASS** |
| Artificial-intelligence disclosure and recording consent | Twilio requires compliance with applicable law and recommends obtaining all-party recording consent, clearly explaining recording before it starts, retaining consent evidence, and respecting refusal. Twilio's AI terms require informed consent when applicable. | Before streaming, the participant heard the approved Brazilian Portuguese AI and no-recording disclosure and pressed `1`. The server recorded only `continue_consent=affirmed`; recording remained disabled throughout. | **PASS** |
| Bidirectional secure Media Stream | `<Connect><Stream>` establishes one bidirectional Stream per call over `wss`; the server receives only the inbound track and may send base64 `audio/x-mulaw` at 8 kHz without file headers. `mark` confirms playback unless the buffer was cleared. Official references differ on server-initiated socket closure, so socket close, `stop`, and terminal call status require independent idempotent cleanup. | The TLS-valid WSS connection emitted `connected` and `start`, received inbound media, returned 25 paced deterministic μ-law frames, and received uncleared mark `phase03-tone-1`. Twilio then emitted `stop`, the harness cleaned up, the call completed, and the participant confirmed hearing the tone. | **PASS** |
| Compatible hosting and fallback | Render documents public FastAPI Web Services, managed TLS, inbound WebSockets, environment secrets, health checks, and logs. WebSocket connections can end when an instance is replaced, and Free services can spin down. | A temporary Cloudflare Quick Tunnel provided the separately authorized feasibility boundary and was removed immediately afterward. Paid Render remains the selected P0.1 persistent-service design; no persistent deployment was created in this phase. | **PASS FOR FEASIBILITY** |

## Safe environment and coordination evidence

| Check | Method | Result |
| --- | --- | --- |
| Branch and remote | Refreshed `origin`, inspected remote branches, and compared local and remote phase refs. | `phase/03-verify-twilio-outbound` matched its remote exactly. Phase 01 and Phase 02 were active but neither conflicts with Phase 03. |
| Pull requests and issues | Read-only GitHub CLI queries. | No pull request or issue existed for the phase; no phase pull request was merged. |
| Worktree | `rtk git status --short --branch` before implementation. | Clean at start. |
| Task tooling | Inspected repository skills and MCP inventory. | `implement-phase` and `context7-mcp` were installed. Context7 was configured but its tools were unavailable in-session, so official provider pages were read directly. |
| Twilio shell access | Tested only whether standard credential names and commands were present; values were never printed. | Standard Twilio credential variables, Twilio CLI, and tunnel CLIs were unavailable. |
| Twilio browser access | Read-only inspection of the authenticated Console after operator-led provisioning. | Confirmed `US1`, one active Twilio-owned local United States number with Voice enabled, Brazil low-risk enabled, and Brazil high-risk disabled. Numbers, account identifiers, and balance were not copied into evidence. |
| Official signature vector | One-off `uvx --from twilio` invocation outside repository manifests. | `twilio-python` 9.11.0 returned `true` for Twilio's official synthetic vector and rejected a tampered URL and tampered parameter. |
| External mutations | Reviewed browser, shell, GitHub, and provider actions. | The operator independently upgraded the account, purchased the number, verified caller IDs, and ran the exact destination permission check. After separate approvals, the agent started one temporary localhost harness and Quick Tunnel and created exactly two unrecorded calls. The first exposed the missing WebSocket transport; the separately approved second passed. Both processes were stopped, the tunnel origin was removed, and no automatic retry, persistent deployment, permission change, or recording occurred. |
| Live smoke interval | Redacted structured harness events plus participant confirmation. | The successful call ran from `2026-08-29T19:53:43Z` through `19:54:50Z`. Events were limited to safe aliases, statuses, timestamps, frame counts, consent outcome, and deterministic mark. The participant confirmed hearing the tone after pressing `1`. |

## Official Twilio source catalogue

Every Twilio-specific conclusion below comes from a current official Twilio documentation, guideline, legal, engineering, or Help Center page. Account observations are intentionally not inferred from documentation.

| Official title and direct URL | Accessed | Applicable mode or region | Phase conclusion and uncertainty |
| --- | --- | --- | --- |
| [Twilio trial account](https://www.twilio.com/docs/usage/trials) | 2026-08-29 | Current Console free trial; sign-up-country restriction | Trial lasts 30 days, provides 75 Voice minutes, allows at most five verified recipients, and restricts Voice calls to the sign-up country. Recipient and country restrictions prevent assuming the canonical rehearsal is eligible. |
| [Try out Twilio Voice](https://www.twilio.com/docs/usage/trials/try-out-voice) | 2026-08-29 | Current Console Voice trial | Per-call limit is 10 minutes, total Voice quota is 75 minutes, and concurrency limit is five. `<Stream>` and `<Record>` are blocked and replaced during trial. An upgraded account is mandatory for Phase 03. |
| [Free Trial Account Restrictions and Limitations](https://help.twilio.com/hc/en-us/articles/360036052753-Twilio-Free-Trial-Limitations) | 2026-08-29 | Legacy trial; US1 | Documents the legacy trial announcement and verified-destination limits. The current product-trial page does not confirm whether the announcement remains, so absence must not be inferred. |
| [Call resource](https://www.twilio.com/docs/voice/api/call-resource) | 2026-08-29 | Programmable Voice; default examples use US1 | Defines valid PSTN `From`, outbound call creation, progress callbacks, status semantics, timestamps, sequence numbers, and eventual consistency. A `completed` status is not evidence that a human answered. |
| [Make outbound phone calls](https://www.twilio.com/docs/voice/tutorials/how-to-make-outbound-phone-calls) | 2026-08-29 | Standard or upgraded Programmable Voice | The normal prerequisite is an account-owned Voice-capable Twilio number. The real origin must be inspected rather than inferred. |
| [REST API: Available Numbers](https://www.twilio.com/docs/phone-numbers/global-catalog/api/available-numbers) | 2026-08-29 | Country-specific number catalogue | Outbound Voice connectivity is an explicit capability. The actual owned number must be preflighted. |
| [Protect your account with Voice Dialing Geographic Permissions](https://www.twilio.com/docs/sip-trunking/voice-dialing-geographic-permissions) | 2026-08-29 | Programmable Voice and Elastic SIP; per account or subaccount | Enable only required low-risk countries for a proof of concept and check every masked allowlisted destination. Owner or Administrator access is required to change permissions. Its broad trial reachability text conflicts with the newer sign-up-country trial restriction, so the newer dedicated trial page controls until clarified. |
| [Mexico: Voice Guidelines](https://www.twilio.com/en-us/guidelines/mx/voice) | 2026-08-29 | Mexico destination, country code `+52` | Domestic and international outbound reachability is documented, but mobile numbers must use the current `+52` plus ten-digit plan. Carrier, caller-ID, number-class, account, and permission checks still apply. |
| [Brazil: Voice Guidelines](https://www.twilio.com/en-us/guidelines/br/voice) | 2026-08-29 | Brazil origin or destination, country code `+55` | Outbound restrictions depend on the origin class; Brazilian toll-free and non-Twilio-owned Brazilian origins have documented restrictions. Telemarketing has an additional `0303` rule. This rehearsal is not to be classified without reviewing its exact use. |
| [Requirements for Calling US and Canada Numbers (+1 Country Code)](https://help.twilio.com/articles/42720101060379) | 2026-08-29 | Calls to `+1`; current 2026 profile rules | An approved compliance profile is required. Any `+1` participant adds provisioning lead time and must be checked before authorization. |
| [How Fast Can I Place or Receive Phone Calls with Twilio?](https://help.twilio.com/articles/223180028-How-fast-can-I-place-or-receive-phone-calls-with-Twilio) | 2026-08-29 | Programmable Voice; accounts upgraded on or after 2026-02-03 | A newly upgraded account without an approved profile is limited to two concurrent calls; an approved Individual profile allows three, and Business removes that concurrency cap. Sequential calls avoid this issue, and literal simultaneous audio is not required by the project. |
| [Webhooks security](https://www.twilio.com/docs/usage/webhooks/webhooks-security) | 2026-08-29 | General Twilio webhooks that emit actual traffic | Requires CA-valid HTTPS, SDK signature validation, exact URL encoding, every form parameter, raw JSON plus `bodySHA256`, and tolerance for added parameters. Test credentials do not generate equivalent live evidence. |
| [Security](https://www.twilio.com/docs/usage/security) | 2026-08-29 | Voice and messaging callbacks | Documents the official synthetic vector used locally, primary-token use, whitespace and path preservation, Voice HTTPS port handling, and the Media Streams trailing-slash troubleshooting note. |
| [Secure your Flask app by validating incoming Twilio requests](https://www.twilio.com/docs/usage/tutorials/how-to-secure-your-flask-app-by-validating-incoming-twilio-requests) | 2026-08-29 | Python behind TLS termination or a tunnel | A reverse proxy can expose internal HTTP while Twilio signed public HTTPS. Trust forwarded headers only from the known proxy, or reconstruct from a configured external base plus untouched path and query. |
| [Webhooks (HTTP callbacks): Connection Overrides](https://www.twilio.com/docs/usage/webhooks/webhooks-connection-overrides) | 2026-08-29 | Voice and most Twilio webhooks | URL-fragment overrides are excluded from signing. Retries have bounded policies and expose `I-Twilio-Idempotency-Token`, but ordinary Voice callbacks have no documented exactly-once guarantee. |
| [Voice Webhooks](https://www.twilio.com/docs/usage/webhooks/voice-webhooks) | 2026-08-29 | Programmable Voice, not Elastic SIP status callbacks | Outbound REST calls can request asynchronous progress callbacks. |
| [Webhooks FAQ](https://www.twilio.com/docs/usage/webhooks/webhooks-faq) | 2026-08-29 | General webhooks including Voice status | A status callback is informational and should receive `200 OK`; it does not require TwiML. |
| [Test Credentials](https://www.twilio.com/docs/iam/test-credentials) | 2026-08-29 | Twilio test credentials, distinct from a trial account | Test calls do not connect, request call TwiML, or trigger status callbacks. They cannot satisfy Phase 03. |
| [Understanding Edge Locations](https://www.twilio.com/docs/global-infrastructure/understanding-edge-locations) | 2026-08-29 | US1 default; region-specific credentials and hosts elsewhere | Record and exercise the account region. Legacy two-part non-US regional API hosts stopped working in 2026. |
| [Media Streams Overview](https://www.twilio.com/docs/voice/media-streams) | 2026-08-29 | US1 by default; IE1 and AU1 are also documented | Bidirectional Streams use `<Connect><Stream>`, allow one Stream per Call, expose only inbound audio to the server, and require TCP 443 plus signature validation. Termination references differ on whether closing the server socket stops only the Stream or also the Call, so treat socket closure, `stop`, and terminal call status as separate signals. |
| [TwiML Voice: `<Stream>`](https://www.twilio.com/docs/voice/twiml/stream) | 2026-08-29 | Programmable Voice Media Streams | `wss` is the only supported protocol. Query strings are not accepted on the Stream URL; use custom parameters. Subsequent TwiML waits until the bidirectional socket closes. |
| [Media Streams - WebSocket Messages](https://www.twilio.com/docs/voice/media-streams/websocket-messages) | 2026-08-29 | Bidirectional Media Streams | Defines `connected`, `start`, inbound `media`, `mark`, and `stop`, plus outbound `media`, `mark`, and `clear`. Returned audio must be headerless base64 μ-law at 8 kHz. A returned mark proves playback only when the related buffer was not cleared. |
| [Media Streams Configuration](https://www.twilio.com/docs/global-infrastructure/firewall-configurations/media-streams-configuration) | 2026-08-29 | Programmable Voice Media Streams | Requires public TCP 443 reachability and signature validation during the WSS upgrade. Twilio does not provide a fixed Media Streams source-IP allowlist. |
| [How to Make Outgoing Calls with Twilio Voice, the OpenAI Realtime API, and Python](https://www.twilio.com/en-us/blog/outbound-calls-python-openai-realtime-api-voice) | 2026-08-29 | Official Twilio engineering tutorial; outbound AI voice | Recommends always disclosing AI use. The smoke test follows this conservative rule without treating the tutorial as jurisdiction-specific legal advice. |
| [Legal Considerations With Recording Voice and Video Communications](https://help.twilio.com/articles/360011522553-Legal-Considerations-with-Recording-Voice-and-Video-Communications) | 2026-08-29 | Any recorded call; jurisdiction-dependent | Twilio recommends the strict all-party approach: disclose recording before it starts, obtain and retain consent, secure recordings, and respect refusal. This is not legal advice; counsel must resolve the participant jurisdictions. |
| [Predictive and Generative AI/ML Features Addendum](https://www.twilio.com/en-us/legal/ai-terms/predictive-generative-ai-features) | 2026-08-29 | Listed Twilio AI features when applicable | Requires informed end-user consents where applicable and retention of consent evidence. Custom Media Streams connected to a customer-owned AI service are not clearly listed, so the addendum's feature-specific consent clause must not be overstated. Volta still requires explicit AI disclosure and consent before streaming. |

## Provider observations for later adapters

These are observations verified by the smoke test and retained as guidance for later adapters. They are not FastAPI data-transfer objects, Volta domain states, or promises of exactly-once delivery.

| Observation | Safe handling |
| --- | --- |
| Provider call, account, and stream identifiers | Never publish account identifiers. Store call and stream identifiers only where later adapter correlation requires them; use generated aliases in evidence and redacted logs. |
| `From` and `To` | Treat as sensitive. Do not log or commit them, including partial screenshots or raw callback bodies. Map the destination to `AUTHORIZED_TEST_A` before evidence emission. |
| `CallStatus`, `Timestamp`, and `SequenceNumber` | Treat status as an open provider enum. Use the timestamp and sequence as ordering observations because callbacks may arrive out of order. A late callback must not regress terminal state. |
| `I-Twilio-Idempotency-Token` | Treat as a transport-attempt discriminator, not a documented logical-event identifier. Keep durable effects idempotent and test duplicates explicitly in Phase 18/19. |
| Media event type and counters | Record only event names, safe timestamps, frame/byte counts, deterministic mark labels, and disconnect reason. Do not retain raw provider payloads or inbound audio. |

## Executed smoke-test procedure

### Completed safe preflight

- The operator reports an upgraded account, and authenticated Console inspection confirmed region `US1` plus an active Twilio-owned local United States number with Voice enabled.
- Brazil low-risk Voice dialing is enabled while high-risk dialing remains disabled.
- The operator reported that Twilio's private exact-number permission check allowed the destination as low risk; the number itself was never exposed to the agent or repository.
- The operator owns the Brazilian destination and separately authorized two technical calls with recording disabled: the first diagnostic attempt and the corrected successful attempt.
- `scripts/twilio_feasibility/` implements the disposable signed HTTPS/WSS boundary, pre-Stream disclosure and DTMF consent, single-connection limit, redacted logs, 20-second answer timeout, 60-second call/Stream limit, deterministic tone, and guarded one-call command.
- Five isolated harness tests pass, including exact HTTP signature acceptance, tampered-form rejection, disclosure ordering, media framing, and the returned `mark` sequence. The full repository Python check also passes.

The operator separately authorized the temporary public exposure, each outbound call, recording-disabled behavior, duration, and expected usage charge. Those approvals were scoped to this completed run and do not authorize another call or deployment.

### Preconditions applied

The operator and agent applied these controls outside Git before dialing:

1. Sign in to an **upgraded** Twilio account and record only the safe account mode, effective region, and applicable concurrency/profile class.
2. Select one account-owned Twilio number whose Voice outbound-connectivity capability is confirmed. Keep the full number and all account identifiers outside evidence.
3. Select synthetic participant label `AUTHORIZED_TEST_A`. Keep the real number only in the provider Console or local secret store. Record the safe authorization timestamp and synthetic label in the dossier before allowlisting; never record the number or participant identity.
4. Check the exact destination against Voice Geo Permissions, the relevant country guideline, number class, and any compliance profile. Do not enable high-risk ranges for this proof.
5. After separate authorization, start a localhost-only disposable harness and expose it through one temporary Quick Tunnel origin with HTTPS status/TwiML paths and a WSS media path without secret query parameters. Persistent Render provisioning remains downstream work.
6. Keep Twilio recording disabled and discard media after deterministic validation. If a later separately authorized test needs recording, confirm a deletion timestamp before requesting consent. Without that timestamp, recording remains prohibited.

### Disclosure and consent script

Use Brazilian Portuguese for this authorized Brazilian smoke test and preserve the script version in safe metadata. This participant-specific choice replaces the earlier Spanish rehearsal assumption without changing product language decisions. Deliver the disclosure through non-streaming TwiML before `<Connect><Stream>` so Twilio does not forward participant audio before consent:

> Olá. Eu sou Volta, um assistente automatizado de inteligência artificial operado pela equipe desta demonstração. Este é um teste técnico autorizado; ele não cria reserva nem compromisso real. Seu áudio será processado em tempo real para devolver uma resposta técnica, mas não será gravado nem armazenado. Para autorizar a continuação, pressione um. Para recusar, desligue.

If the participant declines or is unclear, end the call and record only `continue_consent=declined`. If recording was separately authorized as part of the exact call scope, ask only after consent to continue:

> Você autoriza a gravação desta chamada privada como evidência do hackathon, com acesso restrito e exclusão na data acordada? A gravação só começará depois de uma resposta afirmativa clara.

No Stream starts without affirmative consent to continue, and no recording may start before separate affirmative recording consent. A refusal does not authorize recording; either continue the transport test unrecorded if the participant agrees, or end it. Preserve only the script version, safe synthetic participant label, disclosure timestamp, consent outcome, and recording-start timestamp when applicable. Do not persist or commit audio or transcripts.

If the destination is in the United States, counsel must first confirm the call's purpose, recipient and line type, consent basis, and applicable federal and state rules. The opening must also identify the responsible organization and provide the required callback information; the generic script above is not sufficient by itself.

### Exact authorization checkpoint

Immediately before the external mutation, present the operator with:

- synthetic participant label and destination country, without the number;
- upgraded account mode/region and originating-number class, without identifiers;
- exact public HTTPS callback origin and WSS media path;
- disclosure script version and recording behavior (`disabled` unless separately authorized);
- one outbound call, expected Twilio usage charge, maximum duration, and cleanup behavior;
- safe evidence fields and the absence of raw payload/audio logging.

The operator must explicitly authorize that exact package. Earlier phase approval does not authorize the call, deployment, number purchase, account setting, or recording.

### Required live evidence

The run recorded every PASS requirement safely:

- reported upgraded account mode, observed `US1` region, and Voice-capable origin class;
- destination eligibility and participant authorization under the synthetic label;
- the exact externally visible callback URL and a valid signed request;
- rejection of a tampered URL, parameter/body, or signature;
- redacted progress event names, safe timestamps, and correlation aliases;
- TLS-valid WSS upgrade with a valid lowercase `x-twilio-signature`, followed by `connected`, `start`, inbound `media`, outbound deterministic `media`, matching `mark`, and `stop` or explicit cleanup;
- participant confirmation that the deterministic response was heard;
- AI disclosure and continue-consent outcome;
- recording-consent and recording-start timestamps only if recording was separately authorized.

The deterministic response is a fixed 500-millisecond, 400-hertz tone sent only after `start`, as headerless μ-law frames paced at 20 milliseconds. Send mark `phase03-tone-1` after the final frame and do not issue `clear` before its matching returned mark. Record counts and the mark outcome only; never log either media payload.

## Hosting decision

The selected P0.1 server boundary is a **paid Render Web Service** running the repository's FastAPI application under an ASGI server. This choice is compatible on paper because Render documents a stable public hostname, managed TLS, inbound WebSockets, FastAPI deployment, server-side environment secrets, health checks, and searchable logs.

Operational rules for the rehearsal:

- do not use Render Free because idle spin-up can delay callbacks and connections;
- use `https` and `wss` on the same canonical public origin and default TLS port;
- keep one service instance while Stream state is process-local;
- keep Twilio and OpenAI secrets in Render environment settings, never repository files;
- trust forwarded scheme/host data only from Render's proxy boundary and validate Twilio signatures against the exact configured external URL;
- disable deploys during an active call because an instance replacement can close WebSockets;
- implement ping/pong health, graceful shutdown, and idempotent cleanup across socket closure, `stop`, and terminal call status before P0.1;
- log structured correlation aliases, event names, counters, and safe timestamps only;
- use PostgreSQL or another accepted durable store for product state later; never rely on an instance filesystem for evidence.

Official hosting sources:

| Official title and direct URL | Accessed | Conclusion |
| --- | --- | --- |
| [Web Services — Render Docs](https://render.com/docs/web-services) | 2026-08-29 | Render supports public FastAPI services, managed TLS, public hostnames, WebSockets, health checks, and environment configuration. |
| [WebSockets on Render — Render Docs](https://render.com/docs/websocket) | 2026-08-29 | Public services accept inbound WebSockets and should use `wss`. Connections have no fixed platform timeout but can end on instance replacement, so disconnect handling is mandatory. |
| [Deploy a FastAPI App — Render Docs](https://render.com/docs/deploy-fastapi) | 2026-08-29 | Documents FastAPI deployment under Uvicorn bound to the platform port. |
| [Environment Variables and Secrets — Render Docs](https://render.com/docs/configure-environment-variables) | 2026-08-29 | Secrets can remain outside source control and be environment-scoped. |
| [Fully Managed TLS Certificates — Render Docs](https://render.com/docs/tls) | 2026-08-29 | Public Render hostnames and custom domains receive managed certificates and HTTP-to-HTTPS redirects. |
| [Health Checks — Render Docs](https://render.com/docs/health-checks) | 2026-08-29 | HTTP readiness checks prevent routing to an unready instance and restart unhealthy instances. |
| [Logs in the Render Dashboard — Render Docs](https://render.com/docs/logging) | 2026-08-29 | Runtime logs support safe structured evidence and request correlation when the application redacts provider data first. |
| [Deploy for Free — Render Docs](https://render.com/docs/free) | 2026-08-29 | Free services spin down after inactivity and can take about a minute to return; this is unsuitable for the rehearsal gate. |
| [Using WebSockets — Cloud Run](https://docs.cloud.google.com/run/docs/triggering/websockets) | 2026-08-29 | Cloud Run is the infrastructure fallback because it supports HTTPS and WebSockets, but connections remain subject to request timeout and best-effort session affinity. |
| [Configure request timeout for services — Cloud Run](https://docs.cloud.google.com/run/docs/configuring/request-timeout) | 2026-08-29 | The timeout can be configured up to 60 minutes, which is sufficient for the bounded smoke call but adds an operational limit. |

No hosting was provisioned in Phase 03. If Render is unavailable after authorization, Cloud Run is the documented infrastructure fallback and requires its own explicit provisioning approval. If neither host is available, do not improvise a production claim. Use browser voice, deterministic text, and the private recorded demo for presentation, report P0.1 as unmet, and reschedule the authorized transport trial.

## Completed blockers and follow-up ownership

| Former blocker or follow-up | Resolution or next action | Owner | P0/P0.1 impact |
| --- | --- | --- | --- |
| Temporary public endpoint | A separately authorized Quick Tunnel served the localhost harness for the smoke test and was stopped immediately after completion. A persistent endpoint still requires its own deployment authorization. | Phase 18/19 operator | Phase 03 is unblocked; production-like P0.1 work must provision its accepted host. |
| Exact callback validation | The configured public HTTPS status URL accepted a correctly signed request and rejected a tampered form; live Twilio callbacks and the signed WSS upgrade also passed. | Phase 03 operator | Observed behavior is available to downstream adapter work. |
| First-call WebSocket dependency | The first authorized call revealed that bare Uvicorn lacked a WebSocket transport. The harness command now includes `websockets`; the public WSS preflight and isolated test passed before the second authorization. | Phase 03 operator | Resolved in the disposable harness; downstream manifests must include an ASGI WebSocket transport explicitly. |
| Live status and bidirectional media | The second separately authorized call completed the deterministic no-OpenAI exchange, returned the uncleared mark, stopped cleanly, and was audibly confirmed by the participant. | Phase 03 operator and `AUTHORIZED_TEST_A` | Phase 03 no longer blocks dependent phases. |

No shared specification is changed by this finding. The selected Twilio design is feasible under the tested upgraded-account, `US1`, United States origin, permitted low-risk Brazil destination, signed HTTPS/WSS, consent-first, recording-disabled conditions. Broader destinations, account regions, production hosting, failure recovery, and durable state remain downstream work rather than claims of this bounded PASS.
