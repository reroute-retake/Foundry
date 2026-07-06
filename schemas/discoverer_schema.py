import re
import unicodedata
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

# Typographic characters LLMs habitually fold to ASCII (or vice versa).
_TYPOGRAPHIC_FOLD = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "–": "-", "—": "-", "−": "-",
})

# Markdown link syntax: [text](url) -> text.
_MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# Markdown emphasis/code markers LLMs strip when quoting: * _ ` ~ .
# '#' is deliberately NOT stripped: folding it would silently equate
# "C#" with "C" and "issue #42" with "issue 42" — semantic erasure.
_MARKDOWN_MARKS = re.compile(r"[*_`~]")


def normalize_quote(text: str) -> str:
    """Canonical normalization for evidence-quote comparison (register #36, #43).

    Conservative by design: NFKC (handles ellipses, ligatures, fullwidth forms,
    non-breaking spaces), typographic quote/dash folding, markdown folding
    (emphasis/code markers stripped, links unwrapped to their text), and
    whitespace-run collapsing. It deliberately does NOT strip punctuation
    wholesale — aggressive normalization creates false-positive matches on
    short quotes.

    Markdown folding is REQUIRED, not optional: the source chunk is Extracted
    Markdown, LLMs strip formatting when quoting, and the recovered SOURCE span
    (with markdown) must normalized-match the LLM's quote (without it) for the
    TopicMetadata validator to accept the handoff.

    This function is the single source of truth: the schema validator below and the
    Discoverer script's chunk-matching pass MUST both use it, so the check and the
    checker can never drift. The script may employ more aggressive tiers to LOCATE
    the span in the chunk, but the recovered source text it stores must still pass
    this conservative equivalence — a quote too mangled to pass is weak grounding
    and should trigger an LLM retry, not a workaround.
    """
    unlinked = _MARKDOWN_LINK.sub(r"\1", text)
    folded = unicodedata.normalize("NFKC", unlinked).translate(_TYPOGRAPHIC_FOLD)
    stripped = _MARKDOWN_MARKS.sub("", folded)
    return re.sub(r"\s+", " ", stripped).strip()


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
    evidence_quote: str = Field(..., max_length=350, description="Snippet from the supplied chunk that grounds the entity. LLMs fold smart quotes and collapse whitespace, so the Discoverer script MUST locate this in the chunk via normalize_quote() matching — never naive substring — and store the recovered SOURCE span in provenance.quotation_snippet.")


class TopicMetadata(StrictModel):
    """The Phase-2 `topic_metadata` artifact — the Discoverer → Author handoff.

    Composed deterministically by the Discoverer script, never by the LLM: the LLM
    emits only `classification` (including `evidence_quote`); the script — which chose
    the chunk and therefore knows `document_id` and `chunk_span` — builds `provenance`,
    storing the span it RECOVERED FROM THE SOURCE in `quotation_snippet` (verbatim
    source text, provably present in the document). The recovered span and the LLM's
    quote must agree under normalize_quote(); typographic divergence is tolerated,
    semantic divergence is not. Per the ubiquitous language, Topic Metadata carries a
    concept's classification and its source context, completely devoid of synthesized
    explanations.
    """
    canonical_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$", max_length=64, description="snake_case id derived by slugifying extracted_entity_name (deterministic script logic). Length-capped: ids map to filesystem paths (decision register #37).")
    classification: ClassificationResult
    provenance: SourceRef

    @model_validator(mode="after")
    def _quote_consistent(self) -> "TopicMetadata":
        if normalize_quote(self.provenance.quotation_snippet) != normalize_quote(self.classification.evidence_quote):
            raise ValueError(
                "provenance.quotation_snippet must normalized-match classification.evidence_quote (normalize_quote)"
            )
        return self
