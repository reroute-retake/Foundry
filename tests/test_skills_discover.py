"""Discoverer tests with a mocked LLM (implementation plan, Phase 3).

Covers: quote recovery under typographic divergence, slugify, ghost
reification, retry/skip path with the failures report, dedupe, and ledger
effects. The transport seam (``run_discover.TRANSPORT``) is replaced — no
network, no provider, no cost.
"""

import json
import sys
from pathlib import Path

import pytest

import ledger
import workspace
from pipeline_ledger import ActorRef, ArtifactRef, DocumentEvent, NodeTransitionEvent

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "skills" / "foundry-discover" / "scripts"))

import run_discover  # noqa: E402  (needs the scripts dir on sys.path first)

CHUNK_BODY = (
    "## Replication strategies\n\n"
    "The **leaderless** approach — sometimes called [Dynamo-style](https://example.com/dynamo) "
    "replication — tolerates “node outages” without failover. "
    "Quorum reads and writes require that w + r > n holds.\n"
)
PLAIN_QUOTE = (
    'The leaderless approach - sometimes called Dynamo-style replication - '
    'tolerates "node outages" without failover.'
)


# ---------------------------------------------------------------------------
# Helpers: seed an EXTRACTED document; build fake LLM responses
# ---------------------------------------------------------------------------

def _seed_extracted(root: Path, document_id: str, text: str) -> None:
    artifact_rel = f"documents/{document_id}/extracted_text.md"
    destination = workspace.skills_data_dir(root) / artifact_rel
    data = text.encode("utf-8")
    workspace.atomic_write_bytes(destination, data)
    sha = __import__("canonical_json").sha256_of_bytes(data)
    actor = ActorRef(role="Extractor", execution="deterministic")
    with workspace.ledger_lock(root):
        ledger.append_event(root, DocumentEvent(
            event_id=ledger.new_ulid(), document_id=document_id, action="REGISTER",
            source_sha256=sha, actor=actor, produced=[], occurred_at=ledger.utc_now_iso()))
        ledger.append_event(root, DocumentEvent(
            event_id=ledger.new_ulid(), document_id=document_id, action="EXTRACT",
            source_sha256=sha, actor=actor,
            produced=[ArtifactRef(kind="extracted_text", path=artifact_rel, revision=1, sha256=sha)],
            occurred_at=ledger.utc_now_iso()))
        ledger.rebuild_manifest(root)


def _seed_ghost(root: Path, canonical_id: str) -> None:
    with workspace.ledger_lock(root):
        ledger.append_event(root, NodeTransitionEvent(
            event_id=ledger.new_ulid(), canonical_id=canonical_id, sequence=1,
            action="CREATE_GHOST", from_state=None, to_state="GHOST",
            actor=ActorRef(role="Linker", execution="tier2_script"),
            occurred_at=ledger.utc_now_iso()))
        ledger.rebuild_manifest(root)


def _entity(name: str, quote: str, level: str = "Pattern") -> dict:
    return {
        "sequence_trace": [{
            "level_name": level,
            "axiological_reasoning": "test trace",
            "condition_met": True,
        }],
        "final_classification": level,
        "extracted_entity_name": name,
        "evidence_quote": quote,
    }


def _batch(*entities: dict) -> str:
    return json.dumps({"entities": list(entities)})


@pytest.fixture()
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(run_discover, "RETRY_SLEEP_SECONDS", 0.0)
    return tmp_path


CFG = run_discover.Config(base_url="https://mock", api_key="k", model="mock-model")


def _run(root: Path, document_id: str = "ddia_ch5", **kwargs):
    return run_discover.discover_document(root, REPO, document_id, CFG, **kwargs)


# ---------------------------------------------------------------------------
# Deterministic pieces
# ---------------------------------------------------------------------------

def test_chunk_markdown_splits_on_headings() -> None:
    intro = "intro paragraph that is comfortably long enough to clear the minimum chunk size filter\n"
    text = intro + "## A\n" + "a" * 100 + "\n## B\n" + "b" * 100 + "\n"
    chunks = run_discover.chunk_markdown(text)
    assert [c.index for c in chunks] == [0, 1, 2]
    assert chunks[1].text.startswith("## A")
    assert text[chunks[2].start:].startswith("## B")
    # Headings-only stubs are filtered by the minimum-size rule.
    assert run_discover.chunk_markdown("## Tiny\n\n## Also tiny\n") == []


def test_slugify_rules() -> None:
    assert run_discover.slugify("Two-Phase Commit") == "two_phase_commit"
    assert run_discover.slugify("  Quorum (w + r > n)!  ") == "quorum_w_r_n"
    assert run_discover.slugify("2PC protocol") == "n2pc_protocol"
    with pytest.raises(ValueError):
        run_discover.slugify("!!!")


