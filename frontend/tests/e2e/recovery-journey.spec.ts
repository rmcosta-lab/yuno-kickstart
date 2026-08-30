import { expect, test, type Page, type Route } from "@playwright/test";

import type {
  AuditTimelineResponse,
  CallBriefResponse,
  CommitmentResponse,
  CoordinatorNotificationResponse,
  EscalationResponse,
  OperationDraftResponse,
  OperationResponse,
  QuoteComparisonRow,
  RecoverySimulationResponse,
  WrittenRecapResponse,
} from "../../src/lib/api/generated/models";

const IDS = {
  operation: "10000000-0000-4000-8000-000000000001",
  mandate1: "20000000-0000-4000-8000-000000000001",
  mandate2: "20000000-0000-4000-8000-000000000002",
  commitment1: "30000000-0000-4000-8000-000000000001",
  commitment2: "30000000-0000-4000-8000-000000000002",
  evidence: "40000000-0000-4000-8000-000000000001",
  quote: "50000000-0000-4000-8000-000000000001",
  recap: "60000000-0000-4000-8000-000000000001",
  brief: "70000000-0000-4000-8000-000000000001",
  recoverySafe: "80000000-0000-4000-8000-000000000001",
  recoveryBad: "80000000-0000-4000-8000-000000000002",
  escalation: "90000000-0000-4000-8000-000000000001",
  notification: "a0000000-0000-4000-8000-000000000001",
  event: "b0000000-0000-4000-8000-000000000001",
} as const;

const timestamp = (second: number) =>
  `2026-08-30T12:00:${String(second).padStart(2, "0")}Z`;
const pickup = { start_date: "2026-09-01", end_date: "2026-09-02" };
const terms = {
  amount_minor: 125_000,
  currency: "MXN" as const,
  pickup_window: pickup,
  conditions: ["Same-day confirmation"],
};

const commitment = (id: string, amount = 125_000): CommitmentResponse => ({
  agreed_terms: { ...terms, amount_minor: amount },
  call_id: "call-demo",
  carrier_id: "carrier-demo",
  commitment_id: id,
  created_at: timestamp(id === IDS.commitment1 ? 2 : 6),
  disposition: "ACTIVE",
  evidence: {
    audio_start_ms: 250,
    call_id: "call-demo",
    created_at: timestamp(2),
    event_id: "event-audio",
    evidence_id: IDS.evidence,
    item_id: "item-audio",
    lifecycle: "SIMULATED",
  },
  lifecycle: "SIMULATED",
  mandate_version: 1,
  operation_id: IDS.operation,
  quote_id: IDS.quote,
});

const escalation: EscalationResponse = {
  attempted_alternatives: ["Keep the original pickup", "Use a relay carrier"],
  call_id: "call-demo",
  conflict: "The requested price exceeds the active mandate.",
  correlation_id: "correlation-bad",
  created_at: timestamp(8),
  escalation_id: IDS.escalation,
  operation_id: IDS.operation,
  recommended_action: "Approve a bounded replacement mandate.",
  resolution_state: "OPEN",
};

const notification: CoordinatorNotificationResponse = {
  acknowledged: false,
  correlation_id: "correlation-safe",
  created_at: timestamp(6),
  message: "The carrier accepted a safe pickup adjustment.",
  notification_id: IDS.notification,
  operation_id: IDS.operation,
  operation_version: 3,
  recovery_decision: {
    before: {
      active_commitment_id: IDS.commitment1,
      operation_status: "COMMITTED",
      operation_version: 2,
    },
    after: {
      active_commitment_id: IDS.commitment2,
      operation_status: "COMMITTED",
      operation_version: 3,
    },
    reason: "Within the current mandate.",
  },
};

const recap: WrittenRecapResponse = {
  call_id: "call-demo",
  channel: "SIMULATED",
  commitment_id: IDS.commitment1,
  content_hash: "recap-content-hash",
  created_at: timestamp(3),
  operation_id: IDS.operation,
  recap_id: IDS.recap,
  rendered_content: "Carrier accepted MXN 1,250 for the documented route.",
};

const brief: CallBriefResponse = {
  brief_id: IDS.brief,
  call_id: "call-demo",
  commitment_id: IDS.commitment1,
  changes: ["Pickup moved by one day"],
  created_at: timestamp(4),
  facts: ["Carrier identity verified"],
  objections: ["Traffic risk"],
  operation_id: IDS.operation,
  unresolved_items: ["Final gate slot"],
};

