"""taxonomy.py — discriminator routing, strictness, and canonical-order guards."""
from typing import get_args

import pytest
from pydantic import TypeAdapter, ValidationError

import taxonomy
from support import CANONICAL_ORDER, make_node

ADAPTER = TypeAdapter(taxonomy.KnowledgeArtifact)


@pytest.mark.parametrize("kind", CANONICAL_ORDER)
def test_routes_every_kind(kind: str) -> None:
    node = ADAPTER.validate_python(make_node(kind))
    assert node.primary_kind == kind


def test_union_declared_in_canonical_order() -> None:
    """ADR 007 guard: the KnowledgeArtifact union must mirror the evaluation order."""
    union_args = get_args(get_args(taxonomy.KnowledgeArtifact)[0])
    kinds = [get_args(cls.model_fields["primary_kind"].annotation)[0] for cls in union_args]
    assert kinds == CANONICAL_ORDER


def test_rejects_stray_field_on_node() -> None:
    node = make_node("Concept")
    node["stray_field"] = True
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(node)


def test_rejects_stray_field_in_payload() -> None:
    """The empty ConceptPayload must not silently accept arbitrary keys."""
    node = make_node("Concept")
    node["payload"] = {"anything": 1}
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(node)


def test_rejects_unknown_primary_kind() -> None:
    node = make_node("Concept")
    node["primary_kind"] = "Framework"
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(node)


def test_missing_payload_field_names_the_field() -> None:
    """ADR 010: validation errors must be targeted enough for automated repair."""
    node = make_node("Algorithm")
    del node["payload"]["time_complexity"]
    with pytest.raises(ValidationError) as excinfo:
        ADAPTER.validate_python(node)
    assert "time_complexity" in str(excinfo.value)


def test_core_definition_max_length_enforced() -> None:
    node = make_node("Concept")
    node["core_definition"] = "x" * 351
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(node)


def test_edge_rejects_stray_field() -> None:
    with pytest.raises(ValidationError):
        taxonomy.Edge(predicate="MITIGATES", target_canonical_id="x", stray=1)


def test_edge_rejects_invented_predicate() -> None:
    """ADR 009: the edge vocabulary is closed."""
    with pytest.raises(ValidationError):
        taxonomy.Edge(predicate="HAS_RELATIONSHIP_WITH", target_canonical_id="x")


def test_sourceref_rejects_stray_field() -> None:
    with pytest.raises(ValidationError):
        taxonomy.SourceRef(document_id="d", chunk_span="0:1", quotation_snippet="q", stray=1)


@pytest.mark.parametrize("bad_id", ["Test-Node", "TestNode", "9node", "test node"])
def test_canonical_id_must_be_snake_case(bad_id: str) -> None:
    node = make_node("Concept")
    node["canonical_id"] = bad_id
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(node)
