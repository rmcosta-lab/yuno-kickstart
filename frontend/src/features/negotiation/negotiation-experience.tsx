"use client";

import { useId, useState } from "react";
import { RefreshCw, RotateCcw } from "lucide-react";

import { LoadingState } from "@/components/control-tower/loading-state";
import { StatusBadge } from "@/components/control-tower/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

import { createDemoNegotiationExperienceSource } from "./demo-source";
import { ComparisonView, SessionsView } from "./presentation";
import type {
  DemoScenarioId,
  NegotiationExperienceSnapshot,
  NegotiationExperienceSource,
  NegotiationSurface,
} from "./types";

const DEMO_SOURCE = createDemoNegotiationExperienceSource();

type NegotiationExperienceProps = {
  surface: NegotiationSurface;
  initialScenario?: DemoScenarioId;
  source?: NegotiationExperienceSource;
};

function ExperienceContent({
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
          <p className="font-mono text-xs">
            Request {snapshot.error.request_id}
          </p>
          {snapshot.retryable ? (
            <Button type="button" variant="outline" onClick={onRetry}>
              <RefreshCw aria-hidden="true" data-icon="inline-start" />
              Retry simulated read
            </Button>
          ) : null}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {snapshot.mode === "reconnecting" ? (
        <Alert role="status">
          <RefreshCw aria-hidden="true" />
          <AlertTitle>Reconnecting to simulated data</AlertTitle>
          <AlertDescription>
            The last conforming response remains visible. No API or carrier
            request is sent.
          </AlertDescription>
        </Alert>
      ) : null}
      {surface === "sessions" ? (
        <SessionsView operation={snapshot.data.operation} />
      ) : (
        <ComparisonView operation={snapshot.data.operation} />
      )}
    </div>
  );
}

export function NegotiationExperience({
  surface,
  initialScenario = "active-market",
  source = DEMO_SOURCE,
}: NegotiationExperienceProps) {
  const [scenarioId, setScenarioId] = useState<DemoScenarioId>(initialScenario);
  const [retrySnapshot, setRetrySnapshot] =
    useState<NegotiationExperienceSnapshot | null>(null);
  const scenarioLabelId = useId();
  const snapshot = retrySnapshot ?? source.read(scenarioId);
  const selectedScenario = source.scenarios.find(
    (scenario) => scenario.id === scenarioId,
  );

  return (
    <section aria-labelledby={scenarioLabelId} className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2
              id={scenarioLabelId}
              className="font-heading text-sm font-semibold text-foreground"
            >
              Deterministic scenario
            </h2>
            <StatusBadge tone="neutral" label="SIMULATED · NO CONTACT" />
          </div>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            {selectedScenario?.description}
          </p>
        </div>
        <label className="flex min-w-0 flex-col gap-1.5 font-mono text-xs font-medium text-foreground sm:min-w-56">
          Preview state
          <select
            value={scenarioId}
            onChange={(event) => {
              setScenarioId(event.target.value as DemoScenarioId);
              setRetrySnapshot(null);
            }}
            className="h-10 w-full rounded-md border border-input bg-background px-3 font-sans text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            {source.scenarios.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p
        className="sr-only"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {snapshot.announcement}
      </p>

      <ExperienceContent
        snapshot={snapshot}
        surface={surface}
        onRetry={() => setRetrySnapshot(source.retry(scenarioId))}
      />
    </section>
  );
}
