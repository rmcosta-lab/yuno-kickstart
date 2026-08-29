import ast
from pathlib import Path

import yuno_backend.volta.mandates as mandates


def test_public_surface_matches_phase_contract() -> None:
    expected = {
        "ApproveOperationCommand",
        "ApproveOperationService",
        "CheckMandateCommand",
        "Clock",
        "CreateIntakeDraftCommand",
        "CreateIntakeDraftService",
        "DraftNotApprovable",
        "DraftNotFound",
        "DraftValidationIssue",
        "IdGenerator",
        "IntakeDraft",
        "IntakeDraftRepository",
        "InvalidDomainValue",
        "Mandate",
        "MandateAction",
        "MandateConflict",
        "MandateDecision",
        "MandatePolicy",
        "MandateProposal",
        "Money",
        "Operation",
        "OperationAlreadyApproved",
        "OperationProposal",
        "OperationRepository",
        "OperationUnitOfWork",
        "PickupWindow",
        "Route",
        "StaleDraftVersion",
    }
    assert set(mandates.__all__) == expected


def test_each_public_module_exports_only_its_accepted_contract() -> None:
    from yuno_backend.volta.mandates import commands, errors, models, repositories, services

    assert set(models.__all__) == {
        "DraftValidationIssue",
        "IntakeDraft",
        "Mandate",
        "MandateAction",
        "MandateDecision",
        "MandateProposal",
        "Money",
        "Operation",
        "OperationProposal",
        "PickupWindow",
        "Route",
    }
    assert set(commands.__all__) == {
        "ApproveOperationCommand",
        "CheckMandateCommand",
        "CreateIntakeDraftCommand",
    }
    assert set(services.__all__) == {
        "ApproveOperationService",
        "CreateIntakeDraftService",
        "MandatePolicy",
    }
    assert set(repositories.__all__) == {
        "Clock",
        "IdGenerator",
        "IntakeDraftRepository",
        "OperationRepository",
        "OperationUnitOfWork",
    }
    assert set(errors.__all__) == {
        "DraftNotApprovable",
        "DraftNotFound",
        "InvalidDomainValue",
        "MandateConflict",
        "OperationAlreadyApproved",
        "StaleDraftVersion",
    }


def test_volta_core_has_no_transport_persistence_or_provider_imports() -> None:
    source_root = Path(__file__).parents[4] / "src" / "yuno_backend" / "volta"
    forbidden = ("fastapi", "pydantic", "sqlalchemy", "api", "database", "integrations")
    imported: list[str] = []
    for source_file in source_root.rglob("*.py"):
        tree = ast.parse(source_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
    assert not [name for name in imported if name.split(".")[0] in forbidden]
