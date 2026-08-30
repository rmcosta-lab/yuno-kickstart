import asyncio
import stat
from pathlib import Path
from uuid import UUID

import pytest
from yuno_backend.volta.evidence.storage.filesystem import FilesystemEvidenceStorage


async def test_store_retrieve_and_delete_round_trip(tmp_path: Path) -> None:
    storage = FilesystemEvidenceStorage(tmp_path)
    reference = await storage.store(UUID(int=1), b"synthetic-audio-bytes")

    assert (await storage.retrieve(reference)) == b"synthetic-audio-bytes"

    await storage.delete(reference)
    with pytest.raises(FileNotFoundError):
        await storage.retrieve(reference)

    await storage.delete(reference)  # idempotent no-op


async def test_store_writes_outside_the_repository_and_is_opaque(tmp_path: Path) -> None:
    storage = FilesystemEvidenceStorage(tmp_path)
    reference = await storage.store(UUID(int=1), b"a")
    assert not Path(reference).is_absolute()
    assert (tmp_path / reference).exists()
    artifact = tmp_path / reference
    modes = await asyncio.to_thread(
        lambda: (
            stat.S_IMODE(tmp_path.stat().st_mode),
            stat.S_IMODE(artifact.parent.stat().st_mode),
            stat.S_IMODE(artifact.stat().st_mode),
        )
    )
    assert modes == (0o700, 0o700, 0o600)


@pytest.mark.parametrize("escape", ["../outside.bin", "/etc/passwd"])
async def test_resolve_rejects_references_that_escape_the_storage_root(
    tmp_path: Path, escape: str
) -> None:
    storage = FilesystemEvidenceStorage(tmp_path)
    with pytest.raises(ValueError, match="storage root|relative"):
        await storage.retrieve(escape)
