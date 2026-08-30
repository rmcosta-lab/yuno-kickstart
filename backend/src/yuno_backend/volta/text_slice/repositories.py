"""Persistence-neutral ports for evidence reservations in the text slice."""

from typing import Protocol
from uuid import UUID

from yuno_backend.volta.text_slice.models import EvidenceReservation


class EvidenceReservationRepository(Protocol):
    async def get(
        self, evidence_id: UUID, *, for_update: bool = False
    ) -> EvidenceReservation | None: ...
    async def get_by_quote(self, quote_id: UUID) -> EvidenceReservation | None: ...
    async def add(self, reservation: EvidenceReservation) -> None: ...
    async def consume(self, evidence_id: UUID, commitment_id: UUID) -> None: ...
