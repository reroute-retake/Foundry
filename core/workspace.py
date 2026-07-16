"""Workspace layout and durable-write primitives (ADR 013, register #42).

All runtime artifacts live under ``.skills-data/`` at the repository root —
never inside ``skills/`` (immutable definitions only). Writers here are the
only sanctioned ways to put bytes on disk:

- ``atomic_write_bytes``   — temp file in the same directory + fsync + rename
                             (readers never observe a partial file)
- ``append_bytes_fsync``   — append + flush + fsync (the ledger's JSONL log)
- ``ledger_lock``          — cross-platform inter-process lock via ``filelock``
                             (register #42: ``fcntl.flock`` is Unix-only)
"""

import os
from pathlib import Path

from filelock import FileLock

LOCK_TIMEOUT_SECONDS: float = 30.0


class WorkspaceError(RuntimeError):
    """Raised when the repository root cannot be located."""


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward until a directory containing ``pyproject.toml`` is found."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise WorkspaceError(f"no pyproject.toml found walking up from {current}")


# ---------------------------------------------------------------------------
# Layout (all paths derived, never hard-coded elsewhere)
# ---------------------------------------------------------------------------

def skills_data_dir(root: Path) -> Path:
    return root / ".skills-data"


def pipeline_dir(root: Path) -> Path:
    return skills_data_dir(root) / "pipeline"


def ledger_path(root: Path) -> Path:
    return pipeline_dir(root) / "ledger.jsonl"


def manifest_path(root: Path) -> Path:
    return pipeline_dir(root) / "manifest.json"


def lock_path(root: Path) -> Path:
    return pipeline_dir(root) / "ledger.lock"


def node_dir(root: Path, canonical_id: str) -> Path:
    return skills_data_dir(root) / "nodes" / canonical_id


def artifact_path(root: Path, canonical_id: str, revision: int, kind: str) -> Path:
    """Copy-on-write revision file: ``nodes/<id>/rev-NNN.<kind>.json`` (ADR 002)."""
    return node_dir(root, canonical_id) / f"rev-{revision:03d}.{kind}.json"


def relative_to_skills_data(root: Path, path: Path) -> str:
    """ArtifactRef.path is recorded relative to ``.skills-data/``."""
    return path.resolve().relative_to(skills_data_dir(root).resolve()).as_posix()


# ---------------------------------------------------------------------------
# Durable writes
# ---------------------------------------------------------------------------

def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write via temp file + fsync + atomic rename; never a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def append_bytes_fsync(path: Path, data: bytes) -> None:
    """Append + fsync — the ledger event log's write primitive."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def ledger_lock(root: Path, timeout: float = LOCK_TIMEOUT_SECONDS) -> FileLock:
    """The inter-process ledger lock (write protocol step 1)."""
    lock_file = lock_path(root)
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(lock_file), timeout=timeout)
