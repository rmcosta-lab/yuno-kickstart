import type { ApiErrorResponse } from "@/lib/api/generated/models/apiErrorResponse";
import type { CarrierSessionResponse } from "@/lib/api/generated/models/carrierSessionResponse";
import type { EscalationResponse } from "@/lib/api/generated/models/escalationResponse";
import type { NegotiationResponse } from "@/lib/api/generated/models/negotiationResponse";
import type { OperationResponse } from "@/lib/api/generated/models/operationResponse";
import type { QuoteResponse } from "@/lib/api/generated/models/quoteResponse";

import type {
  DemoScenarioId,
  NegotiationExperienceSnapshot,
  NegotiationExperienceSource,
  NegotiationScenarioOption,
} from "./types";

const OPERATION_ID = "op-demo-mx-042";
const NEGOTIATION_ID = "neg-demo-mx-042";

const SESSION_ONE = {
  call_id: "session-puerto-azul",
  carrier: {
    carrier_id: "carrier-puerto-azul",
    deterministic_rank: 1,
    display_name: "Puerto Azul Drayage",
    eligible: true,
    ranking_evidence: [
      "Covers Manzanillo to Guadalajara",
      "Declared availability for the requested pickup window",
    ],
  },
  channel: "BROWSER_TEXT",
  direction: "OUTBOUND_SIMULATION",
  started_at: "2026-08-29T14:02:00Z",
  state: "ACTIVE",
} satisfies CarrierSessionResponse;

const SESSION_TWO = {
  call_id: "session-ruta-norte",
  carrier: {
    carrier_id: "carrier-ruta-norte",
    deterministic_rank: 2,
    display_name: "Ruta Norte Intermodal de Occidente",
    eligible: true,
    ranking_evidence: [
      "Covers the requested corridor",
      "Second fixed priority among eligible carriers",
    ],
  },
  channel: "BROWSER_TEXT",
  direction: "OUTBOUND_SIMULATION",
  started_at: "2026-08-29T14:04:00Z",
  ended_at: "2026-08-29T14:17:00Z",
  state: "COMPLETED",
} satisfies CarrierSessionResponse;

const SESSION_THREE = {
  call_id: "session-altamar",
  carrier: {
    carrier_id: "carrier-altamar",
    deterministic_rank: 3,
    display_name: "Altamar Logística Portuaria del Pacífico",
    eligible: true,
    ranking_evidence: [
      "Covers the requested corridor",
      "Third fixed priority among eligible carriers",
    ],
  },
  channel: "BROWSER_TEXT",
  direction: "OUTBOUND_SIMULATION",
  started_at: "2026-08-29T14:05:00Z",
  ended_at: "2026-08-29T14:19:00Z",
  state: "COMPLETED",
} satisfies CarrierSessionResponse;

const QUOTE_ONE_EARLIER = {
  call_id: SESSION_ONE.call_id,
  carrier_id: SESSION_ONE.carrier.carrier_id,
  created_at: "2026-08-29T14:09:00Z",
  eligibility: "REJECTED",
  mandate_version: 3,
  operation_id: OPERATION_ID,
  quote_id: "quote-puerto-azul-01",
  rejection_reasons: [
    "Amount exceeds the approved MXN 18,500.00 limit.",
    "Saturday gate fee is not an allowed condition in mandate v3.",
  ],
  terms: {
    amount_minor: 19_300_00,
    currency: "MXN",
    pickup_window: {
      start_date: "2026-09-01T08:00:00-06:00",
      end_date: "2026-09-01T14:00:00-06:00",
    },
    conditions: ["40 ft dry container", "Saturday gate fee added at dispatch"],
  },
  valid_until: "2026-08-29T17:09:00Z",
} satisfies QuoteResponse;

const QUOTE_ONE_CURRENT = {
  call_id: SESSION_ONE.call_id,
  carrier_id: SESSION_ONE.carrier.carrier_id,
  created_at: "2026-08-29T14:15:00Z",
  eligibility: "ELIGIBLE",
  mandate_version: 3,
  operation_id: OPERATION_ID,
  quote_id: "quote-puerto-azul-02",
  rejection_reasons: [],
  terms: {
    amount_minor: 17_950_00,
    currency: "MXN",
    pickup_window: {
      start_date: "2026-09-01T08:00:00-06:00",
      end_date: "2026-09-01T13:00:00-06:00",
    },
    conditions: ["40 ft dry container", "Gate fee included"],
  },
  valid_until: "2026-08-29T18:15:00Z",
} satisfies QuoteResponse;

