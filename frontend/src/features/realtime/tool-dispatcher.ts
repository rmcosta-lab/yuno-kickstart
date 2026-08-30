import {
  createCandidateCommitment,
  recordQuote,
} from "@/lib/api/generated/api";
import type {
  ApiErrorResponse,
  CommitmentResponse,
  CreateCommitmentRequest,
  CreateQuoteRequest,
  QuoteResponse,
} from "@/lib/api/generated/models";
import { ApiErrorCode } from "@/lib/api/generated/models";
import { ApiHttpError } from "@/lib/api/volta-fetch";

const MAX_ARGUMENT_BYTES = 16_384;
const MAX_ID_LENGTH = 128;
const MAX_CONDITION_LENGTH = 500;
const MAX_CONDITIONS = 25;
const MAX_TRACKED_PROVIDER_CALLS = 128;
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type RealtimeOperationalContext = Readonly<{
  operationId: string;
  operationVersion: number;
  mandateVersion: number;
  sessions: readonly Readonly<{ callId: string; carrierId: string }>[];
  selectedQuote: Readonly<{
    callId: string;
    carrierId: string;
    quoteId: string;
  }> | null;
  attachedEvidence: Readonly<{ callId: string; evidenceId: string }> | null;
}>;

type RecordQuoteToolRequest = Readonly<{
  name: "record_quote";
  providerCallId: string;
  arguments: CreateQuoteRequest & { call_id: string };
}>;

type CreateCommitmentToolRequest = Readonly<{
  name: "create_candidate_commitment";
  providerCallId: string;
  arguments: CreateCommitmentRequest & { call_id: string };
}>;

export type RealtimeToolRequest =
  RecordQuoteToolRequest | CreateCommitmentToolRequest;

export type RealtimeToolOutput =
  | Readonly<{ ok: true; data: QuoteResponse | CommitmentResponse }>
  | Readonly<{
      ok: false;
      error: ApiErrorResponse | Readonly<{ code: "TOOL_UNAVAILABLE" }>;
    }>;

export interface RealtimeToolDispatcher {
  dispatch(request: RealtimeToolRequest): Promise<RealtimeToolOutput>;
  markDisconnected(): void;
  reconcile(): Promise<void>;
  isReconciling(): boolean;
}

type DispatcherOptions = Readonly<{
  getContext: () => RealtimeOperationalContext;
  refreshAuthoritativeContext: () => Promise<unknown>;
  onReconciliationChange?: (active: boolean) => void;
  executeTool?: (
    request: RealtimeToolRequest,
    idempotencyKey: string,
  ) => Promise<RealtimeToolOutput>;
}>;

type StoredCall = {
  key: string;
  pending: Promise<RealtimeToolOutput>;
  result?: RealtimeToolOutput;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(
  value: Record<string, unknown>,
  required: readonly string[],
): boolean {
  const keys = Object.keys(value);
  return (
    keys.length === required.length && required.every((key) => key in value)
  );
}

function isIdentifier(value: unknown): value is string {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= MAX_ID_LENGTH &&
    UUID_PATTERN.test(value)
  );
}

function isVersion(value: unknown): value is number {
  return Number.isSafeInteger(value) && Number(value) > 0;
}

function isBoundedString(value: unknown, maximum: number): value is string {
  return (
    typeof value === "string" && value.length > 0 && value.length <= maximum
  );
}

function isCalendarDate(value: unknown): value is string {
  if (!isBoundedString(value, 10) || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

function isRfc3339DateTime(value: unknown): value is string {
  return (
    isBoundedString(value, 64) &&
    /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,9})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(
      value,
    ) &&
    isCalendarDate(value.slice(0, 10)) &&
    !Number.isNaN(Date.parse(value))
  );
}

