"""Ledger engine: lifecycle walk, refusals, bounded quarantine, crash-safety."""

import pytest

import ledger
import workspace
from pipeline_ledger import ActorRef, ArtifactRef, DocumentEvent, NodeTransitionEvent

# ---------------------------------------------------------------------------
# Event-builder helpers (scripts would assemble these; tests do it inline)
# ---------------------------------------------------------------------------

def _actor(role: str, execution: str) -> ActorRef:
    return ActorRef(role=role, execution=execution)  # type: ignore[arg-type]


def _artifact(kind: str, cid: str, rev: int) -> ArtifactRef:
    return ArtifactRef(kind=kind, path=f"nodes/{cid}/rev-{rev:03d}.{kind}.json", revision=rev, sha256="0" * 64)  # type: ignore[arg-type]


def _node_event(resolved: ledger.ResolvedTransition, action: str, cid: str, *, verdict=None, produces=None) -> NodeTransitionEvent:
    return NodeTransitionEvent(
        event_id=ledger.new_ulid(),
        canonical_id=cid,
        sequence=resolved.sequence,
        action=action,  # type: ignore[arg-type]
        from_state=resolved.from_state,
        to_state=resolved.to_state,
        actor=_actor("Discoverer", "tier2_script"),
        produced=produces or [],
        verdict=verdict,
        fix_cycle=resolved.fix_cycle,
        occurred_at=ledger.utc_now_iso(),
    )


def _doc_extract(document_id: str) -> DocumentEvent:
    return DocumentEvent(
        event_id=ledger.new_ulid(),
        document_id=document_id,
        action="EXTRACT",
        source_sha256="a" * 64,
        actor=_actor("Extractor", "deterministic"),
        produced=[ArtifactRef(kind="extracted_text", path="docs/ch.md", revision=1, sha256="a" * 64)],
        occurred_at=ledger.utc_now_iso(),
    )


# ---------------------------------------------------------------------------
# ULID
# ---------------------------------------------------------------------------

def test_ulid_is_26_chars_and_monotonic_across_ms() -> None:
    a = ledger.new_ulid(now_ms=1)
    b = ledger.new_ulid(now_ms=2)
    assert len(a) == len(b) == 26
    assert a < b  # earlier timestamp sorts first


# ---------------------------------------------------------------------------
# Happy-path lifecycle walk to VALIDATED (Phase 1 exit criterion)
# ---------------------------------------------------------------------------

def test_lifecycle_walk_to_validated() -> None:
    cid = "two_phase_commit"
    events: list = [_doc_extract("ddia_ch7")]

    r = ledger.validate_node_transition(events, "DISCOVER", cid, document_extracted=True)
    assert r.to_state == "DISCOVERED" and r.sequence == 1 and r.from_state is None
    events.append(_node_event(r, "DISCOVER", cid, produces=[_artifact("topic_metadata", cid, 1)]))

    r = ledger.validate_node_transition(events, "DRAFT", cid)
    events.append(_node_event(r, "DRAFT", cid, produces=[_artifact("knowledge_draft", cid, 2)]))
    assert r.to_state == "DRAFTED"

    r = ledger.validate_node_transition(events, "REVIEW_BASE", cid)
    events.append(_node_event(r, "REVIEW_BASE", cid, verdict="pass", produces=[_artifact("review_report", cid, 3)]))
    assert r.to_state == "BASE_REVIEWED"

    r = ledger.validate_node_transition(events, "PROMOTE_BASE", cid)
    assert r.to_state == "VALIDATED"
    events.append(_node_event(r, "PROMOTE_BASE", cid, produces=[_artifact("validated_node", cid, 4)]))

    manifest = ledger.fold(events)
    assert manifest.nodes[cid].state == "VALIDATED"
    assert manifest.nodes[cid].last_sequence == 4


# ---------------------------------------------------------------------------
# Precondition refusals
# ---------------------------------------------------------------------------

def test_out_of_order_transition_refused() -> None:
    cid = "b_tree"
    # DRAFT before the node exists.
    with pytest.raises(ledger.TransitionError):
        ledger.validate_node_transition([], "DRAFT", cid)


def test_discover_refused_without_extracted_document() -> None:
    with pytest.raises(ledger.TransitionError):
        ledger.validate_node_transition([], "DISCOVER", "x", document_extracted=False)


def test_promote_refused_without_pass_verdict() -> None:
    cid = "quorum"
    events: list = [_doc_extract("d")]
    r = ledger.validate_node_transition(events, "DISCOVER", cid, document_extracted=True)
    events.append(_node_event(r, "DISCOVER", cid))
    r = ledger.validate_node_transition(events, "DRAFT", cid)
    events.append(_node_event(r, "DRAFT", cid))
    r = ledger.validate_node_transition(events, "REVIEW_BASE", cid)
    events.append(_node_event(r, "REVIEW_BASE", cid, verdict="fail"))
    with pytest.raises(ledger.TransitionError):
        ledger.validate_node_transition(events, "PROMOTE_BASE", cid)


