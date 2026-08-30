import type { ApiErrorResponse } from "./generated/models";
import { getDemoBearerToken } from "../demo-auth";

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

const parseResponseBody = async (response: Response): Promise<unknown> => {
  if ([204, 205, 304].includes(response.status) || response.body === null) {
    return undefined;
  }

  const body = await response.text();
  if (!body) {
    return undefined;
  }

  const contentType = response.headers.get("content-type")?.toLowerCase() ?? "";
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

  const bearerToken = getDemoBearerToken();
  if (bearerToken) {
    headers.set("Authorization", `Bearer ${bearerToken}`);
  }

  const response = await fetch(url, { ...options, headers });
  const result: ApiHttpResponse<unknown> = {
    data: await parseResponseBody(response),
    headers: response.headers,
    status: response.status,
  };

  if (!response.ok) {
    throw new ApiHttpError<ApiErrorResponse>({
      ...result,
      data: result.data as ApiErrorResponse,
    });
  }

  return result as TResponse;
};
