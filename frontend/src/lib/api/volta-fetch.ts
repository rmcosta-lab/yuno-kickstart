import { ApiErrorCode, type ApiErrorResponse } from "./generated/models";

export type ApiHttpResponse<TData> = {
  data: TData;
  headers: Headers;
  status: number;
};

const errorMessage = (data: unknown, status: number): string => {
  if (
    typeof data === "object" &&
    data !== null &&
    "message" in data &&
    typeof data.message === "string"
  ) {
    return data.message;
  }

  return `API request failed with status ${status}`;
};

const apiErrorCodes = new Set<string>(Object.values(ApiErrorCode));

const isApiErrorResponse = (value: unknown): value is ApiErrorResponse => {
  if (typeof value !== "object" || value === null) return false;

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.code === "string" &&
    apiErrorCodes.has(candidate.code) &&
    typeof candidate.message === "string" &&
    typeof candidate.request_id === "string"
  );
};

const safeApiError = (value: unknown, response: Response): ApiErrorResponse => {
  if (isApiErrorResponse(value)) return value;

  return {
    code: ApiErrorCode.INTERNAL_ERROR,
    message: `API request failed with status ${response.status}`,
    request_id:
      response.headers.get("x-request-id")?.trim() || "request-unavailable",
  };
};

export class ApiHttpError<TError = ApiErrorResponse> extends Error {
  readonly data: TError;
  readonly headers: Headers;
  readonly response: ApiHttpResponse<TError>;
  readonly status: number;

  constructor(response: ApiHttpResponse<TError>) {
    super(errorMessage(response.data, response.status));
    this.name = "ApiHttpError";
    this.data = response.data;
    this.headers = response.headers;
    this.response = response;
    this.status = response.status;
  }
}

export type ErrorType<TError> = ApiHttpError<TError>;

const proxiedApiUrl = (url: string): string => {
  if (typeof window === "undefined") return url;

  const upstream = new URL(url, window.location.origin);
  if (
    upstream.origin === window.location.origin &&
    upstream.pathname.startsWith("/api/volta/")
  ) {
    return upstream.toString();
  }

  return new URL(
    `/api/volta${upstream.pathname}${upstream.search}`,
    window.location.origin,
  ).toString();
};

const parseResponseBody = async (response: Response): Promise<unknown> => {
  if ([204, 205, 304].includes(response.status) || response.body === null) {
    return undefined;
  }

  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
  if (response.ok && contentType.startsWith("audio/")) {
    return response.blob();
  }

  const body = await response.text();
  if (!body) {
    return undefined;
  }

  if (!contentType.includes("json")) {
    return body;
  }

  try {
    return JSON.parse(body) as unknown;
  } catch {
    return body;
  }
};

export const voltaFetch = async <TResponse>(
  url: string,
  options?: RequestInit,
): Promise<TResponse> => {
  const headers = new Headers(options?.headers);
  headers.delete("Authorization");

  const response = await fetch(proxiedApiUrl(url), { ...options, headers });
  const result: ApiHttpResponse<unknown> = {
    data: await parseResponseBody(response),
    headers: response.headers,
    status: response.status,
  };

  if (!response.ok) {
    throw new ApiHttpError<ApiErrorResponse>({
      ...result,
      data: safeApiError(result.data, response),
    });
  }

  return result as TResponse;
};
