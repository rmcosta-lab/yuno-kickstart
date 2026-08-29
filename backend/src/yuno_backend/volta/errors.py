"""Common safe errors shared by provider-neutral Volta domain modules."""

__all__ = ["InvalidDomainValue"]


class InvalidDomainValue(ValueError):
    """A domain value violates a local, provider-neutral invariant."""

    def __init__(self, field: str, reason_code: str) -> None:
        self.field = field
        self.reason_code = reason_code
        super().__init__(f"invalid domain value: {field} ({reason_code})")
