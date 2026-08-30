# Decision Log — Capithon

NextWave Hackathon 2026 · São Paulo

## 1. Enforce mandates outside the model  `T+23:41`

**Options considered**

- Put the mandate only in the system prompt;
- Let FastAPI validate it;
- Allow the model to write commitments directly.

**Chosen:** Store each approved mandate as an immutable version in PostgreSQL.

**Why:** Prompts guide conversation but are not a reliable authorization boundary. Keeping enforcement in the core also gives browser, text, inbound, and outbound calls identical rules.
Trade-offs: Every mutation needs typed commands, mandate-version checks, and safe tool-result handling. This adds latency and code, but prevents the model from granting itself authority.

## 2. Bridge Twilio Media Streams instead of using direct SIP  `T+23:42`

**Options considered**

- OpenAI SIP;
- Browser audio only;
- A provider-managed voice-agent platform.

**Chosen:** Twilio owns the PSTN leg and streams μ-law audio to a FastAPI WebSocket.

**Why:** Twilio Media Streams gave us explicit control over request signatures, consent, tool execution, interruption handling, and call lifecycle.
Trade-offs: We own audio conversion, buffering, backpressure, disconnect cleanup, and two asynchronous protocols. Direct SIP would be simpler operationally but give us less control and require a larger architecture change.

## 3. Use durable idempotency before provider calls  `T+23:43`

**Options considered**

- In-memory deduplication;
- Generating a new key on every retry;
- Relying on Twilio’s response.

**Chosen:** Persist an idempotency key, canonical request fingerprint, and normalized result before or around each logical mutation. Replaying the same request returns the stored result; reusing the key with different data fails safely.

**Why:** A timeout does not tell us whether the provider accepted the call. Automatic retries could create a second live call.
Trade-offs: Uncertain outcomes sometimes require human inspection instead of an automatic retry. Persistence and locking are more complex, but the system avoids duplicate external actions.

## 4. Fence AI authority before starting the human handoff  `T+23:43`

**Options considered**

- Stop the AI after Twilio confirms the transfer;
- Hang up and call back;
- Trust the frontend to disable tools.

**Chosen:** Reserve the handoff and persist an AI authority fence transactionally before making Twilio calls. Then redirect the remote leg into a conference, dial the allowlisted coordinator, and use signed callbacks to confirm JOINED.

**Why:** Provider callbacks can be delayed or reordered. Waiting for confirmation leaves a period where both the AI and human could act.
Trade-offs: A failed handoff leaves AI authority suspended and requires an explicit safe state. That is less convenient, but safer than allowing conflicting commitments.

## 5. Run three isolated Realtime sessions behind one operation  `T+23:44`

**Options considered**

- One model session handling all three audio streams;
- Sequential calls;
- Three agents with completely independent state;
- An unbounded concurrent-call runtime.

**Chosen:** Treat each call as an independent Twilio and OpenAI Realtime session. Coordinate the calls through typed tools, stable call identifiers, and shared versioned operation state. Limit the runtime to three active outbound calls and reject a fourth before provider I/O.

**Why:** Independent sessions isolate audio and conversation history and allow carriers to answer and negotiate at different speeds. Shared backend state provides the market-level coordination without mixing model contexts.

## 6. Keep winner selection deterministic  `T+23:45`

**Options considered**

- Let the model choose;
- Select only by price;
- Build a weighted score using price, reliability, timing, and service quality.

**Chosen:** Separate conversational negotiation from winner selection. The model extracts and submits quotes, while a backend comparison function filters them by mandate version, eligibility, and expiration before ranking them by price, pickup date, carrier priority, creation time, and stable ID.

**Why:** Deterministic ranking is reproducible, testable, and easy for the coordinator to audit. A carrier cannot influence the result merely by persuading the model that its offer is “better.”
