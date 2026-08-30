"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import {
  BellRing,
  Check,
  ChevronRight,
  CircleAlert,
  FileAudio,
  Flag,
  RefreshCw,
  ScrollText,
  ShieldAlert,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import {
  StatusBadge,
  type StatusTone,
} from "@/components/control-tower/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  getGetOperationAuditQueryKey,
  getGetOperationQueryKey,
  getOperationAudit,
  useAcknowledgeNotification,
  useGetOperation,
  useGetOperationAudit,
  useReplaceMandate,
  useStartInboundSimulation,
} from "@/lib/api/generated/api";
import {
  ApiErrorCode,
  type AuditTimelineResponse,
  type CommitmentResponse,
  type CoordinatorNotificationResponse,
  type EscalationResponse,
  type OperationResponse,
  RecoveryScenario,
  type RecoverySimulationResponse,
} from "@/lib/api/generated/models";
import { ApiHttpError } from "@/lib/api/volta-fetch";
import { DemoAuthControl, useDemoAuth } from "@/lib/demo-auth";
import { useCurrentOperationId } from "@/lib/live-operation-handoff";

import { auditItemsFromPages } from "./audit-items";
import { EvidenceAudioPlayer } from "./evidence-audio-player";

export type RecoverySurface = "evidence" | "recovery" | "escalation" | "audit";

type LogicalAttempt = {
  complete: boolean;
  key: string;
  signature: string;
};

const MAX_SAFE_MINOR_AMOUNT = BigInt(Number.MAX_SAFE_INTEGER);

const conditionLinesSchema = z.string().superRefine((value, context) => {
  const items = lines(value);
  if (items.length > 25) {
    context.addIssue({
      code: "custom",
      message: "Enter no more than 25 conditions.",
    });
  }
  if (items.some((item) => item.length > 500)) {
    context.addIssue({
      code: "custom",
      message: "Each condition must be 500 characters or fewer.",
    });
  }
});

function amountToMinor(value: string): bigint | null {
  if (!/^\d+(?:\.\d{1,2})?$/.test(value)) return null;
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole) * BigInt(100) + BigInt(fraction.padEnd(2, "0"));
}

const mandateSchema = z
  .object({
    approval_actor: z
      .string()
      .trim()
      .min(1, "Name the approving coordinator.")
      .max(500),
    maximum_amount_mxn: z
      .string()
      .trim()
      .regex(
        /^\d+(?:\.\d{1,2})?$/,
        "Enter an MXN amount with up to two decimals.",
      )
      .refine(
        (value) => {
          const amount = amountToMinor(value);
          return amount === null || amount > BigInt(0);
        },
        {
          message: "Enter an amount greater than zero.",
        },
      )
      .refine(
        (value) => {
          const amount = amountToMinor(value);
          return amount === null || amount <= MAX_SAFE_MINOR_AMOUNT;
        },
        {
          message: "Enter an amount within the supported safe integer range.",
        },
      ),
    pickup_start: z.string().min(1, "Enter the pickup start date."),
    pickup_end: z.string().min(1, "Enter the pickup end date."),
    allowed_conditions: conditionLinesSchema,
    escalation_conditions: conditionLinesSchema,
  })
  .refine((value) => value.pickup_end >= value.pickup_start, {
    message: "Pickup end must be on or after pickup start.",
    path: ["pickup_end"],
  });

type MandateValues = z.infer<typeof mandateSchema>;

function apiDetails(error: unknown) {
  return error instanceof ApiHttpError ? error.data : null;
}

function isStale(error: unknown) {
  const code = apiDetails(error)?.code;
  return (
    code === ApiErrorCode.STALE_OPERATION_VERSION ||
    code === ApiErrorCode.MANDATE_CONFLICT ||
    code === ApiErrorCode.STATE_CONFLICT
  );
}

function isRetryable(error: unknown) {
  const code = apiDetails(error)?.code;
  return (
    code === undefined ||
    code === ApiErrorCode.RATE_LIMITED ||
    code === ApiErrorCode.INTERNAL_ERROR
  );
}

function isAccessDenied(error: unknown) {
  const code = apiDetails(error)?.code;
  return (
    code === ApiErrorCode.ACTION_NOT_AUTHORIZED ||
    code === ApiErrorCode.AUTHENTICATION_REQUIRED ||
    code === ApiErrorCode.AUTHENTICATION_INVALID
  );
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

function moneyLabel(amountMinor: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amountMinor / 100);
}

