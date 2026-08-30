"""Filesystem-backed development adapter for the `EvidenceStorage` port.

Access and deletion behavior
-----------------------------
Recordings are written as opaque binary blobs under `base_dir`, named by a
freshly generated identifier chosen at `store()` time and returned as the
opaque `recording_reference`. Only that reference string is ever persisted
in the database; the bytes never enter PostgreSQL and the directory lives
outside Git (see the repository `.gitignore`).

`retrieve` and `delete` require the exact reference string returned by
`store` and resolve it strictly inside `base_dir`; there is no listing or
enumeration API, so a caller without the reference cannot discover or read
a recording, and a reference that would escape `base_dir` is rejected.
`delete` is idempotent: removing an already-absent reference is a no-op.

This adapter is for local development only. It applies no access control
beyond the host filesystem's own permissions (the process umask) and no
encryption at rest. A production deployment must swap it for a
provider-backed `EvidenceStorage` implementation before handling real
recordings.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

__all__ = ["FilesystemEvidenceStorage"]


class FilesystemEvidenceStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir.resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    async def store(self, commitment_id: uuid.UUID, payload: bytes) -> str:
        reference = f"{commitment_id}/{uuid.uuid4().hex}.bin"
        path = self._resolve(reference)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)

        await asyncio.to_thread(_write)
        return reference

    async def retrieve(self, recording_reference: str) -> bytes:
        path = self._resolve(recording_reference)
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, recording_reference: str) -> None:
        path = self._resolve(recording_reference)
        await asyncio.to_thread(lambda: path.unlink(missing_ok=True))

    def _resolve(self, recording_reference: str) -> Path:
        if not recording_reference or recording_reference.startswith(("/", "\\")):
            raise ValueError("recording_reference must be a relative, non-empty path")
        path = (self._base_dir / recording_reference).resolve()
        if path != self._base_dir and self._base_dir not in path.parents:
            raise ValueError("recording_reference escapes storage root")
        return path
