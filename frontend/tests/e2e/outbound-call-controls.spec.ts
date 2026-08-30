import { expect, test, type Page, type Route } from "@playwright/test";

import type {
  OperationResponse,
  OutboundCallResponseStatus,
} from "../../src/lib/api/generated/models";

const OPERATION_ID = "20000000-0000-4000-8000-000000000020";
const LOWEST_RANK_SESSION_ID = "20000000-0000-4000-8000-000000000021";

const timestamp = (seconds = 0) =>
  new Date(Date.UTC(2026, 7, 30, 12, 0, seconds)).toISOString();

function operationWithSessions(hasSessions: boolean): OperationResponse {
  return {
    active_mandate: {
      approval_actor: "synthetic-coordinator",
      approved_at: timestamp(),
      currency: "MXN",
      mandate_id: "20000000-0000-4000-8000-000000000022",
      maximum_amount_minor: 900_000,
      pickup_window: {
        start_date: "2026-09-03",
        end_date: "2026-09-03",
      },
      version: 1,
    },
    cargo_label: "Synthetic textiles",
    created_at: timestamp(),
    operation_id: OPERATION_ID,
    operation_version: 1,
    route: { origin: "Synthetic origin", destination: "Synthetic destination" },
    sessions: hasSessions
      ? [
          {
            call_id: "20000000-0000-4000-8000-000000000023",
            carrier: {
              carrier_id: "20000000-0000-4000-8000-000000000024",
              deterministic_rank: 2,
              display_name: "Synthetic Carrier Two",
              eligible: true,
            },
            channel: "BROWSER_TEXT",
            direction: "OUTBOUND_SIMULATION",
            state: "ACTIVE",
          },
          {
            call_id: LOWEST_RANK_SESSION_ID,
            carrier: {
              carrier_id: "20000000-0000-4000-8000-000000000025",
              deterministic_rank: 1,
              display_name: "Synthetic Carrier One",
              eligible: true,
            },
            channel: "BROWSER_TEXT",
            direction: "OUTBOUND_SIMULATION",
            state: "ACTIVE",
          },
        ]
      : [],
    status: "NEGOTIATING",
    updated_at: timestamp(1),
  };
}

type CapturedRequest = {
  body: Record<string, unknown>;
  idempotencyKey: string;
};

type NextResponse =
  | { kind: "success"; status: OutboundCallResponseStatus }
  | { kind: "error"; status: number };

async function loadLiveOperation(page: Page) {
  await page.goto("/sessions");
  await page.waitForTimeout(500);
  await page
    .getByRole("textbox", { name: "Live operation ID" })
    .fill(OPERATION_ID);
  await page.getByRole("button", { name: "Load server state" }).click();
}

