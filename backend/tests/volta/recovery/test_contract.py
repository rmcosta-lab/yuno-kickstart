import ast
from pathlib import Path

import yuno_backend.volta.recovery as recovery

ROOT = Path(__file__).parents[4]


def test_public_exports_are_explicit_and_complete() -> None:
    required = {
        "RecoveryAttempt",
        "RecoveryOutcome",
        "PostContactEscalation",
        "Notification",
        "EscalationContext",
        "RecoveryDecisionState",
        "RecoveryDecision",
        "ReplaceMandateCommand",
        "CreateEscalationCommand",
        "AcknowledgeNotificationCommand",
        "SimulateInboundRecoveryCommand",
        "ResumeAfterEscalationCommand",
        "RecoveryAttemptRepository",
        "PostContactEscalationRepository",
        "NotificationRepository",
        "OperationUnitOfWork",
        "SimulateInboundRecoveryService",
        "ResumeAfterEscalationService",
        "ReplaceMandateService",
        "CreateEscalationService",
        "AcknowledgeNotificationService",
        "CommitmentNotFound",
        "EvidenceAlreadyRecorded",
        "InvalidCommitmentDisposition",
        "OperationBlockedByEscalation",
        "MandateVersionNotAdvanced",
        "StaleOperationVersion",
        "NotificationNotFound",
        "NotificationAlreadyAcknowledged",
        "EscalationAlreadyResolved",
        "EscalationContextConflict",
    }
    assert required <= set(recovery.__all__)
    assert all(hasattr(recovery, name) for name in recovery.__all__)


def test_domain_and_application_modules_have_no_transport_or_database_imports() -> None:
    forbidden = {"fastapi", "pydantic", "sqlalchemy", "asyncpg", "openai", "twilio", "yuno"}
    package = ROOT / "backend/src/yuno_backend/volta/recovery"
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
