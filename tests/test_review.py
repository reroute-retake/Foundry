"""review.py — gate discrimination, verdict consistency, closed categories."""
import pytest
from pydantic import TypeAdapter, ValidationError

import review
from support import make_flaw, make_report_base

ADAPTER = TypeAdapter(review.ReviewReport)


def test_ontology_report_round_trip() -> None:
    report = ADAPTER.validate_python(
        {**make_report_base(), "gate": "ontology", "verdict": "fail", "flaws": [make_flaw()]}
    )
    assert type(report).__name__ == "OntologyReviewReport"
    assert report.flaws[0].severity == "critical"


def test_enrichment_report_round_trip() -> None:
    flaw = make_flaw(category="edge_semantics", field_path="edges[0]")
    report = ADAPTER.validate_python(
        {**make_report_base(), "gate": "enrichment", "verdict": "fail", "flaws": [flaw]}
    )
    assert type(report).__name__ == "EnrichmentReviewReport"


def test_clean_pass_round_trip() -> None:
    report = ADAPTER.validate_python(
        {**make_report_base(), "gate": "ontology", "verdict": "pass", "flaws": []}
    )
    assert report.verdict == "pass"


def test_pass_with_only_minor_flaws_is_valid() -> None:
    flaw = make_flaw(severity="minor", category="definition_quality")
    report = ADAPTER.validate_python(
        {**make_report_base(), "gate": "ontology", "verdict": "pass", "flaws": [flaw]}
    )
    assert report.verdict == "pass"


def test_rejects_pass_with_critical_flaw() -> None:
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(
            {**make_report_base(), "gate": "ontology", "verdict": "pass", "flaws": [make_flaw()]}
        )


def test_rejects_fail_with_only_minor_flaws() -> None:
    flaw = make_flaw(severity="minor")
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(
            {**make_report_base(), "gate": "ontology", "verdict": "fail", "flaws": [flaw]}
        )


def test_rejects_duplicate_flaw_ids() -> None:
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(
            {
                **make_report_base(),
                "gate": "ontology",
                "verdict": "fail",
                "flaws": [make_flaw(), make_flaw(severity="major")],
            }
        )


def test_rejects_ontology_category_on_enrichment_gate() -> None:
    """Flaw vocabularies are gate-specific and closed."""
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(
            {**make_report_base(), "gate": "enrichment", "verdict": "fail", "flaws": [make_flaw()]}
        )


def test_rejects_stray_field_on_report() -> None:
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(
            {**make_report_base(), "gate": "ontology", "verdict": "pass", "flaws": [], "stray": 1}
        )


def test_fix_instruction_is_required() -> None:
    flaw = make_flaw()
    del flaw["fix_instruction"]
    with pytest.raises(ValidationError) as excinfo:
        ADAPTER.validate_python(
            {**make_report_base(), "gate": "ontology", "verdict": "fail", "flaws": [flaw]}
        )
    assert "fix_instruction" in str(excinfo.value)