const quote: QuoteComparisonRow = {
  call_id: "call-demo",
  carrier_display_name: "Demo Carrier",
  carrier_id: "carrier-demo",
  created_at: timestamp(1),
  eligibility: "ELIGIBLE",
  mandate_version: 1,
  quote_id: IDS.quote,
  selected: true,
  terms,
  valid_until: "2026-09-01T00:00:00Z",
};

const safeRecovery: RecoverySimulationResponse = {
  active_commitment: commitment(IDS.commitment2, 128_000),
  after_operation_version: 3,
  before_operation_version: 2,
  correlation_id: "correlation-safe",
  created_at: timestamp(6),
  decision_reason: "The adjustment remains inside the active mandate.",
  operation_id: IDS.operation,
  recovery_id: IDS.recoverySafe,
  scenario: "MANDATE_SAFE",
};

const badRecovery: RecoverySimulationResponse = {
  active_commitment: commitment(IDS.commitment2, 128_000),
  after_operation_version: 5,
  before_operation_version: 4,
  correlation_id: "correlation-bad",
  created_at: timestamp(8),
  decision_reason: "Human approval is required outside the mandate.",
  escalation,
  operation_id: IDS.operation,
  recovery_id: IDS.recoveryBad,
  scenario: "OUT_OF_MANDATE",
};

function makeOperation(version: number): OperationResponse {
  const hasReplacement = version >= 6;
  const hasSafeRecovery = version >= 3;
  return {
    active_commitment: hasSafeRecovery
      ? commitment(IDS.commitment2, 128_000)
      : commitment(IDS.commitment1),
    active_mandate: {
      allowed_conditions: ["Same-day confirmation"],
      approval_actor: hasReplacement
        ? "demo-coordinator"
        : "initial-coordinator",
      approved_at: timestamp(hasReplacement ? 10 : 0),
      currency: "MXN",
      escalation_conditions: ["Amount above ceiling"],
      mandate_id: hasReplacement ? IDS.mandate2 : IDS.mandate1,
      maximum_amount_minor: hasReplacement ? 150_000 : 130_000,
      pickup_window: pickup,
      version: hasReplacement ? 2 : 1,
    },
    cargo_label: "Demo electronics",
    created_at: timestamp(0),
    notifications: hasSafeRecovery
      ? [
          {
            ...notification,
            acknowledged: version >= 4,
            acknowledged_at: version >= 4 ? timestamp(7) : null,
            acknowledged_by: version >= 4 ? "demo-coordinator" : null,
          },
        ]
      : [],
    open_escalation: version === 5 ? escalation : null,
    operation_id: IDS.operation,
    operation_version: version,
    quotes: [{ ...quote, operation_id: IDS.operation }],
    route: { origin: "Santos", destination: "São Paulo" },
    sessions: [],
    status: version === 5 ? "ESCALATED" : "COMMITTED",
    updated_at: timestamp(Math.min(version + 1, 10)),
  };
}

const emptyAudit = (
  nextCursor: string | null = null,
): AuditTimelineResponse => ({
  briefs: [],
  commitment_history: [],
  escalations: [],
  events: [],
  next_cursor: nextCursor,
  notifications: [],
  operation_id: IDS.operation,
  quote_comparison: [],
  recaps: [],
  recoveries: [],
});

function auditPage(
  cursor: string | null,
  version: number,
): AuditTimelineResponse {
  if (cursor) {
    return {
      ...emptyAudit(),
      briefs: [brief],
      escalations:
        version >= 5
          ? [
              {
                ...escalation,
                resolution_state: version >= 6 ? "RESOLVED" : "OPEN",
                resolved_at: version >= 6 ? timestamp(10) : null,
              },
            ]
          : [],
      notifications:
        version >= 3 ? [{ ...notification, acknowledged: version >= 4 }] : [],
      recoveries:
        version >= 3
          ? [safeRecovery, ...(version >= 5 ? [badRecovery] : [])]
          : [],
    };
  }
  return {
    ...emptyAudit("cursor-1"),
    commitment_history: [
      {
        ...commitment(IDS.commitment1),
        disposition: version >= 3 ? "SUPERSEDED" : "ACTIVE",
      },
    ],
    events: [
      {
        actor_kind: "SYSTEM",
        correlation_id: "correlation-event",
        event_id: IDS.event,
        event_type: "OPERATION_APPROVED",
        occurred_at: timestamp(1),
        operation_version: 1,
      },
    ],
    quote_comparison: [quote],
    recaps: [recap],
  };
}

