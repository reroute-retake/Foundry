"""Pipeline Ledger contract (ADR 017).

The ledger is the sole sequencing authority for the Foundry pipeline. Events are
canonical and append-only (ledger.jsonl); the manifest is a derived, rebuildable
snapshot (manifest.json). See docs/pipeline-ledger.md.
"""
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# ==========================================
# Core Vocabulary
# ==========================================

NodeState = Literal[
    "GHOST",                # stub created for a dangling edge target (ADR 009)
    "DISCOVERED",           # Topic Metadata exists (Phase 2)
    "DRAFTED",              # Base Knowledge Draft exists (Phase 3, or Gate 1 fix)
    "BASE_REVIEWED",        # Gate 1 Review Report exists (Phase 4a)
    "VALIDATED",            # passed Gate 1 (Phase 4b)
    "LINKED",               # formal edges injected (Phase 5)
    "ENRICHED",             # pedagogical artifacts added (Phase 6, or Gate 2 fix)
    "ENRICHMENT_REVIEWED",  # Gate 2 Review Report exists (Phase 7a)
    "CANONICAL",            # passed Gate 2 (Phase 7b) — terminal
    "QUARANTINED",          # manual intervention required
]

NodeAction = Literal[
    "DISCOVER", "DRAFT", "REVIEW_BASE", "FIX_BASE", "PROMOTE_BASE",
    "LINK", "CREATE_GHOST", "ENRICH", "REVIEW_ENRICHMENT",
    "FIX_ENRICHMENT", "PROMOTE_CANONICAL", "QUARANTINE", "RELEASE",
]

DocumentAction = Literal["REGISTER", "EXTRACT"]

ArtifactKind = Literal[
    "extracted_text", "topic_metadata", "knowledge_draft", "review_report",
    "validated_node", "linked_node", "enriched_node", "canonical_node", "ghost_stub",
]

RoleName = Literal[
    "Extractor", "Discoverer", "Author", "Reviewer", "Fixer",
    "Linker", "Enricher", "Curator", "Renderer", "Operator",
]

# Bounded gate repair (constitution: "Not an Agentic Loop").
MAX_FIX_CYCLES_PER_GATE: int = 2


class ActorRef(BaseModel):
    model_config = ConfigDict(extra='forbid')

    role: RoleName
    execution: Literal["tier1_agent", "tier2_script", "deterministic", "human"]
    model_id: Optional[str] = Field(
        default=None,
        description="LLM identifier when an LLM produced the content (audit trail per ADR 002).",
    )


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra='forbid')

    kind: ArtifactKind
    path: str = Field(..., description="Path relative to .skills-data/.")
    revision: int = Field(..., ge=1, description="The per-node ledger sequence that produced this artifact.")
    sha256: str = Field(..., description="Content hash — immutability witness (ADR 002).")

# ==========================================
# Ledger Events (append-only; discriminated union per ADR 010)
# ==========================================

class NodeTransitionEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')

    event_type: Literal["node_transition"] = "node_transition"
    event_id: str = Field(..., description="ULID — globally unique, lexicographically sortable.")
    canonical_id: str
    sequence: int = Field(..., ge=1, description="Per-node monotonic counter.")
    action: NodeAction
    from_state: Optional[NodeState] = Field(
        default=None,
        description="None only for node-creating actions (DISCOVER from absent, CREATE_GHOST).",
    )
    to_state: NodeState
    actor: ActorRef
    produced: List[ArtifactRef] = Field(default_factory=list)
    consumed: List[ArtifactRef] = Field(default_factory=list)
    verdict: Optional[Literal["pass", "fail"]] = Field(
        default=None, description="Required for REVIEW_* actions; None otherwise."
    )
    fix_cycle: int = Field(default=0, ge=0, description="Gate repair cycle counter after this event.")
    note: Optional[str] = None
    occurred_at: str = Field(..., description="ISO 8601 UTC timestamp.")


class DocumentEvent(BaseModel):
    model_config = ConfigDict(extra='forbid')

    event_type: Literal["document"] = "document"
    event_id: str
    document_id: str
    action: DocumentAction
    source_sha256: str = Field(..., description="Hash of the Source Material file.")
    actor: ActorRef
    produced: List[ArtifactRef] = Field(default_factory=list)
    occurred_at: str


LedgerEvent = Annotated[
    Union[NodeTransitionEvent, DocumentEvent],
    Field(discriminator="event_type"),
]

# ==========================================
# Ghost Stub (ADR 009) — deliberately NOT a BaseNode
# ==========================================

