from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GENERATED_ROOT = REPOSITORY_ROOT / "frontend" / "src" / "lib" / "api" / "generated"

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
