"use client";

import { PhoneCall, ShieldCheck } from "lucide-react";
import { useRef, useState } from "react";

import {
  StatusBadge,
  type StatusTone,
} from "@/components/control-tower/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useCreateOutboundCall } from "@/lib/api/generated/api";
import type { CarrierSessionResponse } from "@/lib/api/generated/models/carrierSessionResponse";
import type { CreateOutboundCallRequest } from "@/lib/api/generated/models/createOutboundCallRequest";
import type { OperationResponse } from "@/lib/api/generated/models/operationResponse";
import {
  OutboundCallResponseStatus,
  type OutboundCallResponseStatus as OutboundCallStatus,
} from "@/lib/api/generated/models/outboundCallResponseStatus";
import { ApiHttpError } from "@/lib/api/volta-fetch";

type PresentationState = "idle" | "starting" | "live" | "ended" | "failed";

type MutationAttempt = {
  completed: boolean;
  data: CreateOutboundCallRequest;
  key: string;
  signature: string;
};

const DESTINATION_LABEL = "synthetic-carrier-one";
const AUTHORIZED_BY = "coordinator-demo";
const UNCERTAIN_HTTP_STATUSES = new Set([429, 500, 502, 503, 504]);

const STATE_PRESENTATION: Record<
  PresentationState,
  { label: string; tone: StatusTone; announcement: string }
> = {
  idle: {
    label: "ready",
    tone: "neutral",
    announcement: "Demo call is ready after authorization is confirmed.",
  },
  starting: {
    label: "starting",
    tone: "pending",
    announcement: "The authorized demo call request is starting.",
  },
  live: {
    label: "live",
    tone: "info",
    announcement: "The latest accepted create-call result is live.",
  },
  ended: {
    label: "ended",
    tone: "success",
    announcement: "The latest accepted create-call result has ended.",
  },
  failed: {
    label: "failed",
    tone: "danger",
    announcement: "The demo call request failed.",
  },
};

function selectLowestRankedSession(
  sessions: CarrierSessionResponse[] | undefined,
) {
  if (!sessions?.length) return null;

  return sessions.reduce((selected, candidate) =>
    candidate.carrier.deterministic_rank < selected.carrier.deterministic_rank
      ? candidate
      : selected,
  );
}

function projectStatus(status: OutboundCallStatus): PresentationState {
  switch (status) {
    case OutboundCallResponseStatus.QUEUED:
    case OutboundCallResponseStatus.INITIATED:
    case OutboundCallResponseStatus.RINGING:
    case OutboundCallResponseStatus.IN_PROGRESS:
      return "live";
    case OutboundCallResponseStatus.COMPLETED:
      return "ended";
    case OutboundCallResponseStatus.BUSY:
    case OutboundCallResponseStatus.FAILED:
    case OutboundCallResponseStatus.NO_ANSWER:
    case OutboundCallResponseStatus.CANCELED:
      return "failed";
  }
}

function isUncertainFailure(error: unknown) {
  return (
    !(error instanceof ApiHttpError) ||
    UNCERTAIN_HTTP_STATUSES.has(error.status)
  );
}

export function OutboundCallControl({
  operation,
}: {
  operation: OperationResponse;
}) {
  const selectedSession = selectLowestRankedSession(operation.sessions);
  const [authorized, setAuthorized] = useState(false);
  const [presentationState, setPresentationState] =
    useState<PresentationState>("idle");
  const attemptRef = useRef<MutationAttempt | null>(null);
  const submitGuardRef = useRef(false);
  const mutation = useCreateOutboundCall();
  const presentation = STATE_PRESENTATION[presentationState];

  const startCall = () => {
    if (!selectedSession || !authorized || submitGuardRef.current) return;

    submitGuardRef.current = true;
    const signature = JSON.stringify({
      operationId: operation.operation_id,
      sessionId: selectedSession.call_id,
    });
    const previousAttempt = attemptRef.current;
    const canReuseAttempt =
      previousAttempt?.signature === signature && !previousAttempt.completed;
    const key = canReuseAttempt ? previousAttempt.key : crypto.randomUUID();
    const data: CreateOutboundCallRequest = canReuseAttempt
      ? previousAttempt.data
      : {
          ai_disclosure_required: true,
          authorized_at: new Date().toISOString(),
          authorized_by: AUTHORIZED_BY,
          call_session_id: selectedSession.call_id,
          destination_label: DESTINATION_LABEL,
          recording_consent_required: false,
          recording_mode: "DISABLED",
        };
    attemptRef.current = { completed: false, data, key, signature };
    setPresentationState("starting");

    mutation.mutate(
      {
        operationId: operation.operation_id,
        data,
        headers: { "Idempotency-Key": key },
      },
      {
        onError: (error) => {
          attemptRef.current = {
            completed: !isUncertainFailure(error),
            data,
            key,
            signature,
          };
          submitGuardRef.current = false;
          setPresentationState("failed");
        },
        onSuccess: (response) => {
          attemptRef.current = { completed: true, data, key, signature };
          submitGuardRef.current = false;
          setPresentationState(projectStatus(response.data.status));
        },
      },
    );
  };

  const unavailable = selectedSession === null;
  const disabled = unavailable || !authorized || mutation.isPending;

  return (
    <Card data-testid="outbound-call-control">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <PhoneCall aria-hidden="true" className="size-5" />
            Authorized demo call
          </span>
          <StatusBadge tone={presentation.tone} label={presentation.label} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Start one server-authorized call to the selected synthetic carrier.
          The server owns the AI disclosure and press-1 continuation flow;
          recording is disabled.
        </p>

        <div className="rounded-md border border-border p-3 text-sm">
          <p className="font-medium text-foreground">Selected carrier</p>
          <p className="mt-1 break-words text-muted-foreground">
            {selectedSession?.carrier.display_name ??
              "No live operation session available"}
          </p>
        </div>

        <label className="flex cursor-pointer items-start gap-3 rounded-md border border-border p-3 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-offset-2 has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60">
          <input
            type="checkbox"
            name="outbound-call-authorization"
            autoComplete="off"
            className="mt-0.5 size-4 shrink-0 accent-primary"
            checked={authorized}
            onChange={(event) => setAuthorized(event.target.checked)}
            disabled={unavailable || mutation.isPending}
          />
          <span>
            I confirm the demo participant is authorized and the call will use
            AI disclosure with press-1 continuation.
          </span>
        </label>

        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" onClick={startCall} disabled={disabled}>
            <ShieldCheck aria-hidden="true" data-icon="inline-start" />
            {mutation.isPending ? "Starting demo call…" : "Start demo call"}
          </Button>
          {disabled && !mutation.isPending ? (
            <p className="text-sm text-muted-foreground">
              {unavailable
                ? "Load an operation with a live carrier session to enable dialing."
                : "Confirm participant authorization to enable dialing."}
            </p>
          ) : null}
        </div>

        <p className="text-sm text-muted-foreground">
          Status is the latest accepted create-call result only. This control
          does not poll or observe later provider activity.
        </p>
        <p className="sr-only" role="status" aria-live="polite">
          {presentation.announcement}
        </p>

        {presentationState === "failed" ? (
          <Alert variant="destructive" role="alert">
            <AlertTitle>Demo call failed</AlertTitle>
            <AlertDescription>
              No provider diagnostics are shown. Try the authorized action
              again, or continue with browser voice and typed text below.
            </AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}
