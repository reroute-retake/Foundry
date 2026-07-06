"""discoverer_schema.py — canonical order mirror, strictness, and Topic Metadata."""
from typing import get_args

import pytest
from pydantic import ValidationError

import discoverer_schema as ds
from support import CANONICAL_ORDER

QUOTE = "drops requests when the arrival rate exceeds a threshold"


def test_taxonomy_level_matches_canonical_order() -> None:
    """ADR 007 guard: TaxonomyLevel is the machine source of truth for the order."""
    assert list(get_args(ds.TaxonomyLevel)) == CANONICAL_ORDER


def _step(level: str, met: bool) -> dict:
    return {
        "level_name": level,
        "axiological_reasoning": "Applying the relevant axiom to the text.",
        "condition_met": met,
    }


def _result(**overrides) -> dict:
    data = {
        "sequence_trace": [_step("Attack Vector", False), _step("Mitigation", True)],
        "final_classification": "Mitigation",
        "extracted_entity_name": "Rate Limiting",
        "evidence_quote": QUOTE,
    }
    data.update(overrides)
    return data


def _provenance(**overrides) -> dict:
    data = {"document_id": "ddia-ch5", "chunk_span": "1200:1450", "quotation_snippet": QUOTE}
    data.update(overrides)
    return data


def test_classification_result_round_trip() -> None:
    result = ds.ClassificationResult(**_result())
    assert result.final_classification == "Mitigation"
    assert result.evidence_quote == QUOTE


def test_evidence_quote_is_required() -> None:
    payload = _result()
    del payload["evidence_quote"]
    with pytest.raises(ValidationError) as excinfo:
        ds.ClassificationResult(**payload)
    assert "evidence_quote" in str(excinfo.value)


def test_rejects_invalid_level() -> None:
    with pytest.raises(ValidationError):
        ds.ClassificationResult(**_result(final_classification="Framework"))


def test_evaluation_step_rejects_stray_field() -> None:
    with pytest.raises(ValidationError):
        ds.EvaluationStep(**_step("Concept", True), stray=1)


def test_classification_result_rejects_stray_field() -> None:
    with pytest.raises(ValidationError):
        ds.ClassificationResult(**_result(stray=1))


def test_topic_metadata_round_trip() -> None:
    metadata = ds.TopicMetadata(
        canonical_id="rate_limiting",
        classification=_result(),
        provenance=_provenance(),
    )
    assert metadata.canonical_id == "rate_limiting"
    assert metadata.provenance.quotation_snippet == metadata.classification.evidence_quote


def test_topic_metadata_quote_mismatch_rejected() -> None:
    """The handoff contract: provenance must carry the verified evidence quote."""
    with pytest.raises(ValidationError):
        ds.TopicMetadata(
            canonical_id="rate_limiting",
            classification=_result(),
            provenance=_provenance(quotation_snippet="a different snippet"),
        )


@pytest.mark.parametrize("bad_id", ["Rate-Limiting", "RateLimiting", "9rate", "rate limiting", ""])
def test_topic_metadata_canonical_id_must_be_snake_case(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        ds.TopicMetadata(
            canonical_id=bad_id,
            classification=_result(),
            provenance=_provenance(),
        )