function wavBuffer() {
  const samples = 8_000;
  const dataSize = samples * 2;
  const buffer = Buffer.alloc(44 + dataSize);
  buffer.write("RIFF", 0);
  buffer.writeUInt32LE(36 + dataSize, 4);
  buffer.write("WAVEfmt ", 8);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(8_000, 24);
  buffer.writeUInt32LE(16_000, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write("data", 36);
  buffer.writeUInt32LE(dataSize, 40);
  return buffer;
}

type Harness = {
  getOperationCount: number;
  safeKeys: string[];
  badKeys: string[];
  replacementBodies: unknown[];
};

async function installApiHarness(page: Page): Promise<Harness> {
  const state: Harness = {
    getOperationCount: 0,
    safeKeys: [],
    badKeys: [],
    replacementBodies: [],
  };
  let version = 2;
  let safeFailures = 0;
  const json = (route: Route, body: unknown, status = 200) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });

  await page.route("**/api/volta/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^\/api\/volta/, "");
    const method = request.method();
    if (path === "/v1/operation-drafts" && method === "POST") {
      const draft: OperationDraftResponse = {
        approval_eligible: true,
        created_at: timestamp(0),
        draft_id: "d0000000-0000-4000-8000-000000000001",
        draft_version: 1,
        extraction_policy_version: "phase-16-test",
        proposed_mandate: {
          allowed_conditions: ["Same-day confirmation"],
          currency: "MXN",
          escalation_conditions: ["Amount above ceiling"],
          maximum_amount_minor: 130_000,
          pickup_window: pickup,
        },
        proposed_pickup_date: "2026-09-01",
        proposed_route: { origin: "Santos", destination: "São Paulo" },
        requested_language: "EN_US",
        source_prompt: "Synthetic deterministic intake prompt.",
        updated_at: timestamp(0),
      };
      return json(route, draft, 201);
    }
    if (path === "/v1/operations" && method === "POST")
      return json(route, makeOperation(version), 201);
    if (path === `/v1/operations/${IDS.operation}` && method === "GET") {
      state.getOperationCount += 1;
      return json(route, makeOperation(version));
    }
    if (path === `/v1/evidence/${IDS.evidence}/audio`) {
      return route.fulfill({
        status: 200,
        contentType: "audio/wav",
        body: wavBuffer(),
      });
    }
    if (path.endsWith("/inbound-simulations") && method === "POST") {
      const body = request.postDataJSON() as { scenario: string };
      const key = request.headers()["idempotency-key"] ?? "";
      if (body.scenario === "MANDATE_SAFE") {
        state.safeKeys.push(key);
        if (safeFailures++ === 0) {
          return route.fulfill({
            status: 502,
            contentType: "text/plain",
            headers: { "X-Request-ID": "request-safe-502" },
            body: "private upstream failure",
          });
        }
        version = 3;
        return json(route, safeRecovery, 201);
      }
      state.badKeys.push(key);
      version = 5;
      return json(route, badRecovery, 201);
    }
    if (path.endsWith("/acknowledgements") && method === "POST") {
      version = 4;
      return json(route, {
        ...notification,
        acknowledged: true,
        acknowledged_at: timestamp(7),
        acknowledged_by: "demo-coordinator",
      });
    }
    if (path.endsWith("/mandates") && method === "POST") {
      state.replacementBodies.push(request.postDataJSON());
      version = 6;
      return json(route, makeOperation(version), 201);
    }
    if (path.endsWith("/audit") && method === "GET") {
      if (url.searchParams.get("limit") === "100") {
        const first = auditPage(null, version);
        const second = auditPage("cursor-1", version);
        return json(route, {
          ...first,
          briefs: second.briefs,
          escalations: second.escalations,
          next_cursor: null,
          notifications: second.notifications,
          recoveries: second.recoveries,
        });
      }
      return json(route, auditPage(url.searchParams.get("cursor"), version));
    }
    return json(
      route,
      {
        code: "RESOURCE_NOT_FOUND",
        message: `Unhandled ${method} ${path}`,
        request_id: "request-unhandled",
      },
      404,
    );
  });
  return state;
}

