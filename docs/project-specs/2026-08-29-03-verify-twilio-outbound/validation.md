# Phase 03 validation — Verify Twilio outbound-call feasibility

## Coordination and scope

- [ ] The work remains on `phase/03-verify-twilio-outbound` and touches only the owned Phase 03 paths.
- [ ] Remote dependencies, conflicts, phase branches, and pull requests were refreshed before implementation and before publication.
- [ ] No frontend, API/BFF, backend/core, generated client, database, manifest, lockfile, `.env.example`, or shared-spec change entered the phase.
- [ ] Any accepted-scope exception received an explicit decision and updated ownership before the change.

## Official documentation evidence

- [ ] Every source is an official current Twilio page with title, direct URL, access date, applicable account mode or region, and a concise conclusion.
- [ ] Account and trial restrictions are documented, including their effect on participant eligibility and provider announcements.
- [ ] Originating-number capabilities, destination verification, geographic permissions, and applicable regional calling constraints are documented.
- [ ] The exact official procedure for validating Twilio callback requests is documented for the public URL used by the test.
- [ ] Call-status callback behavior and the observed status evidence are documented without promoting raw provider fields into Volta application contracts.
- [ ] Bidirectional Media Stream connection, lifecycle, media, TLS, and disconnect requirements are documented.
- [ ] AI disclosure, recording consent, and recording-start requirements are documented for the authorized test context, with legal or policy uncertainty called out rather than guessed.

## Authorization, privacy, and security

- [ ] The operator explicitly approved the exact smoke-call target, originating account or number class, endpoint, disclosure and consent script, and expected provider mutations before the call.
- [ ] The participant and destination were allowlisted and authorized; no real carrier was contacted.
- [ ] AI disclosure occurred before the test interaction, and no recording began without the participant's consent.
- [ ] Credentials, authorization headers, auth tokens, full phone numbers, account identifiers, raw provider payloads, and private audio are absent from Git, logs, screenshots, and published evidence.
- [ ] The endpoint uses valid HTTPS and secure WebSockets, keeps secrets server-side, and logs only redacted structured metadata.
- [ ] The exact signed callback URL is reconstructed correctly through any proxy or tunnel.

## Deterministic and transport checks

- [ ] A valid representative callback passes the official request verifier.
- [ ] A tampered body, parameter, URL, or signature fails verification safely.
- [ ] The endpoint observes safe call-status evidence with redacted correlation identifiers and timestamps.
- [ ] The secure WebSocket observes Twilio stream lifecycle and inbound media events.
- [ ] The endpoint sends deterministic media back through the bidirectional stream, and the authorized participant confirms receipt.
- [ ] Disconnect and cleanup behavior do not leave the test endpoint or call in a falsely successful state.
- [ ] The smoke test is reproducible without OpenAI, Volta domain services, or product application routes.

## Hosting and fallback

- [ ] The findings distinguish the disposable smoke endpoint from the selected compatible P0.1 hosting approach.
- [ ] The hosting decision covers HTTPS, secure WebSockets, callback stability, server-only secrets, logs, account constraints, and operational ownership.
- [ ] A fallback and smallest next action are recorded for account, number, destination, policy, network, and hosting failures.
- [ ] Browser voice, text, and recorded fallbacks are described accurately; they do not satisfy the P0.1 telephony gate.

## Repository checks

- [ ] `rtk git diff --check`
- [ ] `rtk git status --short`
- [ ] Complete tracked and untracked diff review, including a credential, full-phone-number, participant-data, raw-payload, and audio-artifact scan.
- [ ] If Python feasibility code or tests were added: `rtk uv run ruff check .`
- [ ] If Python feasibility code or tests were added: `rtk uv run pytest`
- [ ] If Python feasibility code or tests were added: `rtk make python-check`
- [ ] `pnpm lint` and `pnpm build` are marked not applicable unless frontend scope was explicitly added.
- [ ] OpenAPI/Orval generation, browser application checks, database checks, webhook checks, Yuno checks, Row Level Security, Cross-Origin Resource Sharing, and application authorization checks are marked not applicable unless their scope was explicitly added.

## Gate verdict

- [ ] The final dossier maps every unchanged roadmap-gate clause to official documentation and safe observed evidence.
- [ ] Credentialed provider evidence is labeled separately from deterministic repository checks.
- [ ] PASS is declared only after the authorized bidirectional secure-WebSocket smoke test and every other gate claim succeed.
- [ ] Otherwise BLOCKED is declared with the unmet claim, evidence gathered, smallest next action, owner, and P0/P0.1 impact.
