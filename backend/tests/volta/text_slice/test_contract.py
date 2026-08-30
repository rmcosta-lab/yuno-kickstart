import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yuno_backend.volta.text_slice as text_slice
from yuno_backend.volta.intake import ExtractionRequest
from yuno_backend.volta.mandates.models import Route
from yuno_backend.volta.text_slice import CreateOperationDraftInput

ROOT = Path(__file__).parents[4]


def test_public_boundary_exports_inputs_projections_and_demo_presets() -> None:
    required = {
        "ApproveOperationInput",
        "AuditProjection",
        "AuditQuoteProjection",
        "BrowserChannel",
        "CommitmentEvidenceNotFound",
        "CommitmentProjection",
        "CreateCommitmentInput",
        "CreateOperationDraftInput",
        "DraftProjection",
        "EscalationResolutionState",
        "EvidenceReservationMismatch",
        "MutationOutcome",
        "NegotiationProjection",
        "NegotiationSummaryProjection",
        "OperationProjection",
        "PreContactEscalationProjection",
        "QuoteTerms",
        "RecordQuoteInput",
        "SessionProjection",
        "StartNegotiationInput",
        "TextNegotiationApplication",
        "create_demo_carrier_catalog",
        "create_demo_evidence_storage",
        "create_demo_text_extractor",
    }
    assert required <= set(text_slice.__all__)
    assert all(hasattr(text_slice, name) for name in text_slice.__all__)


def test_text_slice_has_no_transport_database_or_provider_imports() -> None:
    forbidden = {"fastapi", "pydantic", "sqlalchemy", "asyncpg", "openai", "twilio", "yuno"}
    package = ROOT / "backend/src/yuno_backend/volta/text_slice"
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text())
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert not (imports & forbidden), path.name


def test_demo_presets_own_cargo_and_carrier_ranking() -> None:
    request = ExtractionRequest(
        "Move one 40-foot dry container Thursday from Manzanillo to Guadalajara "
        "for MXN 9,000.",
        "EN_US",
        "volta-text-v1",
    )
    proposal = text_slice.canonical_text_extraction_mapping(request)
    carriers = text_slice.create_demo_carrier_catalog().select(proposal.route)

    assert proposal.cargo_label == "40ft dry container"
    assert [carrier.priority for carrier in carriers] == [1, 2, 3]
    assert [carrier.display_label for carrier in carriers] == [
        "Puerto Azul Drayage",
        "Ruta Norte Intermodal de Occidente",
        "Altamar Logistica Portuaria del Pacifico",
    ]


@pytest.mark.parametrize(
    ("origin", "destination"),
    [
        ("port of Manzanillo", "warehouse in Guadalajara"),
        ("Manzanillo port, Mexico", "Guadalajara distribution center"),
        ("PUERTO DE MANZANILLO", "ZONA INDUSTRIAL, GUADALAJARA"),
    ],
)
def test_demo_catalog_accepts_bounded_canonical_route_wording(
    origin: str, destination: str
) -> None:
    carriers = text_slice.create_demo_carrier_catalog().select(Route(origin, destination))

    assert [carrier.priority for carrier in carriers] == [1, 2, 3]


@pytest.mark.parametrize(
    ("origin", "destination"),
    [
        ("Puerto de Veracruz", "warehouse in Guadalajara"),
        ("port of Manzanillo", "Puebla distribution center"),
        ("Guadalajara", "Manzanillo"),
    ],
)
def test_demo_catalog_still_rejects_different_or_reversed_routes(
    origin: str, destination: str
) -> None:
    carriers = text_slice.create_demo_carrier_catalog().select(Route(origin, destination))

    assert carriers == ()


@pytest.mark.asyncio
async def test_application_supplies_clock_date_to_intake_extraction() -> None:
    class ExtractionCaptured(Exception):
        pass

    class CapturingExtractor:
        request: ExtractionRequest | None = None

        async def extract(self, request: ExtractionRequest) -> None:
            self.request = request
            raise ExtractionCaptured

    class FixedClock:
        def now(self) -> datetime:
            return datetime(2026, 8, 30, 12, tzinfo=UTC)

    extractor = CapturingExtractor()
    application = text_slice.TextNegotiationApplication(
        unit_of_work_factory=lambda: object(),  # type: ignore[arg-type,return-value]
        extractor=extractor,  # type: ignore[arg-type]
        carrier_catalog=object(),  # type: ignore[arg-type]
        clock=FixedClock(),
        id_generator=object(),  # type: ignore[arg-type]
        evidence_storage=object(),  # type: ignore[arg-type]
        extraction_policy_version="intake-v1",
    )

    with pytest.raises(ExtractionCaptured):
        await application.create_operation_draft(
            CreateOperationDraftInput("synthetic prompt", "EN_US", "draft-key-0001")
        )

    assert extractor.request is not None
    assert extractor.request.reference_date.isoformat() == "2026-08-30"
