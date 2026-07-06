"""pipeline_ledger.py — event union round-trips and transition-table invariants."""
import pytest
from pydantic import TypeAdapter, ValidationError

import pipeline_ledger as pl
from support import make_transition_event

ADAPTER = TypeAdapter(pl.LedgerEvent)


def test_node_transition_event_round_trip() -> None:
    event = ADAPTER.validate_python(make_transition_event())
    assert type(event).__name__ == "NodeTransitionEvent"
    assert event.to_state == "DISCOVERED"


def test_document_event_round_trip() -> None:
    event = ADAPTER.validate_python(
        {
            "event_type": "document",
            "event_id": "01J0DOCULID",
            "document_id": "ddia-ch5",
            "action": "EXTRACT",
            "source_sha256": "cd" * 32,
            "actor": {"role": "Extractor", "execution": "deterministic"},
            "occurred_at": "2026-07-07T00:00:00Z",
        }
    )
    assert type(event).__name__ == "DocumentEvent"


def test_rejects_stray_field() -> None:
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(make_transition_event(stray_field=True))


def test_rejects_invalid_action() -> None:
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(make_transition_event(action="HALLUCINATED_ACTION"))


def test_manifest_builds_with_defaults() -> None:
    manifest = pl.LedgerManifest()
    assert manifest.ledger_version == "1"
    assert manifest.nodes == {}


def test_ghost_stub_round_trip() -> None:
    stub = pl.GhostStub(
        canonical_id="leaderless_replication",
        title_guess="Leaderless Replication",
        referenced_by="read_repair",
        predicate="REQUIRES",
        created_at="2026-07-07T00:00:00Z",
    )
    assert stub.canonical_id == "leaderless_replication"


@pytest.mark.parametrize("bad_id", ["Leaderless-Replication", "9ghost", "a" * 65])
def test_ghost_stub_id_is_filesystem_guarded(bad_id: str) -> None:
    """Ghost ids originate from LLM-emitted edge targets and create nodes/<id>/ paths
    on disk — pattern and length are enforced in-schema (decision register #30/#37)."""
    with pytest.raises(ValidationError):
        pl.GhostStub(
            canonical_id=bad_id,
            title_guess="x",
            referenced_by="read_repair",
            predicate="REQUIRES",
            created_at="2026-07-07T00:00:00Z",
        )


# ---- Transition-table invariants (guard future edits to TRANSITION_RULES) ----

def test_rule_actions_are_unique_and_release_is_absent() -> None:
    actions = [rule.action for rule in pl.TRANSITION_RULES]
    assert len(actions) == len(set(actions))
    assert "RELEASE" not in actions  # dynamic target; operator-mediated by design


def test_canonical_is_terminal() -> None:
    """No rule may transition OUT of CANONICAL."""
    for rule in pl.TRANSITION_RULES:
        assert "CANONICAL" not in rule.allowed_from, rule.action


def test_ghost_exits_only_via_discover() -> None:
    exits = {rule.action for rule in pl.TRANSITION_RULES if "GHOST" in rule.allowed_from}
    assert exits == {"DISCOVER"}


def test_fix_rules_require_fail_verdict_and_are_bounded() -> None:
    for action in ("FIX_BASE", "FIX_ENRICHMENT"):
        rule = next(r for r in pl.TRANSITION_RULES if r.action == action)
        assert rule.requires_verdict == "fail"
        assert rule.bounded_by_fix_cycle is True


def test_promote_rules_require_pass_verdict() -> None:
    for action in ("PROMOTE_BASE", "PROMOTE_CANONICAL"):
        rule = next(r for r in pl.TRANSITION_RULES if r.action == action)
        assert rule.requires_verdict == "pass"
        assert rule.bounded_by_fix_cycle is False


def test_node_creating_rules_allow_absence() -> None:
    for action in ("DISCOVER", "CREATE_GHOST"):
        rule = next(r for r in pl.TRANSITION_RULES if r.action == action)
        assert None in rule.allowed_from


def test_max_fix_cycles_bound() -> None:
    assert pl.MAX_FIX_CYCLES_PER_GATE == 2
