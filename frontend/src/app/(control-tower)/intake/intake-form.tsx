"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Inbox, Wand2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";

import { useCreateOperationDraft } from "@/lib/api/generated/api";
import {
  RequestedLanguage,
  type ApiErrorResponse,
  type OperationDraftResponse,
} from "@/lib/api/generated/models";
import {
  createOperationDraftFixture,
  INTAKE_TEST_BOUNDARY_ENABLED,
  type IntakeDraftScenario,
} from "@/lib/api/intake-test-boundary";
import { ApiHttpError } from "@/lib/api/volta-fetch";
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
  "Move one 40-foot dry container from the port of Manzanillo to a warehouse in Guadalajara. Pickup within the next three business days, budget ceiling of 45,000 MXN, standard handling conditions.";

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

const SCENARIO_OPTIONS: { value: IntakeDraftScenario; label: string }[] = [
  { value: "approval_eligible", label: "Clean draft (approval-eligible)" },
  { value: "validation_issues", label: "Draft with validation issues" },
  { value: "validation_error", label: "Request validation error (422)" },
];

const LANGUAGE_LABELS: Record<RequestedLanguage, string> = {
  [RequestedLanguage.EN_US]: "English (US)",
  [RequestedLanguage.ES_MX]: "Español (MX)",
};

const scenarioLabel = (value: IntakeDraftScenario) =>
  SCENARIO_OPTIONS.find((option) => option.value === value)?.label ?? value;

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
  const [scenario, setScenario] =
    useState<IntakeDraftScenario>("approval_eligible");
  const [idempotencyKey, setIdempotencyKey] = useState<string>(() =>
    crypto.randomUUID(),
  );
  const [lastAttemptPrompt, setLastAttemptPrompt] = useState<string | null>(
    null,
  );

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
  const boundaryMutation = useMutation<
    OperationDraftResponse,
    ApiHttpError<ApiErrorResponse>,
    IntakeFormValues
  >({
    mutationFn: (values) =>
      createOperationDraftFixture(
        {
          source_prompt: values.source_prompt,
          requested_language: values.requested_language,
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
  const draft: OperationDraftResponse | undefined = INTAKE_TEST_BOUNDARY_ENABLED
    ? boundaryMutation.data
    : generatedMutation.data?.data;

  const onSubmit = (values: IntakeFormValues) => {
    const isRetryOfSamePrompt = lastAttemptPrompt === values.source_prompt;
    const keyForThisAttempt = isRetryOfSamePrompt
      ? idempotencyKey
      : crypto.randomUUID();
    if (!isRetryOfSamePrompt) {
      setIdempotencyKey(keyForThisAttempt);
    }
    setLastAttemptPrompt(values.source_prompt);

    if (INTAKE_TEST_BOUNDARY_ENABLED) {
      boundaryMutation.mutate(values, {
        onSuccess: (response) => {
          if (response.approval_eligible) {
            saveApprovalEligibleDraft(response);
          }
        },
      });
      return;
    }

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
                aria-invalid={Boolean(errors.source_prompt) || undefined}
                aria-describedby="source_prompt-error"
                {...register("source_prompt")}
              />
              <div id="source_prompt-error" className="space-y-1">
                {errors.source_prompt ? (
                  <p className="text-sm text-destructive" role="alert">
                    {errors.source_prompt.message}
                  </p>
                ) : null}
                {fieldIssueMessages(
                  "source_prompt",
                  apiError instanceof ApiHttpError
                    ? apiError.data.field_issues
                    : undefined,
                ).map((issue) => (
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

            {INTAKE_TEST_BOUNDARY_ENABLED ? (
              <div className="space-y-1.5 rounded-lg border border-dashed border-border p-3">
                <Label htmlFor="scenario">
                  Test boundary scenario (no live backend yet)
                </Label>
                <Select
                  value={scenario}
                  onValueChange={(value) =>
                    setScenario(value as IntakeDraftScenario)
                  }
                >
                  <SelectTrigger id="scenario" className="w-full">
                    <SelectValue>
                      {(value: IntakeDraftScenario) => scenarioLabel(value)}
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

            <Button type="submit" disabled={isPending}>
              {isPending ? "Submitting…" : "Submit draft"}
            </Button>
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

              {draft.validation_issues && draft.validation_issues.length > 0 ? (
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
  );
}
