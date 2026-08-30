# Phase 22 plan — Pass the final P0.1 telephony trial

## Task groups

1. **Freeze readiness and contracts**
   - Refresh `origin/main`, dependency PRs, phase/specification PRs, and the conflict graph before
     implementation. Record the Phase 28 final-SHA validation caveat and rerun the complete gate.
   - Reconfirm the canonical Manzanillo-to-Guadalajara fixture, three authorized carrier labels,
     literal-overlap definition, winner/recovery/handoff sequence, five artifacts, and time budget.
   - Verify current official Twilio Voice/Media Streams/calling/recording guidance and OpenAI
     Realtime account/model limits. Freeze the existing HTTP and backend public contracts first.

2. **Implement the bounded API runtime**
   - Give the API integration writer sole ownership of the internal telephony runtime and focused
     tests. Replace singleton outbound state with at most three per-call entries and the global
     active-stream boolean with a lock-protected set or counter bounded to three.
   - Correlate voice lookup, stream-token claim, Realtime session, tool/audio handling, status
     callbacks, terminal cleanup, and handoff authority to the correct call. Reuse the existing
     durable attempt store and provider-neutral services.
   - Prove exact idempotent replay, changed-payload conflict, three independent streams, reordered
     callbacks, per-call disconnect cleanup, and fail-safe fourth-call rejection with zero provider
     I/O. Do not add a new HTTP schema, backend service, migration, dependency, or frontend type.

3. **Run deterministic integration preflight**
   - Run focused API/WebSocket tests, the Phase 20/26/28 paths, `make python-check`,
     `make frontend-check`, `make generate`, and `make check`; generation must leave the committed
     OpenAPI and Orval contracts semantically unchanged.
   - Use fakes to prove three-call overlap/isolation, duplicate and out-of-order events, stale state,
     inbound fail-closed correlation, mandate-safe recovery, handoff `JOINED` callback semantics,
     AI fencing, winner uniqueness, recap state, brief/evidence projections, and cleanup.
   - Exercise the existing browser journey at desktop and mobile widths, then inspect console,
     network, focus, announcements, loading, failure, fallback, and duplicate-action behavior.

4. **Freeze authorization and the live runbook**
   - Obtain separate explicit authorization before any call, participant contact, recording, public
     ingress, temporary deployment/configuration, or provider-account mutation. Phase start and code
     implementation alone do not authorize these actions.
   - Record outside Git the authorized participants/destinations, account and regional restrictions,
     HTTPS/WSS endpoints, disclosure/consent script, recording purpose, duration/cost bounds,
     evidence retention/deletion, stop conditions, cleanup, and responsible operator.
   - Prepare a clean synthetic operation and three sessions. Validate allowlists and fail closed
     without printing phone numbers, credentials, signatures, or provider payloads.

5. **Rehearse artifacts and fallbacks**
   - Verify presentation, demo script, public repository guide, architecture diagram, and decision
     log tell one consistent pre-trial story. Rehearse two timed clean-environment passes.
   - Verify browser voice, text, and private recording switch-over without calling them PSTN proof.
     Keep the private recording and locator outside Git and public logs.

6. **Execute the separately authorized final trial**
   - Start three fresh outbound calls through three explicit human actions and prove a literal
     overlap window from safe per-call status evidence. Each participant receives AI disclosure and
     the accepted recording/consent treatment; each Media Stream and tool action remains isolated.
   - While one call is live, request takeover, wait for the verified durable `JOINED` outcome,
     confirm the remote participant remained connected, and confirm AI speech/commitment authority
     stayed fenced.
   - Complete one signed authorized inbound driver-delay call, fail-closed correlation, disclosure
     and consent, mandate-safe recovery, replacement evidence, notification, brief, and audit trail.
     Do not retry an ambiguous provider mutation with a new idempotency key.

7. **Inspect terminal evidence and clean up**
   - Reload durable state and prove one `ACTIVE` winner, historical `SUPERSEDED` decisions, the final
     winner's idempotent `SIMULATED` recap, structured brief, playable `audio_start_ms` evidence,
     recovery notification, handoff, and correlated audit events.
   - Record redacted restrictions, call outcomes, overlap, latency, continuity, disconnects, gaps,
     duration/cost, and cleanup. A partial run remains an explicit failure, not a softened claim.
   - Stop temporary processes/tunnels, restore authorized temporary configuration, apply the agreed
     audio retention/deletion action, review logs and charges, and confirm no private artifact entered
     Git.

8. **Reconcile and hand off**
   - Refresh other documentation owners, then update only stale public facts proven by the final
     run. No shared roadmap, mission, or stack decision is planned; request `manage-shared-specs` if
     the accepted gate itself must change.
   - Review the complete diff and generated artifacts, run final checks on the publication SHA, and
     record skipped credentialed checks or external blockers explicitly.

## Ownership and sequencing

- The phase coordinator is the sole writer for the phase specification and final redacted evidence.
- One API integration writer owns `api/app/telephony/service.py`, `api/app/main.py`,
  `api/app/routers/telephony.py`, and focused API tests. Contract freeze precedes that work.
- Backend, migrations, frontend source, generated files, manifests, lockfiles, and `.env.example`
  are read-only by default. Any proven defect returns to the coordinator before ownership expands.
- A generation checkpoint owner runs OpenAPI/Orval generation after API tests and verifies no
  semantic diff. Generated files are never edited manually.
- After live evidence exists, one submission reconciliation writer owns factual updates to README,
  submission docs, architecture, and the decision log. Refresh open PRs before touching shared docs.
- The authorized operator alone owns credentials, provider/account configuration, destinations,
  participants, private recordings, and cleanup outside Git.

## Guardrails

- No live call, recording, participant contact, public deployment/ingress, provider-account change,
  or temporary configuration is authorized until separately approved with exact targets and bounds.
- No production access, real carrier contact, external recap delivery, Yuno operation, payment,
  financial mutation, remote database migration, or unrelated infrastructure is in scope.
- Never log, print, stage, screenshot, or persist raw audio/transcripts, real phone numbers,
  credentials, signatures, private locators, or full provider/model payloads.
- Do not weaken the three-call overlap, inbound recovery, live handoff, timestamp evidence, or
  submission timing gate. Browser/text/recorded fallback preserves the demo but not P0.1 success.
