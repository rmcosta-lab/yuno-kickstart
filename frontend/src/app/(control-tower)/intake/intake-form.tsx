"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Inbox, Wand2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { useCreateOperationDraft } from "@/lib/api/generated/api";
import { RequestedLanguage } from "@/lib/api/generated/models";
import { ApiHttpError } from "@/lib/api/volta-fetch";
import { DemoAuthControl, useDemoAuth } from "@/lib/demo-auth";
import { saveApprovalEligibleDraft } from "@/lib/operation-draft-handoff";
import { Button, buttonVariants } from "@/components/ui/button";
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
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/control-tower/empty-state";
import { ErrorState } from "@/components/control-tower/error-state";
import { LoadingState } from "@/components/control-tower/loading-state";
import { StatusBadge } from "@/components/control-tower/status-badge";

const CANONICAL_PROMPT =
  "Find ground transport for Thursday from the port of Manzanillo to our warehouse in Guadalajara for at most MXN 9,000. One 40-foot dry container, standard handling conditions.";

const intakeFormSchema = z.object({
  source_prompt: z
    .string()
    .min(1, "Enter a drayage request.")
    .max(10000, "Keep the prompt under 10,000 characters."),
  requested_language: z.enum([
    RequestedLanguage.EN_US,
    RequestedLanguage.ES_MX,
  ]),
});

type IntakeFormValues = z.infer<typeof intakeFormSchema>;

const LANGUAGE_LABELS: Record<RequestedLanguage, string> = {
  [RequestedLanguage.EN_US]: "English (US)",
  [RequestedLanguage.ES_MX]: "Español (MX)",
};

const moneyLabel = (amountMinor: number, currency: string) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amountMinor / 100);

function fieldIssueMessages(
  field: string,
  issues?: readonly { field: string; message: string }[] | null,
) {
  return (issues ?? []).filter((issue) => issue.field === field);
}

