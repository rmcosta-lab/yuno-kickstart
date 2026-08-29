"use client";

import { useMutation } from "@tanstack/react-query";
import { ClipboardList } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useApproveOperation } from "@/lib/api/generated/api";
import {
  ApiErrorCode,
  type ApiErrorResponse,
  type OperationResponse,
} from "@/lib/api/generated/models";
import {
  approveOperationFixture,
  INTAKE_TEST_BOUNDARY_ENABLED,
  type ApprovalScenario,
} from "@/lib/api/intake-test-boundary";
import { ApiHttpError } from "@/lib/api/volta-fetch";
import {
  clearApprovalEligibleDraft,
  useApprovalEligibleDraft,
} from "@/lib/operation-draft-handoff";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { StatusBadge } from "@/components/control-tower/status-badge";

const DEMO_APPROVAL_ACTOR = "demo-coordinator@volta.dev";

const SCENARIO_OPTIONS: { value: ApprovalScenario; label: string }[] = [
  { value: "approved", label: "Approve successfully" },
  { value: "stale_draft_version", label: "Stale draft version (409)" },
  { value: "mandate_conflict", label: "Mandate conflict (409)" },
];

const scenarioLabel = (value: ApprovalScenario) =>
  SCENARIO_OPTIONS.find((option) => option.value === value)?.label ?? value;

const moneyLabel = (amountMinor: number, currency: string) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amountMinor / 100);

