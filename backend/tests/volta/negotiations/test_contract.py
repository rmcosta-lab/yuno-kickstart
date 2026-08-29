import ast
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
import yuno_backend.volta.negotiations as negotiations
from yuno_backend.volta.mandates import InvalidDomainValue
from yuno_backend.volta.negotiations import (
    CallSessionNotFound,
    CarrierSessionMismatch,
    IdempotencyConflict,
    InvalidNegotiationTransition,
    MutationIdempotency,
    NegotiationAlreadyStarted,
    OperationNotFound,
    QuoteExpired,
    QuoteNotBestCandidate,
    QuoteNotEligible,
    QuoteNotFound,
    StaleMandateVersion,
    StaleOperationVersion,
)

ROOT = Path(__file__).parents[4]


def test_public_exports_are_explicit_and_complete() -> None:
    required = {
        "CarrierProfile",
        "CarrierSession",
        "Negotiation",
        "Quote",
        "QuoteTerms",
        "QuoteComparison",
        "Commitment",
        "PreContactEscalation",
        "StartNegotiationCommand",
        "RecordQuoteCommand",
        "CreateCommitmentCommand",
        "StartNegotiationService",
        "RecordQuoteService",
        "QuoteComparisonService",
        "CreateCommitmentService",
    }
    assert required <= set(negotiations.__all__)
    assert all(hasattr(negotiations, name) for name in negotiations.__all__)


def test_domain_and_application_modules_have_no_transport_or_database_imports() -> None:
    forbidden = {"fastapi", "pydantic", "sqlalchemy", "asyncpg", "openai", "twilio", "yuno"}
    package = ROOT / "backend/src/yuno_backend/volta/negotiations"
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


@pytest.mark.parametrize(
    "key",
    ["x" * 7, "x" * 129, "contains\ncontrol", "contains\tcontrol", "não-ascii"],
)
def test_idempotency_value_rejects_non_contract_keys(key: str) -> None:
    with pytest.raises(InvalidDomainValue):
        MutationIdempotency(
            UUID(int=1),
            "record_quote",
            key,
            "a" * 64,
            UUID(int=2),
            datetime(2026, 9, 1, tzinfo=UTC),
        )


def test_safe_errors_expose_only_codes_and_uuid_version_context() -> None:
    identifier = UUID(int=1)
    errors = (
        OperationNotFound(identifier),
        StaleOperationVersion(identifier, 1, 2),
        StaleMandateVersion(identifier, 1, 2),
        NegotiationAlreadyStarted(identifier, UUID(int=2)),
        CallSessionNotFound(identifier),
        CarrierSessionMismatch(identifier, UUID(int=2)),
        QuoteNotFound(identifier),
        QuoteNotEligible(identifier, ("safe_reason",)),
        QuoteExpired(identifier),
        QuoteNotBestCandidate(identifier, UUID(int=2)),
        InvalidNegotiationTransition(identifier, "safe_reason"),
        IdempotencyConflict(identifier, "record_quote", "sensitive-key-value"),
    )
    for error in errors:
        assert error.code.isascii() and error.code.replace("_", "").islower()
        rendered = str(error)
        assert "sensitive-key-value" not in rendered
        assert "SELECT" not in rendered


@pytest.mark.parametrize("key", ["x" * 8, "x" * 128, " AbCd  X"])
def test_valid_idempotency_boundaries_and_whitespace_case_are_preserved_exactly(
    key: str,
) -> None:
    record = MutationIdempotency(
        UUID(int=1),
        "record_quote",
        key,
        "a" * 64,
        UUID(int=2),
        datetime(2026, 9, 1, tzinfo=UTC),
    )
    assert record.key == key
