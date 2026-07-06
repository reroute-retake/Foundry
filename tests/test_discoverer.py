"""discoverer_schema.py — canonical order mirror and strictness."""
from typing import get_args

import pytest
from pydantic import ValidationError

import discoverer_schema as ds
from support import CANONICAL_ORDER


def test_taxonomy_level_matches_canonical_order() -> None:
    """ADR 007 guard: TaxonomyLevel is the machine source of truth for the order."""
    assert list(get_args(ds.TaxonomyLevel)) == CANONICAL_ORDER


def _step(level: str, met: bool) -> dict:
    return {
        "level_name": level,
        "axiological_reasoning": "Applying the relevant axiom to the text.",
        "condition_met": met,
    }


def test_classification_result_round_trip() -> None:
    result = ds.ClassificationResult(
        sequence_trace=[_step("Attack Vector", False), _step("Mitigation", True)],
        final_classification="Mitigation",
        extracted_entity_name="Rate Limiting",
    )
    assert result.final_classification == "Mitigation"
    assert len(result.sequence_trace) == 2


def test_rejects_invalid_level() -> None:
    with pytest.raises(ValidationError):
        ds.ClassificationResult(
            sequence_trace=[_step("Attack Vector", True)],
            final_classification="Framework",
            extracted_entity_name="x",
        )


def test_evaluation_step_rejects_stray_field() -> None:
    with pytest.raises(ValidationError):
        ds.EvaluationStep(**_step("Concept", True), stray=1)


def test_classification_result_rejects_stray_field() -> None:
    with pytest.raises(ValidationError):
        ds.ClassificationResult(
            sequence_trace=[_step("Concept", True)],
            final_classification="Concept",
            extracted_entity_name="ACID",
            stray=1,
        )
