"use client";

import { ExternalLink, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useGetHealth } from "@/lib/api/generated/api";

type HealthExperienceProps = {
  apiDocsUrl: string;
};

type HealthState = "checking" | "ready" | "unavailable";

const stateLabels: Record<HealthState, string> = {
  checking: "Checking",
  ready: "Ready",
  unavailable: "Unavailable",
};

export function HealthExperience({ apiDocsUrl }: HealthExperienceProps) {
  const { isError, isFetching, isPending, isSuccess, refetch } = useGetHealth({
    query: {
      select: (response) => {
        if (response.data.status !== "ok") {
          throw new Error(
            "The API health response did not match its contract.",
          );
        }

        return response.data;
      },
    },
  });

  const state: HealthState =
    isFetching || isPending
      ? "checking"
      : isError
        ? "unavailable"
        : isSuccess
          ? "ready"
          : "checking";

  return (
    <>
      <div className="hero-actions font-mono">
        <Button
          className="min-w-52"
          size="lg"
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
          aria-describedby="api-health-status"
        >
          Check API
          <RefreshCw
            data-icon="inline-end"
            className={
              isFetching ? "animate-spin motion-reduce:animate-none" : ""
            }
          />
        </Button>
        <Button
          className="min-w-56"
          variant="outline"
          size="lg"
          nativeButton={false}
          render={
            <a href={apiDocsUrl} target="_blank" rel="noreferrer">
              Open API docs
              <ExternalLink data-icon="inline-end" />
            </a>
          }
        />
      </div>

      <aside className="health-panel" aria-labelledby="api-health-title">
        <h2 className="health-title" id="api-health-title">
          API health
        </h2>
        <div className="health-status-row">
          <div className="signal-orbit" data-state={state} aria-hidden="true">
            <span className="signal-ring signal-ring-outer" />
            <span className="signal-ring signal-ring-middle" />
            <span className="signal-ring signal-ring-inner" />
            <span className="signal-core" />
          </div>
          <p
            className="health-state"
            data-state={state}
            id="api-health-status"
            role="status"
            aria-live="polite"
          >
            {stateLabels[state]}
          </p>
        </div>
      </aside>
    </>
  );
}
