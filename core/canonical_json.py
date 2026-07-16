"""Canonical JSON serialization and hashing (register #41).

One function — ``canonical_bytes`` — produces the bytes for BOTH the file write
and the sha256 (hash-what-you-write). Two serialization paths would drift; there
is deliberately no second way to turn an object into bytes in this codebase.

The pinned form (register #41):
    json.dumps(obj, ensure_ascii=False, allow_nan=False, sort_keys=True,
               separators=(",", ":"))
explicitly UTF-8 encoded, with a single trailing newline (POSIX text file; the
newline is part of the hashed bytes because it is part of the written bytes).

Floats are rejected defensively: no schema contains a float field, and
introducing one requires a decision-register entry first (register #41).
"""

import hashlib
import json
from pathlib import Path

_CHUNK = 1 << 20  # 1 MiB — streaming hash for source materials


def _reject_floats(obj: object, path: str = "$") -> None:
    """Raise TypeError if any float lurks anywhere in the structure.

    ``bool`` is an ``int`` subclass and is fine; ``float`` (including values
    that happen to be integral, like 2.0) is not — float repr is the classic
    canonicalization hazard (register #41).
    """
    if isinstance(obj, float):
        raise TypeError(
            f"float at {path} — floats are forbidden in canonical artifacts; "
            "adding one requires a decision-register entry (register #41)"
        )
    if isinstance(obj, dict):
        for key, value in obj.items():
            _reject_floats(key, f"{path}.{key!r}(key)")
            _reject_floats(value, f"{path}.{key!r}")
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _reject_floats(item, f"{path}[{i}]")


def canonical_bytes(obj: object) -> bytes:
    """The one true serialization: pinned dumps kwargs, UTF-8, trailing newline."""
    _reject_floats(obj)
    text = json.dumps(
        obj,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8") + b"\n"


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_of_obj(obj: object) -> str:
    """Hash of exactly the bytes ``canonical_bytes`` would write."""
    return sha256_of_bytes(canonical_bytes(obj))


def sha256_of_file(path: Path) -> str:
    """Streaming hash of an existing file (e.g. Source Material)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()
