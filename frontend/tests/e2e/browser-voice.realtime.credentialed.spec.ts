import { existsSync } from "node:fs";
import { isAbsolute } from "node:path";

import { expect, test, type Page, type Response } from "@playwright/test";

type RealtimeTrace = {
  eventTypes: string[];
  incomingProviderCallIds: string[];
  outgoingProviderCallIds: string[];
};

declare global {
  interface Window {
    __phase13Channels: RTCDataChannel[];
    __phase13DelayMutations: boolean;
    __phase13MutationSeen: boolean;
    __phase13RealtimeTrace: RealtimeTrace;
  }
}

const credentialed = process.env.RUN_OPENAI_CREDENTIALED === "1";
const bearer = process.env.VOLTA_DEMO_BEARER_TOKEN ?? "";
const syntheticAudioPath = process.env.OPENAI_REALTIME_SYNTHETIC_WAV_PATH ?? "";
const evidence = {
  recordingReference: process.env.VOLTA_REALTIME_EVIDENCE_REFERENCE ?? "",
  audioStartMs: process.env.VOLTA_REALTIME_EVIDENCE_AUDIO_START_MS ?? "",
  itemId: process.env.VOLTA_REALTIME_EVIDENCE_ITEM_ID ?? "",
  eventId: process.env.VOLTA_REALTIME_EVIDENCE_EVENT_ID ?? "",
};