# ---------------------------------------------------------------------------
# Bounded fix cycles → QuarantineRequired (constitution: "Not an Agentic Loop")
# ---------------------------------------------------------------------------

def test_fix_cycles_bounded_then_quarantine_required() -> None:
    cid = "split_brain"
    events: list = [_doc_extract("d")]
    r = ledger.validate_node_transition(events, "DISCOVER", cid, document_extracted=True)
    events.append(_node_event(r, "DISCOVER", cid))
    r = ledger.validate_node_transition(events, "DRAFT", cid)
    events.append(_node_event(r, "DRAFT", cid))

    # Two fail→fix cycles are allowed; the third fix must be refused.
    for cycle in range(ledger.MAX_FIX_CYCLES_PER_GATE):
        r = ledger.validate_node_transition(events, "REVIEW_BASE", cid)
        events.append(_node_event(r, "REVIEW_BASE", cid, verdict="fail"))
        r = ledger.validate_node_transition(events, "FIX_BASE", cid)
        assert r.fix_cycle == cycle + 1
        events.append(_node_event(r, "FIX_BASE", cid))

    r = ledger.validate_node_transition(events, "REVIEW_BASE", cid)
    events.append(_node_event(r, "REVIEW_BASE", cid, verdict="fail"))
    with pytest.raises(ledger.QuarantineRequired):
        ledger.validate_node_transition(events, "FIX_BASE", cid)

    # QUARANTINE is always available as the escape hatch.
    q = ledger.validate_node_transition(events, "QUARANTINE", cid)
    assert q.to_state == "QUARANTINED"


# ---------------------------------------------------------------------------
# Crash-safety: fold(read_events) == persisted manifest; hashes reproducible
# ---------------------------------------------------------------------------

def test_append_rebuild_and_fold_equivalence(tmp_path) -> None:
    # tmp_path is not a repo; drop a pyproject marker so find_repo_root works.
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n", encoding="utf-8")
    root = tmp_path

    events: list = [_doc_extract("d")]
    cid = "write_ahead_log"
    r = ledger.validate_node_transition(events, "DISCOVER", cid, document_extracted=True)
    events.append(_node_event(r, "DISCOVER", cid, produces=[_artifact("topic_metadata", cid, 1)]))

    with workspace.ledger_lock(root):
        for event in events:
            ledger.append_event(root, event)
        persisted = ledger.rebuild_manifest(root)

    # Manifest rebuilt from disk equals an in-memory fold of the same events.
    reread = ledger.fold(ledger.read_events(root))
    assert reread.model_dump() == persisted.model_dump()

    # The log line for a re-parsed event round-trips to identical canonical bytes.
    import canonical_json

    reparsed = ledger.read_events(root)
    assert canonical_json.sha256_of_obj(reparsed[0].model_dump(mode="json")) == \
        canonical_json.sha256_of_obj(events[0].model_dump(mode="json"))
    assert reread.nodes[cid].state == "DISCOVERED"

def test_stale_manifest_is_repaired_by_rebuild(tmp_path) -> None:
    """Crash between append and manifest-rename: rebuild must equal fold (ADR 017)."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\n", encoding="utf-8")
    root = tmp_path
    cid = "paxos"

    events: list = [_doc_extract("d")]
    r = ledger.validate_node_transition(events, "DISCOVER", cid, document_extracted=True)
    events.append(_node_event(r, "DISCOVER", cid))
    with workspace.ledger_lock(root):
        for event in events:
            ledger.append_event(root, event)
        ledger.rebuild_manifest(root)

    # Simulate a crash: append the DRAFT event but DO NOT rebuild the manifest.
    r = ledger.validate_node_transition(ledger.read_events(root), "DRAFT", cid)
    draft_event = _node_event(r, "DRAFT", cid)
    with workspace.ledger_lock(root):
        ledger.append_event(root, draft_event)  # manifest now stale

    import json

    stale = json.loads(workspace.manifest_path(root).read_text())
    assert stale["nodes"][cid]["state"] == "DISCOVERED"  # stale snapshot lags the log

    # Recovery: rebuild from the authoritative log folds the missed event forward.
    repaired = ledger.rebuild_manifest(root)
    assert repaired.nodes[cid].state == "DRAFTED"
    assert repaired.model_dump() == ledger.fold(ledger.read_events(root)).model_dump()
