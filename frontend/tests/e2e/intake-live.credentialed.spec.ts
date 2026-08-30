import { expect, test } from "@playwright/test";

const bearer = process.env.VOLTA_DEMO_BEARER_TOKEN;

test("an edited drayage prompt creates an accurately extracted draft", async ({
  page,
}) => {
  test.skip(!bearer, "VOLTA_DEMO_BEARER_TOKEN is required");

  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/intake");
  await expect(page).toHaveTitle(/Volta/i);
  await expect(
    page.getByText("Submit a drayage request", { exact: true }),
  ).toBeVisible();

  await page.getByLabel("Demo bearer token").fill(bearer!);
  await page.getByRole("button", { name: "Connect live API" }).click();
  await expect(page.getByText("CONNECTED", { exact: true })).toBeVisible();

  await page
    .getByLabel("Source prompt")
    .fill(
      "Find ground transport for Thursday from the port of Santos to our " +
        "warehouse in Rio de Janeiro for at most MXN 2,000. One 40-foot dry " +
        "container, standard handling conditions.",
    );
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith("/v1/operation-drafts") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Submit draft" }).click();

  const response = await responsePromise;
  expect(response.status()).toBe(201);
  const draft = (await response.json()) as {
    approval_eligible: boolean;
    proposed_route: { origin: string; destination: string };
    proposed_mandate: { maximum_amount_minor: number };
  };
  expect(draft.approval_eligible).toBe(true);
  expect(draft.proposed_route.origin.toLowerCase()).toContain("santos");
  expect(draft.proposed_route.destination.toLowerCase()).toContain(
    "rio de janeiro",
  );
  expect(draft.proposed_mandate.maximum_amount_minor).toBe(200000);
  await expect(
    page.getByText("APPROVAL ELIGIBLE", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Draft could not be created")).toHaveCount(0);
  await expect(page.getByText(/santos.*→.*rio de janeiro/i)).toBeVisible();
  await expect(page.getByText("MX$2,000.00", { exact: true })).toBeVisible();
  await expect(page.getByText("Validation issues")).toHaveCount(0);
  expect(consoleErrors).toEqual([]);

  const screenshotPath = process.env.INTAKE_E2E_SCREENSHOT_PATH;
  if (screenshotPath) {
    await page.screenshot({ path: screenshotPath, fullPage: true });
  }
});
