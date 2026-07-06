"""Pass-2 Enrichment contract — pedagogical artifacts layered over validated ontology.

Produced by the Enricher (Phase 6) and persisted as the `enriched_node` /
`canonical_node` artifact shape. The Enricher must not alter ontological facts
(constitution §6): `base` must be byte-identical (canonical JSON) to the consumed
linked revision — the ENRICH script's ontology-drift check compares hashes of that
subtree (docs/pipeline-ledger.md §3).
"""
from typing import List, Literal, Optional

from pydantic import Field, field_validator, model_validator

from taxonomy import KnowledgeArtifact, StrictModel

MERMAID_DIAGRAM_TYPES = (
    "flowchart", "graph", "sequenceDiagram", "stateDiagram", "stateDiagram-v2",
    "classDiagram", "erDiagram", "mindmap", "timeline", "journey", "gantt", "pie",
)


class Flashcard(StrictModel):
    card_id: int = Field(..., ge=1, description="Unique within this node; the Renderer derives the Anki GUID as '<canonical_id>::<card_id>'.")
    card_type: Literal["basic", "reversed", "cloze"]
    front: str = Field(..., max_length=350, description="Question (basic/reversed) or cloze text with {{c1::...}} markup (cloze). One fact per card (ADR 005).")
    back: Optional[str] = Field(default=None, max_length=350, description="Answer. Required for basic/reversed; must be omitted for cloze.")
    tags: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _back_matches_type(self) -> "Flashcard":
        if self.card_type == "cloze":
            if self.back is not None:
                raise ValueError("cloze cards must not define 'back'")
            if "{{c" not in self.front:
                raise ValueError("cloze cards must contain '{{c1::...}}' markup in 'front'")
        elif self.back is None:
            raise ValueError(f"{self.card_type} cards require 'back'")
        return self


class Diagram(StrictModel):
    format: Literal["mermaid"] = "mermaid"
    code: str = Field(..., description="Mermaid source. Must begin with a known diagram-type keyword (or an %%{init}%% directive).")
    caption: str = Field(..., max_length=350, description="What the diagram shows, in one sentence.")

    @field_validator("code")
    @classmethod
    def _looks_like_mermaid(cls, value: str) -> str:
        stripped = value.strip()
        first = stripped.split()[0] if stripped else ""
        if not (first in MERMAID_DIAGRAM_TYPES or first.startswith("%%")):
            raise ValueError(f"code must begin with a Mermaid diagram type, got {first!r}")
        return value


class Analogy(StrictModel):
    analogy: str = Field(..., max_length=350, description="The mapping itself: 'X is like Y because...'.")
    domain: str = Field(..., description="The familiar domain the analogy draws from (e.g., 'postal service').")
    limitations: str = Field(..., max_length=350, description="Where the analogy breaks down — required; every analogy lies somewhere.")


class EnrichmentPayload(StrictModel):
    flashcards: List[Flashcard] = Field(..., min_length=1, description="At least one card per node — retention is the product (ADR 005).")
    diagrams: List[Diagram] = Field(default_factory=list)
    analogies: List[Analogy] = Field(default_factory=list)

    @model_validator(mode="after")
    def _card_ids_unique(self) -> "EnrichmentPayload":
        ids = [card.card_id for card in self.flashcards]
        if len(ids) != len(set(ids)):
            raise ValueError("card_id values must be unique within a node")
        return self


class EnrichedNode(StrictModel):
    """The `enriched_node` / `canonical_node` artifact shape (composition, not mutation)."""
    base: KnowledgeArtifact
    enrichment: EnrichmentPayload