async function connectAndCreateOperation(page: Page) {
  await page.goto("/intake");
  await page.waitForTimeout(500);
  await page.getByRole("button", { name: /Use canonical prompt/i }).click();
  await page.getByRole("button", { name: "Submit draft" }).click();
  await page.getByRole("link", { name: "Continue to mandate review" }).click();
  await page.getByRole("button", { name: "Approve mandate" }).click();
  await expect(page.getByText(IDS.operation)).toBeVisible();
}

test("covers recovery surfaces, safe audio lifecycle, retry identity and authoritative refetch", async ({
  page,
}) => {
  const harness = await installApiHarness(page);
  await page.addInitScript(() => {
    const create = URL.createObjectURL.bind(URL);
    const revoke = URL.revokeObjectURL.bind(URL);
    (
      window as typeof window & {
        __createdUrls: string[];
        __revokedUrls: string[];
      }
    ).__createdUrls = [];
    (
      window as typeof window & {
        __createdUrls: string[];
        __revokedUrls: string[];
      }
    ).__revokedUrls = [];
    URL.createObjectURL = (blob) => {
      const url = create(blob);
      (
        window as typeof window & { __createdUrls: string[] }
      ).__createdUrls.push(url);
      return url;
    };
    URL.revokeObjectURL = (url) => {
      (
        window as typeof window & { __revokedUrls: string[] }
      ).__revokedUrls.push(url);
      revoke(url);
    };
  });
  await connectAndCreateOperation(page);

  await page.getByRole("link", { name: "Evidence" }).click();
  await expect(
    page.getByText("LIFECYCLE · SIMULATED", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("DISPOSITION · ACTIVE", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByText(recap.rendered_content)).toBeVisible();
  await expect(page.getByText("Carrier identity verified")).toBeVisible();
  await expect(page.getByText("recording_reference")).toHaveCount(0);
  await page.getByRole("button", { name: "Load evidence audio" }).click();
  await expect
    .poll(() =>
      page
        .locator("audio")
        .evaluate((audio) => (audio as HTMLAudioElement).currentTime),
    )
    .toBeGreaterThanOrEqual(0.24);
  await page.getByRole("button", { name: "Reload audio" }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as typeof window & { __createdUrls: string[] }).__createdUrls
            .length,
      ),
    )
    .toBe(2);
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as typeof window & { __revokedUrls: string[] }).__revokedUrls
            .length,
      ),
    )
    .toBeGreaterThanOrEqual(1);

  await page.getByRole("link", { name: "Recovery" }).click();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (window as typeof window & { __revokedUrls: string[] }).__revokedUrls
            .length,
      ),
    )
    .toBeGreaterThanOrEqual(2);
  const readsBeforeSafe = harness.getOperationCount;
  await page
    .getByRole("button", { name: "Run mandate-safe simulation" })
    .click();
  await expect(
    page.getByText("API request failed with status 502"),
  ).toBeVisible();
  await expect(page.getByText("private upstream failure")).toHaveCount(0);
  await page.getByRole("button", { name: "Retry same attempt" }).click();
  await expect(page.getByText("MANDATE_SAFE", { exact: true })).toBeVisible();
  expect(harness.safeKeys).toHaveLength(2);
  expect(harness.safeKeys[0]).toBe(harness.safeKeys[1]);
  expect(harness.getOperationCount).toBeGreaterThan(readsBeforeSafe);
  await expect(
    page.getByText("The carrier accepted a safe pickup adjustment."),
  ).toBeVisible();
  await page.getByRole("link", { name: "Evidence" }).click();
  await expect(
    page.getByText("DISPOSITION · ACTIVE", { exact: true }),
  ).toHaveCount(1);
  await expect(
    page.getByText("DISPOSITION · SUPERSEDED", { exact: true }),
  ).toHaveCount(1);
  await expect(page.getByText(recap.rendered_content)).toHaveCount(1);
  await page.getByRole("link", { name: "Recovery" }).click();
  const readsBeforeAck = harness.getOperationCount;
  await page
    .getByRole("button", { name: "Acknowledge as demo coordinator" })
    .click();
  await expect(
    page.getByText(/First acknowledged by demo-coordinator/),
  ).toBeVisible();
  expect(harness.getOperationCount).toBeGreaterThan(readsBeforeAck);
  await page
    .getByRole("button", { name: "Run out-of-mandate simulation" })
    .click();
  await expect(page.getByText("OUT_OF_MANDATE", { exact: true })).toBeVisible();
  expect(harness.badKeys).toHaveLength(1);
  expect(harness.badKeys[0]).not.toBe(harness.safeKeys[0]);

  await page.getByRole("link", { name: "Escalation" }).click();
  await expect(page.getByText(escalation.conflict)).toBeVisible();
  await expect(page.getByText(escalation.recommended_action)).toBeVisible();
  const submit = page.getByRole("button", {
    name: "Approve replacement mandate",
  });
  const allowed = page.getByLabel("Allowed conditions · one per line");
  const amount = page.getByLabel("Maximum amount (MXN)");
  await allowed.fill(
    Array.from({ length: 26 }, (_, index) => `condition ${index}`).join("\n"),
  );
  await submit.click();
  await expect(
    page.getByText("Enter no more than 25 conditions."),
  ).toBeVisible();
  await expect(allowed).toBeFocused();
  await expect(allowed).toHaveAttribute(
    "aria-describedby",
    "allowed_conditions-error",
  );
  await allowed.fill("x".repeat(501));
  await submit.click();
  await expect(
    page.getByText("Each condition must be 500 characters or fewer."),
  ).toBeVisible();
  await allowed.fill("Same-day confirmation");
  await amount.fill("abc");
  await submit.click();
  await expect(
    page.getByText("Enter an MXN amount with up to two decimals."),
  ).toBeVisible();
  await expect(amount).toBeFocused();
  await expect(amount).toHaveAttribute(
    "aria-describedby",
    "maximum_amount_mxn-error",
  );
  await amount.fill("");
  await submit.click();
  await expect(
    page.getByText("Enter an MXN amount with up to two decimals."),
  ).toBeVisible();
  await amount.fill("0");
  await submit.click();
  await expect(
    page.getByText("Enter an amount greater than zero."),
  ).toBeVisible();
  await amount.fill("90071992547410.00");
  await submit.click();
  await expect(
    page.getByText("Enter an amount within the supported safe integer range."),
  ).toBeVisible();
  expect(harness.replacementBodies).toHaveLength(0);
  await amount.fill("1500.00");
  await submit.click();
  await expect(page.getByText("Escalation resolved")).toBeVisible();
  await expect(page.getByText("RESOLVED", { exact: true })).toBeVisible();
  await expect(page.getByText("Version 2", { exact: true })).toBeVisible();
  await expect(
    page.getByText("COMMITTED · version 6", { exact: true }),
  ).toBeVisible();
  expect(harness.replacementBodies).toHaveLength(1);
  expect(harness.replacementBodies[0]).toMatchObject({
    maximum_amount_minor: 150_000,
    expected_operation_version: 5,
    resolved_escalation_id: IDS.escalation,
  });

  await page.getByRole("link", { name: "Audit" }).click();
  for (const kind of ["event", "quote", "commitment", "recap"] as const) {
    await expect(page.getByText(kind, { exact: true })).toBeVisible();
  }
  await page.getByRole("button", { name: "Load more audit artifacts" }).click();
  for (const kind of [
    "brief",
    "recovery",
    "escalation",
    "notification",
  ] as const) {
    await expect(page.getByText(kind, { exact: true }).first()).toBeVisible();
  }
  const quoteItem = page.locator("li", {
    hasText: `Quote · ${quote.carrier_display_name}`,
  });
  await expect(quoteItem.getByText(/Correlation/)).toHaveCount(0);
  const eventItem = page.locator("li", { hasText: "OPERATION_APPROVED" });
  await expect(
    eventItem.getByText("Correlation correlation-event"),
  ).toBeVisible();
  const orderedAuditIds = await page
    .locator("ol > li")
    .evaluateAll((items) =>
      items.map((item) =>
        [...item.querySelectorAll("span")]
          .map((span) => span.textContent?.trim())
          .find((text) => /^[-a-f0-9]{36}$/i.test(text ?? "")),
      ),
    );
  expect(orderedAuditIds).toEqual([
    IDS.quote,
    IDS.event,
    IDS.commitment1,
    IDS.recap,
    IDS.brief,
    IDS.recoverySafe,
    IDS.notification,
    IDS.recoveryBad,
    IDS.escalation,
  ]);
  await expect(
    page.getByText("End of the authoritative audit timeline."),
  ).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  for (const surface of ["Evidence", "Recovery", "Escalation", "Audit"]) {
    await page.getByRole("link", { name: surface, exact: true }).click();
    await expect
      .poll(() =>
        page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth,
        ),
      )
      .toBe(true);
  }
});
