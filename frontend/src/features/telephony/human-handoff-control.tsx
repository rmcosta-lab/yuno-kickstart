"use client";

import {
  ArrowRight,
  Check,
  Headphones,
  Keyboard,
  PhoneForwarded,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useId, useRef, useState } from "react";

import {
  StatusBadge,
  type StatusTone,
} from "@/components/control-tower/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  useGetHumanHandoff,
  useGetHumanHandoffReadiness,
  useRequestHumanHandoff,
} from "@/lib/api/generated/api";
import {
  HumanHandoffResponseStatus,
  type RequestHumanHandoffRequest,
} from "@/lib/api/generated/models";
import { ApiHttpError } from "@/lib/api/volta-fetch";

export type HumanHandoffPresentationStatus =
  | "READY"
  | "PROCESSING"
  | "CONNECTING"
  | "JOINED"
  | "STALE"
  | "FAILED_SAFE"
  | "TIMED_OUT_SAFE";

export type HumanHandoffViewModel = Readonly<{
  callId: string;
  callStatus: string;
  coordinatorDestinationLabel: string;
  mandate: Readonly<{
    allowedConditions: readonly string[];
    currency: string;
    escalationConditions: readonly string[];
    maximumAmountMinor: number;
    pickupEnd: string;
    pickupStart: string;
    version: number;
  }>;
  quotes: readonly Readonly<{
    amountMinor: number;
    carrierLabel: string;
    conditions: readonly string[];
    currency: string;
    eligibility: string;
    rank: number;
    selected: boolean;
  }>[];
  brief: Readonly<{
    changes: readonly string[];
    facts: readonly string[];
    objections: readonly string[];
    unresolvedItems: readonly string[];
  }> | null;
}>;

export type HumanHandoffActionResult = Readonly<{
  status: Exclude<HumanHandoffPresentationStatus, "READY" | "PROCESSING">;
}>;

export type HumanHandoffActionBoundary = Readonly<{
  request: () => Promise<HumanHandoffActionResult>;
  refresh?: () => Promise<HumanHandoffActionResult>;
}>;

type HumanHandoffControlProps = Readonly<{
  action?: HumanHandoffActionBoundary;
  viewModel: HumanHandoffViewModel;
}>;

type HandoffAttempt = Readonly<{
  data: RequestHumanHandoffRequest;
  key: string;
}>;

const AUTHORIZED_BY = "coordinator-demo";

const STATUS_PRESENTATION: Record<
  HumanHandoffPresentationStatus,
  { announcement: string; label: string; tone: StatusTone }
> = {
  READY: {
    announcement: "Live call context is ready for explicit human takeover.",
    label: "READY",
    tone: "neutral",
  },
  PROCESSING: {
    announcement:
      "The takeover request is being validated. Human participation is not confirmed yet.",
    label: "PROCESSING",
    tone: "pending",
  },
  CONNECTING: {
    announcement:
      "The coordinator is connecting. Human participation is not confirmed yet.",
    label: "CONNECTING",
    tone: "pending",
  },
  JOINED: {
    announcement:
      "Verified provider evidence confirms the coordinator joined the live call.",
    label: "JOINED",
    tone: "success",
  },
  STALE: {
    announcement:
      "The current call or handoff state changed. Refresh before creating a new explicit confirmation.",
    label: "STATE CHANGED",
    tone: "warning",
  },
  FAILED_SAFE: {
    announcement:
      "The handoff failed safely. Artificial intelligence authority remains suspended.",
    label: "FAILED SAFE",
    tone: "danger",
  },
  TIMED_OUT_SAFE: {
    announcement:
      "The handoff timed out safely. Human participation was not confirmed.",
    label: "TIMED OUT SAFE",
    tone: "danger",
  },
};

const MONEY_FORMATTER = new Intl.NumberFormat("es-MX", {
  currency: "MXN",
  minimumFractionDigits: 2,
  style: "currency",
});

function formatMoney(amountMinor: number, currency: string) {
  if (currency === "MXN") return MONEY_FORMATTER.format(amountMinor / 100);
  return `${currency} ${(amountMinor / 100).toFixed(2)}`;
}

