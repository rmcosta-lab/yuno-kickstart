/**
 * Injected fixture boundary for the intake and mandate screens (Fase 07).
 *
 * The generated `voltaFetch` mutator always performs a real `fetch()`; the
 * `request` option exposed by the generated hooks only merges extra
 * `RequestInit` fields into that same call, it cannot swap the network call
 * itself (see `frontend/src/lib/api/volta-fetch.ts`). So instead of passing
 * a `request` override, this module exports drop-in replacements for the
 * generated `mutationFn`s that resolve/reject with the same generated types
 * without hitting the network. Screens pick between the generated hook and
 * this boundary behind `INTAKE_TEST_BOUNDARY_ENABLED`, so removing the
 * boundary later is a one-line change per screen. See `plan.md` for the
 * recorded deviation from the originally assumed injection mechanism.
 */
import {
  ApiErrorCode,
  RequestedLanguage,
  type ApiErrorResponse,
  type ApproveOperationRequest,
  type CreateOperationDraftRequest,
  type OperationDraftResponse,
  type OperationResponse,
} from "./generated/models";
import { ApiHttpError, type ApiHttpResponse } from "./volta-fetch";

export const INTAKE_TEST_BOUNDARY_ENABLED =
  process.env.NEXT_PUBLIC_INTAKE_USE_TEST_BOUNDARY !== "false";

export type IntakeDraftScenario =
  "approval_eligible" | "validation_issues" | "validation_error";

export type ApprovalScenario =
  "approved" | "stale_draft_version" | "mandate_conflict";

const FIXTURE_LATENCY_MS = 500;
const EXTRACTION_POLICY_VERSION = "policy-2026-08-01";

const wait = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));

let requestSequence = 0;
const nextRequestId = () => {
  requestSequence += 1;
  return `test-boundary-req-${requestSequence.toString().padStart(4, "0")}`;
};

let draftSequence = 0;
const nextDraftId = () => {
  draftSequence += 1;
  return `draft-test-${draftSequence.toString().padStart(4, "0")}`;
};

const throwApiError = (data: ApiErrorResponse, status: number): never => {
  const response: ApiHttpResponse<ApiErrorResponse> = {
    data,
    headers: new Headers({ "content-type": "application/json" }),
    status,
  };
  throw new ApiHttpError<ApiErrorResponse>(response);
};

export const createOperationDraftFixture = async (
  request: CreateOperationDraftRequest,
  scenario: IntakeDraftScenario,
): Promise<OperationDraftResponse> => {
  await wait(FIXTURE_LATENCY_MS);

  if (scenario === "validation_error") {
    return throwApiError(
      {
        code: ApiErrorCode.VALIDATION_ERROR,
        message:
          "The submitted prompt could not be parsed into a drayage request.",
        request_id: nextRequestId(),
        field_issues: [
          {
            field: "source_prompt",
            code: "AMBIGUOUS_PICKUP_DATE",
            message:
              "The requested pickup date could not be determined from the prompt.",
          },
        ],
      },
      422,
    );
  }

  const now = new Date().toISOString();
  const validationIssues =
    scenario === "validation_issues"
      ? [
          {
            field: "proposed_pickup_date",
            message:
              "Pickup date falls on a customs holiday; confirm with the terminal before approval.",
          },
        ]
      : undefined;

  return {
    approval_eligible: scenario !== "validation_issues",
    created_at: now,
    updated_at: now,
    draft_id: nextDraftId(),
    draft_version: 1,
    extraction_policy_version: EXTRACTION_POLICY_VERSION,
    requested_language: request.requested_language ?? RequestedLanguage.EN_US,
    source_prompt: request.source_prompt,
    proposed_route: {
      origin: "Puerto de Manzanillo, Colima",
      destination: "Zona industrial, Guadalajara, Jalisco",
    },
    proposed_pickup_date: "2026-09-02",
    proposed_mandate: {
      currency: "MXN",
      maximum_amount_minor: 4_500_000,
      pickup_window: {
        start_date: "2026-09-02",
        end_date: "2026-09-04",
      },
      allowed_conditions: ["40ft dry container", "Standard handling"],
      escalation_conditions: [
        "No carrier available within budget",
        "Pickup window missed by more than 24 hours",
      ],
    },
    validation_issues: validationIssues,
  };
};

export const approveOperationFixture = async (
  request: ApproveOperationRequest,
  scenario: ApprovalScenario,
): Promise<OperationResponse> => {
  await wait(FIXTURE_LATENCY_MS);

  if (scenario === "stale_draft_version") {
    return throwApiError(
      {
        code: ApiErrorCode.STALE_DRAFT_VERSION,
        message:
          "The draft changed since it was reviewed. Refresh the mandate and approve the latest version.",
        request_id: nextRequestId(),
        current_draft_version: request.expected_draft_version + 1,
        resource_id: request.draft_id,
      },
      409,
    );
  }

  if (scenario === "mandate_conflict") {
    return throwApiError(
      {
        code: ApiErrorCode.MANDATE_CONFLICT,
        message:
          "An active mandate already exists for this operation. Refresh before retrying.",
        request_id: nextRequestId(),
        resource_id: request.draft_id,
      },
      409,
    );
  }

  const now = new Date().toISOString();

  return {
    operation_id: `op-test-${request.draft_id}`,
    operation_version: 1,
    status: "READY",
    cargo_label: "40ft dry container",
    route: {
      origin: "Puerto de Manzanillo, Colima",
      destination: "Zona industrial, Guadalajara, Jalisco",
    },
    created_at: now,
    updated_at: now,
    active_mandate: {
      mandate_id: `mandate-test-${request.draft_id}`,
      version: 1,
      approval_actor: request.approval_actor,
      approved_at: now,
      currency: "MXN",
      maximum_amount_minor: 4_500_000,
      pickup_window: {
        start_date: "2026-09-02",
        end_date: "2026-09-04",
      },
      allowed_conditions: ["40ft dry container", "Standard handling"],
      escalation_conditions: [
        "No carrier available within budget",
        "Pickup window missed by more than 24 hours",
      ],
    },
  };
};