test.describe("authorized OpenAI Realtime browser trial", () => {
  test.skip(
    !credentialed,
    "set RUN_OPENAI_CREDENTIALED=1 to authorize provider usage",
  );
  test.skip(!bearer, "VOLTA_DEMO_BEARER_TOKEN is required");
  test.skip(
    !isAbsolute(syntheticAudioPath) || !existsSync(syntheticAudioPath),
    "OPENAI_REALTIME_SYNTHETIC_WAV_PATH must be an existing absolute private WAV path",
  );

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      const trace: RealtimeTrace = {
        eventTypes: [],
        incomingProviderCallIds: [],
        outgoingProviderCallIds: [],
      };
      Object.defineProperty(window, "__phase13RealtimeTrace", {
        configurable: false,
        value: trace,
      });
      window.__phase13Channels = [];
      window.__phase13DelayMutations = false;
      window.__phase13MutationSeen = false;

      const inspectEvent = (raw: unknown) => {
        if (typeof raw !== "string" || raw.length > 65_536) return;
        try {
          const event = JSON.parse(raw) as {
            type?: unknown;
            item?: { type?: unknown; call_id?: unknown };
          };
          if (typeof event.type === "string") trace.eventTypes.push(event.type);
          if (
            event.type === "response.output_item.done" &&
            event.item?.type === "function_call" &&
            typeof event.item.call_id === "string"
          ) {
            trace.incomingProviderCallIds.push(event.item.call_id);
          }
        } catch {
          // The production parser owns malformed-event handling; the trace stores no payload.
        }
      };

      const dataDescriptor = Object.getOwnPropertyDescriptor(
        MessageEvent.prototype,
        "data",
      );
      if (dataDescriptor?.get && dataDescriptor.configurable) {
        Object.defineProperty(MessageEvent.prototype, "data", {
          configurable: true,
          enumerable: dataDescriptor.enumerable,
          get() {
            const raw = Reflect.apply(dataDescriptor.get!, this, []);
            inspectEvent(raw);
            return raw;
          },
        });
      }

      const nativeSend = RTCDataChannel.prototype.send;
      Object.defineProperty(RTCDataChannel.prototype, "send", {
        configurable: true,
        value(this: RTCDataChannel, payload: unknown) {
          if (typeof payload === "string" && payload.length <= 65_536) {
            try {
              const event = JSON.parse(payload) as {
                type?: unknown;
                item?: { type?: unknown; call_id?: unknown };
              };
              if (
                event.type === "conversation.item.create" &&
                event.item?.type === "function_call_output" &&
                typeof event.item.call_id === "string"
              ) {
                trace.outgoingProviderCallIds.push(event.item.call_id);
              }
            } catch {
              // Do not retain raw provider or application data in the test trace.
            }
          }
          return Reflect.apply(nativeSend, this, [payload]);
        },
      });

      const NativePeerConnection = window.RTCPeerConnection;
      window.RTCPeerConnection = class extends NativePeerConnection {
        createDataChannel(label: string, options?: RTCDataChannelInit) {
          const channel = super.createDataChannel(label, options);
          window.__phase13Channels.push(channel);
          return channel;
        }
      };

      const nativeFetch = window.fetch.bind(window);
      window.fetch = async (...args) => {
        const target =
          args[0] instanceof Request ? args[0].url : String(args[0]);
        const responsePromise = nativeFetch(...args);
        if (
          window.__phase13DelayMutations &&
          /\/v1\/calls\/[^/]+\/(quotes|commitments)$/.test(target)
        ) {
          window.__phase13MutationSeen = true;
          const response = await responsePromise;
          await new Promise((resolve) => window.setTimeout(resolve, 4_000));
          return response;
        }
        return responsePromise;
      };
    });
  });

  test("record_quote and create_candidate_commitment roundtrip with original provider call IDs", async ({
    page,
  }) => {
    test.skip(
      Object.values(evidence).some((value) => !value),
      "the private evidence reference, offset, item ID, and event ID are required",
    );
    const operationId = await createSyntheticOperation(page);
    await openComparisonAndConnectVoice(page, operationId);

    const quoteResponses: Response[] = [];
    page.on("response", (response) => {
      if (/\/v1\/calls\/[^/]+\/quotes$/.test(response.url())) {
        quoteResponses.push(response);
      }
    });
    await sendRealtimeText(
      page,
      "Call record_quote exactly once for the first session in the authoritative context. Use amount_minor 850000, currency MXN, pickup start and end 2026-09-03, conditions 40ft dry container and Standard handling, and valid_until 2026-09-03T18:00:00Z. Use only the exact supplied identifiers and versions.",
    );
    await expect.poll(() => quoteResponses.length, { timeout: 60_000 }).toBe(1);
    expect(quoteResponses[0].status()).toBe(201);

    await expect(
      page.getByText("Create candidate commitment", { exact: true }),
    ).toBeVisible({ timeout: 20_000 });
    await page
      .getByLabel("Private recording reference")
      .fill(evidence.recordingReference);
    await page.getByLabel("Audio start (ms)").fill(evidence.audioStartMs);
    await page.getByLabel("Item ID").fill(evidence.itemId);
    await page.getByLabel("Event ID").fill(evidence.eventId);
    const evidenceResponse = page.waitForResponse(
      (response) =>
        /\/v1\/calls\/[^/]+\/evidence$/.test(response.url()) &&
        response.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Attach supplied evidence" })
      .click();
    expect((await evidenceResponse).status()).toBe(201);
    await expect(
      page.getByText("Agreement evidence attached", { exact: true }),
    ).toBeVisible();

    const commitmentResponses: Response[] = [];
    page.on("response", (response) => {
      if (/\/v1\/calls\/[^/]+\/commitments$/.test(response.url())) {
        commitmentResponses.push(response);
      }
    });
    await sendRealtimeText(
      page,
      "Call create_candidate_commitment exactly once for the selected quote and attached evidence in the authoritative context. Use only the exact supplied identifiers and versions.",
    );
    await expect
      .poll(() => commitmentResponses.length, { timeout: 60_000 })
      .toBe(1);
    expect(commitmentResponses[0].status()).toBe(201);
    await expect(
      page.getByRole("heading", { name: "Active evidence-backed winner" }),
    ).toBeVisible({ timeout: 20_000 });

    const trace = await page.evaluate(() => window.__phase13RealtimeTrace);
    expect(trace.outgoingProviderCallIds).toHaveLength(2);
    expect(new Set(trace.outgoingProviderCallIds).size).toBe(2);
    for (const callId of trace.outgoingProviderCallIds) {
      expect(trace.incomingProviderCallIds).toContain(callId);
    }
  });

  test("an uncertain quote settles once, reconciles, and reconnects with a fresh secret", async ({
    page,
  }) => {
    const operationId = await createSyntheticOperation(page);
    const secretResponses: Response[] = [];
    const quoteResponses: Response[] = [];
    page.on("response", (response) => {
      if (response.url().endsWith("/v1/realtime/client-secrets")) {
        secretResponses.push(response);
      }
      if (/\/v1\/calls\/[^/]+\/quotes$/.test(response.url())) {
        quoteResponses.push(response);
      }
    });
    await openComparisonAndConnectVoice(page, operationId);
    await page.evaluate(() => {
      window.__phase13DelayMutations = true;
    });
    await sendRealtimeText(
      page,
      "Call record_quote exactly once for the first session in the authoritative context. Use amount_minor 860000, currency MXN, pickup start and end 2026-09-03, conditions 40ft dry container and Standard handling, and valid_until 2026-09-03T19:00:00Z. Use only the exact supplied identifiers and versions.",
    );
    await expect.poll(() => quoteResponses.length, { timeout: 60_000 }).toBe(1);
    expect(quoteResponses[0].status()).toBe(201);
    await expect
      .poll(() => page.evaluate(() => window.__phase13MutationSeen))
      .toBe(true);
    await page.evaluate(() => {
      window.__phase13Channels.at(-1)?.dispatchEvent(new Event("error"));
    });
    await expect(page.getByText("RECONCILING", { exact: true })).toBeVisible();
    await expect(page.getByText("DISCONNECTED", { exact: true })).toBeVisible({
      timeout: 15_000,
    });
    expect(quoteResponses).toHaveLength(1);

    await page.getByRole("button", { name: "Reconnect" }).click();
    await expect
      .poll(() => secretResponses.length, { timeout: 30_000 })
      .toBeGreaterThanOrEqual(2);
    await expect(
      page.getByLabel("Send typed text into this voice session"),
    ).toBeEnabled({
      timeout: 30_000,
    });
    expect(quoteResponses).toHaveLength(1);
    await page.getByRole("button", { name: "Stop" }).click();
    await expect(page.getByText("DISCONNECTED", { exact: true })).toBeVisible();
  });
});

