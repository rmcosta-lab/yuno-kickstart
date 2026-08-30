# Fase 13 — Add browser voice and tool roundtrips

## Coordination and objective

- **Priority:** P0 browser voice, required by the complete browser trial in Fase 17.
- **Branch:** `phase/13-add-browser-voice`.
- **Owner:** `rmcosta-lab`; no tracking Issue was requested.
- **Depends on:** Fase 09, merged in PR #7 with the negotiation UI gate; Fase 12, merged in PR #16 with the secure Realtime client-secret contract and generated client.
- **Conflicts with:** none.
- **Objective:** let the operations coordinator explicitly start, use, reconnect, and stop an English browser-voice session from the existing negotiation experience while every operational tool remains a typed call to the FastAPI BFF.
- **Terminal user-visible outcome:** either a cleanly torn-down, reconnectable WebRTC session with visible microphone, playback, connection, and tool status, or an honest text fallback. Browser voice is a simulator channel, not PSTN telephony or proof that a carrier was contacted.
- **Roadmap gate:** the frontend establishes and tears down an English Realtime WebRTC session with natural pacing, handles microphone and playback permissions, barge-in, reconnect, and text fallback, forwards every tool request to typed `/v1` routes, returns the result with the original call identifier, and exposes no standard credential in source, storage, console, or network logs.

## Scope

Included:

- A native browser WebRTC and media lifecycle behind a narrow client feature, with explicit Start, Stop, and Reconnect actions and only one active connection generation.
- Minting a scoped, short-lived credential through the generated client, exchanging local SDP with the official Realtime calls endpoint, playing remote audio, and keeping the ephemeral secret only in memory for the required exchange.
- Allowlisted, bounded Realtime event parsing; human-observed English natural pacing under the server-owned Fase 12 session policy; server-voice-activity and documented cancellation or truncation events during barge-in; visible connection, playback, permission, tool, and error states.
- Dispatch of the two server-configured tools, `record_quote` and `create_candidate_commitment`, through the generated `/v1` operations. Provider correlation `call_id` stays distinct from the Volta carrier-session `call_id` inside tool arguments.
- Before accepting a tool, the voice leaf supplies bounded server-owned context containing the active operation and selected session identifiers, current operation and mandate versions, current quote identifiers, and, only after the existing typed evidence route succeeds, its resulting evidence identifier. The model never invents an identifier; context refreshes from server state after each mutation. The candidate-commitment trial starts only after a selected quote and synthetic attached evidence exist.
- One stable idempotency key and one stored safe result per provider tool-call identifier, so duplicate or uncertain delivery cannot create a second logical mutation.
- `function_call_output` using the original provider `call_id`, followed by `response.create`, only after the typed BFF call returns the fixed safe envelope `{ ok: true, data: QuoteResponse | CommitmentResponse }` or `{ ok: false, error: ApiErrorResponse | { code: "TOOL_UNAVAILABLE" } }`.
- The existing text negotiation journey as a keyboard-operable fallback, plus responsive and accessible status, permission, reconnect, and failure handling.

Excluded:

- Pydantic, OpenAPI, Orval, generated-client, API/BFF, backend/core, persistence, migration, mandate, selection, quote-validation, or commitment-rule changes.
- Client-selected model, instructions, voice, tools, voice-activity configuration, safety identifier, session expiry, or provider payload fields.
- Twilio, PSTN, real inbound or outbound calls, recordings, evidence persistence, recovery, recaps, notifications, or audit screens.
- Raw audio, SDP, transcripts, tool payloads, provider events, authorization values, or credentials in durable browser storage, logs, screenshots, fixtures, or Git.
- Deployment, production access, real participant data, Yuno, payments, financial mutations, or automatic dialing.
- A new dependency or manifest/lockfile change unless implementation proves native browser APIs insufficient and the phase plan is explicitly revised.

## Assumptions, risks, and fallback

- The Fase 12 server fixes the accepted English model, instructions, audio/VAD behavior, and two tool schemas; the browser consumes that authority rather than duplicating it.
- Browser permission and autoplay differences are handled by an explicit user gesture, distinct visible states, and a direct route back to text mode.
- Provider event drift and malformed JSON are contained by allowlisted event names, runtime shape and size guards, and a refresh of official OpenAI Realtime documentation before implementation.
- Natural pacing is a credentialed observation, not a browser-controlled setting. If the server-owned Fase 12 policy fails that trial, this phase stops and coordinates the API owner or a follow-up contract change rather than silently overriding model, voice, or instructions.
- Reconnect races and leaked microphones are prevented by one connection generation plus idempotent teardown that removes listeners, stops every track, clears the remote audio sink, and discards ephemeral references.
- Duplicate tool delivery reuses the same stored idempotency key and result. Mutation state outlives a closed peer long enough to settle an in-flight HTTP request and refetch authoritative operation state. A disconnect with an uncertain mutation marks the old voice call unresolved and blocks another voice mutation until reconciliation; reconnect never aborts and replays it. Stale versions surface the BFF's safe conflict; the browser never repairs arguments or infers authority.
- **Fallback:** the merged generated-client text journey remains usable when permission, playback, credential issuance, SDP, data channel, provider, or network fails. Failure stays visible and never fabricates voice success, replays a mutation, or claims PSTN contact.

