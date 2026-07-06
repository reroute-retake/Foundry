"""enrichment.py — Pass-2 pedagogical artifacts and the base-integrity contract."""
import pytest
from pydantic import TypeAdapter, ValidationError

import enrichment
import taxonomy
from support import make_node


def make_card(**overrides) -> dict:
    card = {
        "card_id": 1,
        "card_type": "basic",
        "front": "What does a Write-Ahead Log guarantee?",
        "back": "Durability: records are persisted before the pages they modify.",
        "tags": ["storage"],
    }
    card.update(overrides)
    return card


def make_enrichment(**overrides) -> dict:
    payload = {
        "flashcards": [make_card()],
        "diagrams": [
            {
                "format": "mermaid",
                "code": "flowchart TD\n  W[Write] --> L[Log]\n  L --> P[Page]",
                "caption": "Writes reach the log before the page.",
            }
        ],
        "analogies": [
            {
                "analogy": "A WAL is like a ship's logbook: events are recorded before actions take effect.",
                "domain": "maritime logbooks",
                "limitations": "Logbooks are for humans; a WAL is replayed mechanically on recovery.",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_enriched_node_round_trip() -> None:
    node = enrichment.EnrichedNode(base=make_node("Data Structure"), enrichment=make_enrichment())
    assert node.base.primary_kind == "Data Structure"
    assert node.enrichment.flashcards[0].card_id == 1
    assert node.enrichment.diagrams[0].format == "mermaid"


def test_base_integrity_dump_matches_input() -> None:
    """The drift-check mechanism: `base` must round-trip identically to Pass-1 content."""
    node_dict = make_node("Data Structure")
    standalone = TypeAdapter(taxonomy.KnowledgeArtifact).validate_python(node_dict)
    wrapped = enrichment.EnrichedNode(base=node_dict, enrichment=make_enrichment())
    assert wrapped.base.model_dump() == standalone.model_dump()


def test_basic_card_requires_back() -> None:
    with pytest.raises(ValidationError):
        enrichment.Flashcard(**make_card(back=None))


def test_reversed_card_valid() -> None:
    card = enrichment.Flashcard(**make_card(card_type="reversed"))
    assert card.card_type == "reversed"


def test_cloze_card_must_not_have_back() -> None:
    with pytest.raises(ValidationError):
        enrichment.Flashcard(
            **make_card(card_type="cloze", front="The WAL is {{c1::append-only}}.")
        )


def test_cloze_card_requires_markup() -> None:
    with pytest.raises(ValidationError):
        enrichment.Flashcard(**make_card(card_type="cloze", front="No markup here.", back=None))


def test_cloze_card_valid() -> None:
    card = enrichment.Flashcard(
        **make_card(card_type="cloze", front="The WAL is {{c1::append-only}}.", back=None)
    )
    assert card.back is None


def test_empty_flashcards_rejected() -> None:
    with pytest.raises(ValidationError):
        enrichment.EnrichmentPayload(**make_enrichment(flashcards=[]))


def test_duplicate_card_ids_rejected() -> None:
    cards = [make_card(), make_card(card_type="reversed")]
    with pytest.raises(ValidationError):
        enrichment.EnrichmentPayload(**make_enrichment(flashcards=cards))


def test_diagram_rejects_prose() -> None:
    with pytest.raises(ValidationError):
        enrichment.Diagram(code="This is a description, not a diagram.", caption="x")


def test_diagram_accepts_known_types_and_init_directive() -> None:
    assert enrichment.Diagram(code="flowchart TD\n A-->B", caption="x").code
    assert enrichment.Diagram(code="%%{init: {'theme':'dark'}}%%\ngraph LR\n A-->B", caption="x").code


def test_analogy_requires_limitations() -> None:
    with pytest.raises(ValidationError) as excinfo:
        enrichment.Analogy(analogy="X is like Y.", domain="post")
    assert "limitations" in str(excinfo.value)


def test_front_length_cap() -> None:
    with pytest.raises(ValidationError):
        enrichment.Flashcard(**make_card(front="x" * 351))
