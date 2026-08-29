"""Deterministic in-memory carrier catalog."""

from collections.abc import Iterable

from yuno_backend.volta.errors import InvalidDomainValue
from yuno_backend.volta.mandates.models import Route
from yuno_backend.volta.negotiations.models import CarrierProfile

__all__ = ["SyntheticCarrierCatalog"]


class SyntheticCarrierCatalog:
    def __init__(self, carriers: Iterable[CarrierProfile]) -> None:
        values = tuple(carriers)
        if len({item.id for item in values}) != len(values):
            raise InvalidDomainValue("carriers", "duplicate_id")
        if len({item.priority for item in values}) != len(values):
            raise InvalidDomainValue("carriers", "duplicate_priority")
        self._carriers = values

    def select(self, route: Route, *, limit: int = 3) -> tuple[CarrierProfile, ...]:
        if not 0 <= limit <= 3:
            raise InvalidDomainValue("limit", "range_0_3_required")
        eligible = (item for item in self._carriers if item.available and item.covers(route))
        return tuple(sorted(eligible, key=lambda item: (item.priority, item.id))[:limit])