async function connectDemoAuth(page: Page) {
  await page.getByLabel("Demo bearer token").fill(bearer);
  await page.getByRole("button", { name: "Connect live API" }).click();
  await expect(
    page.getByText("CONNECTED", { exact: true }).first(),
  ).toBeVisible();
}

async function createSyntheticOperation(page: Page) {
  await page.goto("/intake");
  await connectDemoAuth(page);
  await page.getByRole("button", { name: "Use canonical prompt" }).click();
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
  const operation = (await approved.json()) as { operation_id?: unknown };
  expect(operation.operation_id).toEqual(expect.any(String));
  const operationId = String(operation.operation_id);

  await page.getByRole("link", { name: "Open carrier sessions" }).click();
  const selectionResponse = page.waitForResponse(
    (response) =>
      /\/v1\/operations\/[^/]+\/negotiations$/.test(response.url()) &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Start server selection" }).click();
  expect((await selectionResponse).status()).toBe(201);
  return operationId;
}

async function openComparisonAndConnectVoice(page: Page, operationId: string) {
  await page.getByRole("link", { name: "Comparison" }).click();
  await expect(
    page.getByRole("textbox", { name: "Live operation ID" }),
  ).toHaveValue(operationId);
  const secretResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/v1/realtime/client-secrets") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Start voice" }).click();
  expect((await secretResponse).status()).toBe(201);
  await expect(
    page.getByLabel("Send typed text into this voice session"),
  ).toBeEnabled({
    timeout: 30_000,
  });
}

async function sendRealtimeText(page: Page, prompt: string) {
  const input = page.getByLabel("Send typed text into this voice session");
  await input.fill(prompt);
  await page.getByRole("button", { name: "Send" }).click();
}
