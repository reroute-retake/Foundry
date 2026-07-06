"""Shared constants and factories for the schema test suite."""

CANONICAL_ORDER = [
    "Attack Vector", "Mitigation", "Data Structure", "Algorithm", "Pattern",
    "Failure Mode", "Interface", "Metric", "Tool", "Concept",
]


def valid_payload(kind: str) -> dict:
    """A minimal valid payload for each of the 10 node kinds."""
    return {
        "Attack Vector": {"exploit_vector": "crafted SQL in user input", "target_surface": "query parser"},
        "Mitigation": {"defense_mechanism": "drop requests above an arrival-rate threshold"},
        "Data Structure": {
            "hardware_target": "Disk",
            "read_amplification_profile": "low",
            "write_amplification_profile": "sequential appends",
        },
        "Algorithm": {
            "pre_conditions": ["coordinator elected"],
            "post_conditions": ["all participants commit or all abort"],
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
        },
        "Pattern": {"primary_bottleneck": "cross-replica coordination"},
        "Failure Mode": {
            "trigger_conditions": ["network partition"],
            "blast_radius_assessment": "cluster-wide write conflicts",
        },
        "Interface": {"protocol_type": "REST"},
        "Metric": {"unit_of_measurement": "count", "mathematical_formalism": "w + r > n"},
        "Tool": {"primary_runtime": "C", "license_model": "PostgreSQL License"},
        "Concept": {},
    }[kind]


def make_node(kind: str) -> dict:
    """A minimal valid KnowledgeArtifact input for the given kind."""
    return {
        "canonical_id": "test_node",
        "title": "Test Node",
        "core_definition": "A minimal valid definition for unit tests.",
        "operational_context": "Unit testing.",
        "provenance": {"document_id": "doc-1", "chunk_span": "0:10", "quotation_snippet": "verbatim text"},
        "primary_kind": kind,
        "payload": valid_payload(kind),
    }


def make_report_base() -> dict:
    """Common ReviewReport fields (gate/verdict/flaws supplied by each test)."""
    return {
        "report_id": "01J0REVIEWULID",
        "canonical_id": "write_ahead_log",
        "reviewed_revision": 2,
        "reviewed_sha256": "ab" * 32,
        "summary": "Definition is grounded and atomic; one complexity field is wrong.",
        "reviewer_model_id": "claude-opus-4-5",
        "reviewed_at": "2026-07-07T00:00:00Z",
    }


def make_flaw(**overrides) -> dict:
    """A valid Gate-1 (ontology) flaw; override fields as needed."""
    flaw = {
        "flaw_id": 1,
        "severity": "critical",
        "category": "factual_error",
        "field_path": "payload.time_complexity",
        "description": "Claims O(1) lookup; the source states O(log n).",
        "evidence_quote": "time_complexity: O(1)",
        "source_grounding": "p.83: lookups traverse the tree in logarithmic time",
        "fix_instruction": (
            "Correct time_complexity to match the source; "
            "acceptance: value agrees with the quoted passage."
        ),
    }
    flaw.update(overrides)
    return flaw


def make_transition_event(**overrides) -> dict:
    """A valid node_transition LedgerEvent; override fields as needed."""
    event = {
        "event_type": "node_transition",
        "event_id": "01J0TESTULID",
        "canonical_id": "write_ahead_log",
        "sequence": 1,
        "action": "DISCOVER",
        "from_state": None,
        "to_state": "DISCOVERED",
        "actor": {"role": "Discoverer", "execution": "tier2_script", "model_id": "local-qwen-14b"},
        "produced": [
            {
                "kind": "topic_metadata",
                "path": "nodes/write_ahead_log/rev-001.topic_metadata.json",
                "revision": 1,
                "sha256": "ab" * 32,
            }
        ],
        "occurred_at": "2026-07-07T00:00:00Z",
    }
    event.update(overrides)
    return event
