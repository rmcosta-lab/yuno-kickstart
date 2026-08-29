import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GENERATED_ROOT = REPOSITORY_ROOT / "frontend" / "src" / "lib" / "api" / "generated"
ORVAL_CONFIG = REPOSITORY_ROOT / "frontend" / "orval.config.ts"
VOLTA_FETCH = REPOSITORY_ROOT / "frontend" / "src" / "lib" / "api" / "volta-fetch.ts"

POST_OPERATIONS = (
    ("acknowledge_notification", "AcknowledgeNotification"),
    ("approve_operation", "ApproveOperation"),
    ("attach_commitment_evidence", "AttachCommitmentEvidence"),
    ("create_call_brief", "CreateCallBrief"),
    ("create_candidate_commitment", "CreateCandidateCommitment"),
    ("create_escalation", "CreateEscalation"),
    ("create_operation_draft", "CreateOperationDraft"),
    ("create_simulated_recap", "CreateSimulatedRecap"),
    ("record_quote", "RecordQuote"),
    ("replace_mandate", "ReplaceMandate"),
    ("start_inbound_simulation", "StartInboundSimulation"),
    ("start_negotiation", "StartNegotiation"),
)

GET_OPERATIONS = (
    ("get_operation", "GetOperation"),
    ("get_operation_audit", "GetOperationAudit"),
)

MUTATION_HEADER_MODELS = (
    "acknowledgeNotificationHeaders.ts",
    "approveOperationHeaders.ts",
    "attachCommitmentEvidenceHeaders.ts",
    "createCallBriefHeaders.ts",
    "createCandidateCommitmentHeaders.ts",
    "createEscalationHeaders.ts",
    "createOperationDraftHeaders.ts",
    "createSimulatedRecapHeaders.ts",
    "recordQuoteHeaders.ts",
    "replaceMandateHeaders.ts",
    "startInboundSimulationHeaders.ts",
    "startNegotiationHeaders.ts",
)


def test_orval_exposes_required_named_idempotency_headers() -> None:
    generated_api = (GENERATED_ROOT / "api.ts").read_text(encoding="utf-8")

    for filename in MUTATION_HEADER_MODELS:
        content = (GENERATED_ROOT / "models" / filename).read_text(encoding="utf-8")
        model_name = filename.removesuffix(".ts").replace(filename[0], filename[0].upper(), 1)
        assert '"Idempotency-Key": string;' in content
        assert f"headers: {model_name}" in generated_api


def test_orval_exposes_required_version_inputs_in_typed_bodies() -> None:
    approval = (GENERATED_ROOT / "models" / "approveOperationRequest.ts").read_text(
        encoding="utf-8"
    )
    assert "expected_draft_version: number;" in approval

    operation_version_models = (
        "acknowledgeNotificationRequest.ts",
        "createCallBriefRequest.ts",
        "createCommitmentEvidenceRequest.ts",
        "createCommitmentRequest.ts",
        "createEscalationRequest.ts",
        "createQuoteRequest.ts",
        "createSimulatedRecapRequest.ts",
        "replaceMandateRequest.ts",
        "startInboundSimulationRequest.ts",
        "startNegotiationRequest.ts",
    )
    for filename in operation_version_models:
        content = (GENERATED_ROOT / "models" / filename).read_text(encoding="utf-8")
        assert "expected_operation_version: number;" in content


def test_orval_configuration_classifies_reads_and_state_changes_explicitly() -> None:
    config = ORVAL_CONFIG.read_text(encoding="utf-8")

    for operation_id, _ in POST_OPERATIONS:
        assert re.search(
            rf"{operation_id}:\s*\{{\s*query:\s*\{{\s*"
            r"useMutation:\s*true,\s*useQuery:\s*false\s*\}",
            config,
        )

    for operation_id, _ in GET_OPERATIONS:
        assert re.search(
            rf"{operation_id}:\s*\{{\s*query:\s*\{{\s*"
            r"useMutation:\s*false,\s*useQuery:\s*true\s*\}",
            config,
        )


def test_orval_generates_queries_only_for_read_operations() -> None:
    generated_api = (GENERATED_ROOT / "api.ts").read_text(encoding="utf-8")

    for _, operation_name in GET_OPERATIONS:
        assert f"get{operation_name}QueryKey" in generated_api
        assert f"get{operation_name}QueryOptions" in generated_api
        assert f"get{operation_name}MutationOptions" not in generated_api


def test_orval_generates_mutations_and_no_query_hooks_for_post_operations() -> None:
    generated_api = (GENERATED_ROOT / "api.ts").read_text(encoding="utf-8")

    for _, operation_name in POST_OPERATIONS:
        assert f"get{operation_name}MutationOptions" in generated_api
        assert f"get{operation_name}QueryKey" not in generated_api
        assert f"get{operation_name}QueryOptions" not in generated_api


def test_volta_fetch_preserves_http_metadata_and_throws_typed_errors() -> None:
    config = ORVAL_CONFIG.read_text(encoding="utf-8")
    transport = VOLTA_FETCH.read_text(encoding="utf-8")

    assert 'path: "./src/lib/api/volta-fetch.ts"' in config
    assert 'name: "voltaFetch"' in config
    assert "forceSuccessResponse: true" in config
    assert "includeHttpResponseReturnType: true" in config

    assert "export type ErrorType<TError> = ApiHttpError<TError>;" in transport
    assert "data: await parseResponseBody(response)" in transport
    assert "headers: response.headers" in transport
    assert "status: response.status" in transport
    assert "if (!response.ok)" in transport
    assert "throw new ApiHttpError<ApiErrorResponse>" in transport
    assert "data: result.data as ApiErrorResponse" in transport


def test_generated_transport_types_preserve_headers_and_safe_api_errors() -> None:
    generated_api = (GENERATED_ROOT / "api.ts").read_text(encoding="utf-8")

    assert 'from "../volta-fetch"' in generated_api
    assert "voltaFetch<createCallBriefResponseSuccess>" in generated_api
    assert "headers: Headers;" in generated_api
    assert "export type CreateCallBriefMutationError = ErrorType<ApiErrorResponse>" in generated_api

    for status in (401, 409, 422, 500, 501):
        assert re.search(
            rf"export type createCallBriefResponse{status}\s*=\s*\{{\s*"
            rf"data:\s*ApiErrorResponse;\s*status:\s*{status};",
            generated_api,
        )
