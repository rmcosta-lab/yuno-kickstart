import { expect, test, type Page, type Route } from "@playwright/test";

import type {
  AuditTimelineResponse,
  HumanHandoffReadinessResponse,
  HumanHandoffResponse,
  OperationResponse,
} from "../../src/lib/api/generated/models";

const OPERATION_ID = "28000000-0000-4000-8000-000000000001";
const CALL_ID = "28000000-0000-4000-8000-000000000002";
const HANDOFF_ID = "28000000-0000-4000-8000-000000000003";
const STATUS_UPDATED_AT = "2026-08-30T14:00:01Z";

const operation: OperationResponse = {
  active_mandate: {
    allowed_conditions: ["Gate fee included", "Two hours free wait time"],
    approval_actor: "synthetic-coordinator",
    approved_at: "2026-08-30T13:00:00Z",
    currency: "MXN",
    escalation_conditions: ["Price above the approved ceiling"],
    mandate_id: "28000000-0000-4000-8000-000000000004",
    maximum_amount_minor: 900_000,
    pickup_window: {
      start_date: "2026-09-03",
      end_date: "2026-09-03",
    },
    version: 4,
  },
  cargo_label: "Synthetic textiles",
  created_at: "2026-08-30T13:00:00Z",
  operation_id: OPERATION_ID,
  operation_version: 8,
  quotes: [
    {
      call_id: CALL_ID,
      carrier_id: "28000000-0000-4000-8000-000000000005",
      created_at: "2026-08-30T13:30:00Z",
      eligibility: "ELIGIBLE",
      mandate_version: 4,
      operation_id: OPERATION_ID,
      quote_id: "28000000-0000-4000-8000-000000000006",
      terms: {
        amount_minor: 850_000,
        conditions: ["Gate fee included"],
        currency: "MXN",
        pickup_window: {
          start_date: "2026-09-03",
          end_date: "2026-09-03",
        },
      },
      valid_until: "2026-08-30T18:00:00Z",
    },
  ],
  route: { origin: "Synthetic origin", destination: "Synthetic destination" },
  sessions: [
    {
      call_id: CALL_ID,
      carrier: {
        carrier_id: "28000000-0000-4000-8000-000000000005",
        deterministic_rank: 1,
        display_name: "Synthetic Carrier One",
        eligible: true,
      },
      channel: "BROWSER_TEXT",
      direction: "OUTBOUND_SIMULATION",
      state: "ACTIVE",
    },
  ],
  status: "NEGOTIATING",
  updated_at: "2026-08-30T13:45:00Z",
};

const audit: AuditTimelineResponse = {
  briefs: [
    {
      brief_id: "28000000-0000-4000-8000-000000000007",
      call_id: CALL_ID,
      changes: ["Pickup gate moved to the east entrance"],
      commitment_id: "28000000-0000-4000-8000-000000000008",
      created_at: "2026-08-30T13:50:00Z",
      facts: ["Container is ready for release"],
      objections: ["Driver requested faster gate processing"],
      operation_id: OPERATION_ID,
      unresolved_items: ["Confirm terminal appointment code"],
    },
  ],
  commitment_history: [],
  escalations: [],
  events: [],
  notifications: [],
  operation_id: OPERATION_ID,
  quote_comparison: [
    {
      call_id: CALL_ID,
      carrier_display_name: "Synthetic Carrier One",
      carrier_id: "28000000-0000-4000-8000-000000000005",
      created_at: "2026-08-30T13:30:00Z",
      eligibility: "ELIGIBLE",
      mandate_version: 4,
      quote_id: "28000000-0000-4000-8000-000000000006",
      selected: true,
      terms: {
        amount_minor: 850_000,
        conditions: ["Gate fee included"],
        currency: "MXN",
        pickup_window: {
          start_date: "2026-09-03",
          end_date: "2026-09-03",
        },
      },
      valid_until: "2026-08-30T18:00:00Z",
    },
  ],
  recaps: [],
  recoveries: [],
};

const readiness: HumanHandoffReadinessResponse = {
  call_id: CALL_ID,
  call_status_updated_at: STATUS_UPDATED_AT,
  context: {
    call_status: "IN_PROGRESS",
    eligible_quote_summaries: ["Synthetic Carrier One · MXN 8,500.00"],
    mandate_facts: ["Mandate v4 · maximum MXN 9,000.00"],
    mandate_version: 4,
    structured_call_brief: ["Container ready; appointment code unresolved"],
  },
};

