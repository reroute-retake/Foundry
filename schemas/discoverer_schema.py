from pydantic import BaseModel, Field
from typing import List, Literal

TaxonomyLevel = Literal[
    "Attack Vector", "Mitigation", "Data Structure", "Algorithm", 
    "Pattern", "Failure Mode", "Interface", "Metric", "Tool", "Concept"
]

class EvaluationStep(BaseModel):
    """
    Forces the LLM to write out its reasoning trace BEFORE it emits the boolean condition.
    This acts as a self-attention bridge to prevent instruction amnesia.
    """
    level_name: TaxonomyLevel = Field(..., description="The current taxonomy level being evaluated sequentially.")
    axiological_reasoning: str = Field(..., description="Step-by-step reasoning applying the relevant Axiomatic Tie-Breaker to the text.")
    condition_met: bool = Field(..., description="True if the text matches the level criteria based on the reasoning.")

class ClassificationResult(BaseModel):
    """
    The final output schema expected from the Discoverer model.
    Constrained Decoding will halt generation the moment `condition_met` evaluates to True.
    """
    sequence_trace: List[EvaluationStep] = Field(..., description="The sequential evaluations from Level 1 downwards.")
    final_classification: TaxonomyLevel = Field(..., description="The first level that evaluated to True.")
    extracted_entity_name: str = Field(..., description="The isolated, canonical technical noun being classified.")