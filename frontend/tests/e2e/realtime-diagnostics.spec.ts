import { expect, test, type Page, type Request } from "@playwright/test";

const EXPECTED_RESULTS = {
  malformed: "PASS · malformed JSON rejected · 0 calls",
  unknown: "PASS · unknown tool rejected · 0 calls",
  duplicate: "PASS · duplicate reused one pending safe result · 1 call",
  failed: "PASS · failure reduced to TOOL_UNAVAILABLE · 1 call",
  "fresh-context":
    "PASS · output preceded refreshed v8 context · next quote accepted",
  "exchange-guards": "PASS · expired secret rejected · stalled SDP timed out",
  "pending-disconnect":
    "PASS · new call blocked until authoritative refresh · no replay",
  reconnected: "PASS · new call accepted only after reconciliation · no replay",
} as const;

async function openFallbackWithKeyboard(page: Page) {
  await page.goto("/sessions");
  await expect(page).toHaveTitle("Volta | Control tower");
  await expect(
    page.getByRole("heading", { name: "Carrier sessions" }),
  ).toBeVisible();

  const fallback = page.getByRole("button", {
    name: "Open simulated fallback",
  });
  for (let index = 0; index < 30; index += 1) {
    if (
      await fallback.evaluate((element) => element === document.activeElement)
    )
      break;
    await page.keyboard.press("Tab");
  }
  await expect(fallback).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Voice boundary diagnostics", { exact: false }),
  ).toBeVisible();
}

function isUnexpectedRequest(request: Request) {
  const url = request.url();
  return (
    request.method() !== "GET" ||
    /\/v1\/|api\.openai\.com|realtime\/calls|websocket/i.test(url)
  );
}

async function readClientStorage(page: Page) {
  return page.evaluate(async () => ({
    cookies: document.cookie,
    indexedDatabases:
      typeof indexedDB.databases === "function"
        ? (await indexedDB.databases()).map((database) => database.name ?? "")
        : [],
    localStorage: Object.keys(localStorage),
    sessionStorage: Object.keys(sessionStorage),
  }));
}

test("credential-free voice diagnostics are keyboard-operable and make no mutation", async ({
  page,
}) => {
  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const unexpectedRequests: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("request", (request) => {
    if (isUnexpectedRequest(request)) {
      unexpectedRequests.push(`${request.method()} ${request.url()}`);
    }
  });

  await openFallbackWithKeyboard(page);
  const storageBeforeDiagnostics = await readClientStorage(page);
  await expect(
    page.getByText("LOCAL · NO NETWORK", { exact: true }),
  ).toBeVisible();

  const scenario = page.locator('select[name="voice-diagnostic-scenario"]');
  const result = page.locator('p[role="status"]').last();
  for (const [value, expected] of Object.entries(EXPECTED_RESULTS)) {
    await scenario.selectOption(value);
    await page.getByRole("button", { name: "Run local check" }).click();
    await expect(result).toHaveText(expected);
  }

  expect(await readClientStorage(page)).toEqual(storageBeforeDiagnostics);
  expect(unexpectedRequests).toEqual([]);
  expect(pageErrors).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test("diagnostic fallback remains within a mobile viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/sessions");
  await page.getByRole("button", { name: "Open simulated fallback" }).click();
  await expect(
    page.getByText("Voice boundary diagnostics", { exact: false }),
  ).toBeVisible();

  const viewport = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(viewport.scrollWidth).toBeLessThanOrEqual(viewport.clientWidth);
  await expect(
    page.locator('select[name="voice-diagnostic-scenario"]'),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run local check" }),
  ).toBeVisible();
});