const QUOTE_TWO = {
  call_id: SESSION_TWO.call_id,
  carrier_id: SESSION_TWO.carrier.carrier_id,
  created_at: "2026-08-29T14:13:00Z",
  eligibility: "ELIGIBLE",
  mandate_version: 3,
  operation_id: OPERATION_ID,
  quote_id: "quote-ruta-norte-01",
  rejection_reasons: [],
  terms: {
    amount_minor: 18_250_00,
    currency: "MXN",
    pickup_window: {
      start_date: "2026-09-01T09:00:00-06:00",
      end_date: "2026-09-01T15:00:00-06:00",
    },
    conditions: ["40 ft dry container", "Two-hour free wait time"],
  },
  valid_until: "2026-08-29T18:13:00Z",
} satisfies QuoteResponse;

const QUOTE_THREE = {
  call_id: SESSION_THREE.call_id,
  carrier_id: SESSION_THREE.carrier.carrier_id,
  created_at: "2026-08-29T14:12:00Z",
  eligibility: "REJECTED",
  mandate_version: 3,
  operation_id: OPERATION_ID,
  quote_id: "quote-altamar-01",
  rejection_reasons: [
    "Pickup ends after the approved September 1 window.",
    "Demurrage surcharge is not an allowed condition in mandate v3.",
  ],
  terms: {
    amount_minor: 18_100_00,
    currency: "MXN",
    pickup_window: {
      start_date: "2026-09-02T08:00:00-06:00",
      end_date: "2026-09-02T16:00:00-06:00",
    },
    conditions: [
      "40 ft dry container",
      "Demurrage surcharge applies after 60 minutes at the terminal",
    ],
  },
  valid_until: "2026-08-29T16:12:00Z",
} satisfies QuoteResponse;

const PRE_CONTACT_ESCALATION = {
  attempted_alternatives: [
    "Checked route coverage",
    "Checked declared pickup availability",
  ],
  call_id: null,
  conflict:
    "No synthetic carrier is eligible for both the route and approved pickup window.",
  correlation_id: "corr-demo-no-eligible",
  created_at: "2026-08-29T14:01:00Z",
  escalation_id: "escalation-pre-contact-01",
  operation_id: OPERATION_ID,
  recommended_action:
    "Review the pickup window or add an approved carrier before starting negotiation.",
  resolution_state: "OPEN",
} satisfies EscalationResponse;

const RETRYABLE_ERROR = {
  code: "RATE_LIMITED",
  message:
    "The simulated response is temporarily unavailable. Retry stays inside this demo source.",
  request_id: "request-demo-retryable-01",
  resource_id: OPERATION_ID,
} satisfies ApiErrorResponse;

function createOperation(
  overrides: Partial<OperationResponse> = {},
): OperationResponse {
  return {
    active_commitment: null,
    active_mandate: {
      allowed_conditions: [
        "40 ft dry container",
        "Gate fee included",
        "Up to two hours free wait time",
      ],
      approval_actor: "demo.coordinator",
      approved_at: "2026-08-29T13:45:00Z",
      currency: "MXN",
      escalation_conditions: [
        "Price above MXN 18,500.00",
        "Pickup outside September 1",
      ],
      mandate_id: "mandate-demo-042-v3",
      maximum_amount_minor: 18_500_00,
      pickup_window: {
        start_date: "2026-09-01T08:00:00-06:00",
        end_date: "2026-09-01T18:00:00-06:00",
      },
      version: 3,
    },
    cargo_label: "Synthetic 40 ft dry container · Manzanillo terminal release",
    created_at: "2026-08-29T13:40:00Z",
    negotiation_summary: {
      active_session_count: 0,
      negotiation_id: NEGOTIATION_ID,
      selected_carrier_count: 0,
      valid_quote_count: 0,
    },
    notifications: [],
    open_escalation: null,
    operation_id: OPERATION_ID,
    operation_version: 7,
    quotes: [],
    route: {
      origin: "Manzanillo, Colima",
      destination: "Guadalajara, Jalisco",
    },
    sessions: [],
    status: "NEGOTIATING",
    updated_at: "2026-08-29T14:20:00Z",
    ...overrides,
  };
}

function createNegotiation(
  sessions: CarrierSessionResponse[],
  preContactEscalation: EscalationResponse | null = null,
): NegotiationResponse {
  return {
    negotiation_id: NEGOTIATION_ID,
    operation_id: OPERATION_ID,
    operation_version: 7,
    pre_contact_escalation: preContactEscalation,
    sessions,
    started_at: "2026-08-29T14:01:00Z",
  };
}

const ONE_SESSION = createOperation({
  negotiation_summary: {
    active_session_count: 1,
    negotiation_id: NEGOTIATION_ID,
    selected_carrier_count: 1,
    valid_quote_count: 0,
  },
  sessions: [{ ...SESSION_ONE, started_at: null, state: "SELECTED" }],
  updated_at: "2026-08-29T14:02:00Z",
});

const TWO_SESSIONS = createOperation({
  negotiation_summary: {
    active_session_count: 1,
    negotiation_id: NEGOTIATION_ID,
    selected_carrier_count: 2,
    valid_quote_count: 1,
  },
  quotes: [QUOTE_ONE_EARLIER, QUOTE_TWO],
  sessions: [SESSION_ONE, SESSION_TWO],
  updated_at: "2026-08-29T14:17:00Z",
});

