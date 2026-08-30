import {
  BrowserRealtimeError,
  exchangeRealtimeSdp,
  parseRealtimeServerEvent,
  sendToolResultWithCurrentContext,
} from "./browser-realtime";
import {
  createRealtimeToolDispatcher,
  parseRealtimeToolRequest,
  type RealtimeOperationalContext,
  type RealtimeToolOutput,
  type RealtimeToolRequest,
} from "./tool-dispatcher";

export type RealtimeDiagnosticScenarioId =
  | "malformed"
  | "unknown"
  | "duplicate"
  | "failed"
  | "fresh-context"
  | "exchange-guards"
  | "pending-disconnect"
  | "reconnected";

export const REALTIME_DIAGNOSTIC_SCENARIOS = [
  {
    id: "malformed",
    label: "Malformed event",
    description: "Rejects invalid JSON before any tool dispatch.",
  },
  {
    id: "unknown",
    label: "Unknown tool",
    description: "Rejects a non-allowlisted tool name without mutation.",
  },
  {
    id: "duplicate",
    label: "Duplicate call",
    description: "Reuses one pending result and one injected invocation.",
  },
  {
    id: "failed",
    label: "Failed tool",
    description: "Reduces an injected failure to TOOL_UNAVAILABLE.",
  },
  {
    id: "fresh-context",
    label: "Fresh tool context",
    description:
      "Sends refreshed operation state after output and before the next response.",
  },
  {
    id: "exchange-guards",
    label: "SDP exchange guards",
    description: "Bounds a stalled exchange and rejects an expired secret.",
  },
  {
    id: "pending-disconnect",
    label: "Pending disconnect",
    description: "Blocks a new call until the pending request reconciles.",
  },
  {
    id: "reconnected",
    label: "Reconnected",
    description: "Allows a new call only after authoritative reconciliation.",
  },
] as const satisfies readonly Readonly<{
  id: RealtimeDiagnosticScenarioId;
  label: string;
  description: string;
}>[];

const OPERATION_ID = "00000000-0000-4000-8000-000000000010";
const CALL_ID = "00000000-0000-4000-8000-000000000011";
const CARRIER_ID = "00000000-0000-4000-8000-000000000012";

const CONTEXT: RealtimeOperationalContext = Object.freeze({
  operationId: OPERATION_ID,
  operationVersion: 7,
  mandateVersion: 3,
  sessions: Object.freeze([
    Object.freeze({ callId: CALL_ID, carrierId: CARRIER_ID }),
  ]),
  selectedQuote: null,
  attachedEvidence: null,
});

function quoteArguments(operationVersion = 7) {
  return JSON.stringify({
    call_id: CALL_ID,
    expected_operation_version: operationVersion,
    carrier_id: CARRIER_ID,
    mandate_version: 3,
    terms: {
      amount_minor: 17_950_00,
      currency: "MXN",
      pickup_window: {
        start_date: "2026-09-01",
        end_date: "2026-09-01",
      },
      conditions: ["Synthetic diagnostic condition"],
    },
    valid_until: "2026-08-30T18:15:00Z",
  });
}

const LOCAL_UNAVAILABLE: RealtimeToolOutput = Object.freeze({
  ok: false,
  error: Object.freeze({ code: "TOOL_UNAVAILABLE" }),
});

function quoteRequest(
  providerCallId: string,
  operationVersion = 7,
): RealtimeToolRequest {
  const request = parseRealtimeToolRequest({
    providerCallId,
    name: "record_quote",
    argumentsJson: quoteArguments(operationVersion),
  });
  if (!request) throw new Error("Invalid local diagnostic fixture");
  return request;
}

