"use client";

import { FlaskConical } from "lucide-react";
import { useId, useState } from "react";

import { StatusBadge } from "@/components/control-tower/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

import {
  REALTIME_DIAGNOSTIC_SCENARIOS,
  runRealtimeDiagnosticScenario,
  type RealtimeDiagnosticScenarioId,
} from "./diagnostic-fixtures";

export function RealtimeDiagnosticPreview() {
  const selectId = useId();
  const [scenario, setScenario] =
    useState<RealtimeDiagnosticScenarioId>("malformed");
  const [result, setResult] = useState("Choose a scenario and run it locally.");
  const [running, setRunning] = useState(false);

  const run = async () => {
    setRunning(true);
    try {
      setResult(await runRealtimeDiagnosticScenario(scenario));
    } finally {
      setRunning(false);
    }
  };

  return (
    <Alert>
      <FlaskConical aria-hidden="true" />
      <AlertTitle className="flex flex-wrap items-center gap-2">
        Voice boundary diagnostics
        <StatusBadge tone="neutral" label="LOCAL · NO NETWORK" />
      </AlertTitle>
      <AlertDescription className="space-y-3">
        <p>
          Credential-free parser and dispatcher checks. They never request a
          microphone, provider session, API mutation, or fake provider success.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label
            htmlFor={selectId}
            className="flex min-w-0 flex-1 flex-col gap-1.5 font-medium"
          >
            Diagnostic scenario
            <select
              id={selectId}
              name="voice-diagnostic-scenario"
              value={scenario}
              onChange={(event) => {
                setScenario(event.target.value as RealtimeDiagnosticScenarioId);
                setResult("Ready to run locally.");
              }}
              className="h-10 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              {REALTIME_DIAGNOSTIC_SCENARIOS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <Button
            type="button"
            variant="outline"
            onClick={() => void run()}
            disabled={running}
          >
            {running ? "Running…" : "Run local check"}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          {
            REALTIME_DIAGNOSTIC_SCENARIOS.find(
              (option) => option.id === scenario,
            )?.description
          }
        </p>
        <p className="font-mono text-xs" role="status" aria-live="polite">
          {result}
        </p>
      </AlertDescription>
    </Alert>
  );
}
