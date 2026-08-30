import { chmod, mkdir, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";

import { expect, test, type Page } from "@playwright/test";

import type {
  AuditTimelineResponse,
  CallBriefResponse,
  CommitmentEvidenceResponse,
  CommitmentResponse,
  CreateCallBriefRequest,
  CreateSimulatedRecapRequest,
  NegotiationResponse,
  OperationResponse,
  QuoteResponse,
  WrittenRecapResponse,
} from "../../src/lib/api/generated/models";

const bearer = process.env.VOLTA_DEMO_BEARER_TOKEN ?? "";
const trialDatabaseURL = process.env.VOLTA_TRIAL_DATABASE_URL ?? "";
const apiURL = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8100";
const evidenceRoot = join(tmpdir(), "yuno-volta-text-evidence");
const runId = crypto.randomUUID();
const recordingReference = `phase17/${runId}.wav`;
const recordingPath = join(evidenceRoot, recordingReference);

function isSafeTrialDatabase(value: string) {
  try {
    const parsed = new URL(value);
    return (
      parsed.protocol === "postgresql+asyncpg:" &&
      ["localhost", "127.0.0.1", "[::1]"].includes(parsed.hostname) &&
      parsed.pathname.startsWith("/volta_trial_")
    );
  } catch {
    return false;
  }
}

const prerequisitesAvailable =
  bearer.length > 0 && isSafeTrialDatabase(trialDatabaseURL);

type SafeNetworkEntry = {
  method: string;
  path: string;
  status: number;
};

type Diagnostics = {
  consoleErrors: string[];
  pageErrors: string[];
  network: SafeNetworkEntry[];
};

type BrowserApiResult<T> = {
  body: T;
  headers: Record<string, string | null>;
  status: number;
};

function safePath(rawURL: string) {
  const url = new URL(rawURL);
  return url.pathname.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/gi, ":id");
}

function collectSafeDiagnostics(page: Page): Diagnostics {
  const diagnostics: Diagnostics = {
    consoleErrors: [],
    pageErrors: [],
    network: [],
  };
  page.on("console", (message) => {
    if (message.type() === "error") diagnostics.consoleErrors.push("error");
  });
  page.on("pageerror", (error) => diagnostics.pageErrors.push(error.name));
  page.on("response", (response) => {
    const url = new URL(response.url());
    if (url.origin === new URL(apiURL).origin) {
      diagnostics.network.push({
        method: response.request().method(),
        path: safePath(response.url()),
        status: response.status(),
      });
    }
  });
  return diagnostics;
}

function waveBuffer(durationSeconds = 2) {
  const sampleRate = 8_000;
  const samples = sampleRate * durationSeconds;
  const dataSize = samples * 2;
  const buffer = Buffer.alloc(44 + dataSize);
  buffer.write("RIFF", 0);
  buffer.writeUInt32LE(36 + dataSize, 4);
  buffer.write("WAVEfmt ", 8);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write("data", 36);
  buffer.writeUInt32LE(dataSize, 40);
  return buffer;
}

async function materializePrivateEvidence() {
  const fixtureDirectory = join(evidenceRoot, "phase17");
  await mkdir(fixtureDirectory, { recursive: true, mode: 0o700 });
  await writeFile(recordingPath, waveBuffer());
  await chmod(recordingPath, 0o600);
}

async function connectDemoAuth(page: Page) {
  if ((await page.getByLabel("Demo bearer token").count()) === 0) {
    await expect(
      page.getByText("CONNECTED", { exact: true }).first(),
    ).toBeVisible();
    return;
  }
  await page.getByLabel("Demo bearer token").fill(bearer);
  await page.getByRole("button", { name: "Connect live API" }).click();
  await expect(
    page.getByText("CONNECTED", { exact: true }).first(),
  ).toBeVisible();
  await expect(page.getByLabel("Demo bearer token")).toHaveCount(0);
}

