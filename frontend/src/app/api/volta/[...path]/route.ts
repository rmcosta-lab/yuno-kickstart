import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const REQUEST_HEADERS = [
  "accept",
  "content-type",
  "idempotency-key",
  "x-request-id",
] as const;

const RESPONSE_HEADERS = [
  "cache-control",
  "content-disposition",
  "content-type",
  "idempotency-replayed",
  "retry-after",
  "x-content-type-options",
  "x-request-id",
] as const;

const configurationError = (message: string) =>
  Response.json(
    {
      code: "INTERNAL_ERROR",
      message,
      request_id: "proxy-configuration",
    },
    { status: 503, headers: { "Cache-Control": "no-store" } },
  );

const upstreamBaseUrl = (): URL | null => {
  const configured =
    process.env.API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";

  try {
    const url = new URL(configured);
    const localUpstream = ["localhost", "127.0.0.1", "::1"].includes(
      url.hostname,
    );
    if (url.protocol !== "https:" && !localUpstream) return null;
    return url;
  } catch {
    return null;
  }
};

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const baseUrl = upstreamBaseUrl();
  const bearer = process.env.VOLTA_DEMO_BEARER_TOKEN?.trim();
  if (!baseUrl) {
    return configurationError("The demo API URL is not configured correctly.");
  }
  if (!bearer) {
    return configurationError(
      "Automatic demo authorization is not configured.",
    );
  }

  const { path } = await context.params;
  if (path[0] !== "v1") {
    return Response.json(
      {
        code: "RESOURCE_NOT_FOUND",
        message: "The requested demo API route is unavailable.",
        request_id: "proxy-route",
      },
      { status: 404, headers: { "Cache-Control": "no-store" } },
    );
  }
  const requestUrl = new URL(request.url);
  const upstreamUrl = new URL(
    path.join("/"),
    `${baseUrl.toString().replace(/\/$/, "")}/`,
  );
  upstreamUrl.search = requestUrl.search;

  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  headers.set("Authorization", `Bearer ${bearer}`);
  headers.set("Origin", request.headers.get("origin") ?? requestUrl.origin);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      body: hasBody ? await request.arrayBuffer() : undefined,
      cache: "no-store",
      headers,
      method: request.method,
      redirect: "manual",
    });
  } catch {
    return Response.json(
      {
        code: "INTERNAL_ERROR",
        message: "The demo API is temporarily unavailable.",
        request_id: "proxy-upstream",
      },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }

  const responseHeaders = new Headers();
  for (const name of RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  responseHeaders.set("Cache-Control", "no-store");

  return new Response(upstream.body, {
    headers: responseHeaders,
    status: upstream.status,
    statusText: upstream.statusText,
  });
}

export const GET = proxy;
export const POST = proxy;
