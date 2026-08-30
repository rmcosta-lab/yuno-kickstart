"""Canonical deterministic P0 text fixtures owned by the backend boundary."""

import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import gettempdir
from uuid import UUID, uuid4

from yuno_backend.volta.evidence.storage.filesystem import FilesystemEvidenceStorage
from yuno_backend.volta.intake.extraction import (
    DeterministicIntakeExtractor,
    ExtractionRequest,
)
from yuno_backend.volta.mandates.models import (
    MandateProposal,
    Money,
    OperationProposal,
    PickupWindow,
    Route,
)
from yuno_backend.volta.negotiations.catalog import SyntheticCarrierCatalog
from yuno_backend.volta.negotiations.models import CarrierProfile

__all__ = [
    "canonical_text_extraction_mapping",
    "create_demo_carrier_catalog",
    "create_demo_evidence_storage",
    "create_demo_text_extractor",
]


def _pcm_wave_silence(*, sample_rate: int, duration_seconds: int) -> bytes:
    """Build deterministic unsigned 8-bit mono PCM accepted by browser playback."""
    audio = b"\x80" * (sample_rate * duration_seconds)
    return b"".join(
        (
            b"RIFF",
            (36 + len(audio)).to_bytes(4, "little"),
            b"WAVE",
            b"fmt ",
            (16).to_bytes(4, "little"),
            (1).to_bytes(2, "little"),
            (1).to_bytes(2, "little"),
            sample_rate.to_bytes(4, "little"),
            sample_rate.to_bytes(4, "little"),
            (1).to_bytes(2, "little"),
            (8).to_bytes(2, "little"),
            b"data",
            len(audio).to_bytes(4, "little"),
            audio,
        )
    )


_PICKUP_DATE = date(2026, 9, 3)
_CANONICAL_ROUTE = Route(
    "Puerto de Manzanillo, Colima",
    "Zona industrial, Guadalajara, Jalisco",
)
_NO_ELIGIBLE_ROUTE = Route("Puerto de Veracruz, Veracruz", "Puebla, Puebla")
_RECOVERY_FIXTURE_NAME = "fixture-recovery-mandate-safe.wav"
_RECOVERY_FIXTURE_PAYLOAD = _pcm_wave_silence(sample_rate=8_000, duration_seconds=3)


def canonical_text_extraction_mapping(request: ExtractionRequest) -> OperationProposal:
    """Map the bounded demo prompts without network access or model discretion."""
    normalized = request.source_prompt.casefold()
    if "veracruz" in normalized and "puebla" in normalized:
        route = _NO_ELIGIBLE_ROUTE
    elif "manzanillo" in normalized and "guadalajara" in normalized:
        route = _CANONICAL_ROUTE
    else:
        route = Route("", "")
    cargo_label = (
        "40ft dry container"
        if any(token in normalized for token in ("40-foot", "40 foot", "40ft", "40 ft"))
        else ""
    )
    return OperationProposal(
        route=route,
        pickup_date=_PICKUP_DATE,
        cargo_label=cargo_label,
        mandate=MandateProposal(
            maximum_amount=Money(Decimal("9000"), "MXN"),
            pickup_window=PickupWindow(_PICKUP_DATE, _PICKUP_DATE),
            allowed_conditions=("40ft dry container", "Standard handling"),
            escalation_conditions=(
                "No carrier available within budget",
                "Pickup window missed by more than 24 hours",
            ),
        ),
    )


def create_demo_text_extractor() -> DeterministicIntakeExtractor:
    return DeterministicIntakeExtractor(mapping=canonical_text_extraction_mapping)


def create_demo_carrier_catalog() -> SyntheticCarrierCatalog:
    route = ((_CANONICAL_ROUTE.origin, _CANONICAL_ROUTE.destination),)
    return SyntheticCarrierCatalog(
        (
            CarrierProfile(
                UUID("1f104db7-49c8-4ee7-86f3-752389f78601"),
                "Puerto Azul Drayage",
                route,
                True,
                1,
            ),
            CarrierProfile(
                UUID("1f104db7-49c8-4ee7-86f3-752389f78602"),
                "Ruta Norte Intermodal de Occidente",
                route,
                True,
                2,
            ),
            CarrierProfile(
                UUID("1f104db7-49c8-4ee7-86f3-752389f78603"),
                "Altamar Logistica Portuaria del Pacifico",
                route,
                True,
                3,
            ),
        )
    )


def create_demo_evidence_storage(base_dir: Path | None = None) -> FilesystemEvidenceStorage:
    """Build the local text harness storage outside the source checkout."""
    root = Path(gettempdir()) / "yuno-volta-text-evidence" if base_dir is None else base_dir
    storage = FilesystemEvidenceStorage(root)
    _materialize_recovery_fixture(root)
    return storage


def _materialize_recovery_fixture(root: Path) -> None:
    """Atomically restore the known recovery fixture when a prior run left it invalid."""
    fixture = root / _RECOVERY_FIXTURE_NAME
    try:
        valid_fixture = fixture.read_bytes() == _RECOVERY_FIXTURE_PAYLOAD
    except OSError:
        valid_fixture = False

    if valid_fixture:
        fixture.chmod(0o600)
        return

    temporary_fixture = root / f".{_RECOVERY_FIXTURE_NAME}.{uuid4().hex}.tmp"
    descriptor = os.open(
        temporary_fixture,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as artifact:
            artifact.write(_RECOVERY_FIXTURE_PAYLOAD)
        temporary_fixture.chmod(0o600)
        os.replace(temporary_fixture, fixture)
    except BaseException:
        temporary_fixture.unlink(missing_ok=True)
        raise