def test_recover_span_typographic_divergence() -> None:
    recovered = run_discover.recover_span(CHUNK_BODY, PLAIN_QUOTE)
    assert recovered is not None
    text, start, end = recovered
    # The stored span is SOURCE text — markdown and typography intact.
    assert "**leaderless**" in text and "[Dynamo-style](https://example.com/dynamo)" in text
    assert CHUNK_BODY[start:end] == text
    from discoverer_schema import normalize_quote
    assert normalize_quote(text) == normalize_quote(PLAIN_QUOTE)


def test_recover_span_rejects_fabricated_quote() -> None:
    assert run_discover.recover_span(CHUNK_BODY, "Paxos elects a stable leader") is None


# ---------------------------------------------------------------------------
# End-to-end with mocked transport
# ---------------------------------------------------------------------------

def test_discover_happy_path_ledger_effects(root: Path, monkeypatch) -> None:
    _seed_extracted(root, "ddia_ch5", CHUNK_BODY)
    monkeypatch.setattr(run_discover, "TRANSPORT",
                        lambda cfg, sp, up: _batch(_entity("Leaderless Replication", PLAIN_QUOTE)))
    summary = _run(root)
    assert summary.discovered == 1 and summary.failed_chunks == 0

    manifest = ledger.fold(ledger.read_events(root))
    entry = manifest.nodes["leaderless_replication"]
    assert entry.state == "DISCOVERED"
    artifact = workspace.skills_data_dir(root) / entry.current_artifacts[0].path
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["provenance"]["document_id"] == "ddia_ch5"
    assert "**leaderless**" in payload["provenance"]["quotation_snippet"]
    import canonical_json
    assert canonical_json.sha256_of_file(artifact) == entry.current_artifacts[0].sha256


def test_discover_reifies_ghost(root: Path, monkeypatch) -> None:
    _seed_extracted(root, "ddia_ch5", CHUNK_BODY)
    _seed_ghost(root, "leaderless_replication")
    monkeypatch.setattr(run_discover, "TRANSPORT",
                        lambda cfg, sp, up: _batch(_entity("Leaderless Replication", PLAIN_QUOTE)))
    summary = _run(root)
    assert summary.discovered == 1 and summary.reified_ghosts == 1
    events = [e for e in ledger.read_events(root)
              if getattr(e, "canonical_id", None) == "leaderless_replication"]
    assert events[-1].from_state == "GHOST" and events[-1].sequence == 2


def test_duplicate_entities_dedupe(root: Path, monkeypatch) -> None:
    _seed_extracted(root, "ddia_ch5", CHUNK_BODY)
    same = _entity("Leaderless Replication", PLAIN_QUOTE)
    monkeypatch.setattr(run_discover, "TRANSPORT", lambda cfg, sp, up: _batch(same, same))
    summary = _run(root)
    assert summary.discovered == 1 and summary.duplicates == 1


def test_retry_then_success(root: Path, monkeypatch) -> None:
    _seed_extracted(root, "ddia_ch5", CHUNK_BODY)
    calls = {"n": 0}

    def flaky(cfg, sp, up):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("HTTP 503")
        return _batch(_entity("Leaderless Replication", PLAIN_QUOTE))

    monkeypatch.setattr(run_discover, "TRANSPORT", flaky)
    summary = _run(root)
    assert calls["n"] == 3 and summary.discovered == 1 and summary.failed_chunks == 0


def test_exhausted_retries_write_failure_report(root: Path, monkeypatch) -> None:
    _seed_extracted(root, "ddia_ch5", CHUNK_BODY)
    monkeypatch.setattr(run_discover, "TRANSPORT",
                        lambda cfg, sp, up: (_ for _ in ()).throw(RuntimeError("HTTP 500")))
    summary = _run(root)
    assert summary.failed_chunks == 1 and summary.discovered == 0
    report = workspace.pipeline_dir(root) / "discovery-failures.jsonl"
    record = json.loads(report.read_text(encoding="utf-8").splitlines()[0])
    assert record["attempts"] == run_discover.MAX_ATTEMPTS
    assert record["document_id"] == "ddia_ch5"


def test_unverifiable_quote_retries_then_fails(root: Path, monkeypatch) -> None:
    _seed_extracted(root, "ddia_ch5", CHUNK_BODY)
    monkeypatch.setattr(run_discover, "TRANSPORT",
                        lambda cfg, sp, up: _batch(_entity("Paxos", "a fabricated ungrounded quote")))
    summary = _run(root)
    assert summary.failed_chunks == 1 and summary.discovered == 0
    report = (workspace.pipeline_dir(root) / "discovery-failures.jsonl").read_text()
    assert "Paxos" in report


def test_discover_refuses_unextracted_document(root: Path) -> None:
    with pytest.raises(RuntimeError, match="not EXTRACTED"):
        _run(root, document_id="never_registered")
