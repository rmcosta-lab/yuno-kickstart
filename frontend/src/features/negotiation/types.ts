import type { ApiErrorResponse } from "@/lib/api/generated/models/apiErrorResponse";
import type { NegotiationResponse } from "@/lib/api/generated/models/negotiationResponse";
import type { OperationResponse } from "@/lib/api/generated/models/operationResponse";

export type NegotiationSurface = "sessions" | "comparison";

export type DemoScenarioId =
  | "loading"
  | "one-session"
  | "two-sessions"
  | "active-market"
  | "reconnecting"
  | "retryable-error"
  | "no-eligible"
  | "terminal-success"
  | "terminal-failure";

export type NegotiationDataSnapshot = {
  operation: OperationResponse;
  negotiation?: NegotiationResponse;
};

export type NegotiationExperienceSnapshot =
  | {
      mode: "loading";
      announcement: string;
    }
  | {
      mode: "reconnecting";
      announcement: string;
      data: NegotiationDataSnapshot;
    }
  | {
      mode: "ready" | "terminal";
      announcement: string;
      data: NegotiationDataSnapshot;
    }
  | {
      mode: "error";
      announcement: string;
      error: ApiErrorResponse;
      retryable: boolean;
    };

export type NegotiationScenarioOption = {
  id: DemoScenarioId;
  label: string;
  description: string;
};

export interface NegotiationExperienceSource {
  readonly scenarios: readonly NegotiationScenarioOption[];
  read(scenarioId: DemoScenarioId): NegotiationExperienceSnapshot;
  retry(scenarioId: DemoScenarioId): NegotiationExperienceSnapshot;
}