test("gates one authorized generated call, maps safe states, and preserves fallbacks", async ({
  page,
}) => {
  let hasSessions = false;
  let nextResponse: NextResponse = { kind: "success", status: "QUEUED" };
  const pendingResponse: { release?: () => void } = {};
  let holdResponse = false;
  const requests: CapturedRequest[] = [];
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];

  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push("error");
  });

  await page.route("**/api/volta/**", async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const apiPath = url.pathname.replace(/^\/api\/volta/, "");
    if (
      request.method() === "GET" &&
      apiPath === `/v1/operations/${OPERATION_ID}`
    ) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(operationWithSessions(hasSessions)),
      });
    }

    if (
      request.method() === "POST" &&
      apiPath === `/v1/operations/${OPERATION_ID}/outbound-calls`
    ) {
      requests.push({
        body: request.postDataJSON() as Record<string, unknown>,
        idempotencyKey: request.headers()["idempotency-key"] ?? "",
      });
      if (holdResponse) {
        await new Promise<void>((resolve) => {
          pendingResponse.release = resolve;
        });
        holdResponse = false;
      }
      if (nextResponse.kind === "error") {
        return route.fulfill({
          status: nextResponse.status,
          contentType: "application/json",
          body: JSON.stringify({
            code: "INTERNAL_ERROR",
            message: "Private provider diagnostic must stay hidden",
            request_id: "request-private-provider-detail",
          }),
        });
      }
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          call_session_id: LOWEST_RANK_SESSION_ID,
          created_at: timestamp(2),
          provider_call_id: "provider-private-identifier",
          status: nextResponse.status,
          status_updated_at: timestamp(3),
        }),
      });
    }

    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({
        code: "RESOURCE_NOT_FOUND",
        message: "Synthetic route not handled",
        request_id: "request-unhandled",
      }),
    });
  });

  await loadLiveOperation(page);
  const control = page.getByTestId("outbound-call-control");
  const startButton = control.getByRole("button", {
    name: "Start Authorized Call",
  });
  const consent = control.getByRole("checkbox", {
    name: /I confirm this participant agreed/i,
  });

  await expect(control).toContainText("No live operation session available");
  await expect(consent).toBeDisabled();
  await expect(startButton).toBeDisabled();
  expect(requests).toHaveLength(0);

  hasSessions = true;
  await page.getByRole("button", { name: "Reload" }).click();
  await expect(control).toContainText("Synthetic Carrier One");
  await expect(control).not.toContainText("Synthetic Carrier Two");
  await expect(startButton).toBeDisabled();
  expect(requests).toHaveLength(0);

  await page
    .locator("summary")
    .filter({ hasText: "More Session Tools" })
    .click();
  await expect(page.getByText("Browser voice simulator")).toBeVisible();
  const textFallback = page.getByRole("button", { name: "Use text fallback" });
  await expect(textFallback).toBeVisible();
  await expect(textFallback).toBeEnabled();

  await consent.check();
  await expect(startButton).toBeEnabled();
  holdResponse = true;
  nextResponse = { kind: "success", status: "QUEUED" };
  await startButton.click();
  await expect(control.getByText("starting", { exact: true })).toBeVisible();
  await expect(
    control.getByRole("button", { name: /Starting Call/ }),
  ).toBeDisabled();
  await control
    .getByRole("button", { name: /Starting Call/ })
    .dispatchEvent("click");
  expect(requests).toHaveLength(1);

  const firstRequest = requests[0];
  expect(firstRequest.idempotencyKey).toMatch(/^[\x20-\x7E]{8,128}$/);
  expect(firstRequest.body).toEqual({
    ai_disclosure_required: true,
    authorized_at: expect.any(String),
    authorized_by: "coordinator-demo",
    call_session_id: LOWEST_RANK_SESSION_ID,
    destination_label: "coordinator-1",
    recording_consent_required: false,
    recording_mode: "DISABLED",
  });
  expect(new Date(String(firstRequest.body.authorized_at)).toISOString()).toBe(
    firstRequest.body.authorized_at,
  );
  pendingResponse.release?.();
  await expect(control.getByText("live", { exact: true })).toBeVisible();

  for (const status of ["INITIATED", "RINGING", "IN_PROGRESS"] as const) {
    const countBefore = requests.length;
    nextResponse = { kind: "success", status };
    await startButton.click();
    await expect(control.getByText("live", { exact: true })).toBeVisible();
    expect(requests).toHaveLength(countBefore + 1);
  }

  nextResponse = { kind: "success", status: "COMPLETED" };
  await startButton.click();
  await expect(control.getByText("ended", { exact: true })).toBeVisible();

  for (const status of ["BUSY", "FAILED", "NO_ANSWER", "CANCELED"] as const) {
    const countBefore = requests.length;
    nextResponse = { kind: "success", status };
    await startButton.click();
    await expect(control.getByText("failed", { exact: true })).toBeVisible();
    expect(requests).toHaveLength(countBefore + 1);
  }

  nextResponse = { kind: "error", status: 503 };
  await startButton.click();
  await expect(control.getByRole("alert")).toContainText("Demo call failed");
  const uncertainKey = requests.at(-1)?.idempotencyKey;
  const uncertainBody = requests.at(-1)?.body;
  expect(await control.textContent()).not.toContain(
    "Private provider diagnostic must stay hidden",
  );
  expect(await control.textContent()).not.toContain(
    "provider-private-identifier",
  );

  await textFallback.click();
  await expect(page.getByText("FALLBACK", { exact: true })).toBeVisible();
  await expect(
    page.getByLabel("Send typed text into this voice session"),
  ).toBeVisible();

  nextResponse = { kind: "success", status: "QUEUED" };
  await startButton.click();
  await expect(control.getByText("live", { exact: true })).toBeVisible();
  expect(requests.at(-1)?.idempotencyKey).toBe(uncertainKey);
  expect(requests.at(-1)?.body).toEqual(uncertainBody);

  await page.waitForTimeout(2);
  await startButton.click();
  await expect(control.getByText("live", { exact: true })).toBeVisible();
  expect(requests.at(-1)?.idempotencyKey).not.toBe(uncertainKey);
  expect(requests.at(-1)?.body.authorized_at).not.toBe(
    uncertainBody?.authorized_at,
  );

  expect(pageErrors).toEqual([]);
  // Chromium emits redacted resource errors for the intentional readiness 404
  // inside advanced tools and the intentional outbound-call 503.
  expect(consoleErrors).toEqual(["error", "error"]);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  expect(await page.evaluate(() => Object.keys(sessionStorage))).toEqual([]);
});