async function createOperation(page: Page, prompt: string) {
  await page.goto("/intake");
  await connectDemoAuth(page);
  await page.getByLabel("Source prompt").fill(prompt);
  const draftResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/v1/operation-drafts") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Submit draft" }).click();
  expect((await draftResponse).status()).toBe(201);
  await page.getByRole("link", { name: "Continue to mandate review" }).click();

  const approvalResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/v1/operations") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Approve mandate" }).click();
  const approved = await approvalResponse;
  expect(approved.status()).toBe(201);
  return (await approved.json()) as OperationResponse;
}

async function startNegotiation(page: Page) {
  await page.getByRole("link", { name: "Open carrier sessions" }).click();
  const responsePromise = page.waitForResponse(
    (response) =>
      /\/v1\/operations\/[^/]+\/negotiations$/.test(response.url()) &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Start server selection" }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  return (await response.json()) as NegotiationResponse;
}

async function recordQuote(
  page: Page,
  callId: string,
  amount: string,
  useRejectedConditions = false,
) {
  await page.locator("#quote-call-id").selectOption(callId);
  await page
    .getByRole("button", {
      name: useRejectedConditions
        ? "Use above-cap sample"
        : "Use displayed mandate cap",
    })
    .click();
  await page.getByLabel("Amount (MXN)").fill(amount);
  await page.getByLabel("Valid until (ISO)").fill("2030-09-03T18:00:00Z");
  const responsePromise = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/v1/calls/${callId}/quotes`) &&
      response.request().method() === "POST",
  );
  const authoritativeReload = page.waitForResponse(
    (response) =>
      /\/v1\/operations\/[^/]+$/.test(response.url()) &&
      response.request().method() === "GET" &&
      response.status() === 200,
  );
  await page.getByRole("button", { name: "Record through live API" }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  await authoritativeReload;
  return (await response.json()) as QuoteResponse;
}

async function browserApi<T>(
  page: Page,
  method: "GET" | "POST",
  path: string,
  body?: unknown,
): Promise<BrowserApiResult<T>> {
  return page.evaluate(
    async ({ apiURL, bearer, body, method, path }) => {
      const headers = new Headers({ Authorization: `Bearer ${bearer}` });
      if (body !== undefined) {
        headers.set("Content-Type", "application/json");
        headers.set("Idempotency-Key", crypto.randomUUID());
      }
      const response = await fetch(`${apiURL}${path}`, {
        body: body === undefined ? undefined : JSON.stringify(body),
        headers,
        method,
      });
      const result = (await response.json()) as T;
      return {
        body: result,
        headers: {
          cacheControl: response.headers.get("cache-control"),
          contentType: response.headers.get("content-type"),
          pragma: response.headers.get("pragma"),
          requestId: response.headers.get("x-request-id"),
        },
        status: response.status,
      };
    },
    { apiURL, bearer, body, method, path },
  );
}

async function getOperation(page: Page, operationId: string) {
  const response = await browserApi<OperationResponse>(
    page,
    "GET",
    `/v1/operations/${operationId}`,
  );
  expect(response.status).toBe(200);
  return response.body;
}

async function attachEvidenceAndCommit(page: Page) {
  await page.getByLabel("Private recording reference").fill(recordingReference);
  await page.getByLabel("Audio start (ms)").fill("250");
  await page.getByLabel("Item ID").fill(`phase17-item-${runId}`);
  await page.getByLabel("Event ID").fill(`phase17-event-${runId}`);
  const evidenceResponse = page.waitForResponse(
    (response) =>
      /\/v1\/calls\/[^/]+\/evidence$/.test(response.url()) &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Attach supplied evidence" }).click();
  const evidence = await evidenceResponse;
  expect(evidence.status()).toBe(201);
  const evidenceBody = (await evidence.json()) as CommitmentEvidenceResponse;

  const commitmentResponse = page.waitForResponse(
    (response) =>
      /\/v1\/calls\/[^/]+\/commitments$/.test(response.url()) &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Create evidence-backed candidate" })
    .click();
  const commitment = await commitmentResponse;
  expect(commitment.status()).toBe(201);
  return {
    commitment: (await commitment.json()) as CommitmentResponse,
    evidence: evidenceBody,
  };
}

function assertOneActive(audit: AuditTimelineResponse, activeId: string) {
  const active = audit.commitment_history.filter(
    (item) => item.disposition === "ACTIVE",
  );
  expect(active).toHaveLength(1);
  expect(active[0].commitment_id).toBe(activeId);
}

test.describe("complete P0 browser trial", () => {
  test.skip(
    !prerequisitesAvailable,
    "chromium-trial requires VOLTA_DEMO_BEARER_TOKEN and a loopback VOLTA_TRIAL_DATABASE_URL whose database starts with volta_trial_",
  );

  test.beforeEach(async ({ page }, testInfo) => {
    if (!testInfo.title.includes("runs canonical")) return;
    void page;
    await materializePrivateEvidence();
  });

  test.afterEach(async ({}, testInfo) => {
    if (!testInfo.title.includes("runs canonical")) return;
    await rm(recordingPath, { force: true });
  });

  test("runs canonical negotiation, evidence, recovery, escalation and audit through real services", async ({
    page,
  }) => {
    const diagnostics = collectSafeDiagnostics(page);
    const operation = await createOperation(
      page,
      "Find ground transport for Thursday from the port of Manzanillo to our warehouse in Guadalajara for at most MXN 9,000. One 40-foot dry container, standard handling conditions.",
    );
    expect(operation.route.origin).toContain("Manzanillo");
    expect(operation.route.destination).toContain("Guadalajara");
    expect(operation.active_mandate.maximum_amount_minor).toBe(900_000);

    const negotiation = await startNegotiation(page);
    expect(negotiation.sessions).toHaveLength(3);
    const [first, second, third] = negotiation.sessions ?? [];

    await page.getByRole("link", { name: "Comparison" }).click();
    const firstQuote = await recordQuote(page, first.call_id, "8500.00");
    expect(firstQuote.eligibility).toBe("ELIGIBLE");
    const rejectedQuote = await recordQuote(
      page,
      second.call_id,
      "9500.00",
      true,
    );
    expect(rejectedQuote.eligibility).toBe("REJECTED");
    expect(rejectedQuote.rejection_reasons?.length).toBeGreaterThan(0);
    const thirdQuote = await recordQuote(page, third.call_id, "8750.00");
    expect(thirdQuote.eligibility).toBe("ELIGIBLE");

    const comparison = await browserApi<AuditTimelineResponse>(
      page,
      "GET",
      `/v1/operations/${operation.operation_id}/audit?limit=100`,
    );
    expect(comparison.status).toBe(200);
    const eligibleComparison = comparison.body.quote_comparison.filter(
      (item) => item.eligibility === "ELIGIBLE",
    );
    expect(eligibleComparison).toHaveLength(2);
    expect(
      eligibleComparison.some(
        (item) => item.quote_id === rejectedQuote.quote_id,
      ),
    ).toBe(false);
    expect(
      comparison.body.quote_comparison.filter((item) => item.selected),
    ).toHaveLength(1);

    const created = await attachEvidenceAndCommit(page);
    expect(created.commitment.lifecycle).toBe("CANDIDATE");
    expect(created.commitment.disposition).toBe("ACTIVE");
    expect(created.commitment.evidence?.audio_start_ms).toBe(250);
    expect(JSON.stringify(created.commitment)).not.toContain(
      recordingReference,
    );

    let current = await getOperation(page, operation.operation_id);
    const recapRequest = {
      commitment_id: created.commitment.commitment_id,
      expected_operation_version: current.operation_version,
      rendered_content:
        "SIMULATED recap: synthetic carrier accepted MXN 8,500 for the approved Thursday window.",
    } satisfies CreateSimulatedRecapRequest;
    const recap = await browserApi<WrittenRecapResponse>(
      page,
      "POST",
      `/v1/calls/${created.commitment.call_id}/recaps`,
      recapRequest,
    );
    expect(recap.status).toBe(201);
    expect(recap.body.channel).toBe("SIMULATED");
    current = await getOperation(page, operation.operation_id);
    const briefRequest = {
      changes: ["No approved terms changed"],
      expected_operation_version: current.operation_version,
      facts: ["Thursday pickup confirmed", "MXN 8,500 accepted"],
      objections: ["Above-cap quote rejected"],
      unresolved_items: [],
    } satisfies CreateCallBriefRequest;
    const brief = await browserApi<CallBriefResponse>(
      page,
      "POST",
      `/v1/calls/${created.commitment.call_id}/briefs`,
      briefRequest,
    );
    expect(brief.status).toBe(201);

    await page.getByRole("link", { name: "Evidence" }).click();
    await connectDemoAuth(page);
    const audioResponsePromise = page.waitForResponse(
      (response) =>
        response
          .url()
          .endsWith(`/v1/evidence/${created.evidence.evidence_id}/audio`) &&
        response.request().method() === "GET",
    );
    await page.getByRole("button", { name: "Load evidence audio" }).click();
    const audioResponse = await audioResponsePromise;
    expect(audioResponse.status()).toBe(200);
    expect(audioResponse.headers()["content-type"]).toContain("audio/wav");
    expect(audioResponse.headers()["cache-control"]).toBe("private, no-store");
    expect(audioResponse.headers()["pragma"]).toBe("no-cache");
    expect(audioResponse.headers()["x-content-type-options"]).toBe("nosniff");
    expect(audioResponse.url()).not.toContain(recordingReference);
    await expect
      .poll(() =>
        page
          .locator("audio")
          .first()
          .evaluate((node) => (node as HTMLAudioElement).currentTime),
      )
      .toBeGreaterThanOrEqual(0.24);
    await expect(page.getByText(recap.body.rendered_content)).toBeVisible();
    await expect(page.getByText("Thursday pickup confirmed")).toBeVisible();

    const failedAudioResponse = page.waitForResponse(
      (response) =>
        response
          .url()
          .endsWith(`/v1/evidence/${created.evidence.evidence_id}/audio`) &&
        response.request().method() === "GET" &&
        response.status() === 404,
    );
    await rm(recordingPath, { force: true });
    await page.getByRole("button", { name: "Reload audio" }).click();
    await failedAudioResponse;
    const audioUnavailableAlert = page
      .getByRole("alert")
      .filter({ hasText: "Audio unavailable" });
    await expect(audioUnavailableAlert).toContainText("Audio unavailable");
    await expect(audioUnavailableAlert).toContainText(
      "Evidence audio is unavailable. The recap and brief remain available.",
    );
    await expect(
      page.getByText("LIFECYCLE · CANDIDATE", { exact: true }).first(),
    ).toBeVisible();
    await expect(page.getByText(recap.body.rendered_content)).toBeVisible();
    await expect(page.getByText("Thursday pickup confirmed")).toBeVisible();
    await page.getByRole("link", { name: "Audit" }).click();
    await expect(
      page.getByRole("heading", { name: "Audit trail" }),
    ).toBeVisible();
    await expect(page.getByText(recap.body.rendered_content)).toBeVisible();
    await expect(
      page.getByText("Call brief", { exact: true }).first(),
    ).toBeVisible();

    await page.getByRole("link", { name: "Recovery" }).click();
    await connectDemoAuth(page);
    const safeResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/inbound-simulations") &&
        response.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Run mandate-safe simulation" })
      .click();
    expect((await safeResponsePromise).status()).toBe(201);
    await expect(page.getByText("MANDATE_SAFE", { exact: true })).toBeVisible();
    await expect(
      page.getByText("A mandate-safe replacement commitment was activated."),
    ).toBeVisible();
    current = await getOperation(page, operation.operation_id);
    expect(current.active_commitment?.commitment_id).not.toBe(
      created.commitment.commitment_id,
    );
    expect(
      current.notifications?.some((notification) => !notification.acknowledged),
    ).toBe(true);
    const activeAfterSafe = current.active_commitment?.commitment_id ?? "";

    await page
      .getByRole("button", { name: "Acknowledge as demo coordinator" })
      .click();
    await expect(page.getByText("ACKNOWLEDGED", { exact: true })).toBeVisible();
    const badResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/inbound-simulations") &&
        response.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Run out-of-mandate simulation" })
      .click();
    expect((await badResponsePromise).status()).toBe(201);
    await expect(
      page.getByText("OUT_OF_MANDATE", { exact: true }).first(),
    ).toBeVisible();
    current = await getOperation(page, operation.operation_id);
    expect(current.active_commitment?.commitment_id).toBe(activeAfterSafe);
    expect(current.open_escalation?.resolution_state).toBe("OPEN");

    await page.getByRole("link", { name: "Escalation" }).click();
    await page
      .getByRole("button", { name: "Approve replacement mandate" })
      .click();
    await expect(
      page.getByText("RESOLVED", { exact: true }).first(),
    ).toBeVisible();
    current = await getOperation(page, operation.operation_id);
    expect(current.active_mandate.version).toBe(2);
    expect(current.active_commitment?.commitment_id).toBe(activeAfterSafe);

    const audit = await browserApi<AuditTimelineResponse>(
      page,
      "GET",
      `/v1/operations/${operation.operation_id}/audit?limit=100`,
    );
    expect(audit.status).toBe(200);
    expect(audit.body.recaps).toHaveLength(1);
    expect(audit.body.briefs).toHaveLength(1);
    expect(audit.body.recoveries).toHaveLength(2);
    expect(audit.body.notifications).toHaveLength(1);
    expect(audit.body.escalations).toHaveLength(1);
    assertOneActive(audit.body, activeAfterSafe);
    expect(audit.body.commitment_history).toContainEqual(
      expect.objectContaining({
        commitment_id: created.commitment.commitment_id,
        disposition: "SUPERSEDED",
      }),
    );

    const recoveryEvidence = current.active_commitment?.evidence;
    expect(recoveryEvidence).toBeTruthy();
    if (!recoveryEvidence) throw new Error("Recovery evidence is required");
    expect(recoveryEvidence.audio_start_ms).toBe(1_840);
    await page.getByRole("link", { name: "Evidence" }).click();
    await connectDemoAuth(page);
    const recoveryEvidenceCard = page
      .locator('[data-slot="card"]')
      .filter({ hasText: recoveryEvidence.evidence_id });
    await expect(recoveryEvidenceCard).toHaveCount(1);
    const recoveryAudioResponsePromise = page.waitForResponse(
      (response) =>
        response
          .url()
          .endsWith(`/v1/evidence/${recoveryEvidence.evidence_id}/audio`) &&
        response.request().method() === "GET",
    );
    await recoveryEvidenceCard
      .getByRole("button", { name: "Load evidence audio" })
      .click();
    const recoveryAudioResponse = await recoveryAudioResponsePromise;
    expect(recoveryAudioResponse.status()).toBe(200);
    expect(recoveryAudioResponse.headers()["content-type"]).toContain(
      "audio/wav",
    );
    expect(recoveryAudioResponse.headers()["cache-control"]).toBe(
      "private, no-store",
    );
    expect(recoveryAudioResponse.headers()["pragma"]).toBe("no-cache");
    expect(recoveryAudioResponse.headers()["x-content-type-options"]).toBe(
      "nosniff",
    );
    await expect
      .poll(() =>
        recoveryEvidenceCard
          .locator("audio")
          .evaluate((node) => (node as HTMLAudioElement).currentTime),
      )
      .toBeGreaterThanOrEqual(1.83);

    const browserState = await page.evaluate(() => ({
      bodyText: document.body.textContent ?? "",
      cookies: document.cookie,
      indexedDatabaseCount:
        typeof indexedDB.databases === "function" ? undefined : 0,
      localStorageKeys: Object.keys(localStorage),
      sessionStorageKeys: Object.keys(sessionStorage),
    }));
    expect(browserState.bodyText).not.toContain(bearer);
    expect(browserState.bodyText).not.toContain(recordingReference);
    expect(browserState.cookies).not.toContain(bearer);
    expect(browserState.localStorageKeys).toEqual([]);
    expect(browserState.sessionStorageKeys).toEqual([]);
    // Chromium emits one redacted console error for the intentionally missing
    // private audio resource exercised above.
    expect(diagnostics.consoleErrors).toEqual(["error"]);
    expect(diagnostics.pageErrors).toEqual([]);
    expect(diagnostics.network.filter((entry) => entry.status >= 400)).toEqual([
      {
        method: "GET",
        path: "/v1/evidence/:id/audio",
        status: 404,
      },
    ]);
  });

  test("keeps accessible text controls usable when microphone permission is denied", async ({
    page,
  }) => {
    await page.addInitScript(() => {
      Object.defineProperty(navigator.mediaDevices, "getUserMedia", {
        configurable: true,
        value: async () => {
          throw new DOMException(
            "Synthetic permission denial",
            "NotAllowedError",
          );
        },
      });
    });
    const diagnostics = collectSafeDiagnostics(page);
    await createOperation(
      page,
      "Find ground transport for Thursday from the port of Manzanillo to our warehouse in Guadalajara for at most MXN 9,000. One 40-foot dry container, standard handling conditions.",
    );
    await startNegotiation(page);
    await page.getByRole("link", { name: "Comparison" }).click();

    let clientSecretRequests = 0;
    page.on("request", (request) => {
      if (request.url().endsWith("/v1/realtime/client-secrets")) {
        clientSecretRequests += 1;
      }
    });
    await page.getByRole("button", { name: "Start voice" }).click();
    await expect(
      page
        .getByRole("alert")
        .filter({ hasText: "Microphone permission denied" }),
    ).toContainText("Microphone permission denied");
    await expect(
      page.getByRole("status").filter({
        hasText: "Voice connection error. Microphone permission denied.",
      }),
    ).toContainText("Voice connection error. Microphone permission denied.");
    expect(clientSecretRequests).toBe(0);

    await page.getByRole("button", { name: "Use text fallback" }).click();
    await expect(page.getByText("FALLBACK", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Record through live API" }),
    ).toBeEnabled();
    await page
      .getByRole("button", { name: "Use displayed mandate cap" })
      .click();
    await expect(page.getByLabel("Amount (MXN)")).toHaveValue("9000.00");
    expect(diagnostics.consoleErrors).toEqual([]);
    expect(diagnostics.pageErrors).toEqual([]);
    expect(diagnostics.network.filter((entry) => entry.status >= 400)).toEqual(
      [],
    );
  });

  test("creates a pre-contact escalation and no sessions for Veracruz to Puebla", async ({
    page,
  }) => {
    const diagnostics = collectSafeDiagnostics(page);
    const operation = await createOperation(
      page,
      "Find transport Thursday from Veracruz to Puebla for at most MXN 9,000, one 40-foot dry container, standard handling.",
    );
    const negotiation = await startNegotiation(page);
    expect(negotiation.sessions ?? []).toEqual([]);
    expect(negotiation.pre_contact_escalation?.resolution_state).toBe("OPEN");
    const current = await getOperation(page, operation.operation_id);
    expect(current.sessions ?? []).toEqual([]);
    expect(current.quotes ?? []).toEqual([]);
    expect(current.active_commitment).toBeNull();
    expect(current.open_escalation?.resolution_state).toBe("OPEN");
    expect(diagnostics.consoleErrors).toEqual([]);
    expect(diagnostics.pageErrors).toEqual([]);
    expect(diagnostics.network.filter((entry) => entry.status >= 400)).toEqual(
      [],
    );
  });
});