## Acceptance criteria

- A user gesture creates one English WebRTC session; Stop, unmount, failed connect, and reconnect deterministically close the data channel and peer, remove listeners, stop every media track, clear audio `srcObject`, and discard secret/session references.
- Reconnect always mints a fresh credential, cannot overlap the previous attempt, and preserves the existing text controls throughout failure and recovery.
- Permission denied, unavailable microphone, blocked playback, client-secret failure or expiry, SDP failure, provider error, tool failure, and clean or unclean disconnect are textually distinct, accessible states.
- Speaking over model audio produces observable interruption handling and a coherent later response; natural-paced English audio succeeds in the separately authorized browser trial.
- Each supported function call is schema-checked before mutation, reaches exactly its generated `/v1` operation, returns a bounded safe output with the original provider `call_id`, and refreshes operation state from the server result. Unknown, malformed, oversized, or duplicate calls cannot cause an extra mutation.
- A disconnect during a mutation lets the HTTP request settle when possible, reconciles through a fresh operation read, and resolves the old call before another voice mutation becomes available. It never replays the uncertain request under a new provider call ID.
- No browser callback selects a carrier, validates a mandate or quote, creates a winner directly, or treats model speech as durable operational state.
- The standard OpenAI credential is absent from browser source, bundle, DOM, storage, console, and network logs. The ephemeral secret is absent from storage, UI, console, screenshots, and committed artifacts.
- Mobile and desktop layouts preserve keyboard access, visible focus, meaningful live announcements, non-color status cues, and usable text fallback.

## HTTP contract gate

This phase consumes the merged contract and does not regenerate it:

| Boundary | Typed contract and semantics |
| --- | --- |
| `POST /v1/realtime/client-secrets` | Generated `createRealtimeClientSecret()` sends no body and returns `201 RealtimeClientSecretResponse { client_secret, expires_at, session_id, model }`. `401`, `403`, `429`, `500`, and `502` are safe `ApiErrorResponse` failures. The browser supplies existing in-memory demo authorization through `voltaFetch`; the user agent automatically supplies `Origin`, which frontend code neither sets nor overrides. The secret is discarded after SDP exchange, failure, or teardown. |
| `POST https://api.openai.com/v1/realtime/calls` | Provider-only HTTPS exchange: local SDP with `Content-Type: application/sdp` and ephemeral bearer; the SDP answer becomes the peer remote description. The standard key never enters the browser. |
| `POST /v1/calls/{call_id}/quotes` | `record_quote` arguments map to generated `recordQuote(operationalCallId, CreateQuoteRequest, RecordQuoteHeaders)` and `201 QuoteResponse`; declared `401`, `403`, `404`, `409`, `422`, `429`, `500`, and `501` failures become bounded safe tool output. |
| `POST /v1/calls/{call_id}/commitments` | `create_candidate_commitment` arguments map to generated `createCandidateCommitment(operationalCallId, CreateCommitmentRequest, CreateCandidateCommitmentHeaders)` and `201 CommitmentResponse`; the same declared safe-error statuses apply. |

For both mutation tools, the provider function-call identifier is preserved separately from the operational route identifier. A valid tool result emits `conversation.item.create` with a `function_call_output` item and the original provider `call_id`, then emits `response.create`. The output is exactly `{ ok: true, data }` with the generated `QuoteResponse` or `CommitmentResponse`, or `{ ok: false, error }` with a safe generated `ApiErrorResponse`; failures without a typed envelope reduce to `{ ok: false, error: { code: "TOOL_UNAVAILABLE" } }`. Generated functions throw `ApiHttpError` for declared non-success statuses, so the dispatcher extracts only the safe typed envelope and never forwards `Error.message`, a transport wrapper, raw response, or exception. The feature-session result map reuses one idempotency key and safe result for duplicate delivery and remains alive through uncertain-request reconciliation.

## Frontend application contract gate

