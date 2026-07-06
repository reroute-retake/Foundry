from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from taxonomy import SourceRef, StrictModel

# CANONICAL EVALUATION ORDER (ADR 007) — DO NOT REORDER.
# The Discoverer evaluates levels sequentially from lowest semantic entropy
# ("Attack Vector") to highest ("Concept"); the first TRUE locks the classification.
# docs/taxonomy.md and Foundry.md mirror this exact sequence.
TaxonomyLevel = Literal[
    "Attack Vector", "Mitigation", "Data Structure", "Algorithm",
    "Pattern", "Failure Mode", "Interface", "Metric", "Tool", "Concept"
]

class EvaluationStep(BaseModel):
    """
    Forces the LLM to write out its reasoning trace BEFORE it emits the boolean condition.
    This acts as a self-attention bridge to prevent instruction amnesia.
    """
    model_config = ConfigDict(extra='forbid')

    level_name: TaxonomyLevel = Field(..., description="The current taxonomy level being evaluated sequentially.")
    axiological_reasoning: str = Field(..., description="Step-by-step reasoning applying the relevant Axiomatic Tie-Breaker to the text.")
    condition_met: bool = Field(..., description="True if the text matches the level criteria based on the reasoning.")

class ClassificationResult(BaseModel):
    """
    The final output schema expected from the Discoverer model.
    Constrained Decoding will halt generation the moment `condition_met` evaluates to True.
    """
    model_config = ConfigDict(extra='forbid')

    sequence_trace: List[EvaluationStep] = Field(..., description="The sequential evaluations from Level 1 downwards.")
    final_classification: TaxonomyLevel = Field(..., description="The first level that evaluated to True.")
    extracted_entity_name: str = Field(..., description="The isolated, canonical technical noun being classified.")
    evidence_quote: str = Field(..., max_length=350, description="Verbatim snippet from the supplied chunk that grounds the entity. The Discoverer script MUST verify this is a substring of the chunk before accepting the result (deterministic hallucination check).")


class TopicMetadata(StrictModel):
    """The Phase-2 `topic_metadata` artifact — the Discoverer → Author handoff.

    Composed deterministically by the Discoverer script, never by the LLM: the LLM
    emits only `classification` (including `evidence_quote`); the script — which chose
    the chunk and therefore knows `document_id` and `chunk_span` — builds `provenance`,
    copying the substring-verified `evidence_quote` into `quotation_snippet`. Per the
    ubiquitous language, Topic Metadata carries a concept's classification and its
    source context, completely devoid of synthesized explanations.
    """
    canonical_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$", description="snake_case id derived by slugifying extracted_entity_name (deterministic script logic).")
    classification: ClassificationResult
    provenance: SourceRef

    @model_validator(mode="after")
    def _quote_consistent(self) -> "TopicMetadata":
        if self.provenance.quotation_snippet != self.classification.evidence_quote:
            raise ValueError("provenance.quotation_snippet must equal classification.evidence_quote")
        return self
