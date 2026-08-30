"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  Database,
  FlaskConical,
  RefreshCw,
  RotateCcw,
  Send,
} from "lucide-react";
import {
  useEffect,
  useId,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
  type RefObject,
} from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { EmptyState } from "@/components/control-tower/empty-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { StatusBadge } from "@/components/control-tower/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  getGetOperationAuditQueryKey,
  getGetOperationQueryKey,
  useAttachCommitmentEvidence,
  useCreateCandidateCommitment,
  useGetOperation,
  useGetOperationAudit,
  useRecordQuote,
  useStartNegotiation,
  type AttachCommitmentEvidenceMutationBody,
  type CreateCandidateCommitmentMutationBody,
  type RecordQuoteMutationBody,
} from "@/lib/api/generated/api";
import {
  ApiErrorCode,
  BrowserChannel,
  type CarrierSessionResponse,
  type CommitmentEvidenceResponse,
  CommitmentDisposition,
  type AuditTimelineResponse,
  type CommitmentResponse,
  type OperationResponse,
} from "@/lib/api/generated/models";
import { ApiHttpError } from "@/lib/api/volta-fetch";
import { DemoAuthControl, useDemoAuth } from "@/lib/demo-auth";
import {
  saveCurrentOperationId,
  useCurrentOperationId,
} from "@/lib/live-operation-handoff";

import { createDemoNegotiationExperienceSource } from "./demo-source";
import { ComparisonView, SessionsView } from "./presentation";
import {
  BrowserVoiceExperience,
  RealtimeDiagnosticPreview,
  type AuthoritativeVoiceState,
} from "../realtime";
import {
  HumanHandoffControl,
  OutboundCallControl,
  type HumanHandoffViewModel,
} from "../telephony";
import type {
  DemoScenarioId,
  NegotiationExperienceSnapshot,
  NegotiationExperienceSource,
  NegotiationSurface,
} from "./types";

const DEMO_SOURCE = createDemoNegotiationExperienceSource();

const quoteFormSchema = z.object({
  amount_mxn: z
    .string()
    .trim()
    .regex(
      /^\d+(?:\.\d{1,2})?$/,
      "Enter an MXN amount with up to two decimals.",
    ),
  call_id: z.string().min(1, "Select a server-created carrier session."),
  conditions: z.string().max(5000, "Keep conditions under 5,000 characters."),
  pickup_end: z.string().min(1, "Enter the pickup-window end."),
  pickup_start: z.string().min(1, "Enter the pickup-window start."),
  valid_until: z.string().min(1, "Enter the quote expiry as an ISO timestamp."),
});

const evidenceFormSchema = z.object({
  audio_start_ms: z
    .string()
    .trim()
    .regex(/^\d+$/, "Enter a non-negative whole millisecond offset."),
  event_id: z.string().trim().min(1, "Enter the provider event ID."),
  item_id: z.string().trim().min(1, "Enter the provider item ID."),
  recording_reference: z
    .string()
    .trim()
    .min(1, "Enter the private fixture recording reference."),
});

type QuoteFormValues = z.infer<typeof quoteFormSchema>;
type EvidenceFormValues = z.infer<typeof evidenceFormSchema>;

type MutationAttempt = {
  completed: boolean;
  key: string;
  signature: string;
};

type NegotiationExperienceProps = {
  surface: NegotiationSurface;
  initialScenario?: DemoScenarioId;
  source?: NegotiationExperienceSource;
};

function mutationKeyFor(
  attempt: MutationAttempt | null,
  signature: string,
): string {
  if (attempt?.signature === signature && !attempt.completed) {
    return attempt.key;
  }
  return crypto.randomUUID();
}

function isReplay(headers?: Headers) {
  return headers?.get("Idempotency-Replayed")?.toLowerCase() === "true";
}

function apiErrorDetails(error: unknown) {
  return error instanceof ApiHttpError ? error.data : null;
}

function maskIdentifier(value: string) {
  if (value.length <= 10) return "••••••";
  return value.slice(0, 6) + "…" + value.slice(-4);
}

function LiveMutationError({
  error,
  onReconnect,
  onRetry,
  title,
}: {
  error: unknown;
  onReconnect: () => void;
  onRetry: () => void;
  title: string;
}) {
  const details = apiErrorDetails(error);
  const reconnect =
    details?.code === ApiErrorCode.STALE_OPERATION_VERSION ||
    details?.code === ApiErrorCode.MANDATE_CONFLICT ||
    details?.code === ApiErrorCode.STATE_CONFLICT;
  const retryable =
    details === null ||
    details.code === ApiErrorCode.RATE_LIMITED ||
    details.code === ApiErrorCode.INTERNAL_ERROR;

  return (
    <Alert variant="destructive" role="alert">
      <RotateCcw aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="flex flex-col items-start gap-3">
        <p>{details?.message ?? "The live API request did not complete."}</p>
        {details ? (
          <p className="font-mono text-xs">
            {details.code.replaceAll("_", " ")} · request {details.request_id}
          </p>
        ) : null}
        {reconnect || retryable ? (
          <Button
            type="button"
            variant="outline"
            onClick={reconnect ? onReconnect : onRetry}
          >
            <RefreshCw aria-hidden="true" data-icon="inline-start" />
            {reconnect ? "Reload current operation" : "Retry same attempt"}
          </Button>
        ) : (
          <p>Correct the input or begin a new logical action.</p>
        )}
      </AlertDescription>
    </Alert>
  );
}

