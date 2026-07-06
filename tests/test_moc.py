"""moc.py — hierarchical structure, learning-sequence consistency, strictness."""
import pytest
from pydantic import ValidationError

import moc


def make_moc(**overrides) -> dict:
    data = {
        "moc_id": "replication_moc",
        "title": "Replication",
        "scope": "Replication strategies in distributed databases.",
        "sections": [
            {
                "heading": "Foundations",
                "narrative": "Start with the guarantees, then the mechanisms.",
                "entries": [
                    {"canonical_id": "eventual_consistency", "annotation": "The guarantee everything else trades against."},
                    {"canonical_id": "replication_lag"},
                ],
                "subsections": [
                    {
                        "heading": "Leaderless",
                        "entries": [{"canonical_id": "leaderless_replication"}],
                        "subsections": [],
                    }
                ],
            }
        ],
        "learning_sequence": ["eventual_consistency", "replication_lag", "leaderless_replication"],
    }
    data.update(overrides)
    return data


def test_nested_moc_round_trip() -> None:
    m = moc.MapOfContent(**make_moc())
    assert m.sections[0].subsections[0].heading == "Leaderless"
    assert len(m.learning_sequence) == 3


def test_empty_section_rejected() -> None:
    with pytest.raises(ValidationError):
        moc.MocSection(heading="Empty", entries=[], subsections=[])


def test_sections_must_be_nonempty() -> None:
    with pytest.raises(ValidationError):
        moc.MapOfContent(**make_moc(sections=[], learning_sequence=[]))


def test_duplicate_learning_sequence_rejected() -> None:
    with pytest.raises(ValidationError):
        moc.MapOfContent(
            **make_moc(learning_sequence=["eventual_consistency", "eventual_consistency"])
        )


def test_unknown_sequence_id_rejected() -> None:
    with pytest.raises(ValidationError) as excinfo:
        moc.MapOfContent(**make_moc(learning_sequence=["not_in_sections"]))
    assert "not_in_sections" in str(excinfo.value)


def test_sequence_subset_is_valid() -> None:
    m = moc.MapOfContent(**make_moc(learning_sequence=["leaderless_replication"]))
    assert m.learning_sequence == ["leaderless_replication"]


def test_annotation_length_cap() -> None:
    with pytest.raises(ValidationError):
        moc.MocEntry(canonical_id="x", annotation="y" * 351)


def test_stray_field_rejected() -> None:
    with pytest.raises(ValidationError):
        moc.MapOfContent(**make_moc(), stray=1)
