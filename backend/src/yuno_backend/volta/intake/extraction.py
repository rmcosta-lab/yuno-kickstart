"""Provider-neutral intake extraction protocol and deterministic fallback."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from yuno_backend.volta.mandates import OperationProposal

__all__ = ["DeterministicIntakeExtractor", "ExtractionRequest", "IntakeExtractor"]


@dataclass(frozen=True, slots=True)
class ExtractionRequest:
    source_prompt: str = field(repr=False)
    requested_language: str
    extraction_policy_version: str


class IntakeExtractor(Protocol):
    async def extract(self, request: ExtractionRequest) -> OperationProposal:
        """Extract a provider-neutral proposal without granting authority."""
        ...


class DeterministicIntakeExtractor:
    """No-network extractor backed by a fixed proposal or pure mapping."""

    def __init__(
        self,
        proposal: OperationProposal | None = None,
        *,
        mapping: Callable[[ExtractionRequest], OperationProposal] | None = None,
    ) -> None:
        if (proposal is None) == (mapping is None):
            raise ValueError("exactly one deterministic extraction source is required")
        self._proposal = proposal
        self._mapping = mapping

    async def extract(self, request: ExtractionRequest) -> OperationProposal:
        if self._mapping is not None:
            return self._mapping(request)
        assert self._proposal is not None
        return self._proposal