function parseQuoteArguments(
  value: unknown,
): RecordQuoteToolRequest["arguments"] | null {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
      "call_id",
      "expected_operation_version",
      "carrier_id",
      "mandate_version",
      "terms",
      "valid_until",
    ]) ||
    !isIdentifier(value.call_id) ||
    !isVersion(value.expected_operation_version) ||
    !isIdentifier(value.carrier_id) ||
    !isVersion(value.mandate_version) ||
    !isRfc3339DateTime(value.valid_until) ||
    !isRecord(value.terms) ||
    !hasExactKeys(value.terms, [
      "amount_minor",
      "currency",
      "pickup_window",
      "conditions",
    ]) ||
    !Number.isSafeInteger(value.terms.amount_minor) ||
    Number(value.terms.amount_minor) < 0 ||
    value.terms.currency !== "MXN" ||
    !isRecord(value.terms.pickup_window) ||
    !hasExactKeys(value.terms.pickup_window, ["start_date", "end_date"]) ||
    !isCalendarDate(value.terms.pickup_window.start_date) ||
    !isCalendarDate(value.terms.pickup_window.end_date) ||
    !Array.isArray(value.terms.conditions) ||
    value.terms.conditions.length > MAX_CONDITIONS ||
    !value.terms.conditions.every((item) =>
      isBoundedString(item, MAX_CONDITION_LENGTH),
    )
  ) {
    return null;
  }

  return value as RecordQuoteToolRequest["arguments"];
}

function parseCommitmentArguments(
  value: unknown,
): CreateCommitmentToolRequest["arguments"] | null {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
      "call_id",
      "expected_operation_version",
      "quote_id",
      "mandate_version",
      "evidence_id",
    ]) ||
    !isIdentifier(value.call_id) ||
    !isVersion(value.expected_operation_version) ||
    !isIdentifier(value.quote_id) ||
    !isVersion(value.mandate_version) ||
    !isIdentifier(value.evidence_id)
  ) {
    return null;
  }

  return value as CreateCommitmentToolRequest["arguments"];
}

export function parseRealtimeToolRequest(
  input: Readonly<{
    providerCallId: unknown;
    name: unknown;
    argumentsJson: unknown;
  }>,
): RealtimeToolRequest | null {
  if (
    !isBoundedString(input.providerCallId, MAX_ID_LENGTH) ||
    typeof input.argumentsJson !== "string" ||
    new TextEncoder().encode(input.argumentsJson).byteLength >
      MAX_ARGUMENT_BYTES
  ) {
    return null;
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(input.argumentsJson) as unknown;
  } catch {
    return null;
  }

  if (input.name === "record_quote") {
    const toolArguments = parseQuoteArguments(parsed);
    return toolArguments
      ? {
          name: "record_quote",
          providerCallId: input.providerCallId,
          arguments: toolArguments,
        }
      : null;
  }

  if (input.name === "create_candidate_commitment") {
    const toolArguments = parseCommitmentArguments(parsed);
    return toolArguments
      ? {
          name: "create_candidate_commitment",
          providerCallId: input.providerCallId,
          arguments: toolArguments,
        }
      : null;
  }

  return null;
}

function unavailable(): RealtimeToolOutput {
  return { ok: false, error: { code: "TOOL_UNAVAILABLE" } };
}

function safeApiError(value: unknown): ApiErrorResponse | null {
  if (!isRecord(value)) return null;
  const allowedKeys = new Set([
    "code",
    "current_draft_version",
    "current_operation_version",
    "field_issues",
    "message",
    "request_id",
    "resource_id",
  ]);
  if (
    Object.keys(value).some((key) => !allowedKeys.has(key)) ||
    !Object.values(ApiErrorCode).includes(value.code as ApiErrorCode) ||
    !isBoundedString(value.message, 500) ||
    !isBoundedString(value.request_id, 128)
  ) {
    return null;
  }
  for (const key of [
    "current_draft_version",
    "current_operation_version",
  ] as const) {
    if (key in value && value[key] !== null && !isVersion(value[key]))
      return null;
  }
  if (
    "resource_id" in value &&
    value.resource_id !== null &&
    !isBoundedString(value.resource_id, MAX_ID_LENGTH)
  ) {
    return null;
  }
  if ("field_issues" in value && value.field_issues !== null) {
    if (
      !Array.isArray(value.field_issues) ||
      value.field_issues.length > 50 ||
      !value.field_issues.every(
        (issue) =>
          isRecord(issue) &&
          hasExactKeys(issue, ["code", "field", "message"]) &&
          isBoundedString(issue.code, 100) &&
          isBoundedString(issue.field, 500) &&
          isBoundedString(issue.message, 500),
      )
    ) {
      return null;
    }
  }
  return value as ApiErrorResponse;
}

