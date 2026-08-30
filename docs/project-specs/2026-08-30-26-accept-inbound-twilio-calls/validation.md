# Fase 26 — Validation

## Planning and coordination

- [ ] Requirements, exclusions, contracts, ownership, risks, and fallback match the unchanged Fase 26 roadmap gate.
- [ ] Fases 15 and 19 remain DONE with merged validation evidence; no Fase 26 remote branch/PR or declared active conflict supersedes this claim.
- [ ] Only approved phase paths enter the branch; unrelated/shared changes and real participant/provider data remain absent.
- [ ] Current official Twilio voice webhook, request validation, DTMF consent/TwiML, `<Connect><Stream>`, custom parameter, and WebSocket message documentation is recorded before implementation.

## Signed inbound ingress and correlation

- [ ] The supported validator checks the exact configured HTTPS URL and every received form pair before parsing/delegation; missing/tampered signatures, proxy/origin mismatch, unexpected account/destination, duplicate fields, malformed body, and oversized body fail closed.
- [ ] One configured opaque synthetic caller binding resolves exactly one eligible active operation and one active commitment under server ownership.
- [ ] Unallowlisted caller, zero/multiple matches, stale/ineligible operation, open escalation, second active attempt, and provider-call replay conflict return no stream instruction and cause zero Realtime/evidence/recovery mutation.
- [ ] Telephone numbers, raw forms, signatures, auth tokens, bindings, candidate operation IDs, provider payloads, and internal errors are absent from logs, responses, audit metadata, fixtures, screenshots, and Git.

## Disclosure, consent, and Media Stream

- [ ] Valid voice TwiML announces artificial intelligence and recording and gathers one explicit DTMF consent before any `<Connect><Stream>` instruction.
- [ ] Consent is signed, matched to the reserved provider call, and durably persisted before one opaque single-use stream binding is returned; refusal, missing digit, expiry, mismatch, duplicate change, and replay fail safely.
- [ ] The existing signed WSS route accepts only the matching account/call/stream ID, inbound track, `audio/x-mulaw`/8 kHz/mono format, and consumed binding.
- [ ] `connected`, `start`, bounded `media`, Realtime output/barge-in, and `stop` pass; malformed/out-of-order/oversized frames, binding replay, capacity, timeout, model/tool/storage failure, and disconnect close once without leaked tasks or false success.

## Backend, persistence, recovery, and evidence

- [ ] Inbound domain/application inputs are provider-neutral and import no FastAPI/Pydantic or raw Twilio structures; Twilio XML/form/frame mapping stays in API telephony modules.
- [ ] The migration/repositories constrain one active inbound attempt per operation and provider call, persist consent/status/completion fingerprints/results, and handle concurrency and duplicates transactionally.
- [ ] Only bounded post-consent audio is converted to the accepted playable format and stored through private `EvidenceStorage`; pre-consent/unbounded audio and transcripts are discarded.
- [ ] Staged evidence is removed on storage/database/domain failure, and identical completion replay neither stores another artifact nor repeats a mutation.
- [ ] One driver-delay completion reuses the existing mandate-safe recovery service, supersedes exactly one commitment, advances the operation once to the accepted status, and persists one recovery, notification, playable timestamp evidence, structured brief, inbound attempt result, and correlated audit sequence.
- [ ] Out-of-mandate/model-selected terms, missing evidence, stale version, changed replay, concurrent completion, and duplicate provider events preserve the previous authoritative state and return safe typed failure.
- [ ] PostgreSQL tests prove commit, rollback, row-lock/uniqueness, replay after restart, evidence cleanup, and complete bounded operation/audit projections.

## Public contracts and frontend projection

- [ ] Existing `get_operation`, `get_operation_audit`, and authorized evidence-audio routes expose the completed status, replacement, recovery, brief, evidence timestamp/playback, notification, and audit events without raw/provider-sensitive data.
- [ ] API contract tests pass before `make generate`; OpenAPI and Orval generation has no unintended semantic diff and generated files are never hand-edited.
- [ ] Current Recovery, Evidence, and Audit surfaces render the authoritative inbound result after refresh at desktop and mobile widths; evidence playback, loading/error states, keyboard/focus behavior, console, and network inspection pass.
- [ ] No new browser-owned business rule, caller binding, provider credential/payload, E.164 value, or parallel TypeScript DTO is introduced.

## Deterministic commands and review

- [ ] `uv run ruff check .` passes for affected Python paths.
- [ ] `uv run pytest` passes for affected API/backend tests.
- [ ] `make python-check` passes from the repository root.
- [ ] `make generate` passes and a clean second generation is confirmed.
- [ ] `pnpm lint` passes from `frontend/`.
- [ ] `pnpm typecheck` passes from `frontend/`.
- [ ] `pnpm build` passes from `frontend/`.
- [ ] `make check` passes from the repository root.
- [ ] Browser smoke runs the recovery/evidence/audit journey first, then console and network inspection finds no runtime failure.
- [ ] Migration, generated artifacts, complete diff/untracked files, `git diff --check`, and targeted secret/E.164/audio/signature/raw-payload scans pass.

## Separately authorized sandbox call

- [ ] Before external mutation, explicit authorization records the synthetic participant label, country, origin class, Twilio number configuration, public HTTPS/WSS endpoint, disclosure/consent wording, recording purpose, expected cost/duration, retention, cleanup, and who will place the inbound call.
- [ ] One authorized sandbox inbound PSTN call proves the signed webhook, exact one-operation correlation, disclosure and consent before stream, bidirectional audio, driver-delay recovery, clean termination, and no duplicate commitment.
- [ ] The existing browser surfaces show the persisted status, brief, playable timestamp evidence, notification, and audit correlation from that call; proof is redacted and contains no real number, signature, token, raw form/audio/transcript, provider payload, or private endpoint.
- [ ] Endpoint/number configuration, retained private evidence, account logs, cost, errors, and temporary resources are reviewed and cleaned according to the authorization.

## Explicitly not authorized by phase start

- [ ] No deployment, Twilio account/number/permission mutation, caller enrollment, production access, unapproved PSTN call, recording, Yuno operation, payment, financial mutation, remote migration, or unrelated remote change occurs without explicit scope.

## Planning evidence recorded on 2026-08-30

- Official Twilio references reviewed: [Voice webhooks](https://www.twilio.com/docs/usage/webhooks/voice-webhooks), [secure webhooks and request validation](https://www.twilio.com/docs/usage/webhooks/webhooks-security), [TwiML Voice](https://www.twilio.com/docs/voice/twiml), [TwiML `<Stream>`](https://www.twilio.com/docs/voice/twiml/stream), and [Media Stream WebSocket messages](https://www.twilio.com/docs/voice/media-streams/websocket-messages).
- The official references confirm that incoming calls invoke the configured voice webhook; Twilio signs HTTP requests in `X-Twilio-Signature`; form validation uses the exact URL plus all received form parameters; `<Connect><Stream>` creates a bidirectional `wss` stream, accepts custom parameters instead of URL query parameters, and exposes only inbound caller audio to the server; `start` carries account/call/stream IDs, tracks, media format, and custom parameters.
- Fases 15 and 19 were confirmed merged through pull requests #22 and #28. At the final planning-base refresh, `origin/main` was `d4277889e47d0d0f54e175bd06c37f9e200b3e25`, no Fase 26 branch or pull request existed, and no conflict was declared.
- Context7 tooling was unavailable in this environment, so the provider lookup used current official Twilio documentation directly, as allowed by the repository source-routing rule. No credentialed request, call, recording, deployment, provider-account change, or remote migration occurred during planning.
