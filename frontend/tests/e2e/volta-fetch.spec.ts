import { expect, test } from "@playwright/test";

import type { ApiErrorResponse } from "../../src/lib/api/generated/models";
import {
  ApiHttpError,
  type ApiHttpResponse,
  voltaFetch,
} from "../../src/lib/api/volta-fetch";

const originalFetch = globalThis.fetch;

test.afterEach(() => {
  globalThis.fetch = originalFetch;
});

test("preserves proxied audio bytes as a Blob without browser authorization", async () => {
  const wav = new Uint8Array([
    0x52, 0x49, 0x46, 0x46, 0x04, 0x00, 0x00, 0x00, 0x57, 0x41, 0x56, 0x45,
  ]);
  let requestHeaders = new Headers();
  globalThis.fetch = async (_input, init) => {
    requestHeaders = new Headers(init?.headers);
    return new Response(wav, {
      status: 200,
      headers: {
        "Content-Type": "audio/wav",
        "X-Request-ID": "request-audio-1",
      },
    });
  };

  const response = await voltaFetch<ApiHttpResponse<Blob>>(
    "http://localhost.test/v1/evidence/id/audio",
    { headers: { Authorization: "discarded" } },
  );

  expect(response.data).toBeInstanceOf(Blob);
  expect(new Uint8Array(await response.data.arrayBuffer())).toEqual(wav);
  expect(response.headers.get("X-Request-ID")).toBe("request-audio-1");
  expect(requestHeaders.get("Authorization")).toBeNull();
});

test("keeps JSON success and typed JSON errors intact", async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ state: "current" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  const success = await voltaFetch<ApiHttpResponse<{ state: string }>>(
    "http://localhost.test/v1/operation",
  );
  expect(success.data).toEqual({ state: "current" });

  const apiError: ApiErrorResponse = {
    code: "RESOURCE_NOT_FOUND",
    message: "Evidence audio is unavailable.",
    request_id: "request-error-1",
  };
  globalThis.fetch = async () =>
    new Response(JSON.stringify(apiError), {
      status: 404,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": "request-error-1",
      },
    });

  await expect(
    voltaFetch("http://localhost.test/v1/evidence/id/audio"),
  ).rejects.toMatchObject({
    status: 404,
    data: apiError,
  } satisfies Partial<ApiHttpError<ApiErrorResponse>>);
});

test("normalizes non-JSON errors into a safe typed fallback", async () => {
  globalThis.fetch = async () =>
    new Response("upstream stack trace that must not reach the UI", {
      status: 502,
      headers: {
        "Content-Type": "text/plain",
        "X-Request-ID": "request-fallback-1",
      },
    });

  await expect(
    voltaFetch("http://localhost.test/v1/operation"),
  ).rejects.toMatchObject({
    status: 502,
    data: {
      code: "INTERNAL_ERROR",
      message: "API request failed with status 502",
      request_id: "request-fallback-1",
    },
  } satisfies Partial<ApiHttpError<ApiErrorResponse>>);
});
