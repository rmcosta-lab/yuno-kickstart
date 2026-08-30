import ast
from pathlib import Path

import yuno_backend.volta.evidence as evidence

ROOT = Path(__file__).parents[4]


def test_public_exports_are_explicit_and_complete() -> None:
    required = {
        "AgreementEvidence",
        "CallBrief",
        "Recap",
        "RecapDisclosureState",
        "EvidenceRepository",
        "BriefRepository",
        "RecapRepository",
        "EvidenceStorage",
        "RecordEvidenceService",
        "GenerateBriefService",
        "GenerateRecapService",
        "CommitmentNotFound",
        "EvidenceAlreadyRecorded",
        "InvalidCommitmentDisposition",
    }
    assert required <= set(evidence.__all__)
    assert all(hasattr(evidence, name) for name in evidence.__all__)


def test_domain_and_application_modules_have_no_transport_or_database_imports() -> None:
    forbidden = {"fastapi", "pydantic", "sqlalchemy", "asyncpg", "openai", "twilio", "yuno"}
    package = ROOT / "backend/src/yuno_backend/volta/evidence"
    for path in package.rglob("*.py"):
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