export function MandateApproval() {
  const router = useRouter();
  const draft = useApprovalEligibleDraft();
  const [scenario, setScenario] = useState<ApprovalScenario>("approved");
  const [idempotencyKey, setIdempotencyKey] = useState<{
    draftId: string;
    key: string;
  } | null>(null);

  const generatedMutation = useApproveOperation();
  const boundaryMutation = useMutation<
    OperationResponse,
    ApiHttpError<ApiErrorResponse>,
    { draft_id: string; expected_draft_version: number }
  >({
    mutationFn: (variables) =>
      approveOperationFixture(
        {
          approval_actor: DEMO_APPROVAL_ACTOR,
          draft_id: variables.draft_id,
          expected_draft_version: variables.expected_draft_version,
        },
        scenario,
      ),
  });

  const isPending = INTAKE_TEST_BOUNDARY_ENABLED
    ? boundaryMutation.isPending
    : generatedMutation.isPending;
  const isError = INTAKE_TEST_BOUNDARY_ENABLED
    ? boundaryMutation.isError
    : generatedMutation.isError;
  const isSuccess = INTAKE_TEST_BOUNDARY_ENABLED
    ? boundaryMutation.isSuccess
    : generatedMutation.isSuccess;
  const apiError = INTAKE_TEST_BOUNDARY_ENABLED
    ? boundaryMutation.error
    : generatedMutation.error;
  const operation: OperationResponse | undefined = INTAKE_TEST_BOUNDARY_ENABLED
    ? boundaryMutation.data
    : generatedMutation.data?.data;

  const isConflict =
    apiError instanceof ApiHttpError &&
    (apiError.data.code === ApiErrorCode.STALE_DRAFT_VERSION ||
      apiError.data.code === ApiErrorCode.MANDATE_CONFLICT);

  const approve = () => {
    if (!draft) return;
    const keyEntry =
      idempotencyKey?.draftId === draft.draft_id
        ? idempotencyKey
        : { draftId: draft.draft_id, key: crypto.randomUUID() };
    if (keyEntry !== idempotencyKey) {
      setIdempotencyKey(keyEntry);
    }

    if (INTAKE_TEST_BOUNDARY_ENABLED) {
      boundaryMutation.mutate(
        {
          draft_id: draft.draft_id,
          expected_draft_version: draft.draft_version,
        },
        { onSuccess: () => clearApprovalEligibleDraft() },
      );
      return;
    }

    generatedMutation.mutate(
      {
        data: {
          approval_actor: DEMO_APPROVAL_ACTOR,
          draft_id: draft.draft_id,
          expected_draft_version: draft.draft_version,
        },
        headers: { "Idempotency-Key": keyEntry.key },
      },
      { onSuccess: () => clearApprovalEligibleDraft() },
    );
  };

  const startOver = () => {
    clearApprovalEligibleDraft();
    router.push("/intake");
  };

  if (!draft && !isSuccess) {
    return (
      <EmptyState
        icon={ClipboardList}
        title="No approval-eligible draft"
        description="Submit and complete an intake draft first — an approval-eligible draft appears here for review once /intake produces one."
      />
    );
  }

  if (isSuccess && operation) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-sm">{operation.operation_id}</span>
            <StatusBadge tone="success" label={operation.status} />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-foreground">Mandate version</dt>
              <dd className="text-muted-foreground">
                v{operation.active_mandate.version}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Approved by</dt>
              <dd className="text-muted-foreground">
                {operation.active_mandate.approval_actor}
              </dd>
            </div>
          </dl>
          <p className="font-mono text-xs text-muted-foreground">
            {DEMO_APPROVAL_ACTOR} is a demo identity placeholder, not a login
            system.
          </p>
          <Button variant="outline" onClick={startOver}>
            Start a new intake
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-sm">
              {draft!.draft_id} · v{draft!.draft_version}
            </span>
            <StatusBadge tone="pending" label="PENDING APPROVAL" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="font-medium text-foreground">Price cap</dt>
              <dd className="text-muted-foreground">
                {moneyLabel(
                  draft!.proposed_mandate.maximum_amount_minor,
                  draft!.proposed_mandate.currency,
                )}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Pickup window</dt>
              <dd className="text-muted-foreground">
                {draft!.proposed_mandate.pickup_window.start_date} –{" "}
                {draft!.proposed_mandate.pickup_window.end_date}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-foreground">Extraction policy</dt>
              <dd className="font-mono text-xs text-muted-foreground">
                {draft!.extraction_policy_version}
              </dd>
            </div>
          </dl>
          <Separator />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <p className="text-sm font-medium text-foreground">
                Allowed conditions
              </p>
              <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                {(draft!.proposed_mandate.allowed_conditions ?? []).map(
                  (condition) => (
                    <li key={condition}>&bull; {condition}</li>
                  ),
                )}
              </ul>
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">
                Escalation conditions
              </p>
              <ul className="mt-1 space-y-1 text-sm text-muted-foreground">
                {(draft!.proposed_mandate.escalation_conditions ?? []).map(
                  (condition) => (
                    <li key={condition}>&bull; {condition}</li>
                  ),
                )}
              </ul>
            </div>
          </div>
          <p className="font-mono text-xs text-muted-foreground">
            Approval actor: {DEMO_APPROVAL_ACTOR} (demo identity placeholder,
            not a login system)
          </p>
        </CardContent>
      </Card>

      {INTAKE_TEST_BOUNDARY_ENABLED ? (
        <div className="space-y-1.5 rounded-lg border border-dashed border-border p-3">
          <Label htmlFor="approval-scenario">
            Test boundary scenario (no live backend yet)
          </Label>
          <Select
            value={scenario}
            onValueChange={(value) => setScenario(value as ApprovalScenario)}
          >
            <SelectTrigger id="approval-scenario" className="w-full">
              <SelectValue>
                {(value: ApprovalScenario) => scenarioLabel(value)}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {SCENARIO_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      ) : null}

      {isPending ? <LoadingState label="Approving operation" /> : null}

      {!isPending && isError ? (
        <div className="space-y-3">
          <ErrorState
            title={isConflict ? "Mandate is out of date" : "Approval failed"}
            description={
              apiError instanceof ApiHttpError
                ? apiError.data.message
                : "The mandate service could not be reached."
            }
          />
          {isConflict ? (
            <Button variant="outline" onClick={startOver}>
              Return to intake for a fresh draft
            </Button>
          ) : (
            <Button variant="outline" onClick={approve}>
              Retry approval
            </Button>
          )}
        </div>
      ) : null}

      {!isPending ? <Button onClick={approve}>Approve mandate</Button> : null}

      <p className="text-sm text-muted-foreground">
        Approving creates the operation and its first immutable mandate version.
        This action does not happen automatically — a coordinator must click
        Approve.
      </p>

      <Link
        href="/intake"
        className="inline-block text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
      >
        Back to intake
      </Link>
    </div>
  );
}
