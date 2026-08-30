"""Safe provider-neutral failures for the integrated text commitment seam."""

from uuid import UUID

__all__ = [
    "CommitmentEvidenceNotFound",
    "EvidenceArtifactUnavailable",
    "EvidenceReservationMismatch",
    "EvidenceReservationNotFound",
]


class _SafeTextCommitmentError(RuntimeError):
    code = "text_commitment_error"


class EvidenceReservationMismatch(_SafeTextCommitmentError):
    """The text-mode evidence reservation is not correlated to its quote."""

    code = "evidence_reservation_mismatch"

    def __init__(self, quote_id: UUID, evidence_id: UUID) -> None:
        self.quote_id = quote_id
        self.evidence_id = evidence_id
        super().__init__(f"evidence reservation mismatch: quote={quote_id} evidence={evidence_id}")


class EvidenceReservationNotFound(_SafeTextCommitmentError, LookupError):
    code = "evidence_reservation_not_found"

    def __init__(self, evidence_id: UUID) -> None:
        self.evidence_id = evidence_id
        super().__init__(f"evidence reservation not found: evidence={evidence_id}")


class EvidenceArtifactUnavailable(_SafeTextCommitmentError, LookupError):
    code = "evidence_artifact_unavailable"

    def __init__(self, recording_reference: str) -> None:
        self.recording_reference = recording_reference
        super().__init__("evidence artifact is unavailable")


class CommitmentEvidenceNotFound(_SafeTextCommitmentError, LookupError):
    """A durable commitment cannot be projected without its evidence row."""

    code = "commitment_evidence_not_found"

    def __init__(self, commitment_id: UUID, evidence_id: UUID) -> None:
        self.commitment_id = commitment_id
        self.evidence_id = evidence_id
        super().__init__(
            f"commitment evidence not found: commitment={commitment_id} evidence={evidence_id}"
        )