function identifier(value: string) {
  return value.length > 20 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value;
}

function lines(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toneForState(state: string): StatusTone {
  if (["ACTIVE", "ACKNOWLEDGED", "RESOLVED", "MANDATE_SAFE"].includes(state)) {
    return "success";
  }
  if (["OPEN", "OUT_OF_MANDATE"].includes(state)) return "danger";
  if (["CANDIDATE", "PENDING"].includes(state)) return "pending";
  return "neutral";
}

function QueryError({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  const details = apiDetails(error);
  const denied = isAccessDenied(error);
  return (
    <div className="flex flex-col items-start gap-3">
      <ErrorState
        title={denied ? "Access denied" : "Recovery data unavailable"}
        description={
          details?.message ??
          (denied
            ? "Reconnect the demo authorization, then retry the live request."
            : "The live API request did not complete. Retry to load authoritative state.")
        }
      />
      <Button type="button" variant="outline" onClick={onRetry}>
        <RefreshCw aria-hidden="true" data-icon="inline-start" />
        {denied ? "Retry after reconnecting" : "Retry live request"}
      </Button>
    </div>
  );
}

function QueryRefreshError({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}) {
  const details = apiDetails(error);
  const denied = isAccessDenied(error);
  return (
    <Alert variant="destructive" role="alert">
      <CircleAlert aria-hidden="true" />
      <AlertTitle>
        {denied ? "Authorization refresh failed" : "Live refresh failed"}
      </AlertTitle>
      <AlertDescription className="flex flex-col items-start gap-3">
        <p>
          {details?.message ??
            "The last authoritative view remains visible while the live request is unavailable."}
        </p>
        <Button type="button" variant="outline" onClick={onRetry}>
          <RefreshCw aria-hidden="true" data-icon="inline-start" />
          {denied ? "Retry after reconnecting" : "Retry live refresh"}
        </Button>
      </AlertDescription>
    </Alert>
  );
}

function MutationError({
  error,
  onRefresh,
  onRetry,
}: {
  error: unknown;
  onRefresh: () => void;
  onRetry: () => void;
}) {
  const details = apiDetails(error);
  const stale = isStale(error);
  return (
    <Alert variant="destructive" role="alert">
      <CircleAlert aria-hidden="true" />
      <AlertTitle>
        {stale ? "Authoritative state changed" : "Action did not complete"}
      </AlertTitle>
      <AlertDescription className="flex flex-col items-start gap-3">
        <p>
          {details?.message ?? "The live API request could not be completed."}
        </p>
        {details ? (
          <p className="break-all font-mono text-xs">
            {details.code.replaceAll("_", " ")} · request {details.request_id}
          </p>
        ) : null}
        {stale || isRetryable(error) ? (
          <Button
            type="button"
            variant="outline"
            onClick={stale ? onRefresh : onRetry}
          >
            <RefreshCw aria-hidden="true" data-icon="inline-start" />
            {stale ? "Load current state" : "Retry same attempt"}
          </Button>
        ) : (
          <p>Review the operation and begin a new logical action.</p>
        )}
      </AlertDescription>
    </Alert>
  );
}

function useAttempts() {
  const attempts = useRef(new Map<string, LogicalAttempt>());
  const keyFor = (name: string, signature: string) => {
    const current = attempts.current.get(name);
    if (current?.signature === signature && !current.complete)
      return current.key;
    const key = crypto.randomUUID();
    attempts.current.set(name, { complete: false, key, signature });
    return key;
  };
  const complete = (name: string) => {
    const current = attempts.current.get(name);
    if (current) attempts.current.set(name, { ...current, complete: true });
  };
  return { complete, keyFor };
}

function EvidenceSurface({
  commitments,
  audit,
}: {
  commitments: CommitmentResponse[];
  audit: AuditTimelineResponse;
}) {
  if (commitments.length === 0) {
    return (
      <EmptyState
        icon={FileAudio}
        title="No commitment evidence"
        description="Evidence appears after a server-created commitment receives an evidence artifact."
      />
    );
  }

  return (
    <ul className="flex flex-col gap-5">
      {commitments.map((commitment) => {
        const evidence = commitment.evidence;
        const recap = audit.recaps.find(
          (item) => item.commitment_id === commitment.commitment_id,
        );
        const brief = audit.briefs.find(
          (item) => item.commitment_id === commitment.commitment_id,
        );
        return (
          <li key={commitment.commitment_id}>
            <Card>
              <CardHeader className="border-b">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <CardTitle className="break-words">
                      Commitment {identifier(commitment.commitment_id)}
                    </CardTitle>
                    <CardDescription>
                      Recorded {formatTimestamp(evidence.created_at)}
                    </CardDescription>
                  </div>
                  <div
                    className="flex flex-wrap gap-2"
                    aria-label="Evidence states"
                  >
                    <StatusBadge
                      tone={toneForState(evidence.lifecycle)}
                      label={`LIFECYCLE · ${evidence.lifecycle}`}
                    />
                    <StatusBadge
                      tone={toneForState(commitment.disposition)}
                      label={`DISPOSITION · ${commitment.disposition}`}
                    />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-5">
                <dl className="grid grid-cols-1 gap-4 font-mono text-xs sm:grid-cols-2 xl:grid-cols-4">
                  <div>
                    <dt className="text-muted-foreground">Evidence</dt>
                    <dd className="mt-1 break-all text-foreground">
                      {evidence.evidence_id}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Call</dt>
                    <dd className="mt-1 break-all text-foreground">
                      {evidence.call_id}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Item / event</dt>
                    <dd className="mt-1 break-all text-foreground">
                      {evidence.item_id} / {evidence.event_id}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Audio offset</dt>
                    <dd className="mt-1 text-foreground">
                      {(evidence.audio_start_ms / 1000).toFixed(3)} seconds
                    </dd>
                  </div>
                </dl>
                <section
                  aria-labelledby={`audio-${evidence.evidence_id}`}
                  className="flex flex-col gap-3"
                >
                  <div>
                    <h3
                      id={`audio-${evidence.evidence_id}`}
                      className="font-heading text-sm font-semibold"
                    >
                      Evidence audio
                    </h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      Loaded only on demand through the authenticated API; bytes
                      never enter the query cache.
                    </p>
                  </div>
                  <EvidenceAudioPlayer
                    key={evidence.evidence_id}
                    evidenceId={evidence.evidence_id}
                    audioStartMs={evidence.audio_start_ms}
                  />
                </section>
                {recap ? (
                  <section aria-labelledby={`recap-${recap.recap_id}`}>
                    <h3
                      id={`recap-${recap.recap_id}`}
                      className="font-heading text-sm font-semibold"
                    >
                      Written recap · {recap.channel}
                    </h3>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
                      {recap.rendered_content}
                    </p>
                  </section>
                ) : null}
                {brief ? (
                  <section aria-labelledby={`brief-${brief.brief_id}`}>
                    <h3
                      id={`brief-${brief.brief_id}`}
                      className="font-heading text-sm font-semibold"
                    >
                      Call brief
                    </h3>
                    <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
                      {(
                        [
                          ["Facts", brief.facts],
                          ["Changes", brief.changes],
                          ["Objections", brief.objections],
                          ["Unresolved", brief.unresolved_items],
                        ] as const
                      ).map(([label, items]) => (
                        <div key={label}>
                          <p className="text-xs font-medium text-muted-foreground">
                            {label}
                          </p>
                          {items?.length ? (
                            <ul className="mt-1 list-disc pl-5 text-sm">
                              {items.map((item) => (
                                <li key={item} className="break-words">
                                  {item}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="mt-1 text-sm text-muted-foreground">
                              None recorded.
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                ) : null}
              </CardContent>
            </Card>
          </li>
        );
      })}
    </ul>
  );
}

function NotificationCard({
  notification,
  operationVersion,
  onSettled,
}: {
  notification: CoordinatorNotificationResponse;
  operationVersion: number;
  onSettled: () => Promise<void>;
}) {
  const attempts = useAttempts();
  const mutation = useAcknowledgeNotification();
  const actor = "demo-coordinator";
  const acknowledge = () => {
    const signature = JSON.stringify({
      notification: notification.notification_id,
      operationVersion,
      actor,
    });
    const key = attempts.keyFor("acknowledge", signature);
    mutation.mutate(
      {
        notificationId: notification.notification_id,
        data: {
          acknowledged_by: actor,
          expected_operation_version: operationVersion,
        },
        headers: { "Idempotency-Key": key },
      },
      {
        onError: (error) => {
          if (!isRetryable(error)) attempts.complete("acknowledge");
          if (isStale(error)) void onSettled();
        },
        onSuccess: async () => {
          attempts.complete("acknowledge");
          await onSettled();
        },
      },
    );
  };

  return (
    <Card size="sm">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <CardTitle className="flex items-center gap-2">
            <BellRing aria-hidden="true" />
            Coordinator notification
          </CardTitle>
          <StatusBadge
            tone={notification.acknowledged ? "success" : "pending"}
            label={notification.acknowledged ? "ACKNOWLEDGED" : "PENDING"}
          />
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">{notification.message}</p>
        {notification.acknowledged ? (
          <p className="font-mono text-xs text-muted-foreground">
            First acknowledged by {notification.acknowledged_by} ·{" "}
            {notification.acknowledged_at
              ? formatTimestamp(notification.acknowledged_at)
              : "stored timestamp unavailable"}
          </p>
        ) : (
          <Button
            type="button"
            variant="outline"
            onClick={acknowledge}
            disabled={mutation.isPending}
          >
            <Check aria-hidden="true" data-icon="inline-start" />
            {mutation.isPending
              ? "Acknowledging…"
              : "Acknowledge as demo coordinator"}
          </Button>
        )}
        {mutation.isError ? (
          <MutationError
            error={mutation.error}
            onRefresh={() => void onSettled()}
            onRetry={acknowledge}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

function RecoverySurfaceView({
  operationId,
  operationVersion,
  activeCommitment,
  notifications,
  onSettled,
}: {
  operationId: string;
  operationVersion: number;
  activeCommitment: CommitmentResponse | null | undefined;
  notifications: CoordinatorNotificationResponse[];
  onSettled: () => Promise<void>;
}) {
  const attempts = useAttempts();
  const mutation = useStartInboundSimulation();
  const [lastResult, setLastResult] =
    useState<RecoverySimulationResponse | null>(null);
  const [lastScenario, setLastScenario] = useState<RecoveryScenario | null>(
    null,
  );

  if (!activeCommitment) {
    return (
      <EmptyState
        icon={Flag}
        title="No active commitment"
        description="Recovery simulations require the operation's current active commitment."
      />
    );
  }

  const simulate = (scenario: RecoveryScenario) => {
    setLastScenario(scenario);
    const data = {
      active_commitment_id: activeCommitment.commitment_id,
      expected_operation_version: operationVersion,
      scenario,
    };
    const signature = JSON.stringify({ data, operationId });
    const key = attempts.keyFor(scenario, signature);
    mutation.mutate(
      { operationId, data, headers: { "Idempotency-Key": key } },
      {
        onError: (error) => {
          if (!isRetryable(error)) attempts.complete(scenario);
          if (isStale(error)) void onSettled();
        },
        onSuccess: async (response) => {
          attempts.complete(scenario);
          setLastResult(response.data);
          await onSettled();
        },
      },
    );
  };

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Simulate an inbound change</CardTitle>
          <CardDescription>
            Both actions use the active commitment and operation version shown
            by the server.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Active commitment</dt>
              <dd className="mt-1 break-all font-mono text-xs">
                {activeCommitment.commitment_id}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Operation version</dt>
              <dd className="mt-1 font-mono">v{operationVersion}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Current terms</dt>
              <dd className="mt-1">
                {moneyLabel(
                  activeCommitment.agreed_terms.amount_minor,
                  activeCommitment.agreed_terms.currency,
                )}
              </dd>
            </div>
          </dl>
          <Separator />
          <div className="flex flex-col gap-3 sm:flex-row">
            <Button
              type="button"
              onClick={() => simulate(RecoveryScenario.MANDATE_SAFE)}
              disabled={mutation.isPending}
            >
              {mutation.isPending &&
              lastScenario === RecoveryScenario.MANDATE_SAFE
                ? "Simulating…"
                : "Run mandate-safe simulation"}
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => simulate(RecoveryScenario.OUT_OF_MANDATE)}
              disabled={mutation.isPending}
            >
              {mutation.isPending &&
              lastScenario === RecoveryScenario.OUT_OF_MANDATE
                ? "Simulating…"
                : "Run out-of-mandate simulation"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {mutation.isError && lastScenario ? (
        <MutationError
          error={mutation.error}
          onRefresh={() => void onSettled()}
          onRetry={() => simulate(lastScenario)}
        />
      ) : null}

      {lastResult ? (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Returned recovery decision</CardTitle>
                <CardDescription>{lastResult.decision_reason}</CardDescription>
              </div>
              <StatusBadge
                tone={toneForState(lastResult.scenario)}
                label={lastResult.scenario}
              />
            </div>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-muted-foreground">Before / after</dt>
                <dd className="mt-1 font-mono">
                  v{lastResult.before_operation_version} → v
                  {lastResult.after_operation_version}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Active commitment</dt>
                <dd className="mt-1 break-all font-mono text-xs">
                  {lastResult.active_commitment?.commitment_id ??
                    "Unchanged / none returned"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Escalation</dt>
                <dd className="mt-1 break-all font-mono text-xs">
                  {lastResult.escalation?.escalation_id ?? "None returned"}
                </dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      ) : null}

      {notifications.length ? (
        <section
          aria-labelledby="recovery-notifications"
          className="flex flex-col gap-3"
        >
          <h2
            id="recovery-notifications"
            className="font-heading text-lg font-semibold"
          >
            Notifications
          </h2>
          {notifications.map((notification) => (
            <NotificationCard
              key={notification.notification_id}
              notification={notification}
              operationVersion={operationVersion}
              onSettled={onSettled}
            />
          ))}
        </section>
      ) : null}
    </div>
  );
}

function MandateReplacementForm({
  operationId,
  operationVersion,
  escalationId,
  mandate,
  onSettled,
}: {
  operationId: string;
  operationVersion: number;
  escalationId: string;
  mandate: {
    maximum_amount_minor: number;
    pickup_window: { start_date: string; end_date: string };
    allowed_conditions?: string[];
    escalation_conditions?: string[];
  };
  onSettled: () => Promise<void>;
}) {
  const attempts = useAttempts();
  const mutation = useReplaceMandate();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<MandateValues>({
    resolver: zodResolver(mandateSchema),
    shouldFocusError: true,
    defaultValues: {
      approval_actor: "demo-coordinator",
      maximum_amount_mxn: (mandate.maximum_amount_minor / 100).toFixed(2),
      pickup_start: mandate.pickup_window.start_date,
      pickup_end: mandate.pickup_window.end_date,
      allowed_conditions: (mandate.allowed_conditions ?? []).join("\n"),
      escalation_conditions: (mandate.escalation_conditions ?? []).join("\n"),
    },
  });

  const submit = (values: MandateValues) => {
    const data = {
      approval_actor: values.approval_actor,
      maximum_amount_minor: Number(amountToMinor(values.maximum_amount_mxn)),
      currency: "MXN" as const,
      pickup_window: {
        start_date: values.pickup_start,
        end_date: values.pickup_end,
      },
      allowed_conditions: lines(values.allowed_conditions),
      escalation_conditions: lines(values.escalation_conditions),
      expected_operation_version: operationVersion,
      resolved_escalation_id: escalationId,
    };
    const signature = JSON.stringify({ data, operationId });
    const key = attempts.keyFor("replace-mandate", signature);
    mutation.mutate(
      { operationId, data, headers: { "Idempotency-Key": key } },
      {
        onError: (error) => {
          if (!isRetryable(error)) attempts.complete("replace-mandate");
        },
        onSuccess: async () => {
          attempts.complete("replace-mandate");
          await onSettled();
        },
      },
    );
  };
  const refreshCurrentState = async () => {
    await onSettled();
    mutation.reset();
  };

  const inputClass =
    "h-10 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive";
  return (
    <form
      onSubmit={handleSubmit(submit)}
      className="flex flex-col gap-5"
      noValidate
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="approval_actor">Approval actor</Label>
          <input
            id="approval_actor"
            autoComplete="off"
            {...register("approval_actor")}
            aria-describedby={
              errors.approval_actor ? "approval_actor-error" : undefined
            }
            aria-invalid={Boolean(errors.approval_actor)}
            className={inputClass}
          />
          {errors.approval_actor ? (
            <p
              id="approval_actor-error"
              className="text-sm text-destructive"
              role="alert"
            >
              {errors.approval_actor.message}
            </p>
          ) : null}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="maximum_amount_mxn">Maximum amount (MXN)</Label>
          <input
            id="maximum_amount_mxn"
            autoComplete="off"
            inputMode="decimal"
            {...register("maximum_amount_mxn")}
            aria-describedby={
              errors.maximum_amount_mxn ? "maximum_amount_mxn-error" : undefined
            }
            aria-invalid={Boolean(errors.maximum_amount_mxn)}
            className={inputClass}
          />
          {errors.maximum_amount_mxn ? (
            <p
              id="maximum_amount_mxn-error"
              className="text-sm text-destructive"
              role="alert"
            >
              {errors.maximum_amount_mxn.message}
            </p>
          ) : null}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pickup_start">Pickup start</Label>
          <input
            id="pickup_start"
            type="date"
            autoComplete="off"
            {...register("pickup_start")}
            aria-describedby={
              errors.pickup_start ? "pickup_start-error" : undefined
            }
            aria-invalid={Boolean(errors.pickup_start)}
            className={inputClass}
          />
          {errors.pickup_start ? (
            <p
              id="pickup_start-error"
              className="text-sm text-destructive"
              role="alert"
            >
              {errors.pickup_start.message}
            </p>
          ) : null}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="pickup_end">Pickup end</Label>
          <input
            id="pickup_end"
            type="date"
            autoComplete="off"
            {...register("pickup_end")}
            aria-describedby={
              errors.pickup_end ? "pickup_end-error" : undefined
            }
            aria-invalid={Boolean(errors.pickup_end)}
            className={inputClass}
          />
          {errors.pickup_end ? (
            <p
              id="pickup_end-error"
              className="text-sm text-destructive"
              role="alert"
            >
              {errors.pickup_end.message}
            </p>
          ) : null}
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="allowed_conditions">
            Allowed conditions · one per line
          </Label>
          <Textarea
            id="allowed_conditions"
            autoComplete="off"
            {...register("allowed_conditions")}
            aria-describedby={
              errors.allowed_conditions ? "allowed_conditions-error" : undefined
            }
            aria-invalid={Boolean(errors.allowed_conditions)}
          />
          {errors.allowed_conditions ? (
            <p
              id="allowed_conditions-error"
              className="text-sm text-destructive"
              role="alert"
            >
              {errors.allowed_conditions.message}
            </p>
          ) : null}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="escalation_conditions">
            Escalation conditions · one per line
          </Label>
          <Textarea
            id="escalation_conditions"
            autoComplete="off"
            {...register("escalation_conditions")}
            aria-describedby={
              errors.escalation_conditions
                ? "escalation_conditions-error"
                : undefined
            }
            aria-invalid={Boolean(errors.escalation_conditions)}
          />
          {errors.escalation_conditions ? (
            <p
              id="escalation_conditions-error"
              className="text-sm text-destructive"
              role="alert"
            >
              {errors.escalation_conditions.message}
            </p>
          ) : null}
        </div>
      </div>
      <p className="font-mono text-xs text-muted-foreground">
        Resolves escalation {escalationId} against operation v{operationVersion}
        .
      </p>
      <Button type="submit" disabled={mutation.isPending}>
        {mutation.isPending
          ? "Replacing mandate…"
          : "Approve replacement mandate"}
      </Button>
      {mutation.isError ? (
        <MutationError
          error={mutation.error}
          onRefresh={() => void refreshCurrentState()}
          onRetry={handleSubmit(submit)}
        />
      ) : null}
    </form>
  );
}

function EscalationSurfaceView({
  operation,
  audit,
  onSettled,
}: {
  operation: OperationResponse;
  audit: AuditTimelineResponse;
  onSettled: () => Promise<void>;
}) {
  const openEscalation =
    operation.open_escalation ??
    [...audit.escalations]
      .reverse()
      .find((item) => item.resolution_state === "OPEN") ??
    null;
  const resolvedEscalation = [...audit.escalations]
    .reverse()
    .find((item) => item.resolution_state === "RESOLVED");
  if (!openEscalation && resolvedEscalation) {
    return (
      <ResolvedEscalationSummary
        escalation={resolvedEscalation}
        operation={operation}
      />
    );
  }
  if (!openEscalation)
    return (
      <EmptyState
        icon={ShieldAlert}
        title="No open escalation"
        description="The current operation has no unresolved human-decision boundary."
      />
    );
  const escalation = openEscalation;
  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Decision boundary</CardTitle>
              <CardDescription>
                {formatTimestamp(escalation.created_at)}
              </CardDescription>
            </div>
            <StatusBadge
              tone={toneForState(escalation.resolution_state)}
              label={escalation.resolution_state}
            />
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Conflict
            </p>
            <p className="mt-1 text-sm">{escalation.conflict}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Attempted alternatives
            </p>
            {escalation.attempted_alternatives?.length ? (
              <ul className="mt-1 list-disc pl-5 text-sm">
                {escalation.attempted_alternatives.map((item) => (
                  <li key={item} className="break-words">
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-1 text-sm text-muted-foreground">
                None recorded.
              </p>
            )}
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground">
              Recommended action
            </p>
            <p className="mt-1 text-sm">{escalation.recommended_action}</p>
          </div>
          <p className="break-all font-mono text-xs text-muted-foreground">
            Correlation {escalation.correlation_id}
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Replacement mandate</CardTitle>
          <CardDescription>
            Approval is submitted with the named escalation and current server
            version. The view closes only after an authoritative refetch.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MandateReplacementForm
            key={escalation.escalation_id}
            operationId={operation.operation_id}
            operationVersion={operation.operation_version}
            escalationId={escalation.escalation_id}
            mandate={operation.active_mandate}
            onSettled={onSettled}
          />
        </CardContent>
      </Card>
    </div>
  );
}

function ResolvedEscalationSummary({
  escalation,
  operation,
}: {
  escalation: EscalationResponse;
  operation: OperationResponse;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <CardTitle>Escalation resolved</CardTitle>
            <CardDescription>
              The refreshed operation confirms the coordinator decision.
            </CardDescription>
          </div>
          <StatusBadge tone="success" label={escalation.resolution_state} />
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground">Immutable mandate</dt>
            <dd className="mt-1 font-medium">
              Version {operation.active_mandate.version}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Operation state</dt>
            <dd className="mt-1 font-medium">
              {operation.status} · version {operation.operation_version}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Resolved</dt>
            <dd className="mt-1 font-medium">
              {escalation.resolved_at
                ? formatTimestamp(escalation.resolved_at)
                : "Confirmed by the authoritative audit"}
            </dd>
          </div>
        </dl>
        <p className="break-all font-mono text-xs text-muted-foreground">
          Escalation {escalation.escalation_id}
        </p>
      </CardContent>
    </Card>
  );
}

function AuditSurfaceView({
  operationId,
  firstPage,
}: {
  operationId: string;
  firstPage: AuditTimelineResponse;
}) {
  const [pagination, setPagination] = useState<{
    operationId: string;
    firstCursor: string | null;
    pages: AuditTimelineResponse[];
    pending: boolean;
    error: unknown;
  }>({
    operationId,
    firstCursor: firstPage.next_cursor ?? null,
    pages: [],
    pending: false,
    error: null,
  });
  const matches =
    pagination.operationId === operationId &&
    pagination.firstCursor === (firstPage.next_cursor ?? null);
  const extraPages = useMemo(
    () => (matches ? pagination.pages : []),
    [matches, pagination.pages],
  );
  const pages = useMemo(
    () => [firstPage, ...extraPages],
    [firstPage, extraPages],
  );
  const items = useMemo(() => auditItemsFromPages(pages), [pages]);
  const nextCursor = extraPages.length
    ? extraPages.at(-1)?.next_cursor
    : firstPage.next_cursor;

  const loadMore = async () => {
    if (!nextCursor) return;
    setPagination({
      operationId,
      firstCursor: firstPage.next_cursor ?? null,
      pages: extraPages,
      pending: true,
      error: null,
    });
    try {
      const response = await getOperationAudit(operationId, {
        cursor: nextCursor,
        limit: 25,
      });
      setPagination({
        operationId,
        firstCursor: firstPage.next_cursor ?? null,
        pages: [...extraPages, response.data],
        pending: false,
        error: null,
      });
    } catch (error) {
      setPagination({
        operationId,
        firstCursor: firstPage.next_cursor ?? null,
        pages: extraPages,
        pending: false,
        error,
      });
    }
  };

  if (!items.length)
    return (
      <EmptyState
        icon={ScrollText}
        title="No audit artifacts"
        description="The append-only timeline will appear as the operation records events and artifacts."
      />
    );
  return (
    <div className="flex flex-col gap-5">
      <ol className="relative border-l border-border pl-6">
        {items.map((item) => (
          <li
            key={`${item.sourceKind}:${item.id}`}
            className="relative pb-7 [content-visibility:auto] last:pb-0"
          >
            <span
              aria-hidden="true"
              className="absolute top-1.5 -left-[1.78rem] size-3 rounded-full border-2 border-primary bg-background"
            />
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="font-heading text-sm font-semibold">
                  {item.title}
                </p>
                <p className="mt-1 break-words text-sm text-muted-foreground">
                  {item.description}
                </p>
              </div>
              {item.state ? (
                <StatusBadge
                  tone={toneForState(
                    item.state.split(" · ").at(-1) ?? item.state,
                  )}
                  label={item.state}
                />
              ) : null}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs text-muted-foreground">
              <span>{formatTimestamp(item.timestamp)}</span>
              <span>{item.sourceKind}</span>
              <span className="break-all">{item.id}</span>
            </div>
            {item.correlationId ? (
              <p className="mt-1 break-all font-mono text-xs text-muted-foreground">
                Correlation {item.correlationId}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
      {pagination.error ? (
        <MutationError
          error={pagination.error}
          onRefresh={() => void loadMore()}
          onRetry={() => void loadMore()}
        />
      ) : null}
      {nextCursor ? (
        <Button
          type="button"
          variant="outline"
          onClick={() => void loadMore()}
          disabled={pagination.pending}
        >
          {pagination.pending
            ? "Loading next page…"
            : "Load more audit artifacts"}
          <ChevronRight aria-hidden="true" data-icon="inline-end" />
        </Button>
      ) : (
        <p className="text-sm text-muted-foreground" role="status">
          End of the authoritative audit timeline.
        </p>
      )}
    </div>
  );
}

export function RecoveryExperience({ surface }: { surface: RecoverySurface }) {
  const auth = useDemoAuth();
  const operationId = useCurrentOperationId();
  const queryClient = useQueryClient();
  const operationQuery = useGetOperation(operationId ?? "", {
    query: { enabled: auth.connected && Boolean(operationId) },
  });
  const auditQuery = useGetOperationAudit(
    operationId ?? "",
    { limit: surface === "audit" ? 25 : 100 },
    { query: { enabled: auth.connected && Boolean(operationId) } },
  );

  const refresh = async () => {
    if (!operationId) return;
    await Promise.all([
      queryClient.invalidateQueries({
        queryKey: getGetOperationQueryKey(operationId),
      }),
      queryClient.invalidateQueries({
        queryKey: getGetOperationAuditQueryKey(operationId),
      }),
    ]);
  };
  const queryError = operationQuery.isError
    ? operationQuery.error
    : auditQuery.isError
      ? auditQuery.error
      : null;

  let content;
  if (!auth.connected) {
    content = (
      <EmptyState
        icon={ShieldAlert}
        title="Demo authorization required"
        description="Connect the local demo bearer to load the current operation. The token remains in memory only."
      />
    );
  } else if (!operationId) {
    content = (
      <EmptyState
        icon={Flag}
        title="No live operation selected"
        description="Create and approve an intake, then open carrier sessions to establish the current operation."
      />
    );
  } else if (operationQuery.isPending || auditQuery.isPending) {
    content = (
      <LoadingState
        label={`Loading ${surface} from the live operation`}
        rows={3}
      />
    );
  } else if (queryError && (!operationQuery.data || !auditQuery.data)) {
    content = <QueryError error={queryError} onRetry={() => void refresh()} />;
  } else if (!operationQuery.data || !auditQuery.data) {
    content = (
      <EmptyState
        icon={Flag}
        title="No authoritative data"
        description="The API returned no current operation view."
      />
    );
  } else {
    const operation = operationQuery.data.data;
    const audit = auditQuery.data.data;
    const commitmentsById = new Map(
      audit.commitment_history.map((item) => [item.commitment_id, item]),
    );
    if (operation.active_commitment) {
      commitmentsById.set(
        operation.active_commitment.commitment_id,
        operation.active_commitment,
      );
    }
    const commitments = [...commitmentsById.values()].sort((left, right) =>
      left.created_at.localeCompare(right.created_at),
    );
    let surfaceContent;
    if (surface === "evidence")
      surfaceContent = (
        <EvidenceSurface commitments={commitments} audit={audit} />
      );
    else if (surface === "recovery")
      surfaceContent = (
        <RecoverySurfaceView
          operationId={operation.operation_id}
          operationVersion={operation.operation_version}
          activeCommitment={operation.active_commitment}
          notifications={operation.notifications ?? []}
          onSettled={refresh}
        />
      );
    else if (surface === "escalation")
      surfaceContent = (
        <EscalationSurfaceView
          operation={operation}
          audit={audit}
          onSettled={refresh}
        />
      );
    else
      surfaceContent = (
        <AuditSurfaceView
          operationId={operation.operation_id}
          firstPage={audit}
        />
      );
    content = (
      <div className="flex flex-col gap-5">
        {queryError ? (
          <QueryRefreshError
            error={queryError}
            onRetry={() => void refresh()}
          />
        ) : null}
        {surfaceContent}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <DemoAuthControl />
      {content}
      <div className="sr-only" aria-live="polite">
        {operationQuery.isFetching || auditQuery.isFetching
          ? "Refreshing authoritative operation state"
          : "Authoritative operation state is current"}
      </div>
    </div>
  );
}