| Import path | Public symbols | Construction, typed inputs/outputs, and failures |
| --- | --- | --- |
| `frontend/src/features/realtime/index.ts` | `BrowserVoiceExperience` | Smallest React client leaf integrated into the existing negotiation screen. It owns explicit controls and safe UI state, not server or domain state. |
| `frontend/src/features/realtime/browser-realtime.ts` | `BrowserRealtimeOptions`, `BrowserRealtimeConnection`, `BrowserRealtimeError`, `connectBrowserRealtime` | Options inject `issueClientSecret`, `dispatchTool`, `remoteAudio`, and `onStatus`. `connectBrowserRealtime(options) -> Promise<BrowserRealtimeConnection>` returns immutable safe session metadata plus `sendText(text: string): void` and idempotent `close(): void`; it rejects only a safe categorized `BrowserRealtimeError`. It owns peer, channel, tracks, SDP exchange, listeners, and cleanup. |
| `frontend/src/features/realtime/tool-dispatcher.ts` | `RealtimeOperationalContext`, `RealtimeToolRequest`, `RealtimeToolOutput`, `RealtimeToolDispatcher`, `createRealtimeToolDispatcher` | Context contains server-owned IDs and versions refreshed from generated reads. The closed request union keeps `providerCallId` separate from the operational arguments. `dispatch(request) -> Promise<RealtimeToolOutput>` resolves only the fixed success/error envelope, calls generated operations, extracts safe `ApiErrorResponse` from `ApiHttpError`, and reconciles uncertain mutations before allowing another dispatch. |

UI state is the closed frontend-only discriminated union `idle | requesting_permission | connecting | connected | reconciling | reconnecting | disconnected | fallback | error`. The feature boundary catches browser, provider, and HTTP failures and retains only safe categories; no backend service import, raw `Response`, bearer, secret, SDP, transcript, raw event, or provider payload crosses into presentation.

## Layer, provider, security, visual, and accessibility decisions

- **Frontend:** App Router pages stay Server Components; the voice experience is the smallest practical Client Component and keeps transient connection/media state local. Generated client functions remain the only application-data transport.
- **API/BFF, backend/core, and data:** no changes. FastAPI continues to own authorization and error translation; the core continues to own mandate, quote, and commitment decisions; PostgreSQL state is observed only through existing responses.
- **OpenAI:** the browser uses only the server-minted ephemeral credential and the server-fixed session/tools. Provider URLs, events, and media handling stay inside the frontend Realtime boundary rather than leaking into general presentation code.
- **Yuno, payment, and telephony:** not applicable. The phase creates no Yuno handoff, payment data, PSTN call, or real carrier contact.
- **Security and privacy:** no generic raw-event logging, durable browser storage, real participant data, or retained audio/transcript. Safe visible errors contain only actionable categories.
- **Visual:** preserve the established Volta control-tower hierarchy and tokens; voice controls show state and recovery without decorative provider chrome or a misleading live-carrier claim.
- **Accessibility:** controls have semantic labels, keyboard operation, visible focus, sufficient contrast, non-color cues, restrained live announcements, and clear permission/fallback instructions at mobile and desktop widths.

## Browser/server handoff and ownership

The browser requests a no-store ephemeral credential from FastAPI, establishes WebRTC directly with OpenAI, and forwards allowlisted model tool requests to the generated FastAPI client. FastAPI and the deterministic core remain the only path to operational mutations. The frontend sends only the core's result back to Realtime with the original provider correlation.

| Path or artifact | Writer | Rule |
| --- | --- | --- |
| `docs/project-specs/2026-08-30-13-add-browser-voice/**` | `rmcosta-lab` phase coordinator | Own requirements, plan, and validation. |
| `frontend/src/features/realtime/**` | Fase 13 frontend writer | Own WebRTC lifecycle, event guards, tool dispatch, safe state, and controls. |
| `frontend/src/features/negotiation/**`, `frontend/src/app/(control-tower)/sessions/**` | Same Fase 13 frontend writer | Integrate the voice leaf and server-state refresh without recalculating domain state. |
| `frontend/src/components/control-tower/**` | Same writer only when narrowly required | Preserve all existing consumers and established visual language. |
| `frontend/package.json`, `pnpm-lock.yaml` | No expected writer | Native browser APIs are sufficient; one coordinator owns both only after an explicit plan revision. |
| `api/openapi.json`, `frontend/src/lib/api/generated/**`, `api/**`, `backend/**`, `.env.example` | No Fase 13 writer | Consume only; do not edit or regenerate. |
| Mission, tech stack, roadmap, challenge plan, other phase specs | No Fase 13 writer | No shared decision change is required. Use the owning workflow if that changes. |
| `experiments/openai-capabilities/**` | Read-only reference | Reuse findings, not product code or credentials. |

There is no Yuno browser/server handoff and no payment outcome in Volta.