function FactList({ items }: { items: readonly string[] }) {
  return items.length > 0 ? (
    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-foreground">
      {items.map((item) => (
        <li key={item} className="wrap-break-word">
          {item}
        </li>
      ))}
    </ul>
  ) : (
    <p className="mt-2 text-sm text-muted-foreground">None recorded.</p>
  );
}

export function HumanHandoffControl({
  action,
  viewModel,
}: HumanHandoffControlProps) {
  const confirmationId = useId();
  const [confirmed, setConfirmed] = useState(false);
  const [hasAttempt, setHasAttempt] = useState(false);
  const [status, setStatus] = useState<HumanHandoffPresentationStatus>("READY");
  const [handoffId, setHandoffId] = useState("");
  const attemptRef = useRef<HandoffAttempt | null>(null);
  const submitGuardRef = useRef(false);
  const mutation = useRequestHumanHandoff();
  const readinessQuery = useGetHumanHandoffReadiness(viewModel.callId, {
    query: { enabled: action === undefined, retry: false },
  });
  const handoffQuery = useGetHumanHandoff(viewModel.callId, handoffId, {
    query: {
      enabled: action === undefined && handoffId.length > 0,
      refetchInterval: (query) =>
        query.state.data?.data.status === HumanHandoffResponseStatus.CONNECTING
          ? 1_000
          : false,
      retry: false,
    },
  });
  const effectiveStatus = handoffQuery.data?.data.status ?? status;
  const presentation = STATUS_PRESENTATION[effectiveStatus];
  const processing =
    effectiveStatus === "PROCESSING" || effectiveStatus === "CONNECTING";
  const terminal = effectiveStatus === "JOINED";
  const recoverable =
    effectiveStatus === "FAILED_SAFE" || effectiveStatus === "TIMED_OUT_SAFE";
  const duplicateDisabled =
    processing || terminal || effectiveStatus === "STALE";
  const readiness = readinessQuery.data?.data;
  const available =
    action !== undefined ||
    (readiness !== undefined && !readinessQuery.isFetching);

  const requestGeneratedHandoff = async () => {
    if (!readiness) throw new Error("Handoff readiness is unavailable");
    const attempt =
      attemptRef.current ??
      ({
        data: {
          authorized_at: new Date().toISOString(),
          authorized_by: AUTHORIZED_BY,
          coordinator_destination_label: viewModel.coordinatorDestinationLabel,
          expected_call_status_updated_at: readiness.call_status_updated_at,
        },
        key: crypto.randomUUID(),
      } satisfies HandoffAttempt);
    attemptRef.current = attempt;
    setHasAttempt(true);
    const response = await mutation.mutateAsync({
      callId: viewModel.callId,
      data: attempt.data,
      headers: { "Idempotency-Key": attempt.key },
    });
    setHandoffId(response.data.handoff_id);
    return { status: response.data.status } satisfies HumanHandoffActionResult;
  };

  const refreshGeneratedHandoff = async () => {
    if (handoffId.length === 0) return requestGeneratedHandoff();
    const response = await handoffQuery.refetch();
    if (!response.data) throw response.error ?? new Error("Refresh failed");
    return {
      status: response.data.data.status,
    } satisfies HumanHandoffActionResult;
  };

  const run = async (kind: "request" | "refresh") => {
    if (submitGuardRef.current) return;
    submitGuardRef.current = true;
    setStatus("PROCESSING");
    try {
      const result = action
        ? kind === "refresh" && action.refresh
          ? await action.refresh()
          : await action.request()
        : kind === "refresh"
          ? await refreshGeneratedHandoff()
          : await requestGeneratedHandoff();
      setStatus(result.status);
    } catch (error) {
      setStatus(
        error instanceof ApiHttpError && error.status === 409
          ? "STALE"
          : error instanceof ApiHttpError && error.status === 504
            ? "TIMED_OUT_SAFE"
            : "FAILED_SAFE",
      );
    } finally {
      submitGuardRef.current = false;
    }
  };

  return (
    <Card data-testid="human-handoff-control">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle className="flex items-center gap-2">
              <PhoneForwarded aria-hidden="true" className="size-5" />
              Human takeover
            </CardTitle>
            <CardDescription className="mt-1">
              Transfer the same live conversation with context intact.
            </CardDescription>
          </div>
          <StatusBadge tone={presentation.tone} label={presentation.label} />
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs font-medium text-muted-foreground">
              Normalized call status
            </p>
            <p className="mt-1 font-medium wrap-break-word">
              {readiness
                ? readiness.context.call_status.replaceAll("_", " ")
                : action
                  ? viewModel.callStatus.replaceAll("_", " ")
                  : "Loading live call status…"}
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs font-medium text-muted-foreground">
              Coordinator destination
            </p>
            <p className="mt-1 font-medium wrap-break-word">
              {viewModel.coordinatorDestinationLabel}
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-xs font-medium text-muted-foreground">
              Authority after acceptance
            </p>
            <p className="mt-1 font-medium">AI speech + commitments off</p>
          </div>
        </div>

        <section aria-labelledby="handoff-mandate-heading">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3
              id="handoff-mandate-heading"
              className="font-heading font-medium"
            >
              Current immutable mandate
            </h3>
            <StatusBadge
              tone="info"
              label={`MANDATE V${viewModel.mandate.version}`}
            />
          </div>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-muted-foreground">Maximum rate</dt>
              <dd className="mt-1 font-medium">
                {formatMoney(
                  viewModel.mandate.maximumAmountMinor,
                  viewModel.mandate.currency,
                )}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Pickup window</dt>
              <dd className="mt-1 flex flex-wrap items-center gap-1 font-medium">
                <span>{viewModel.mandate.pickupStart}</span>
                <ArrowRight aria-hidden="true" className="size-3.5" />
                <span>{viewModel.mandate.pickupEnd}</span>
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Allowed conditions</dt>
              <dd>
                <FactList items={viewModel.mandate.allowedConditions} />
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Escalate when</dt>
              <dd>
                <FactList items={viewModel.mandate.escalationConditions} />
              </dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby="handoff-quotes-heading">
          <h3 id="handoff-quotes-heading" className="font-heading font-medium">
            Server-ranked quotes
          </h3>
          {viewModel.quotes.length > 0 ? (
            <ol className="mt-3 grid gap-3 lg:grid-cols-2">
              {viewModel.quotes.map((quote) => (
                <li
                  key={`${quote.rank}-${quote.carrierLabel}`}
                  className="rounded-lg border border-border p-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-xs text-muted-foreground">
                        Server rank {quote.rank}
                      </p>
                      <p className="font-medium wrap-break-word">
                        {quote.carrierLabel}
                      </p>
                    </div>
                    <StatusBadge
                      tone={quote.selected ? "success" : "neutral"}
                      label={quote.selected ? "SELECTED" : quote.eligibility}
                    />
                  </div>
                  <p className="mt-2 text-sm font-medium">
                    {formatMoney(quote.amountMinor, quote.currency)}
                  </p>
                  <FactList items={quote.conditions} />
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground">
              No quote projection is available for this call.
            </p>
          )}
        </section>

        <section aria-labelledby="handoff-brief-heading">
          <h3 id="handoff-brief-heading" className="font-heading font-medium">
            Structured call brief · no transcript
          </h3>
          {viewModel.brief ||
          readiness?.context.structured_call_brief.length ? (
            <div className="mt-3 grid gap-4 rounded-lg border border-border p-3 sm:grid-cols-2">
              {(viewModel.brief
                ? ([
                    ["Facts", viewModel.brief.facts],
                    ["Changes", viewModel.brief.changes],
                    ["Objections", viewModel.brief.objections],
                    ["Unresolved", viewModel.brief.unresolvedItems],
                  ] as const)
                : ([
                    [
                      "Current call context",
                      readiness?.context.structured_call_brief ?? [],
                    ],
                  ] as const)
              ).map(([label, items]) => (
                <div key={label}>
                  <p className="text-xs font-medium text-muted-foreground">
                    {label}
                  </p>
                  <FactList items={items} />
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground">
              No bounded brief has been recorded for this call yet.
            </p>
          )}
        </section>

        <div className="rounded-lg border border-border bg-muted/40 p-4">
          <label
            htmlFor={confirmationId}
            className="flex cursor-pointer items-start gap-3 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-offset-2 has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60"
          >
            <input
              id={confirmationId}
              type="checkbox"
              autoComplete="off"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
              disabled={!available || duplicateDisabled}
              className="mt-0.5 size-4 shrink-0 accent-primary"
            />
            <span>
              I confirm a fresh human takeover by the demo coordinator. AI
              speech and commitment authority must stop before transfer.
            </span>
          </label>

          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button
              type="button"
              size="lg"
              onClick={() => void run("request")}
              disabled={!available || !confirmed || duplicateDisabled}
            >
              {processing ? (
                <RefreshCw
                  aria-hidden="true"
                  data-icon="inline-start"
                  className="animate-spin motion-reduce:animate-none"
                />
              ) : (
                <Check aria-hidden="true" data-icon="inline-start" />
              )}
              {processing ? "Taking over live call…" : "Take over live call"}
            </Button>
            <p className="text-sm text-muted-foreground">
              {duplicateDisabled
                ? "Duplicate takeover is disabled for this call."
                : available
                  ? "The coordinator joins only after verified provider evidence."
                  : "Current live-call readiness must load before takeover."}
            </p>
          </div>
        </div>

        <p className="sr-only" role="status" aria-live="polite" aria-atomic>
          {presentation.announcement}
        </p>

        {action === undefined && readinessQuery.isError ? (
          <Alert variant="destructive" role="alert">
            <RefreshCw aria-hidden="true" />
            <AlertTitle>Live call readiness is unavailable</AlertTitle>
            <AlertDescription className="space-y-3">
              <p>
                Takeover stays disabled until the current server-owned call
                status and version can be read safely.
              </p>
              <Button
                type="button"
                variant="outline"
                onClick={() => void readinessQuery.refetch()}
              >
                <RefreshCw aria-hidden="true" data-icon="inline-start" />
                Reload live call readiness
              </Button>
            </AlertDescription>
          </Alert>
        ) : null}

        {effectiveStatus === "JOINED" ? (
          <Alert role="status">
            <Check aria-hidden="true" />
            <AlertTitle>Coordinator joined</AlertTitle>
            <AlertDescription>
              Verified evidence confirms the coordinator is in the same live
              conversation. AI speech and commitment actions remain disabled.
            </AlertDescription>
          </Alert>
        ) : null}

        {effectiveStatus === "STALE" ? (
          <Alert variant="destructive" role="alert">
            <RefreshCw aria-hidden="true" />
            <AlertTitle>Call or handoff state changed</AlertTitle>
            <AlertDescription>
              Refresh the current state before creating a new explicit
              confirmation. This response may represent stale call context, an
              active handoff, or an idempotency conflict.
            </AlertDescription>
          </Alert>
        ) : null}

        {recoverable ? (
          <Alert variant="destructive" role="alert">
            <ShieldAlert aria-hidden="true" />
            <AlertTitle>
              {effectiveStatus === "FAILED_SAFE"
                ? "Handoff failed safely"
                : "Handoff timed out safely"}
            </AlertTitle>
            <AlertDescription className="space-y-3">
              <p>
                Human participation is not confirmed. The remote leg remains
                explicit and AI authority stays suspended. This phase does not
                expose a call-termination action.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void run("refresh")}
                  disabled={action ? !action.refresh : !hasAttempt}
                >
                  <RefreshCw aria-hidden="true" data-icon="inline-start" />
                  Recheck handoff status
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="flex flex-wrap gap-2 border-t border-border pt-4">
          <a
            href="#browser-voice-fallback"
            className={buttonVariants({ variant: "outline" })}
          >
            <Headphones aria-hidden="true" data-icon="inline-start" />
            Browser voice fallback
          </a>
          <a
            href="#voice-text-fallback"
            className={buttonVariants({ variant: "ghost" })}
          >
            <Keyboard aria-hidden="true" data-icon="inline-start" />
            Text fallback
          </a>
        </div>
      </CardContent>
    </Card>
  );
}
