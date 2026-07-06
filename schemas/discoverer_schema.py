from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

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