function handoff(status: HumanHandoffResponse["status"]): HumanHandoffResponse {
  return {
    call_id: CALL_ID,
    context: readiness.context,
    handoff_id: HANDOFF_ID,
    requested_at: "2026-08-30T14:01:00Z",
    status,
    status_updated_at: "2026-08-30T14:01:01Z",
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    body: JSON.stringify(body),
    contentType: "application/json",
    status,
  });
}

async function loadLiveOperation(page: Page) {
  await page.goto("/sessions");
  await page.waitForTimeout(500);
  await page
    .getByRole("textbox", { name: "Live operation ID" })
    .fill(OPERATION_ID);
  await page.getByRole("button", { name: "Load server state" }).click();
  await page
    .locator("summary")
    .filter({ hasText: "More Session Tools" })
    .click();
}

test("confirms once, polls durable status, and preserves transcript-free context", async ({
  page,
}) => {
  const postRequests: { body: unknown; key: string }[] = [];
  let getCount = 0;
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));

  await page.route("**/api/volta/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace(/^\/api\/volta/, "");
    if (request.method() === "GET" && path === `/v1/operations/${OPERATION_ID}`)
      return fulfillJson(route, operation);
    if (
      request.method() === "GET" &&
      path === `/v1/operations/${OPERATION_ID}/audit`
    )
      return fulfillJson(route, audit);
    if (
      request.method() === "GET" &&
      path === `/v1/calls/${CALL_ID}/handoff-readiness`
    )
      return fulfillJson(route, readiness);
    if (
      request.method() === "POST" &&
      path === `/v1/calls/${CALL_ID}/handoffs`
    ) {
      postRequests.push({
        body: request.postDataJSON(),
        key: request.headers()["idempotency-key"] ?? "",
      });
      await new Promise((resolve) => setTimeout(resolve, 150));
      return fulfillJson(route, handoff("CONNECTING"), 202);
    }
    if (
      request.method() === "GET" &&
      path === `/v1/calls/${CALL_ID}/handoffs/${HANDOFF_ID}`
    ) {
      getCount += 1;
      return fulfillJson(
        route,
        handoff(getCount >= 2 ? "JOINED" : "CONNECTING"),
      );
    }
    return fulfillJson(
      route,
      {
        code: "RESOURCE_NOT_FOUND",
        message: "Unhandled fixture",
        request_id: "fixture",
      },
      404,
    );
  });

  await loadLiveOperation(page);
  const control = page.getByTestId("human-handoff-control");
  await expect(control.getByText("IN PROGRESS", { exact: true })).toBeVisible();
  await expect(control.getByText("$9,000.00", { exact: true })).toBeVisible();
  await expect(
    control.getByText("Synthetic Carrier One", { exact: true }),
  ).toBeVisible();
  await expect(
    control.getByText("Container ready; appointment code unresolved", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(control).toContainText("no transcript");
  await expect(control).not.toContainText("provider-private-sid");
  await expect(control).not.toContainText("+15551234567");

  const confirmation = control.getByRole("checkbox", {
    name: /fresh human takeover/i,
  });
  const takeover = control.getByRole("button", { name: "Take over live call" });
  await confirmation.focus();
  await page.keyboard.press("Space");
  await expect(confirmation).toBeChecked();
  await takeover.focus();
  await page.keyboard.press("Enter");
  await expect(control.getByText("PROCESSING", { exact: true })).toBeVisible();
  await expect(
    control.getByRole("button", { name: /Taking over live call/ }),
  ).toBeDisabled();

  await expect(control.getByText("JOINED", { exact: true })).toBeVisible({
    timeout: 5_000,
  });
  await expect(control).toContainText("Duplicate takeover is disabled");
  expect(postRequests).toHaveLength(1);
  expect(postRequests[0].key).toMatch(/^[\x20-\x7E]{8,128}$/);
  expect(postRequests[0].body).toEqual({
    authorized_at: expect.any(String),
    authorized_by: "coordinator-demo",
    coordinator_destination_label: "Demo coordinator",
    expected_call_status_updated_at: STATUS_UPDATED_AT,
  });
  expect(getCount).toBeGreaterThanOrEqual(2);

  await control.getByRole("link", { name: "Browser voice fallback" }).click();
  await expect(page.getByText("Browser voice simulator")).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test("rechecks an uncertain timeout with the exact same request and no provider retry", async ({
  page,
}) => {
  const postRequests: { body: unknown; key: string }[] = [];

  await page.route("**/api/volta/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace(/^\/api\/volta/, "");
    if (request.method() === "GET" && path === `/v1/operations/${OPERATION_ID}`)
      return fulfillJson(route, operation);
    if (
      request.method() === "GET" &&
      path === `/v1/operations/${OPERATION_ID}/audit`
    )
      return fulfillJson(route, audit);
    if (
      request.method() === "GET" &&
      path === `/v1/calls/${CALL_ID}/handoff-readiness`
    )
      return fulfillJson(route, readiness);
    if (
      request.method() === "POST" &&
      path === `/v1/calls/${CALL_ID}/handoffs`
    ) {
      postRequests.push({
        body: request.postDataJSON(),
        key: request.headers()["idempotency-key"] ?? "",
      });
      return postRequests.length === 1
        ? fulfillJson(
            route,
            {
              code: "TELEPHONY_OUTCOME_UNCERTAIN",
              message: "Private provider diagnostic must stay hidden",
              request_id: "provider-private-sid",
            },
            504,
          )
        : fulfillJson(route, handoff("TIMED_OUT_SAFE"), 202);
    }
    if (
      request.method() === "GET" &&
      path === `/v1/calls/${CALL_ID}/handoffs/${HANDOFF_ID}`
    )
      return fulfillJson(route, handoff("TIMED_OUT_SAFE"));
    return fulfillJson(
      route,
      {
        code: "RESOURCE_NOT_FOUND",
        message: "Unhandled fixture",
        request_id: "fixture",
      },
      404,
    );
  });

  await loadLiveOperation(page);
  const control = page.getByTestId("human-handoff-control");
  await control
    .getByRole("checkbox", { name: /fresh human takeover/i })
    .check();
  await control.getByRole("button", { name: "Take over live call" }).click();
  await expect(
    control.getByText("TIMED OUT SAFE", { exact: true }),
  ).toBeVisible();
  await expect(control).toContainText("Human participation is not confirmed");
  await expect(control).toContainText("AI authority stays suspended");
  await expect(control).not.toContainText("Private provider diagnostic");
  await expect(control).not.toContainText("provider-private-sid");

  await control.getByRole("button", { name: "Recheck handoff status" }).click();
  await expect(
    control.getByText("TIMED OUT SAFE", { exact: true }),
  ).toBeVisible();
  expect(postRequests).toHaveLength(2);
  expect(postRequests[1]).toEqual(postRequests[0]);
  await expect(control).not.toContainText("Retry safe handoff");
  await expect(control).not.toContainText("Terminate call");
});

test("keeps takeover disabled until readiness succeeds and describes 409 generically", async ({
  page,
}) => {
  let readinessAvailable = false;
  await page.route("**/api/volta/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace(/^\/api\/volta/, "");
    if (request.method() === "GET" && path === `/v1/operations/${OPERATION_ID}`)
      return fulfillJson(route, operation);
    if (
      request.method() === "GET" &&
      path === `/v1/operations/${OPERATION_ID}/audit`
    )
      return fulfillJson(route, audit);
    if (
      request.method() === "GET" &&
      path === `/v1/calls/${CALL_ID}/handoff-readiness`
    ) {
      return readinessAvailable
        ? fulfillJson(route, readiness)
        : fulfillJson(
            route,
            {
              code: "STATE_CONFLICT",
              message: "Call is not ready",
              request_id: "safe-request",
            },
            409,
          );
    }
    if (request.method() === "POST" && path === `/v1/calls/${CALL_ID}/handoffs`)
      return fulfillJson(
        route,
        {
          code: "STATE_CONFLICT",
          message: "State changed",
          request_id: "safe-request",
        },
        409,
      );
    return fulfillJson(
      route,
      {
        code: "RESOURCE_NOT_FOUND",
        message: "Unhandled fixture",
        request_id: "fixture",
      },
      404,
    );
  });

  await loadLiveOperation(page);
  const control = page.getByTestId("human-handoff-control");
  await expect(
    control.getByRole("checkbox", { name: /fresh human takeover/i }),
  ).toBeDisabled();
  await expect(
    control.getByText("Live call readiness is unavailable"),
  ).toBeVisible();
  readinessAvailable = true;
  await control
    .getByRole("button", { name: "Reload live call readiness" })
    .click();
  await expect(control.getByText("IN PROGRESS", { exact: true })).toBeVisible();
  await control
    .getByRole("checkbox", { name: /fresh human takeover/i })
    .check();
  await control.getByRole("button", { name: "Take over live call" }).click();
  await expect(
    control.getByText("STATE CHANGED", { exact: true }),
  ).toBeVisible();
  await expect(control).toContainText(
    "stale call context, an active handoff, or an idempotency conflict",
  );
  await expect(control).not.toContainText("No transfer was started");
});
