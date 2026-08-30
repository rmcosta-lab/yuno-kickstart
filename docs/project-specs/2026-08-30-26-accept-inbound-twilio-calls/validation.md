# Fase 26 — Validation

## Planning and coordination

- [x] Requirements, exclusions, contracts, ownership, risks, and fallback match the unchanged Fase 26 roadmap gate.
- [x] Fases 15 and 19 remain DONE with merged validation evidence; no Fase 26 remote branch/PR or declared active conflict supersedes this claim.
- [x] Only approved phase paths enter the branch; unrelated/shared changes and real participant/provider data remain absent.
- [x] Current official Twilio voice webhook, request validation, DTMF consent/TwiML, `<Connect><Stream>`, custom parameter, and WebSocket message documentation is recorded before implementation.

## Signed inbound ingress and correlation

- [x] The supported validator checks the exact configured HTTPS URL and every received form pair before parsing/delegation; missing/tampered signatures, proxy/origin mismatch, unexpected account/destination, duplicate fields, malformed body, and oversized body fail closed.
- [x] One configured opaque synthetic caller binding resolves exactly one eligible active operation and one active commitment under server ownership.
- [x] Unallowlisted caller, zero/multiple matches, stale/ineligible operation, open escalation, second active attempt, and provider-call replay conflict return no stream instruction and cause zero Realtime/evidence/recovery mutation.
- [x] Telephone numbers, raw forms, signatures, auth tokens, bindings, candidate operation IDs, provider payloads, and internal errors are absent from logs, responses, audit metadata, fixtures, screenshots, and Git.

## Disclosure, consent, and Media Stream

- [x] Valid voice TwiML announces artificial intelligence and recording and gathers one explicit DTMF consent before any `<Connect><Stream>` instruction.
- [x] Consent is signed, matched to the reserved provider call, and durably persisted before one opaque single-use stream binding is returned; refusal, missing digit, expiry, mismatch, duplicate change, and replay fail safely.
- [x] The existing signed WSS route accepts only the matching account/call/stream ID, inbound track, `audio/x-mulaw`/8 kHz/mono format, and consumed binding.
- [x] `connected`, `start`, bounded `media`, Realtime output/barge-in, and `stop` pass; malformed/out-of-order/oversized frames, binding replay, capacity, timeout, model/tool/storage failure, and disconnect close once without leaked tasks or false success.

## Backend, persistence, recovery, and evidence

- [x] Inbound domain/application inputs are provider-neutral and import no FastAPI/Pydantic or raw Twilio structures; Twilio XML/form/frame mapping stays in API telephony modules.
- [x] The migration/repositories constrain one active inbound attempt per operation and provider call, persist consent/status/completion fingerprints/results, and handle concurrency and duplicates transactionally.
- [x] Only bounded post-consent audio is converted to the accepted playable format and stored through private `EvidenceStorage`; pre-consent/unbounded audio and transcripts are discarded.
- [x] Staged evidence is removed on storage/database/domain failure, and identical completion replay neither stores another artifact nor repeats a mutation.
- [x] One driver-delay completion reuses the existing mandate-safe recovery service, supersedes exactly one commitment, advances the operation once to the accepted status, and persists one recovery, notification, playable timestamp evidence, structured brief, inbound attempt result, and correlated audit sequence.
- [x] Out-of-mandate/model-selected terms, missing evidence, stale version, changed replay, concurrent completion, and duplicate provider events preserve the previous authoritative state and return safe typed failure.
- [x] PostgreSQL tests prove commit, rollback, row-lock/uniqueness, replay after restart, evidence cleanup, and complete bounded operation/audit projections.

## Public contracts and frontend projection

- [x] Existing `get_operation`, `get_operation_audit`, and authorized evidence-audio routes expose the completed status, replacement, recovery, brief, evidence timestamp/playback, notification, and audit events without raw/provider-sensitive data.
- [x] API contract tests pass before `make generate`; OpenAPI and Orval generation has no unintended semantic diff and generated files are never hand-edited.
- [x] Current Recovery, Evidence, and Audit surfaces render the authoritative inbound result after refresh at desktop and mobile widths; evidence playback, loading/error states, keyboard/focus behavior, console, and network inspection pass.
- [x] No new browser-owned business rule, caller binding, provider credential/payload, E.164 value, or parallel TypeScript DTO is introduced.

## Deterministic commands and review

- [x] `uv run ruff check .` passes for affected Python paths.
- [x] `uv run pytest` passes for affected API/backend tests.
- [x] `make python-check` passes from the repository root.
- [x] `make generate` passes and a clean second generation is confirmed.
- [x] `pnpm lint` passes from `frontend/`.
- [x] `pnpm typecheck` passes from `frontend/`.
- [x] `pnpm build` passes from `frontend/`.
- [x] `make check` passes from the repository root.
- [x] Browser smoke runs the recovery/evidence/audit journey first, then console and network inspection finds no runtime failure.
- [x] Migration, generated artifacts, complete diff/untracked files, `git diff --check`, and targeted secret/E.164/audio/signature/raw-payload scans pass.

## Separately authorized sandbox call

- [x] Before external mutation, explicit authorization records the synthetic participant label, country, origin class, Twilio number configuration, public HTTPS/WSS endpoint, disclosure/consent wording, recording purpose, expected cost/duration, retention, cleanup, and who will place the inbound call.
- [x] One authorized sandbox inbound PSTN call proves the signed webhook, exact one-operation correlation, disclosure and consent before stream, bidirectional audio, driver-delay recovery, clean termination, and no duplicate commitment.
- [x] The existing browser surfaces show the persisted status, brief, playable timestamp evidence, notification, and audit correlation from that call; proof is redacted and contains no real number, signature, token, raw form/audio/transcript, provider payload, or private endpoint.
- [x] Endpoint/number configuration, retained private evidence, account logs, cost, errors, and temporary resources are reviewed and cleaned according to the authorization.