export function IntakeForm() {
  const auth = useDemoAuth();
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() =>
    crypto.randomUUID(),
  );
  const [lastAttempt, setLastAttempt] = useState<IntakeFormValues | null>(null);

  const {
    control,
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<IntakeFormValues>({
    resolver: zodResolver(intakeFormSchema),
    defaultValues: {
      source_prompt: "",
      requested_language: RequestedLanguage.EN_US,
    },
  });

  const generatedMutation = useCreateOperationDraft();
  const {
    data,
    error: apiError,
    isError,
    isPending,
    isSuccess,
  } = generatedMutation;
  const draft = data?.data;

  const sourcePromptServerIssues = fieldIssueMessages(
    "source_prompt",
    apiError instanceof ApiHttpError ? apiError.data.field_issues : undefined,
  );

  const onSubmit = (values: IntakeFormValues) => {
    if (!auth.connected) return;

    const isRetryOfUnsettledAttempt =
      !isSuccess &&
      lastAttempt !== null &&
      lastAttempt.source_prompt === values.source_prompt &&
      lastAttempt.requested_language === values.requested_language;
    const keyForThisAttempt = isRetryOfUnsettledAttempt
      ? idempotencyKey
      : crypto.randomUUID();
    if (!isRetryOfUnsettledAttempt) {
      setIdempotencyKey(keyForThisAttempt);
    }
    setLastAttempt(values);

    generatedMutation.mutate(
      {
        data: values,
        headers: { "Idempotency-Key": keyForThisAttempt },
      },
      {
        onSuccess: (response) => {
          if (response.data.approval_eligible) {
            saveApprovalEligibleDraft(response.data);
          }
        },
      },
    );
  };

  const submitForm = handleSubmit(onSubmit);

  return (
    <div className="space-y-6">
      <DemoAuthControl />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Submit a drayage request</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={submitForm} noValidate className="space-y-4">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="source_prompt">Source prompt</Label>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      setValue("source_prompt", CANONICAL_PROMPT, {
                        shouldValidate: true,
                      })
                    }
                  >
                    <Wand2 data-icon="inline-start" aria-hidden="true" />
                    Use canonical prompt
                  </Button>
                </div>
                <Textarea
                  id="source_prompt"
                  rows={6}
                  aria-invalid={
                    Boolean(errors.source_prompt) ||
                    sourcePromptServerIssues.length > 0 ||
                    undefined
                  }
                  aria-describedby="source_prompt-error"
                  {...register("source_prompt")}
                />
                <div id="source_prompt-error" className="space-y-1">
                  {errors.source_prompt ? (
                    <p className="text-sm text-destructive" role="alert">
                      {errors.source_prompt.message}
                    </p>
                  ) : null}
                  {sourcePromptServerIssues.map((issue) => (
                    <p
                      key={issue.message}
                      className="text-sm text-destructive"
                      role="alert"
                    >
                      {issue.message}
                    </p>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="requested_language">Requested language</Label>
                <Controller
                  control={control}
                  name="requested_language"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="requested_language">
                        <SelectValue>
                          {(value: RequestedLanguage) => LANGUAGE_LABELS[value]}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={RequestedLanguage.EN_US}>
                          English (US)
                        </SelectItem>
                        <SelectItem value={RequestedLanguage.ES_MX}>
                          Español (MX)
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </div>

              <Button type="submit" disabled={isPending || !auth.connected}>
                {isPending ? "Submitting…" : "Submit draft"}
              </Button>
              {!auth.connected ? (
                <p className="text-sm text-muted-foreground" role="status">
                  Connect the live demo API before submitting.
                </p>
              ) : null}
            </form>
          </CardContent>
        </Card>

        <div>
          {isPending ? <LoadingState label="Submitting intake draft" /> : null}

          {!isPending && isError ? (
            <div className="space-y-3">
              <ErrorState
                title="Draft could not be created"
                description={
                  apiError instanceof ApiHttpError
                    ? apiError.data.message
                    : "The extraction policy could not process the submitted prompt."
                }
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => submitForm()}
              >
                Retry submission
              </Button>
            </div>
          ) : null}

          {!isPending && !isError && !isSuccess ? (
            <EmptyState
              icon={Inbox}
              title="No draft submitted yet"
              description="Submit a canonical drayage prompt to see the extracted route, pickup window, and proposed mandate."
            />
          ) : null}

          {!isPending && isSuccess && draft ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-mono text-sm">{draft.draft_id}</span>
                  <StatusBadge
                    tone={draft.approval_eligible ? "success" : "pending"}
                    label={
                      draft.approval_eligible
                        ? "APPROVAL ELIGIBLE"
                        : "NEEDS REVIEW"
                    }
                  />
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {data.headers.get("Idempotency-Replayed")?.toLowerCase() ===
                "true" ? (
                  <p className="text-sm text-muted-foreground" role="status">
                    This is the durable result of an idempotent retry; no second
                    draft was created.
                  </p>
                ) : null}
                <p className="text-sm text-pretty text-foreground">
                  &ldquo;{draft.source_prompt}&rdquo;
                </p>
                <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="font-medium text-foreground">
                      Extraction policy
                    </dt>
                    <dd className="font-mono text-xs text-muted-foreground">
                      {draft.extraction_policy_version} · draft v
                      {draft.draft_version}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-foreground">Route</dt>
                    <dd className="text-muted-foreground">
                      {draft.proposed_route.origin} →{" "}
                      {draft.proposed_route.destination}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-foreground">Pickup date</dt>
                    <dd className="text-muted-foreground">
                      {draft.proposed_pickup_date}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-foreground">Price cap</dt>
                    <dd className="text-muted-foreground">
                      {moneyLabel(
                        draft.proposed_mandate.maximum_amount_minor,
                        draft.proposed_mandate.currency,
                      )}
                    </dd>
                  </div>
                </dl>

                {draft.validation_issues &&
                draft.validation_issues.length > 0 ? (
                  <>
                    <Separator />
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-foreground">
                        Validation issues
                      </p>
                      <ul className="space-y-1">
                        {draft.validation_issues.map((issue) => (
                          <li
                            key={`${issue.field}-${issue.message}`}
                            className="text-sm text-destructive"
                          >
                            <span className="font-mono text-xs">
                              {issue.field}:
                            </span>{" "}
                            {issue.message}
                          </li>
                        ))}
                      </ul>
                      <p className="text-sm text-muted-foreground">
                        Edit the prompt above and resubmit to resolve these
                        issues.
                      </p>
                    </div>
                  </>
                ) : null}

                {draft.approval_eligible ? (
                  <Link href="/mandate" className={buttonVariants()}>
                    Continue to mandate review
                    <ArrowRight data-icon="inline-end" aria-hidden="true" />
                  </Link>
                ) : null}
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