function safeFailure(error: unknown): RealtimeToolOutput {
  if (!(error instanceof ApiHttpError)) return unavailable();
  const safe = safeApiError(error.data);
  return safe ? { ok: false, error: safe } : unavailable();
}

function requestMatchesContext(
  request: RealtimeToolRequest,
  context: RealtimeOperationalContext,
): boolean {
  if (
    request.arguments.expected_operation_version !== context.operationVersion ||
    request.arguments.mandate_version !== context.mandateVersion
  ) {
    return false;
  }

  if (request.name === "record_quote") {
    const args = request.arguments;
    return context.sessions.some(
      (session) =>
        session.callId === args.call_id &&
        session.carrierId === args.carrier_id,
    );
  }

  const args = request.arguments;
  return Boolean(
    context.selectedQuote &&
    context.attachedEvidence &&
    context.selectedQuote.callId === args.call_id &&
    context.selectedQuote.quoteId === args.quote_id &&
    context.attachedEvidence.callId === args.call_id &&
    context.attachedEvidence.evidenceId === args.evidence_id,
  );
}

export function createRealtimeToolDispatcher(
  options: DispatcherOptions,
): RealtimeToolDispatcher {
  const calls = new Map<string, StoredCall>();
  let disconnectedWhilePending = false;
  let reconciliation: Promise<void> | null = null;

  const reconcile = async () => {
    if (!disconnectedWhilePending) return;
    if (reconciliation) return reconciliation;

    options.onReconciliationChange?.(true);
    reconciliation = Promise.all(
      [...calls.values()].map((call) => call.pending),
    )
      .then(() => options.refreshAuthoritativeContext())
      .then(() => {
        disconnectedWhilePending = false;
      })
      .finally(() => {
        reconciliation = null;
        options.onReconciliationChange?.(false);
      });
    return reconciliation;
  };

  const dispatch = (
    request: RealtimeToolRequest,
  ): Promise<RealtimeToolOutput> => {
    const existing = calls.get(request.providerCallId);
    if (existing) return existing.pending;
    if (disconnectedWhilePending || reconciliation) {
      return Promise.resolve(unavailable());
    }
    if (calls.size >= MAX_TRACKED_PROVIDER_CALLS) {
      return Promise.resolve(unavailable());
    }

    const context = options.getContext();
    if (!requestMatchesContext(request, context)) {
      return Promise.resolve(unavailable());
    }

    const key = crypto.randomUUID();
    const pending = (async (): Promise<RealtimeToolOutput> => {
      try {
        if (options.executeTool) {
          const output = await options.executeTool(request, key);
          await options.refreshAuthoritativeContext();
          return output;
        }
        if (request.name === "record_quote") {
          const { call_id: callId, ...data } = request.arguments;
          const response = await recordQuote(callId, data, {
            "Idempotency-Key": key,
          });
          await options.refreshAuthoritativeContext();
          return { ok: true, data: response.data };
        }

        const { call_id: callId, ...data } = request.arguments;
        const response = await createCandidateCommitment(callId, data, {
          "Idempotency-Key": key,
        });
        await options.refreshAuthoritativeContext();
        return { ok: true, data: response.data };
      } catch (error) {
        await options.refreshAuthoritativeContext().catch(() => undefined);
        return safeFailure(error);
      }
    })();

    const stored: StoredCall = { key, pending };
    calls.set(request.providerCallId, stored);
    void pending.then((result) => {
      stored.result = result;
    });
    return pending;
  };

  return {
    dispatch,
    isReconciling: () => disconnectedWhilePending || reconciliation !== null,
    markDisconnected: () => {
      disconnectedWhilePending =
        disconnectedWhilePending ||
        [...calls.values()].some((call) => call.result === undefined);
    },
    reconcile,
  };
}