class GhostStub(BaseModel):
    model_config = ConfigDict(extra='forbid')

    canonical_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$", max_length=64, description="snake_case id. A ghost creates nodes/<id>/ on disk, so it is a filesystem anchor: pattern and length are enforced here (decision register #30/#37).")
    title_guess: str
    referenced_by: str = Field(..., description="canonical_id of the node whose edge created this stub.")
    predicate: str = Field(..., description="Edge predicate that referenced the missing target.")
    created_at: str

# ==========================================
# Derived Manifest (fold of the event log — rebuildable, never authoritative)
# ==========================================

class NodeManifestEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

    canonical_id: str
    state: NodeState
    revision: int
    fix_cycle_gate1: int = 0
    fix_cycle_gate2: int = 0
    last_event_id: str
    last_sequence: int
    current_artifacts: List[ArtifactRef] = Field(default_factory=list)
    updated_at: str


class DocumentManifestEntry(BaseModel):
    model_config = ConfigDict(extra='forbid')

    document_id: str
    source_sha256: str
    extracted: bool = False
    extracted_text: Optional[ArtifactRef] = None


class LedgerManifest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    ledger_version: Literal["1"] = "1"
    nodes: Dict[str, NodeManifestEntry] = Field(default_factory=dict)
    documents: Dict[str, DocumentManifestEntry] = Field(default_factory=dict)
    folded_through_event_id: Optional[str] = Field(
        default=None, description="Last event folded into this snapshot."
    )

# ==========================================
# Transition Rules — the machine-readable precondition table.
# Every mutation script MUST validate against these before executing (ADR 017).
# ==========================================

class TransitionRule(BaseModel):
    model_config = ConfigDict(extra='forbid')

    action: NodeAction
    phase: str
    allowed_from: List[Optional[NodeState]] = Field(
        ..., description="None in this list means 'node must not exist yet'."
    )
    to_state: NodeState
    executed_by: RoleName
    requires_verdict: Optional[Literal["pass", "fail"]] = Field(
        default=None, description="Precondition on the node's LATEST review verdict."
    )
    bounded_by_fix_cycle: bool = Field(
        default=False,
        description="If True, refused once the gate's cycle reaches MAX_FIX_CYCLES_PER_GATE; script must QUARANTINE instead.",
    )
    requires_document_extracted: bool = False
    produces: List[ArtifactKind] = Field(default_factory=list)


TRANSITION_RULES: List[TransitionRule] = [
    TransitionRule(action="DISCOVER", phase="2", allowed_from=[None, "GHOST"], to_state="DISCOVERED",
                   executed_by="Discoverer", requires_document_extracted=True, produces=["topic_metadata"]),
    TransitionRule(action="DRAFT", phase="3", allowed_from=["DISCOVERED"], to_state="DRAFTED",
                   executed_by="Author", produces=["knowledge_draft"]),
    TransitionRule(action="REVIEW_BASE", phase="4a", allowed_from=["DRAFTED"], to_state="BASE_REVIEWED",
                   executed_by="Reviewer", produces=["review_report"]),
    TransitionRule(action="PROMOTE_BASE", phase="4b", allowed_from=["BASE_REVIEWED"], to_state="VALIDATED",
                   executed_by="Fixer", requires_verdict="pass", produces=["validated_node"]),
    TransitionRule(action="FIX_BASE", phase="4b", allowed_from=["BASE_REVIEWED"], to_state="DRAFTED",
                   executed_by="Fixer", requires_verdict="fail", bounded_by_fix_cycle=True,
                   produces=["knowledge_draft"]),
    TransitionRule(action="LINK", phase="5", allowed_from=["VALIDATED"], to_state="LINKED",
                   executed_by="Linker", produces=["linked_node"]),
    TransitionRule(action="CREATE_GHOST", phase="5", allowed_from=[None], to_state="GHOST",
                   executed_by="Linker", produces=["ghost_stub"]),
    TransitionRule(action="ENRICH", phase="6", allowed_from=["LINKED"], to_state="ENRICHED",
                   executed_by="Enricher", produces=["enriched_node"]),
    TransitionRule(action="REVIEW_ENRICHMENT", phase="7a", allowed_from=["ENRICHED"],
                   to_state="ENRICHMENT_REVIEWED", executed_by="Reviewer", produces=["review_report"]),
    TransitionRule(action="PROMOTE_CANONICAL", phase="7b", allowed_from=["ENRICHMENT_REVIEWED"],
                   to_state="CANONICAL", executed_by="Fixer", requires_verdict="pass",
                   produces=["canonical_node"]),
    TransitionRule(action="FIX_ENRICHMENT", phase="7b", allowed_from=["ENRICHMENT_REVIEWED"],
                   to_state="ENRICHED", executed_by="Fixer", requires_verdict="fail",
                   bounded_by_fix_cycle=True, produces=["enriched_node"]),
    TransitionRule(action="QUARANTINE", phase="any",
                   allowed_from=["DISCOVERED", "DRAFTED", "BASE_REVIEWED", "VALIDATED",
                                 "LINKED", "ENRICHED", "ENRICHMENT_REVIEWED"],
                   to_state="QUARANTINED", executed_by="Operator", produces=[]),
    # RELEASE is intentionally absent from this table: its to_state is dynamic
    # (any state present in the node's own history), chosen by the Operator with a
    # mandatory note. The release script enforces history membership.
]
