"""Safe application errors shared by evidence and recovery mutations.

`CommitmentNotFound`, `EvidenceAlreadyRecorded`, and `InvalidCommitmentDisposition`
are defined in `yuno_backend.volta.evidence.errors` and re-exported here so a
single stable import path (`yuno_backend.volta.recovery.errors`, per the phase
application contract) covers both evidence and recovery services.
`StaleOperationVersion` is re-exported unchanged from
`yuno_backend.volta.negotiations.errors` (same optimistic-concurrency contract
introduced in Fase 08).
"""

from uuid import UUID

from yuno_backend.volta.evidence.errors import (
    CommitmentNotFound,
    EvidenceAlreadyRecorded,
    InvalidCommitmentDisposition,
)
from yuno_backend.volta.negotiations.errors import StaleOperationVersion

__all__ = [
    "CommitmentNotFound",
    "EscalationNotFound",
    "EvidenceAlreadyRecorded",
    "InvalidCommitmentDisposition",
    "MandateVersionNotAdvanced",
    "OperationBlockedByEscalation",
    "StaleOperationVersion",
]


class _SafeRecoveryError(RuntimeError):
    code = "recovery_error"


class EscalationNotFound(_SafeRecoveryError, LookupError):
    """No unresolved-or-resolved escalation exists for the given identifier.

    Not part of the phase's minimal error vocabulary table but required so
    `ResumeAfterEscalationService` can fail safely on a bad `escalation_id`
    instead of raising an unstructured error.
    """

    code = "escalation_not_found"

    def __init__(self, escalation_id: UUID) -> None:
        self.escalation_id = escalation_id
        super().__init__(f"escalation not found: {escalation_id}")


class OperationBlockedByEscalation(_SafeRecoveryError):
    code = "operation_blocked_by_escalation"

    def __init__(self, operation_id: UUID, escalation_id: UUID) -> None:
        self.operation_id = operation_id
        self.escalation_id = escalation_id
        super().__init__(f"operation blocked by escalation: {operation_id} ({escalation_id})")


class MandateVersionNotAdvanced(_SafeRecoveryError):
    code = "mandate_version_not_advanced"

    def __init__(
        self, operation_id: UUID, escalation_mandate_version: int, provided_mandate_version: int
    ) -> None:
        self.operation_id = operation_id
        self.escalation_mandate_version = escalation_mandate_version
        self.provided_mandate_version = provided_mandate_version
        super().__init__(
            f"mandate version not advanced: {operation_id} "
            f"(escalation={escalation_mandate_version}, provided={provided_mandate_version})"
        )
