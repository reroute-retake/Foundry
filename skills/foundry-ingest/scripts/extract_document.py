"""EXTRACT: Source Material → Extracted Text (v1: markdown identity transform).

Deterministic (ADR 003 — this file is AST-scanned in CI: no LLM client may
ever be imported here). v1 copies the markdown source verbatim into
``.skills-data/documents/<id>/extracted_text.md`` — extraction is a copy +
hash, deferring the Marker/Docling benchmark until real PDFs enter
(register #40).

Preconditions enforced under the ledger lock:
- the document is REGISTERED and not yet EXTRACTED (append-only; ADR 002)
- the source file's hash still equals the registered ``source_sha256``
  (integrity witness: the file must not have changed since registration)

The identity transform makes the artifact hash provably equal to the source
hash — asserted, not assumed (hash-what-you-write, register #41).
"""

import argparse
import json
import sys
from pathlib import Path

import _bootstrap
from register_document import derive_document_id

import canonical_json
import ledger
import workspace
from pipeline_ledger import ActorRef, ArtifactRef, DocumentEvent

_ACTOR = ActorRef(role="Extractor", execution="deterministic")


def fail(code: str, message: str) -> int:
    print(json.dumps({"ok": False, "error": code, "message": message}), file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="the registered Source Material file")
    parser.add_argument("--document-id", default=None, help="override the derived id")
    args = parser.parse_args(argv)

    source = args.source.resolve()
    if not source.is_file():
        return fail("SOURCE_MISSING", f"source file not found: {source}")
    try:
        document_id = args.document_id or derive_document_id(source)
    except ValueError as exc:
        return fail("BAD_DOCUMENT_ID", str(exc))

    root = _bootstrap.data_root()
    data = source.read_bytes()
    artifact_sha256 = canonical_json.sha256_of_bytes(data)

    with workspace.ledger_lock(root):
        manifest = ledger.fold(ledger.read_events(root))
        entry = manifest.documents.get(document_id)
        if entry is None:
            return fail("NOT_REGISTERED", f"document {document_id!r} has no REGISTER event — run register_document.py first")
        if entry.extracted:
            return fail("ALREADY_EXTRACTED", f"document {document_id!r} is already extracted; the ledger is append-only")
        if artifact_sha256 != entry.source_sha256:
            return fail(
                "SOURCE_CHANGED",
                f"source hash {artifact_sha256[:12]}… no longer matches the registered "
                f"{entry.source_sha256[:12]}… — the file changed after registration; "
                "re-register under a new document id",
            )

        relative = f"documents/{document_id}/extracted_text.md"
        destination = workspace.skills_data_dir(root) / relative
        workspace.atomic_write_bytes(destination, data)
        # Identity transform: the written bytes ARE the source bytes (witnessed).
        written_sha256 = canonical_json.sha256_of_file(destination)
        if written_sha256 != artifact_sha256:
            return fail("WRITE_CORRUPTION", "written artifact hash does not match source hash")

        event = DocumentEvent(
            event_id=ledger.new_ulid(),
            document_id=document_id,
            action="EXTRACT",
            source_sha256=entry.source_sha256,
            actor=_ACTOR,
            produced=[ArtifactRef(kind="extracted_text", path=relative, revision=1, sha256=written_sha256)],
            occurred_at=ledger.utc_now_iso(),
        )
        ledger.append_event(root, event)
        ledger.rebuild_manifest(root)

    print(json.dumps({
        "ok": True,
        "action": "EXTRACT",
        "document_id": document_id,
        "artifact": relative,
        "sha256": written_sha256,
        "bytes": len(data),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
