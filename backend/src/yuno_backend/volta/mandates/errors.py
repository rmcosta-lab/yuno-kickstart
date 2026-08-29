"""Safe public errors for the mandate application boundary."""

from uuid import UUID

__all__ = [
    "DraftNotApprovable",
    "DraftNotFound",
    "InvalidDomainValue",
    "MandateConflict",
    "OperationAlreadyApproved",
    "StaleDraftVersion",
]


class InvalidDomainValue(ValueError):
    """A domain value violates a local, provider-neutral invariant."""

    def __init__(self, field: str, reason_code: str) -> None:
        self.field = field
        self.reason_code = reason_code
        super().__init__(f"invalid domain value: {field} ({reason_code})")


class DraftNotFound(LookupError):
    def __init__(self, draft_id: UUID) -> None:
        self.draft_id = draft_id
        super().__init__(f"draft not found: {draft_id}")


class StaleDraftVersion(RuntimeError):
    def __init__(self, draft_id: UUID, expected_version: int, current_version: int) -> None:
        self.draft_id = draft_id
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__(
            f"stale draft version: {draft_id} "
            f"(expected={expected_version}, current={current_version})"
        )


class DraftNotApprovable(RuntimeError):
    def __init__(self, draft_id: UUID, reason_codes: tuple[str, ...]) -> None:
        self.draft_id = draft_id
        self.reason_codes = reason_codes
        super().__init__(f"draft not approvable: {draft_id} ({','.join(reason_codes)})")


class OperationAlreadyApproved(RuntimeError):
    def __init__(self, draft_id: UUID, operation_id: UUID) -> None:
        self.draft_id = draft_id
        self.operation_id = operation_id
        super().__init__(f"draft already approved: {draft_id} (operation={operation_id})")


class MandateConflict(RuntimeError):
    def __init__(
        self,
        operation_id: UUID,
        mandate_version: int,
        reason_codes: tuple[str, ...],
    ) -> None:
        self.operation_id = operation_id
        self.mandate_version = mandate_version
        self.reason_codes = reason_codes
        super().__init__(
            f"mandate conflict: {operation_id} version={mandate_version} "
            f"({','.join(reason_codes)})"
        )
