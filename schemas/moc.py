"""Map of Content (MOC) contract — Phase 8 Curator output.

A MOC is a structure note: a hierarchical pathway map through a cluster of the
Knowledge Graph (ubiquitous language: "Map of Content"), plus an ordered learning
sequence. It contains no atomic knowledge of its own — narratives are brief
connective orientation, never content (ADR 005 applies to notes; MOCs organize them).
Stored under .skills-data/mocs/<moc_id>.json (ADR 013).
"""
from typing import List, Optional

from pydantic import Field, model_validator

from taxonomy import StrictModel


class MocEntry(StrictModel):
    canonical_id: str
    annotation: Optional[str] = Field(default=None, max_length=350, description="Why this node belongs here / what to notice. Brief.")


class MocSection(StrictModel):
    heading: str
    narrative: Optional[str] = Field(default=None, max_length=350, description="1–2 sentences of connective orientation.")
    entries: List[MocEntry] = Field(default_factory=list)
    subsections: List["MocSection"] = Field(default_factory=list)

    @model_validator(mode="after")
    def _not_empty(self) -> "MocSection":
        if not self.entries and not self.subsections:
            raise ValueError("a section must contain entries or subsections")
        return self


MocSection.model_rebuild()


class MapOfContent(StrictModel):
    moc_id: str = Field(..., description="Unique snake_case identifier in the MOC namespace.")
    title: str
    scope: str = Field(..., max_length=350, description="The Knowledge Graph cluster this MOC maps.")
    sections: List[MocSection] = Field(..., min_length=1)
    learning_sequence: List[str] = Field(
        default_factory=list,
        description="Recommended traversal order (canonical_ids). Ids must be unique and present in sections.",
    )

    @model_validator(mode="after")
    def _sequence_consistent(self) -> "MapOfContent":
        def collect(sections: List[MocSection]) -> List[str]:
            ids: List[str] = []
            for section in sections:
                ids.extend(entry.canonical_id for entry in section.entries)
                ids.extend(collect(section.subsections))
            return ids

        if len(self.learning_sequence) != len(set(self.learning_sequence)):
            raise ValueError("learning_sequence must not contain duplicates")
        available = set(collect(self.sections))
        unknown = [cid for cid in self.learning_sequence if cid not in available]
        if unknown:
            raise ValueError(f"learning_sequence references ids not present in sections: {unknown}")
        return self
