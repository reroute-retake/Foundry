from typing import List, Literal, Union, Annotated
from pydantic import BaseModel, Field, ConfigDict

# ==========================================
# Core Primitives
# ==========================================

EdgePredicate = Literal[
    "IS_A", "PART_OF", "IMPLEMENTS", "REQUIRES", 
    "MITIGATES", "CAUSES", "EXEMPLIFIES", "MEASURED_BY", "TRADES_OFF_AGAINST"
]

class Edge(BaseModel):
    predicate: EdgePredicate = Field(..., description="Strictly enforced edge relationship type.")
    target_canonical_id: str = Field(..., description="The canonical_id of the target node.")

class SourceRef(BaseModel):
    document_id: str
    chunk_span: str = Field(..., description="Exact character or token span from the source document.")
    quotation_snippet: str = Field(..., description="Direct text snippet to verify ground truth.")

# ==========================================
# Taxonomy Payloads
# ==========================================

class ConceptPayload(BaseModel):
    pass 

class AlgorithmPayload(BaseModel):
    pre_conditions: List[str]
    post_conditions: List[str]
    time_complexity: str = Field(..., description="Big O notation.")
    space_complexity: str = Field(..., description="Big O notation.")

class PatternPayload(BaseModel):
    primary_bottleneck: str = Field(..., description="Physical or logical scaling limit.")

class DataStructurePayload(BaseModel):
    hardware_target: Literal["Memory", "Disk", "Network"]
    read_amplification_profile: str
    write_amplification_profile: str

class ToolPayload(BaseModel):
    primary_runtime: str
    license_model: str

class InterfacePayload(BaseModel):
    protocol_type: str = Field(..., description="e.g., REST, gRPC, binary")

class MetricPayload(BaseModel):
    unit_of_measurement: str
    mathematical_formalism: str = Field(..., description="LaTeX formatted formula.")

class FailureModePayload(BaseModel):
    trigger_conditions: List[str]
    blast_radius_assessment: str

class AttackVectorPayload(BaseModel):
    exploit_vector: str
    target_surface: str

class MitigationPayload(BaseModel):
    defense_mechanism: str

# ==========================================
# Base Node & Discriminated Subclasses
# ==========================================

class BaseNode(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
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

KnowledgeArtifact = Annotated[
    Union[
        ConceptNode, AlgorithmNode, PatternNode, DataStructureNode, 
        ToolNode, InterfaceNode, MetricNode, FailureModeNode, 
        AttackVectorNode, MitigationNode
    ],
    Field(discriminator="primary_kind")
]