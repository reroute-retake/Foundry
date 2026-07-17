"""REGISTER a Source Material file with the Pipeline Ledger.

Deterministic (ADR 003: no LLM anywhere near extraction). Follows the ledger
write protocol: flock → precondition check → append event + fsync → manifest
rename. Refuses with a structured error if the document is already registered
— the ledger is append-only and registration is not repeatable (ADR 002).

Usage:
    python3 skills/foundry-ingest/scripts/register_document.py works/sources/ch.md
    ... [--document-id my_chapter]
"""

import argparse
import json
import re
import sys
from pathlib import Path

import _bootstrap

import canonical_json
import ledger
import workspace
from pipeline_ledger import ActorRef, DocumentEvent

_ACTOR = ActorRef(role="Extractor", execution="deterministic")


def fail(code: str, message: str) -> "int":
    print(json.dumps({"ok": False, "error": code, "message": message}), file=sys.stderr)
    return 1


def derive_document_id(source: Path) -> str:
    """Deterministic snake_case id from the filename stem (filesystem anchor rules)."""
    slug = re.sub(r"[^a-z0-9]+", "_", source.stem.lower()).strip("_")[:64]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", slug):
        raise ValueError(f"cannot derive a valid document_id from {source.name!r}")
    return slug


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Source Material file (v1: markdown)")
    parser.add_argument("--document-id", default=None, help="override the derived id")
    args = parser.parse_args(argv)

    source = args.source.resolve()
    if not source.is_file():
        return fail("SOURCE_MISSING", f"source file not found: {source}")
    if source.suffix.lower() not in (".md", ".markdown"):
        return fail(
            "UNSUPPORTED_FORMAT",
            "v1 ingests markdown only (register #40 — the extractor benchmark for "
            f"PDFs is deferred); got {source.suffix!r}",
        )

    try:
        document_id = args.document_id or derive_document_id(source)
    except ValueError as exc:
        return fail("BAD_DOCUMENT_ID", str(exc))

    root = _bootstrap.data_root()
    source_sha256 = canonical_json.sha256_of_file(source)

    with workspace.ledger_lock(root):
        manifest = ledger.fold(ledger.read_events(root))
        if document_id in manifest.documents:
            return fail(
                "ALREADY_REGISTERED",
                f"document {document_id!r} is already registered "
                f"(sha256 {manifest.documents[document_id].source_sha256[:12]}…); "
                "the ledger is append-only",
            )
        event = DocumentEvent(
            event_id=ledger.new_ulid(),
            document_id=document_id,
            action="REGISTER",
            source_sha256=source_sha256,
            actor=_ACTOR,
            produced=[],
            occurred_at=ledger.utc_now_iso(),
        )
        ledger.append_event(root, event)
        ledger.rebuild_manifest(root)

    print(json.dumps({
        "ok": True,
        "action": "REGISTER",
        "document_id": document_id,
        "source_sha256": source_sha256,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
