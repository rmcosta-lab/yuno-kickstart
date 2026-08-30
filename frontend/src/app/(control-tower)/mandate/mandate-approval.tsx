"use client";

import { ClipboardList } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useApproveOperation } from "@/lib/api/generated/api";
import { ApiErrorCode } from "@/lib/api/generated/models";
import { ApiHttpError } from "@/lib/api/volta-fetch";
import { DemoAuthControl, useDemoAuth } from "@/lib/demo-auth";
import { saveCurrentOperationId } from "@/lib/live-operation-handoff";
import {
  clearApprovalEligibleDraft,
  useApprovalEligibleDraft,
} from "@/lib/operation-draft-handoff";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { StatusBadge } from "@/components/control-tower/status-badge";

const DEMO_APPROVAL_ACTOR = "demo-coordinator@volta.dev";

const moneyLabel = (amountMinor: number, currency: string) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amountMinor / 100);

export function MandateApproval() {
  const router = useRouter();
  const auth = useDemoAuth();
  const draft = useApprovalEligibleDraft();
  const [idempotencyKey, setIdempotencyKey] = useState<{
    draftId: string;
    key: string;
  } | null>(null);

  const generatedMutation = useApproveOperation();
  const {
    data,
    error: apiError,
    isError,
    isPending,
    isSuccess,
  } = generatedMutation;
  const operation = data?.data;

  const isConflict =
    apiError instanceof ApiHttpError &&
    (apiError.data.code === ApiErrorCode.STALE_DRAFT_VERSION ||
      apiError.data.code === ApiErrorCode.MANDATE_CONFLICT);

  const approve = () => {
    if (!draft || !auth.connected) return;
    const keyEntry =
      idempotencyKey?.draftId === draft.draft_id
        ? idempotencyKey
        : { draftId: draft.draft_id, key: crypto.randomUUID() };
    if (keyEntry !== idempotencyKey) {
      setIdempotencyKey(keyEntry);
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
      {
        onSuccess: (response) => {
          saveCurrentOperationId(response.data.operation_id);
          clearApprovalEligibleDraft();
        },
      },
    );
  };

  const startOver = () => {
    clearApprovalEligibleDraft();
    router.push("/intake");
  };

  if (!draft && !isSuccess) {
    return (
      <div className="space-y-6">
        <DemoAuthControl />
        <EmptyState
          icon={ClipboardList}
          title="No approval-eligible draft"
          description="Submit and complete an intake draft first — an approval-eligible draft appears here for review once /intake produces one."
        />
      </div>
    );
  }

  if (isSuccess && operation) {
    return (
      <div className="space-y-6">
        <DemoAuthControl />
        <Card>
          <CardHeader>
            <CardTitle className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-sm">
                {operation.operation_id}
              </span>
              <StatusBadge tone="success" label={operation.status} />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.headers.get("Idempotency-Replayed")?.toLowerCase() ===
            "true" ? (
              <p className="text-sm text-muted-foreground" role="status">
                The server replayed the original approval result without
                creating another operation or mandate.
              </p>
            ) : null}
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
            <div className="flex flex-wrap gap-3">
              <Link href="/sessions" className={buttonVariants()}>
                Open carrier sessions
              </Link>
              <Button variant="outline" onClick={startOver}>
                Start a new intake
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <DemoAuthControl />
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

      {!isPending ? (
        <Button onClick={approve} disabled={!auth.connected}>
          Approve mandate
        </Button>
      ) : null}

      {!auth.connected ? (
        <p className="text-sm text-muted-foreground" role="status">
          Connect the live demo API before approving.
        </p>
      ) : null}

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