## Explicitly not authorized by phase start

- [x] No deployment, Twilio account/number/permission mutation, caller enrollment, production access, unapproved PSTN call, recording, Yuno operation, payment, financial mutation, remote migration, or unrelated remote change occurs without explicit scope.

## Planning evidence recorded on 2026-08-30

- Official Twilio references reviewed: [Voice webhooks](https://www.twilio.com/docs/usage/webhooks/voice-webhooks), [secure webhooks and request validation](https://www.twilio.com/docs/usage/webhooks/webhooks-security), [TwiML Voice](https://www.twilio.com/docs/voice/twiml), [TwiML `<Stream>`](https://www.twilio.com/docs/voice/twiml/stream), and [Media Stream WebSocket messages](https://www.twilio.com/docs/voice/media-streams/websocket-messages).
- The official references confirm that incoming calls invoke the configured voice webhook; Twilio signs HTTP requests in `X-Twilio-Signature`; form validation uses the exact URL plus all received form parameters; `<Connect><Stream>` creates a bidirectional `wss` stream, accepts custom parameters instead of URL query parameters, and exposes only inbound caller audio to the server; `start` carries account/call/stream IDs, tracks, media format, and custom parameters.
- Fases 15 and 19 were confirmed merged through pull requests #22 and #28. At the final planning-base refresh, `origin/main` was `d4277889e47d0d0f54e175bd06c37f9e200b3e25`, no Fase 26 branch or pull request existed, and no conflict was declared.
- Context7 tooling was unavailable in this environment, so the provider lookup used current official Twilio documentation directly, as allowed by the repository source-routing rule. No credentialed request, call, recording, deployment, provider-account change, or remote migration occurred during planning.

## Implementation evidence recorded on 2026-08-30

- `make check` passed after integration: Ruff passed, pytest reported **656 passed, 47 skipped, 2 deselected**, and frontend lint, TypeScript typecheck, and the Next.js production build passed. The additional skipped case is the credential-gated PostgreSQL test, which passed separately against local PostgreSQL (**3 passed**).
- `make python-check` passed independently. `make generate` passed twice; `api/openapi.json` and `frontend/src/lib/api/generated/` remained semantically unchanged. `uv lock --check` resolved the committed lockfile successfully.
- The focused live-PostgreSQL suite exercised durable completion, restart replay, changed replay rejection, rollback, evidence cleanup, and active-attempt uniqueness against the migrated schema.
- In-app Browser smoke covered Recovery and Evidence at desktop width and Audit at 390 x 844; navigation, DOM state, and console inspection passed. The credential-free Playwright recovery journey passed **1/1**, including authoritative refresh, evidence playback lifecycle, and retry identity.
- The existing browser surfaces required no source change. The sandbox-derived terminal Recovery, Evidence, and Audit result was inspected at desktop and 390 x 844 mobile widths after reconnecting the in-memory demo bearer and selecting the persisted operation.

## Authorized sandbox evidence recorded on 2026-08-30

- The user authorized the opaque `synthetic-driver-26` test handset, human-origin inbound call, existing sandbox Twilio number, temporary signed-route-only Cloudflare HTTPS/WSS facade, the implemented artificial-intelligence/recording disclosure and DTMF consent, a two-minute maximum, inspection-only private evidence retention, deletion, webhook restoration, and tunnel cleanup. Separate confirmation explicitly authorized Cloudflare transit of signed forms, identifiers, origin/destination numbers, consented audio, and technical connection metadata.
- The first attempt ended before consent because the legacy outbound allowlist in the local ignored `.env` was not valid JSON; zero inbound attempt/evidence/recovery state was persisted. The second proved signed voice, disclosure, DTMF consent, and Media Stream ingress, then failed safely because the initially seeded operation did not match the canonical mandate-safe fixture. No recovery was claimed, and the private fixture directory was cleaned before recreating the isolated database.
- The final canonical call persisted exactly one `COMPLETED` inbound attempt, `INBOUND_CALL_ACCEPTED`, `INBOUND_CONSENT_RECORDED`, and `INBOUND_RECOVERY_COMPLETED`; one active commitment at MXN 8,750, one replacement recovery, one brief, one pending coordinator notification, and one playable private WAV with a 564 ms offset. The human caller separately confirmed that Realtime outbound audio was audible after consent, completing the bidirectional-media proof.
- Recovery showed operation version 5 and the active replacement; Evidence showed superseded/active commitments, the driver-delay brief, and a 30-second `blob:` WAV at `readyState=4`; Audit showed the complete correlated inbound sequence once. Desktop and 390 x 844 inspections had no console warnings/errors. Operation, audit, and evidence-audio requests returned HTTP 200.
- The three recent sandbox attempts totaled 103 seconds. Twilio reported two completed calls, one no-answer call, and USD 0.017 in aggregate Twilio-side price. The final inbound call was `completed`, lasted 58 seconds, and cost USD 0.00850; caller-carrier charges are outside Twilio's account data.
- The original Twilio voice webhook was restored with HTTP 200 and a read-back confirmed the temporary URL was absent. The Cloudflare tunnel, local API/frontend processes, isolated PostgreSQL database, three mode-0600 evidence files under a mode-0700 root, orchestration scripts, and compiled cache were permanently removed. They are not recoverable. No deployment, production access, Yuno/payment operation, remote migration, transcript retention, or unrelated remote mutation occurred.
