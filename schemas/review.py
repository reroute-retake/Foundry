"""Review Report contract — the Reviewer ↔ Fixer interface (Gates 1 and 2).

A Review Report is an independent, immutable JSON critique of a reviewed artifact
(ubiquitous language: "Review Report"). It is produced at the pipeline's two gates by
a Tier 2 gate script invoking the reviewer model as a tool-less structured-output API
call (docs/pipeline-ledger.md §3), validated against this schema, and persisted as a
`review_report` artifact. Reviews are canonical and preserved for model tuning
(constitution §4).

The Reviewer critiques; it never authors. `fix_instruction` describes what must change
and how success is judged — it must not contain full replacement text.
"""
from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

Severity = Literal["critical", "major", "minor"]
# critical — factual error or hallucination that must never reach Canonical
# major    — violates a binding principle (atomicity, grounding, schema misuse)
# minor    — quality issue; does not block promotion on its own

BLOCKING_SEVERITIES = frozenset({"critical", "major"})

OntologyFlawCategory = Literal[
    "factual_error", "hallucination", "provenance_mismatch", "atomicity_violation",
    "transclusion_violation", "misclassification", "payload_deficiency",
    "definition_quality",
]

EnrichmentFlawCategory = Literal[
    "edge_semantics", "edge_direction", "ghost_unjustified", "flashcard_inaccuracy",
    "flashcard_pedagogy", "analogy_inaccuracy", "diagram_error", "ontology_drift",
]


class _FlawBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    flaw_id: int = Field(..., ge=1, description="Unique within this report; referenced by Fixer resolutions and fix commits.")
    severity: Severity
    field_path: str = Field(..., description="Dot/bracket path into the reviewed JSON (e.g. 'core_definition', 'payload.time_complexity', 'edges[2]').")
    description: str = Field(..., description="What is wrong, stated precisely.")
    evidence_quote: Optional[str] = Field(default=None, description="Verbatim excerpt from the reviewed artifact demonstrating the flaw.")
    source_grounding: Optional[str] = Field(default=None, description="Citation or quotation from the Source Material justifying factual flaws.")
    fix_instruction: str = Field(..., description="Imperative: what must change and the acceptance criterion. MUST NOT contain full replacement text — authorship belongs to the Fixer.")


class OntologyFlaw(_FlawBase):
    category: OntologyFlawCategory


class EnrichmentFlaw(_FlawBase):
    category: EnrichmentFlawCategory


class _ReviewReportBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    report_id: str = Field(..., description="ULID — globally unique, sortable.")
    canonical_id: str
    reviewed_revision: int = Field(..., ge=1, description="Per-node ledger sequence of the reviewed artifact.")
    reviewed_sha256: str = Field(..., description="Hash of the exact artifact reviewed — immutability pin (ADR 002).")
    verdict: Literal["pass", "fail"]
    summary: str = Field(..., description="Reviewer's overall assessment in 1–3 sentences (preserved for model tuning).")
    reviewer_model_id: str = Field(..., description="Model that produced the critique (audit per ADR 002).")
    reviewed_at: str = Field(..., description="ISO 8601 UTC timestamp.")

    @model_validator(mode="after")
    def _verdict_matches_flaws(self) -> "_ReviewReportBase":
        flaws = getattr(self, "flaws", [])
        ids = [f.flaw_id for f in flaws]
        if len(ids) != len(set(ids)):
            raise ValueError("flaw_id values must be unique within a report")
        blocking = any(f.severity in BLOCKING_SEVERITIES for f in flaws)
        if blocking and self.verdict != "fail":
            raise ValueError("verdict must be 'fail' when any critical or major flaw is present")
        if not blocking and self.verdict != "pass":
            raise ValueError("verdict must be 'pass' when no critical or major flaw is present")
        return self


class OntologyReviewReport(_ReviewReportBase):
    """Gate 1 (Phase 4a): critique of a Base Knowledge Draft."""
    gate: Literal["ontology"] = "ontology"
    flaws: List[OntologyFlaw] = Field(default_factory=list)


class EnrichmentReviewReport(_ReviewReportBase):
    """Gate 2 (Phase 7a): critique of edges and pedagogical artifacts."""
    gate: Literal["enrichment"] = "enrichment"
    flaws: List[EnrichmentFlaw] = Field(default_factory=list)


ReviewReport = Annotated[
    Union[OntologyReviewReport, EnrichmentReviewReport],
    Field(discriminator="gate"),
]
