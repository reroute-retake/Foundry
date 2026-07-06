from typing import List, Literal, Union, Annotated
from pydantic import BaseModel, Field, ConfigDict

# ==========================================
# Core Primitives
# ==========================================

EdgePredicate = Literal[
    "IS_A", "PART_OF", "IMPLEMENTS", "REQUIRES",
    "MITIGATES", "CAUSES", "EXEMPLIFIES", "MEASURED_BY", "TRADES_OFF_AGAINST"
]

class StrictModel(BaseModel):
    """Shared base: every Foundry model forbids stray fields (ADR 010; AGENTS.md rule 9)."""
    model_config = ConfigDict(extra='forbid')

class Edge(StrictModel):
    predicate: EdgePredicate = Field(..., description="Strictly enforced edge relationship type.")
    target_canonical_id: str = Field(..., description="The canonical_id of the target node.")

class SourceRef(StrictModel):
    document_id: str
    chunk_span: str = Field(..., description="Exact character or token span from the source document.")
    quotation_snippet: str = Field(..., description="Direct text snippet to verify ground truth.")

# ==========================================
# Taxonomy Payloads
# ==========================================

class ConceptPayload(StrictModel):
    pass

class AlgorithmPayload(StrictModel):
    pre_conditions: List[str]
    post_conditions: List[str]
    time_complexity: str = Field(..., description="Big O notation.")
    space_complexity: str = Field(..., description="Big O notation.")

class PatternPayload(StrictModel):
    primary_bottleneck: str = Field(..., description="Physical or logical scaling limit.")

class DataStructurePayload(StrictModel):
    hardware_target: Literal["Memory", "Disk", "Network"]
    read_amplification_profile: str
    write_amplification_profile: str

class ToolPayload(StrictModel):
    primary_runtime: str
    license_model: str

class InterfacePayload(StrictModel):
    protocol_type: str = Field(..., description="e.g., REST, gRPC, binary")

class MetricPayload(StrictModel):
    unit_of_measurement: str
    mathematical_formalism: str = Field(..., description="LaTeX formatted formula.")

class FailureModePayload(StrictModel):
    trigger_conditions: List[str]
    blast_radius_assessment: str

class AttackVectorPayload(StrictModel):
    exploit_vector: str
    target_surface: str

class MitigationPayload(StrictModel):
    defense_mechanism: str

# ==========================================
# Base Node & Discriminated Subclasses
# ==========================================

class BaseNode(StrictModel):
    canonical_id: str = Field(..., description="Globally unique, snake_case identifier.")
    title: str
    aliases: List[str] = Field(default_factory=list)
    core_definition: str = Field(..., max_length=350, description="Strictly atomic definition. No markdown lists.")
    operational_context: str
    edges: List[Edge] = Field(default_factory=list)
    provenance: SourceRef

class ConceptNode(BaseNode):
    primary_kind: Literal["Concept"] = "Concept"
    payload: ConceptPayload

class AlgorithmNode(BaseNode):
    primary_kind: Literal["Algorithm"] = "Algorithm"
    payload: AlgorithmPayload

class PatternNode(BaseNode):
    primary_kind: Literal["Pattern"] = "Pattern"
    payload: PatternPayload

class DataStructureNode(BaseNode):
    primary_kind: Literal["Data Structure"] = "Data Structure"
    payload: DataStructurePayload

class ToolNode(BaseNode):
    primary_kind: Literal["Tool"] = "Tool"
    payload: ToolPayload

class InterfaceNode(BaseNode):
    primary_kind: Literal["Interface"] = "Interface"
    payload: InterfacePayload

class MetricNode(BaseNode):
    primary_kind: Literal["Metric"] = "Metric"
    payload: MetricPayload

class FailureModeNode(BaseNode):
    primary_kind: Literal["Failure Mode"] = "Failure Mode"
    payload: FailureModePayload

class AttackVectorNode(BaseNode):
    primary_kind: Literal["Attack Vector"] = "Attack Vector"
    payload: AttackVectorPayload

class MitigationNode(BaseNode):
    primary_kind: Literal["Mitigation"] = "Mitigation"
    payload: MitigationPayload

# ==========================================
# Orchestrator Union Schema
# ==========================================

# Members listed in the CANONICAL EVALUATION ORDER (ADR 007) for consistency with
# docs/taxonomy.md and schemas/discoverer_schema.py. Validation routing is O(1) via
# the `primary_kind` discriminator, so this ordering is documentation, not logic.
KnowledgeArtifact = Annotated[
    Union[
        AttackVectorNode, MitigationNode, DataStructureNode, AlgorithmNode,
        PatternNode, FailureModeNode, InterfaceNode, MetricNode,
        ToolNode, ConceptNode
    ],
    Field(discriminator="primary_kind")
]