const ACTIVE_MARKET = createOperation({
  negotiation_summary: {
    active_session_count: 1,
    negotiation_id: NEGOTIATION_ID,
    selected_carrier_count: 3,
    valid_quote_count: 2,
  },
  quotes: [QUOTE_ONE_EARLIER, QUOTE_ONE_CURRENT, QUOTE_TWO, QUOTE_THREE],
  sessions: [SESSION_ONE, SESSION_TWO, SESSION_THREE],
});

const NO_ELIGIBLE = createOperation({
  negotiation_summary: {
    active_session_count: 0,
    negotiation_id: NEGOTIATION_ID,
    selected_carrier_count: 0,
    valid_quote_count: 0,
  },
  open_escalation: PRE_CONTACT_ESCALATION,
  sessions: [],
  status: "ESCALATED",
  updated_at: PRE_CONTACT_ESCALATION.created_at,
});

const TERMINAL_FAILURE = createOperation({
  negotiation_summary: {
    active_session_count: 0,
    negotiation_id: NEGOTIATION_ID,
    selected_carrier_count: 1,
    valid_quote_count: 0,
  },
  sessions: [
    {
      ...SESSION_ONE,
      ended_at: "2026-08-29T14:11:00Z",
      state: "FAILED",
    },
  ],
  updated_at: "2026-08-29T14:11:00Z",
});

const SCENARIOS = [
  {
    id: "loading",
    label: "Loading",
    description: "Initial operation read is still pending.",
  },
  {
    id: "one-session",
    label: "1 selected",
    description: "One ranked carrier is selected, before contact begins.",
  },
  {
    id: "two-sessions",
    label: "2 sessions",
    description: "Two sessions show eligible and mandate-rejected terms.",
  },
  {
    id: "active-market",
    label: "3 sessions",
    description: "Three sessions and a quote revision, stopping at comparison.",
  },
  {
    id: "reconnecting",
    label: "Reconnecting",
    description: "Previously rendered data remains visible during reconnect.",
  },
  {
    id: "retryable-error",
    label: "Retryable error",
    description: "A sanitized injected error offers a side-effect-free retry.",
  },
  {
    id: "no-eligible",
    label: "No eligible",
    description: "A pre-contact escalation appears with zero sessions.",
  },
  {
    id: "terminal-failure",
    label: "Failed",
    description: "The only carrier session ended without a quote.",
  },
] as const satisfies readonly NegotiationScenarioOption[];

const SNAPSHOTS = {
  loading: {
    mode: "loading",
    announcement: "Loading simulated negotiation data…",
  },
  "one-session": {
    mode: "ready",
    announcement: "One selected carrier session is displayed.",
    data: {
      operation: ONE_SESSION,
      negotiation: createNegotiation(ONE_SESSION.sessions ?? []),
    },
  },
  "two-sessions": {
    mode: "ready",
    announcement:
      "Two carrier sessions and their recorded quotes are displayed.",
    data: {
      operation: TWO_SESSIONS,
      negotiation: createNegotiation(TWO_SESSIONS.sessions ?? []),
    },
  },
  "active-market": {
    mode: "ready",
    announcement:
      "Three carrier sessions and their comparison are displayed without a winner.",
    data: {
      operation: ACTIVE_MARKET,
      negotiation: createNegotiation(ACTIVE_MARKET.sessions ?? []),
    },
  },
  reconnecting: {
    mode: "reconnecting",
    announcement:
      "Reconnecting to the injected source. Previously rendered data remains available.",
    data: {
      operation: ACTIVE_MARKET,
      negotiation: createNegotiation(ACTIVE_MARKET.sessions ?? []),
    },
  },
  "retryable-error": {
    mode: "error",
    announcement: "The simulated read failed and can be retried safely.",
    error: RETRYABLE_ERROR,
    retryable: true,
  },
  "no-eligible": {
    mode: "terminal",
    announcement:
      "No carrier was contacted. A pre-contact escalation is displayed.",
    data: {
      operation: NO_ELIGIBLE,
      negotiation: createNegotiation([], PRE_CONTACT_ESCALATION),
    },
  },
  "terminal-failure": {
    mode: "terminal",
    announcement: "The carrier session ended without a recorded quote.",
    data: {
      operation: TERMINAL_FAILURE,
      negotiation: createNegotiation(TERMINAL_FAILURE.sessions ?? []),
    },
  },
} as const satisfies Record<DemoScenarioId, NegotiationExperienceSnapshot>;

export function createDemoNegotiationExperienceSource(): NegotiationExperienceSource {
  return {
    scenarios: SCENARIOS,
    read(scenarioId) {
      return SNAPSHOTS[scenarioId];
    },
    retry() {
      return SNAPSHOTS.reconnecting;
    },
  };
}
