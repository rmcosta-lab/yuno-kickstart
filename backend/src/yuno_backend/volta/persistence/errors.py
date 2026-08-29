"""Safe persistence errors that never render SQL, values, or driver diagnostics."""

import re
from uuid import UUID

__all__ = ["PersistenceConflict", "PersistenceUnavailable"]

_SAFE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class _SafePersistenceError(RuntimeError):
    def __init__(
        self,
        reason_code: str,
        resource_code: str,
        resource_id: UUID | None = None,
    ) -> None:
        if not _SAFE_CODE.fullmatch(reason_code) or not _SAFE_CODE.fullmatch(resource_code):
            raise ValueError("persistence errors require stable safe codes")
        if resource_id is not None and not isinstance(resource_id, UUID):
            raise TypeError("persistence resource identifiers must be UUID values")
        self.reason_code = reason_code
        self.resource_code = resource_code
        self.resource_id = resource_id
        identifier = "" if resource_id is None else f" id={resource_id}"
        super().__init__(f"persistence {reason_code}: {resource_code}{identifier}")


class PersistenceConflict(_SafePersistenceError):
    """A database constraint rejected otherwise well-formed application state."""


class PersistenceUnavailable(_SafePersistenceError):
    """The database could not complete an expected persistence operation."""