export async function runRealtimeDiagnosticScenario(
  scenario: RealtimeDiagnosticScenarioId,
): Promise<string> {
  if (scenario === "malformed") {
    return parseRealtimeServerEvent("{") === null
      ? "PASS · malformed JSON rejected · 0 calls"
      : "FAIL · malformed JSON accepted";
  }
  if (scenario === "unknown") {
    const parsed = parseRealtimeToolRequest({
      providerCallId: "provider-call-unknown",
      name: "unknown_mutation",
      argumentsJson: "{}",
    });
    return parsed === null
      ? "PASS · unknown tool rejected · 0 calls"
      : "FAIL · unknown tool accepted";
  }
  if (scenario === "exchange-guards") {
    const signal = new AbortController().signal;
    let expired = false;
    try {
      await exchangeRealtimeSdp({
        clientSecret: "local-expired-secret",
        expiresAt: 1,
        offerSdp: "local-offer",
        signal,
        now: () => 1_001,
      });
    } catch (error) {
      expired =
        error instanceof BrowserRealtimeError &&
        error.category === "credential_expired";
    }

    let timedOut = false;
    try {
      await exchangeRealtimeSdp({
        clientSecret: "local-timeout-secret",
        expiresAt: 60,
        offerSdp: "local-offer",
        signal,
        now: () => 0,
        maximumTimeoutMs: 1,
        fetcher: ((_input, init) =>
          new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener(
              "abort",
              () => reject(new DOMException("Aborted", "AbortError")),
              { once: true },
            );
          })) as typeof fetch,
      });
    } catch (error) {
      timedOut =
        error instanceof BrowserRealtimeError && error.category === "timeout";
    }
    return expired && timedOut
      ? "PASS · expired secret rejected · stalled SDP timed out"
      : "FAIL · SDP exchange guard did not terminate safely";
  }

  if (scenario === "fresh-context") {
    let currentContext = CONTEXT;
    let invocationCount = 0;
    const sent: unknown[] = [];
    const dispatcher = createRealtimeToolDispatcher({
      getContext: () => currentContext,
      refreshAuthoritativeContext: async () => {
        currentContext = Object.freeze({
          ...CONTEXT,
          operationVersion: 8,
        });
      },
      executeTool: async () => {
        invocationCount += 1;
        return LOCAL_UNAVAILABLE;
      },
    });
    await sendToolResultWithCurrentContext({
      dispatchTool: (request) => dispatcher.dispatch(request),
      getAuthoritativeContext: () =>
        JSON.stringify({ operation_version: currentContext.operationVersion }),
      onStatus: () => undefined,
      providerCallId: "provider-call-fresh-context",
      request: quoteRequest("provider-call-fresh-context"),
      send: (event) => sent.push(event),
    });
    await dispatcher.dispatch(
      quoteRequest("provider-call-fresh-context-next", 8),
    );
    const serialized = sent.map((event) => JSON.stringify(event));
    return invocationCount === 2 &&
      serialized[0]?.includes('"function_call_output"') &&
      serialized[1]?.includes('\\"operation_version\\":8') &&
      serialized[2]?.includes('"response.create"')
      ? "PASS · output preceded refreshed v8 context · next quote accepted"
      : "FAIL · stale context reached the next response";
  }

  let invocationCount = 0;
  let refreshCount = 0;
  let releasePending!: () => void;
  const pendingGate = new Promise<void>((resolve) => {
    releasePending = resolve;
  });
  const dispatcher = createRealtimeToolDispatcher({
    getContext: () => CONTEXT,
    refreshAuthoritativeContext: async () => {
      refreshCount += 1;
    },
    executeTool: async () => {
      invocationCount += 1;
      if (scenario === "failed") throw new Error("diagnostic failure");
      if (scenario === "pending-disconnect" || scenario === "reconnected") {
        await pendingGate;
      }
      return LOCAL_UNAVAILABLE;
    },
  });

  const firstRequest = quoteRequest(`provider-call-${scenario}-one`);
  if (scenario === "duplicate") {
    const [first, duplicate] = await Promise.all([
      dispatcher.dispatch(firstRequest),
      dispatcher.dispatch(firstRequest),
    ]);
    return invocationCount === 1 && first === duplicate
      ? "PASS · duplicate reused one pending safe result · 1 call"
      : "FAIL · duplicate invoked more than once";
  }

  if (scenario === "failed") {
    const output = await dispatcher.dispatch(firstRequest);
    return !output.ok && output.error.code === "TOOL_UNAVAILABLE"
      ? "PASS · failure reduced to TOOL_UNAVAILABLE · 1 call"
      : "FAIL · unsafe failure escaped";
  }

  const pending = dispatcher.dispatch(firstRequest);
  dispatcher.markDisconnected();
  const reconciliation = dispatcher.reconcile();
  const blocked = await dispatcher.dispatch(
    quoteRequest(`provider-call-${scenario}-blocked`),
  );
  releasePending();
  await Promise.all([pending, reconciliation]);

  if (scenario === "pending-disconnect") {
    return !blocked.ok && invocationCount === 1 && refreshCount >= 1
      ? "PASS · new call blocked until authoritative refresh · no replay"
      : "FAIL · pending disconnect was not contained";
  }

  await dispatcher.dispatch(quoteRequest("provider-call-reconnected-new"));
  return !blocked.ok && invocationCount === 2 && refreshCount >= 2
    ? "PASS · new call accepted only after reconciliation · no replay"
    : "FAIL · reconnect boundary was not preserved";
}