function StartNegotiationControl({
  operation,
  onStateChanged,
}: {
  operation: OperationResponse;
  onStateChanged: () => Promise<unknown>;
}) {
  const [attempt, setAttempt] = useState<MutationAttempt | null>(null);
  const mutation = useStartNegotiation();

  const start = () => {
    const data = {
      channel: BrowserChannel.BROWSER_TEXT,
      expected_operation_version: operation.operation_version,
    };
    const signature = JSON.stringify({
      data,
      operationId: operation.operation_id,
    });
    const key = mutationKeyFor(attempt, signature);
    setAttempt({ completed: false, key, signature });

    mutation.mutate(
      {
        data,
        headers: { "Idempotency-Key": key },
        operationId: operation.operation_id,
      },
      {
        onError: (error) => {
          if (
            error instanceof ApiHttpError &&
            error.status !== 429 &&
            error.status !== 500
          ) {
            setAttempt({ completed: true, key, signature });
          }
        },
        onSuccess: async () => {
          setAttempt({ completed: true, key, signature });
          await onStateChanged();
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center justify-between gap-2">
          <span>Start text negotiation</span>
          <StatusBadge tone="neutral" label="SYNTHETIC · NO CONTACT" />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          The backend selects eligible synthetic carriers and returns either one
          to three sessions or a pre-contact escalation. The browser does not
          rank or filter carriers.
        </p>
        <Button type="button" onClick={start} disabled={mutation.isPending}>
          <Send aria-hidden="true" data-icon="inline-start" />
          {mutation.isPending ? "Starting…" : "Start server selection"}
        </Button>
        {mutation.isSuccess ? (
          <p className="text-sm text-success" role="status">
            Server selection recorded
            {isReplay(mutation.data.headers) ? " · idempotent replay" : ""}.
          </p>
        ) : null}
        {mutation.isError ? (
          <LiveMutationError
            title="Negotiation could not start"
            error={mutation.error}
            onReconnect={() => void onStateChanged()}
            onRetry={start}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}

function QuoteControl({
  operation,
  onStateChanged,
}: {
  operation: OperationResponse;
  onStateChanged: () => Promise<unknown>;
}) {
  const sessions = operation.sessions ?? [];
  const [attempt, setAttempt] = useState<MutationAttempt | null>(null);
  const mutation = useRecordQuote();
  const {
    formState: { errors },
    handleSubmit,
    register,
    setValue,
  } = useForm<QuoteFormValues>({
    resolver: zodResolver(quoteFormSchema),
    defaultValues: {
      amount_mxn: "",
      call_id: sessions[0]?.call_id ?? "",
      conditions: "",
      pickup_end: "",
      pickup_start: "",
      valid_until: "",
    },
  });

  const fillSample = (aboveDisplayedCap: boolean) => {
    const amountMinor =
      operation.active_mandate.maximum_amount_minor +
      (aboveDisplayedCap ? 10_000 : 0);
    setValue("amount_mxn", (amountMinor / 100).toFixed(2), {
      shouldValidate: true,
    });
    setValue(
      "pickup_start",
      operation.active_mandate.pickup_window.start_date,
      { shouldValidate: true },
    );
    setValue("pickup_end", operation.active_mandate.pickup_window.end_date, {
      shouldValidate: true,
    });
    setValue(
      "conditions",
      aboveDisplayedCap
        ? "Unapproved synthetic surcharge"
        : (operation.active_mandate.allowed_conditions ?? []).join("\n"),
      { shouldValidate: true },
    );
    setValue(
      "valid_until",
      new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
      { shouldValidate: true },
    );
  };

  const record = (values: QuoteFormValues) => {
    const session = sessions.find(
      (candidate) => candidate.call_id === values.call_id,
    );
    if (!session) return;

    const data: RecordQuoteMutationBody = {
      carrier_id: session.carrier.carrier_id,
      expected_operation_version: operation.operation_version,
      mandate_version: operation.active_mandate.version,
      terms: {
        amount_minor: Math.round(Number(values.amount_mxn) * 100),
        conditions: values.conditions
          .split("\n")
          .map((condition) => condition.trim())
          .filter(Boolean),
        currency: "MXN",
        pickup_window: {
          end_date: values.pickup_end,
          start_date: values.pickup_start,
        },
      },
      valid_until: values.valid_until,
    };
    const signature = JSON.stringify({ callId: session.call_id, data });
    const key = mutationKeyFor(attempt, signature);
    setAttempt({ completed: false, key, signature });

    mutation.mutate(
      {
        callId: session.call_id,
        data,
        headers: { "Idempotency-Key": key },
      },
      {
        onError: (error) => {
          if (
            error instanceof ApiHttpError &&
            error.status !== 429 &&
            error.status !== 500
          ) {
            setAttempt({ completed: true, key, signature });
          }
        },
        onSuccess: async () => {
          setAttempt({ completed: true, key, signature });
          await onStateChanged();
        },
      },
    );
  };

  const submit = handleSubmit(record);

  if (sessions.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center justify-between gap-2">
          <span>Record a synthetic quote</span>
          <StatusBadge tone="neutral" label="NO CARRIER CONTACT" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} noValidate className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="quote-call-id">Server-created session</Label>
            <select
              id="quote-call-id"
              {...register("call_id")}
              autoComplete="off"
              aria-invalid={Boolean(errors.call_id) || undefined}
              aria-describedby={
                errors.call_id ? "quote-call-id-error" : undefined
              }
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              {sessions.map((session) => (
                <option key={session.call_id} value={session.call_id}>
                  {session.carrier.display_name} · {session.call_id}
                </option>
              ))}
            </select>
            {errors.call_id ? (
              <p
                id="quote-call-id-error"
                className="text-sm text-destructive"
                role="alert"
              >
                {errors.call_id.message}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => fillSample(false)}
            >
              Use displayed mandate cap
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => fillSample(true)}
            >
              Use above-cap sample
            </Button>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="quote-amount">Amount (MXN)</Label>
              <input
                id="quote-amount"
                inputMode="decimal"
                {...register("amount_mxn")}
                autoComplete="off"
                aria-invalid={Boolean(errors.amount_mxn) || undefined}
                aria-describedby={
                  errors.amount_mxn ? "quote-amount-error" : undefined
                }
                className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
              {errors.amount_mxn ? (
                <p
                  id="quote-amount-error"
                  className="text-sm text-destructive"
                  role="alert"
                >
                  {errors.amount_mxn.message}
                </p>
              ) : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="quote-valid-until">Valid until (ISO)</Label>
              <input
                id="quote-valid-until"
                {...register("valid_until")}
                autoComplete="off"
                spellCheck={false}
                aria-invalid={Boolean(errors.valid_until) || undefined}
                aria-describedby={
                  errors.valid_until ? "quote-valid-until-error" : undefined
                }
                className="h-10 w-full rounded-md border border-input bg-background px-3 font-mono text-xs text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
              {errors.valid_until ? (
                <p
                  id="quote-valid-until-error"
                  className="text-sm text-destructive"
                  role="alert"
                >
                  {errors.valid_until.message}
                </p>
              ) : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="quote-pickup-start">Pickup start</Label>
              <input
                id="quote-pickup-start"
                {...register("pickup_start")}
                autoComplete="off"
                spellCheck={false}
                aria-invalid={Boolean(errors.pickup_start) || undefined}
                aria-describedby={
                  errors.pickup_start ? "quote-pickup-start-error" : undefined
                }
                className="h-10 w-full rounded-md border border-input bg-background px-3 font-mono text-xs text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
              {errors.pickup_start ? (
                <p
                  id="quote-pickup-start-error"
                  className="text-sm text-destructive"
                  role="alert"
                >
                  {errors.pickup_start.message}
                </p>
              ) : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="quote-pickup-end">Pickup end</Label>
              <input
                id="quote-pickup-end"
                {...register("pickup_end")}
                autoComplete="off"
                spellCheck={false}
                aria-invalid={Boolean(errors.pickup_end) || undefined}
                aria-describedby={
                  errors.pickup_end ? "quote-pickup-end-error" : undefined
                }
                className="h-10 w-full rounded-md border border-input bg-background px-3 font-mono text-xs text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
              {errors.pickup_end ? (
                <p
                  id="quote-pickup-end-error"
                  className="text-sm text-destructive"
                  role="alert"
                >
                  {errors.pickup_end.message}
                </p>
              ) : null}
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="quote-conditions">Conditions (one per line)</Label>
            <Textarea
              id="quote-conditions"
              rows={4}
              {...register("conditions")}
              autoComplete="off"
              aria-invalid={Boolean(errors.conditions) || undefined}
              aria-describedby={
                errors.conditions ? "quote-conditions-error" : undefined
              }
            />
            {errors.conditions ? (
              <p
                id="quote-conditions-error"
                className="text-sm text-destructive"
                role="alert"
              >
                {errors.conditions.message}
              </p>
            ) : null}
          </div>

          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Recording…" : "Record through live API"}
          </Button>
        </form>

        {mutation.isSuccess ? (
          <Alert className="mt-4" role="status">
            <Database aria-hidden="true" />
            <AlertTitle>Quote persisted by the server</AlertTitle>
            <AlertDescription>
              {mutation.data.data.eligibility.replaceAll("_", " ")}
              {isReplay(mutation.data.headers) ? " · idempotent replay" : ""}
              {mutation.data.data.rejection_reasons?.length
                ? ` · ${mutation.data.data.rejection_reasons.join(" · ")}`
                : ""}
            </AlertDescription>
          </Alert>
        ) : null}
        {mutation.isError ? (
          <div className="mt-4">
            <LiveMutationError
              title="Quote could not be recorded"
              error={mutation.error}
              onReconnect={() => void onStateChanged()}
              onRetry={() => void submit()}
            />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function ActiveCommitment({
  commitment,
  headingRef,
  replayed,
}: {
  commitment: CommitmentResponse;
  headingRef: RefObject<HTMLHeadingElement | null>;
  replayed: boolean;
}) {
  return (
    <Card className="ring-2 ring-primary">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center justify-between gap-2">
          <h2
            ref={headingRef}
            tabIndex={-1}
            className="rounded-sm outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            Active evidence-backed winner
          </h2>
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone="success" label={commitment.disposition} />
            <StatusBadge tone="info" label={commitment.lifecycle} />
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {replayed ? (
          <p className="text-sm text-muted-foreground" role="status">
            The server replayed the original commitment result without creating
            another active winner.
          </p>
        ) : null}
        <p className="text-sm text-muted-foreground">
          This is the server-returned active commitment. It is not a booking,
          and this text harness did not contact a carrier or provider.
        </p>
        <dl className="grid gap-4 text-sm sm:grid-cols-2 xl:grid-cols-3">
          <div>
            <dt className="font-medium text-foreground">Commitment</dt>
            <dd className="mt-1 font-mono text-xs text-muted-foreground">
              {maskIdentifier(commitment.commitment_id)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Selected quote</dt>
            <dd className="mt-1 font-mono text-xs text-muted-foreground">
              {maskIdentifier(commitment.quote_id)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Carrier session</dt>
            <dd className="mt-1 font-mono text-xs text-muted-foreground">
              {maskIdentifier(commitment.call_id)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Evidence lifecycle</dt>
            <dd className="mt-1 text-muted-foreground">
              {commitment.evidence.lifecycle}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Audio start</dt>
            <dd className="mt-1 font-mono text-xs text-muted-foreground">
              {commitment.evidence.audio_start_ms} ms
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Recording</dt>
            <dd className="mt-1 text-muted-foreground">
              Private recording linked · access controlled
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Evidence ID</dt>
            <dd className="mt-1 font-mono text-xs text-muted-foreground">
              {maskIdentifier(commitment.evidence.evidence_id)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Item ID</dt>
            <dd className="mt-1 font-mono text-xs text-muted-foreground">
              {maskIdentifier(commitment.evidence.item_id)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-foreground">Event ID</dt>
            <dd className="mt-1 font-mono text-xs text-muted-foreground">
              {maskIdentifier(commitment.evidence.event_id)}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

function CommitmentTerminalRegion({
  announcement,
  busy,
  children,
}: {
  announcement: string;
  busy: boolean;
  children: ReactNode;
}) {
  return (
    <section aria-busy={busy} aria-label="Candidate commitment status">
      <p
        className="sr-only"
        role="status"
        aria-atomic="true"
        aria-live="polite"
      >
        {announcement}
      </p>
      {children}
    </section>
  );
}

function CommitmentTerminal({
  audit,
  auditError,
  auditPending,
  onRetryAudit,
  onEvidenceAttached,
  onStateChanged,
  operation,
}: {
  audit?: AuditTimelineResponse;
  auditError: unknown;
  auditPending: boolean;
  onRetryAudit: () => void;
  onEvidenceAttached: (evidence: CommitmentEvidenceResponse) => void;
  onStateChanged: () => Promise<unknown>;
  operation: OperationResponse;
}) {
  const [attempt, setAttempt] = useState<MutationAttempt | null>(null);
  const [evidenceAttempt, setEvidenceAttempt] =
    useState<MutationAttempt | null>(null);
  const [evidenceForCallId, setEvidenceForCallId] = useState<string | null>(
    null,
  );
  const evidenceMutation = useAttachCommitmentEvidence();
  const mutation = useCreateCandidateCommitment();
  const focusWinnerOnSuccessRef = useRef(false);
  const winnerHeadingRef = useRef<HTMLHeadingElement>(null);
  const {
    formState: { errors: evidenceErrors },
    handleSubmit: handleEvidenceSubmit,
    register: registerEvidence,
  } = useForm<EvidenceFormValues>({
    resolver: zodResolver(evidenceFormSchema),
    defaultValues: {
      audio_start_ms: "",
      event_id: "",
      item_id: "",
      recording_reference: "",
    },
  });
  const activeCommitments = (audit?.commitment_history ?? []).filter(
    (commitment) => commitment.disposition === CommitmentDisposition.ACTIVE,
  );
  const operationCommitment =
    operation.active_commitment?.disposition === CommitmentDisposition.ACTIVE
      ? operation.active_commitment
      : null;
  const mutationCommitment =
    mutation.data?.data.disposition === CommitmentDisposition.ACTIVE
      ? mutation.data.data
      : null;
  const distinctActiveCommitments = new Map<string, CommitmentResponse>();

  for (const commitment of [
    ...activeCommitments,
    operationCommitment,
    mutationCommitment,
  ]) {
    if (commitment) {
      distinctActiveCommitments.set(commitment.commitment_id, commitment);
    }
  }

  const activeCommitment = distinctActiveCommitments.values().next().value;

  useEffect(() => {
    if (!activeCommitment || !focusWinnerOnSuccessRef.current) return;

    focusWinnerOnSuccessRef.current = false;
    winnerHeadingRef.current?.focus();
  }, [activeCommitment]);

  if (activeCommitments.length > 1 || distinctActiveCommitments.size > 1) {
    return (
      <CommitmentTerminalRegion
        announcement="Candidate commitment is unavailable because the server returned conflicting active commitments."
        busy={false}
      >
        <Alert variant="destructive" role="alert">
          <RotateCcw aria-hidden="true" />
          <AlertTitle>Conflicting active commitment projection</AlertTitle>
          <AlertDescription className="flex flex-col items-start gap-3">
            <p>
              The server returned more than one active commitment. No winner is
              rendered or inferred from this inconsistent state.
            </p>
            <Button type="button" variant="outline" onClick={onRetryAudit}>
              <RefreshCw aria-hidden="true" data-icon="inline-start" />
              Reload server projections
            </Button>
          </AlertDescription>
        </Alert>
      </CommitmentTerminalRegion>
    );
  }

  if (activeCommitment) {
    const replayed = isReplay(mutation.data?.headers);
    return (
      <CommitmentTerminalRegion
        announcement={
          replayed
            ? "Active evidence-backed winner restored. The server replayed the original commitment without creating another winner."
            : "Candidate commitment created. The active evidence-backed winner is ready."
        }
        busy={false}
      >
        <ActiveCommitment
          commitment={activeCommitment}
          headingRef={winnerHeadingRef}
          replayed={replayed}
        />
      </CommitmentTerminalRegion>
    );
  }

  if (auditPending) {
    return (
      <CommitmentTerminalRegion
        announcement="Loading the server quote selection."
        busy
      >
        <LoadingState label="Loading server quote selection" rows={2} />
      </CommitmentTerminalRegion>
    );
  }

  if (auditError) {
    return (
      <CommitmentTerminalRegion
        announcement="The server quote selection could not be loaded."
        busy={false}
      >
        <LiveMutationError
          title="Server quote selection could not be loaded"
          error={auditError}
          onReconnect={onRetryAudit}
          onRetry={onRetryAudit}
        />
      </CommitmentTerminalRegion>
    );
  }

  if (!audit) {
    return (
      <CommitmentTerminalRegion
        announcement="Candidate commitment is waiting for the server audit projection."
        busy={false}
      >
        {null}
      </CommitmentTerminalRegion>
    );
  }

  const selectedQuotes = audit.quote_comparison.filter(
    (quote) => quote.selected,
  );

  if (selectedQuotes.length !== 1) {
    return (
      <CommitmentTerminalRegion
        announcement={
          selectedQuotes.length === 0
            ? "No server-selected quote is ready for a candidate commitment."
            : "Candidate commitment is unavailable because the server selected more than one quote."
        }
        busy={false}
      >
        <Alert>
          <Database aria-hidden="true" />
          <AlertTitle>
            {selectedQuotes.length === 0
              ? "No server-selected quote"
              : "Ambiguous server-selected quotes"}
          </AlertTitle>
          <AlertDescription>
            {selectedQuotes.length === 0
              ? "Record eligible terms and reload until the audit projection marks exactly one quote as selected."
              : "The audit projection marked more than one quote as selected. No commitment action is available until the server resolves the conflict."}
          </AlertDescription>
        </Alert>
      </CommitmentTerminalRegion>
    );
  }

  const selectedQuote = selectedQuotes[0];
  const attachedEvidence =
    evidenceMutation.isSuccess && evidenceForCallId === selectedQuote.call_id
      ? evidenceMutation.data.data
      : null;

  const attachEvidence = (values: EvidenceFormValues) => {
    const data: AttachCommitmentEvidenceMutationBody = {
      audio_start_ms: Number(values.audio_start_ms),
      event_id: values.event_id.trim(),
      expected_operation_version: operation.operation_version,
      item_id: values.item_id.trim(),
      recording_reference: values.recording_reference.trim(),
    };
    const signature = JSON.stringify({
      callId: selectedQuote.call_id,
      data,
    });
    const key = mutationKeyFor(evidenceAttempt, signature);
    setEvidenceAttempt({ completed: false, key, signature });

    evidenceMutation.mutate(
      {
        callId: selectedQuote.call_id,
        data,
        headers: { "Idempotency-Key": key },
      },
      {
        onError: (error) => {
          if (
            error instanceof ApiHttpError &&
            error.status !== 429 &&
            error.status !== 500
          ) {
            setEvidenceAttempt({ completed: true, key, signature });
          }
        },
        onSuccess: async (response) => {
          setEvidenceAttempt({ completed: true, key, signature });
          setEvidenceForCallId(selectedQuote.call_id);
          onEvidenceAttached(response.data);
          await onStateChanged();
        },
      },
    );
  };

  const submitEvidence = handleEvidenceSubmit(attachEvidence);

  const createCommitment = () => {
    if (!attachedEvidence) return;
    focusWinnerOnSuccessRef.current = true;
    const data: CreateCandidateCommitmentMutationBody = {
      evidence_id: attachedEvidence.evidence_id,
      expected_operation_version: operation.operation_version,
      mandate_version: operation.active_mandate.version,
      quote_id: selectedQuote.quote_id,
    };
    const signature = JSON.stringify({ callId: selectedQuote.call_id, data });
    const key = mutationKeyFor(attempt, signature);
    setAttempt({ completed: false, key, signature });

    mutation.mutate(
      {
        callId: selectedQuote.call_id,
        data,
        headers: { "Idempotency-Key": key },
      },
      {
        onError: (error) => {
          if (
            error instanceof ApiHttpError &&
            error.status !== 429 &&
            error.status !== 500
          ) {
            focusWinnerOnSuccessRef.current = false;
            setAttempt({ completed: true, key, signature });
          }
        },
        onSuccess: async () => {
          setAttempt({ completed: true, key, signature });
          await onStateChanged();
        },
      },
    );
  };

  const terminalAnnouncement = evidenceMutation.isPending
    ? "Attaching the supplied agreement evidence."
    : mutation.isPending
      ? "Creating the evidence-backed candidate commitment."
      : evidenceMutation.isError
        ? "The supplied agreement evidence could not be attached."
        : mutation.isError
          ? "The candidate commitment could not be created."
          : attachedEvidence
            ? "Agreement evidence attached. The candidate commitment is ready to be created."
            : "One server-selected quote is ready for its agreement evidence.";

  return (
    <CommitmentTerminalRegion
      announcement={terminalAnnouncement}
      busy={evidenceMutation.isPending || mutation.isPending}
    >
      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center justify-between gap-2">
            <span>Create candidate commitment</span>
            <StatusBadge tone="neutral" label="TEXT · SYNTHETIC · NO CONTACT" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            The audit projection selected quote{" "}
            {maskIdentifier(selectedQuote.quote_id)}. Attach an existing private
            Phase 14 fixture for this session before creating the commitment.
            The browser does not derive evidence metadata or choose a winner.
          </p>
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-foreground">Carrier</dt>
              <dd className="mt-1 text-muted-foreground">
                {selectedQuote.carrier_display_name}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Session</dt>
              <dd className="mt-1 font-mono text-xs text-muted-foreground">
                {maskIdentifier(selectedQuote.call_id)}
              </dd>
            </div>
          </dl>

          {!attachedEvidence ? (
            <form
              onSubmit={submitEvidence}
              noValidate
              className="space-y-4 rounded-lg border border-border p-4"
            >
              <div>
                <h3 className="font-heading font-medium text-foreground">
                  Agreement evidence fixture
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  Supply the private recording and exact agreement-turn
                  correlation already produced by the Phase 14 fixture. This
                  action does not create or fabricate audio.
                </p>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="commitment-recording-reference">
                  Private recording reference
                </Label>
                <input
                  id="commitment-recording-reference"
                  {...registerEvidence("recording_reference")}
                  autoComplete="off"
                  spellCheck={false}
                  aria-invalid={
                    Boolean(evidenceErrors.recording_reference) || undefined
                  }
                  aria-describedby={
                    evidenceErrors.recording_reference
                      ? "commitment-recording-reference-error"
                      : "commitment-recording-reference-help"
                  }
                  className="h-10 w-full rounded-md border border-input bg-background px-3 font-mono text-xs text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                />
                <p
                  id="commitment-recording-reference-help"
                  className="text-xs text-muted-foreground"
                >
                  The reference is sent only to this repository&apos;s API and
                  is not shown in the winner summary.
                </p>
                {evidenceErrors.recording_reference ? (
                  <p
                    id="commitment-recording-reference-error"
                    className="text-sm text-destructive"
                    role="alert"
                  >
                    {evidenceErrors.recording_reference.message}
                  </p>
                ) : null}
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-1.5">
                  <Label htmlFor="commitment-audio-start-ms">
                    Audio start (ms)
                  </Label>
                  <input
                    id="commitment-audio-start-ms"
                    inputMode="numeric"
                    {...registerEvidence("audio_start_ms")}
                    autoComplete="off"
                    aria-invalid={
                      Boolean(evidenceErrors.audio_start_ms) || undefined
                    }
                    aria-describedby={
                      evidenceErrors.audio_start_ms
                        ? "commitment-audio-start-ms-error"
                        : undefined
                    }
                    className="h-10 w-full rounded-md border border-input bg-background px-3 font-mono text-xs text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  />
                  {evidenceErrors.audio_start_ms ? (
                    <p
                      id="commitment-audio-start-ms-error"
                      className="text-sm text-destructive"
                      role="alert"
                    >
                      {evidenceErrors.audio_start_ms.message}
                    </p>
                  ) : null}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="commitment-item-id">Item ID</Label>
                  <input
                    id="commitment-item-id"
                    {...registerEvidence("item_id")}
                    autoComplete="off"
                    spellCheck={false}
                    aria-invalid={Boolean(evidenceErrors.item_id) || undefined}
                    aria-describedby={
                      evidenceErrors.item_id
                        ? "commitment-item-id-error"
                        : undefined
                    }
                    className="h-10 w-full rounded-md border border-input bg-background px-3 font-mono text-xs text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  />
                  {evidenceErrors.item_id ? (
                    <p
                      id="commitment-item-id-error"
                      className="text-sm text-destructive"
                      role="alert"
                    >
                      {evidenceErrors.item_id.message}
                    </p>
                  ) : null}
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="commitment-event-id">Event ID</Label>
                  <input
                    id="commitment-event-id"
                    {...registerEvidence("event_id")}
                    autoComplete="off"
                    spellCheck={false}
                    aria-invalid={Boolean(evidenceErrors.event_id) || undefined}
                    aria-describedby={
                      evidenceErrors.event_id
                        ? "commitment-event-id-error"
                        : undefined
                    }
                    className="h-10 w-full rounded-md border border-input bg-background px-3 font-mono text-xs text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  />
                  {evidenceErrors.event_id ? (
                    <p
                      id="commitment-event-id-error"
                      className="text-sm text-destructive"
                      role="alert"
                    >
                      {evidenceErrors.event_id.message}
                    </p>
                  ) : null}
                </div>
              </div>

              <Button type="submit" disabled={evidenceMutation.isPending}>
                {evidenceMutation.isPending
                  ? "Attaching supplied evidence…"
                  : "Attach supplied evidence"}
              </Button>

              {evidenceMutation.isError ? (
                <LiveMutationError
                  title="Agreement evidence could not be attached"
                  error={evidenceMutation.error}
                  onReconnect={() => void onStateChanged()}
                  onRetry={() => void submitEvidence()}
                />
              ) : null}
            </form>
          ) : (
            <Alert>
              <Database aria-hidden="true" />
              <AlertTitle>Agreement evidence attached</AlertTitle>
              <AlertDescription>
                Evidence {maskIdentifier(attachedEvidence.evidence_id)} is
                correlated to this server session
                {isReplay(evidenceMutation.data?.headers)
                  ? " · idempotent replay"
                  : ""}
                .
              </AlertDescription>
            </Alert>
          )}

          <Button
            type="button"
            onClick={createCommitment}
            disabled={!attachedEvidence || mutation.isPending}
          >
            {!attachedEvidence
              ? "Attach evidence before commitment"
              : mutation.isPending
                ? "Creating evidence-backed candidate…"
                : "Create evidence-backed candidate"}
          </Button>
          {mutation.isError ? (
            <LiveMutationError
              title="Candidate commitment could not be created"
              error={mutation.error}
              onReconnect={() => void onStateChanged()}
              onRetry={createCommitment}
            />
          ) : null}
        </CardContent>
      </Card>
    </CommitmentTerminalRegion>
  );
}

function LiveOperation({
  audit,
  auditError,
  auditPending,
  onRetryAudit,
  operation,
  onStateChanged,
  surface,
}: {
  audit?: AuditTimelineResponse;
  auditError: unknown;
  auditPending: boolean;
  onRetryAudit: () => void;
  operation: OperationResponse;
  onStateChanged: () => Promise<AuthoritativeVoiceState>;
  surface: NegotiationSurface;
}) {
  const [attachedEvidence, setAttachedEvidence] =
    useState<CommitmentEvidenceResponse | null>(null);
  const [advancedToolsOpen, setAdvancedToolsOpen] = useState(false);
  const handoffSession = (
    operation.sessions ?? []
  ).reduce<CarrierSessionResponse | null>(
    (selected, candidate) =>
      selected === null ||
      candidate.carrier.deterministic_rank < selected.carrier.deterministic_rank
        ? candidate
        : selected,
    null,
  );
  const handoffViewModel: HumanHandoffViewModel | null = handoffSession
    ? {
        callId: handoffSession.call_id,
        callStatus: handoffSession.state,
        coordinatorDestinationLabel: "Demo coordinator",
        mandate: {
          allowedConditions: operation.active_mandate.allowed_conditions ?? [],
          currency: operation.active_mandate.currency,
          escalationConditions:
            operation.active_mandate.escalation_conditions ?? [],
          maximumAmountMinor: operation.active_mandate.maximum_amount_minor,
          pickupEnd: operation.active_mandate.pickup_window.end_date,
          pickupStart: operation.active_mandate.pickup_window.start_date,
          version: operation.active_mandate.version,
        },
        quotes: (operation.quotes ?? [])
          .map((quote) => {
            const session = operation.sessions?.find(
              (candidate) => candidate.call_id === quote.call_id,
            );
            const comparison = audit?.quote_comparison.find(
              (candidate) => candidate.quote_id === quote.quote_id,
            );
            return {
              amountMinor: quote.terms.amount_minor,
              carrierLabel:
                session?.carrier.display_name ?? "Synthetic carrier",
              conditions: quote.terms.conditions ?? [],
              currency: quote.terms.currency,
              eligibility: quote.eligibility,
              rank: session?.carrier.deterministic_rank ?? 999,
              selected: comparison?.selected ?? false,
            };
          })
          .toSorted((left, right) => left.rank - right.rank),
        brief: (() => {
          const brief = audit?.briefs.find(
            (candidate) => candidate.call_id === handoffSession.call_id,
          );
          return brief
            ? {
                changes: brief.changes ?? [],
                facts: brief.facts ?? [],
                objections: brief.objections ?? [],
                unresolvedItems: brief.unresolved_items ?? [],
              }
            : null;
        })(),
      }
    : null;

  if (surface === "sessions") {
    return (
      <div className="space-y-5">
        <OutboundCallControl operation={operation} />

        <details
          className="group rounded-xl border border-border bg-card"
          onToggle={(event) => setAdvancedToolsOpen(event.currentTarget.open)}
        >
          <summary className="cursor-pointer list-none px-4 py-3 font-heading text-sm font-medium text-foreground marker:content-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 [&::-webkit-details-marker]:hidden">
            <span className="flex items-center justify-between gap-3">
              More Session Tools
              <span
                aria-hidden="true"
                className="text-muted-foreground transition-transform group-open:rotate-45 motion-reduce:transition-none"
              >
                +
              </span>
            </span>
          </summary>
          {advancedToolsOpen ? (
            <div className="space-y-6 border-t border-border p-4">
              <p className="text-sm text-muted-foreground">
                Use these tools only when you need browser voice, typed
                negotiation, handoff controls, or detailed session evidence.
              </p>

              {handoffViewModel ? (
                <HumanHandoffControl viewModel={handoffViewModel} />
              ) : null}

              <BrowserVoiceExperience
                operation={operation}
                audit={audit}
                attachedEvidence={attachedEvidence}
                refreshAuthoritativeState={onStateChanged}
              />

              <div className="grid gap-5 xl:grid-cols-2">
                <StartNegotiationControl
                  operation={operation}
                  onStateChanged={onStateChanged}
                />
                <QuoteControl
                  key={operation.operation_version}
                  operation={operation}
                  onStateChanged={onStateChanged}
                />
              </div>

              <SessionsView operation={operation} />
            </div>
          ) : null}
        </details>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <OutboundCallControl operation={operation} />

      {handoffViewModel ? (
        <HumanHandoffControl viewModel={handoffViewModel} />
      ) : null}

      <BrowserVoiceExperience
        operation={operation}
        audit={audit}
        attachedEvidence={attachedEvidence}
        refreshAuthoritativeState={onStateChanged}
      />

      <div className="grid gap-5 xl:grid-cols-2">
        <StartNegotiationControl
          operation={operation}
          onStateChanged={onStateChanged}
        />
        <QuoteControl
          key={operation.operation_version}
          operation={operation}
          onStateChanged={onStateChanged}
        />
      </div>

      <div className="space-y-6">
        <ComparisonView operation={operation} />
        <CommitmentTerminal
          audit={audit}
          auditError={auditError}
          auditPending={auditPending}
          onRetryAudit={onRetryAudit}
          onEvidenceAttached={setAttachedEvidence}
          onStateChanged={onStateChanged}
          operation={operation}
        />
      </div>
    </div>
  );
}

function SimulatedContent({
  snapshot,
  surface,
  onRetry,
}: {
  snapshot: NegotiationExperienceSnapshot;
  surface: NegotiationSurface;
  onRetry: () => void;
}) {
  if (snapshot.mode === "loading") {
    return <LoadingState label={snapshot.announcement} rows={3} />;
  }

  if (snapshot.mode === "error") {
    return (
      <Alert variant="destructive" role="alert">
        <RotateCcw aria-hidden="true" />
        <AlertTitle>{snapshot.error.code.replaceAll("_", " ")}</AlertTitle>
        <AlertDescription className="flex flex-col items-start gap-4">
          <p>{snapshot.error.message}</p>
          {snapshot.retryable ? (
            <Button type="button" variant="outline" onClick={onRetry}>
              Retry simulated read
            </Button>
          ) : null}
        </AlertDescription>
      </Alert>
    );
  }

  return surface === "sessions" ? (
    <SessionsView operation={snapshot.data.operation} />
  ) : (
    <ComparisonView operation={snapshot.data.operation} />
  );
}

function SimulatedPreview({
  initialScenario,
  source,
  surface,
}: {
  initialScenario: DemoScenarioId;
  source: NegotiationExperienceSource;
  surface: NegotiationSurface;
}) {
  const [scenarioId, setScenarioId] = useState(initialScenario);
  const [retrySnapshot, setRetrySnapshot] =
    useState<NegotiationExperienceSnapshot | null>(null);
  const snapshot = retrySnapshot ?? source.read(scenarioId);

  return (
    <section className="space-y-5 rounded-lg border border-dashed border-border p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-heading text-sm font-semibold text-foreground">
              Deterministic fallback preview
            </h2>
            <StatusBadge tone="neutral" label="SIMULATED · NO CONTACT" />
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Diagnostic presentation only. This mode performs no API, database,
            carrier, or provider request and cannot satisfy the live gate.
          </p>
        </div>
        <label className="flex min-w-0 flex-col gap-1.5 text-sm font-medium sm:min-w-56">
          Preview state
          <select
            name="fallback-preview-state"
            value={scenarioId}
            onChange={(event) => {
              setScenarioId(event.target.value as DemoScenarioId);
              setRetrySnapshot(null);
            }}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            {source.scenarios.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <SimulatedContent
        snapshot={snapshot}
        surface={surface}
        onRetry={() => setRetrySnapshot(source.retry(scenarioId))}
      />
      <RealtimeDiagnosticPreview />
    </section>
  );
}

export function NegotiationExperience({
  surface,
  initialScenario = "active-market",
  source = DEMO_SOURCE,
}: NegotiationExperienceProps) {
  const auth = useDemoAuth();
  const handoffOperationId = useCurrentOperationId();
  const lookupLabelId = useId();
  const [operationIdInput, setOperationIdInput] = useState("");
  const [selectedOperationId, setSelectedOperationId] = useState<string | null>(
    null,
  );
  const [showFallback, setShowFallback] = useState(false);
  const operationId = selectedOperationId ?? handoffOperationId ?? "";
  const visibleOperationId = operationIdInput || operationId;

  const operationQuery = useGetOperation(operationId, {
    query: {
      enabled: auth.connected && operationId.length > 0,
      queryKey: [...getGetOperationQueryKey(operationId), auth.revision],
      retry: false,
    },
  });
  const auditQuery = useGetOperationAudit(operationId, undefined, {
    query: {
      enabled:
        auth.connected && operationId.length > 0 && surface === "comparison",
      queryKey: [...getGetOperationAuditQueryKey(operationId), auth.revision],
      retry: false,
    },
  });

  const loadOperation = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = visibleOperationId.trim();
    if (!normalized || !auth.connected) return;
    saveCurrentOperationId(normalized);
    setSelectedOperationId(normalized);
  };

  const refreshOperation = async () => {
    const [operationResult, auditResult] = await Promise.all([
      operationQuery.refetch(),
      surface === "comparison" ? auditQuery.refetch() : Promise.resolve(null),
    ]);
    if (!operationResult.data) {
      throw new Error("Authoritative operation refresh failed");
    }
    return {
      operation: operationResult.data.data,
      audit: auditResult?.data?.data,
    } satisfies AuthoritativeVoiceState;
  };

  return (
    <section aria-labelledby={lookupLabelId} className="space-y-6">
      <DemoAuthControl />

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <form
            onSubmit={loadOperation}
            className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-end"
          >
            <div className="min-w-0 flex-1 space-y-1.5">
              <Label id={lookupLabelId} htmlFor="live-operation-id">
                Live operation ID
              </Label>
              <input
                id="live-operation-id"
                name="live-operation-id"
                value={visibleOperationId}
                onChange={(event) => setOperationIdInput(event.target.value)}
                autoComplete="off"
                spellCheck={false}
                translate="no"
                placeholder="e.g. b5afda8f-…"
                className="h-10 w-full rounded-md border border-input bg-background px-3 font-mono text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              />
            </div>
            <Button
              type="submit"
              disabled={!auth.connected || !visibleOperationId.trim()}
            >
              <Database aria-hidden="true" data-icon="inline-start" />
              Load server state
            </Button>
          </form>
          <div className="flex flex-wrap gap-2">
            {operationId ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => void refreshOperation()}
                disabled={operationQuery.isFetching || auditQuery.isFetching}
              >
                <RefreshCw aria-hidden="true" data-icon="inline-start" />
                Reload
              </Button>
            ) : null}
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowFallback((visible) => !visible)}
            >
              <FlaskConical aria-hidden="true" data-icon="inline-start" />
              {showFallback ? "Hide fallback" : "Open simulated fallback"}
            </Button>
          </div>
        </div>
      </div>

      {!auth.connected ? (
        <Alert role="status">
          <Database aria-hidden="true" />
          <AlertTitle>Live authorization required</AlertTitle>
          <AlertDescription>
            Connect the demo API above. The bearer is not persisted, so a full
            reload requires entering it again.
          </AlertDescription>
        </Alert>
      ) : null}

      {auth.connected && !operationId ? (
        <EmptyState
          icon={Database}
          title="No live operation loaded"
          description="Approve an intake draft or enter an operation ID to reconstruct sessions and quotes from the server."
        />
      ) : null}

      {operationQuery.isPending && operationId && auth.connected ? (
        <LoadingState label="Loading live operation" rows={3} />
      ) : null}

      {auth.connected &&
      (operationQuery.isFetching ||
        (surface === "comparison" && auditQuery.isFetching)) &&
      operationQuery.data ? (
        <Alert role="status">
          <RefreshCw aria-hidden="true" />
          <AlertTitle>Reconnecting to live state</AlertTitle>
          <AlertDescription>
            Previously loaded server data remains visible while operation and
            audit projections are refreshed.
          </AlertDescription>
        </Alert>
      ) : null}

      {auth.connected && operationQuery.isError ? (
        <LiveMutationError
          title="Operation could not be loaded"
          error={operationQuery.error}
          onReconnect={() => void operationQuery.refetch()}
          onRetry={() => void operationQuery.refetch()}
        />
      ) : null}

      {auth.connected && operationQuery.data ? (
        <LiveOperation
          key={operationQuery.data.data.operation_id}
          audit={auditQuery.data?.data}
          auditError={surface === "comparison" ? auditQuery.error : null}
          auditPending={
            surface === "comparison" && auditQuery.isPending && !auditQuery.data
          }
          onRetryAudit={() => void auditQuery.refetch()}
          operation={operationQuery.data.data}
          onStateChanged={refreshOperation}
          surface={surface}
        />
      ) : null}

      {showFallback ? (
        <SimulatedPreview
          initialScenario={initialScenario}
          source={source}
          surface={surface}
        />
      ) : null}
    </section>
  );
}
