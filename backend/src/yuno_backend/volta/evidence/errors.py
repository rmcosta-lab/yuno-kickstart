"""Safe application errors for evidence mutations.

These classes are re-exported from `yuno_backend.volta.recovery.errors` so a
single stable import path (per the phase application contract) covers both
evidence and recovery services without recovery importing evidence models,
or evidence importing recovery.
"""

from uuid import UUID

__all__ = ["CommitmentNotFound", "EvidenceAlreadyRecorded", "InvalidCommitmentDisposition"]


class _SafeEvidenceError(RuntimeError):
    code = "evidence_error"


class CommitmentNotFound(_SafeEvidenceError, LookupError):
    code = "commitment_not_found"

    def __init__(self, commitment_id: UUID) -> None:
        self.commitment_id = commitment_id
        super().__init__(f"commitment not found: {commitment_id}")


class EvidenceAlreadyRecorded(_SafeEvidenceError):
    """A different evidence payload was already recorded for this commitment.

    Attaching an identical payload twice is a no-op that returns the stored
    record instead of raising; this error signals a genuine conflict when
    the recorded fields differ.
    """

    code = "evidence_already_recorded"

    def __init__(self, commitment_id: UUID) -> None:
        self.commitment_id = commitment_id
        super().__init__(f"evidence already recorded: {commitment_id}")


class InvalidCommitmentDisposition(_SafeEvidenceError):
    code = "invalid_commitment_disposition"

    def __init__(self, commitment_id: UUID, disposition: str) -> None:
        self.commitment_id = commitment_id
        self.disposition = disposition
        super().__init__(f"invalid commitment disposition: {commitment_id} ({disposition})")
