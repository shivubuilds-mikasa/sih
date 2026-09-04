"""Pydantic schemas for SHARMI Phase 9 — End-to-End Decision Engine API."""

from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field


class SHARMIRequest(BaseModel):
    """Request schema for SHARMI analysis."""

    hazard_id: Annotated[str, Field(description="ID of the hazard to analyze (e.g., H001)")]


class ConfidenceComponentsResponse(BaseModel):
    """Confidence component scores."""

    data_quality: float
    model_coverage: float
    input_completeness: float
    cascade_strength: float
    time_certainty: float


class CommunityAnalysisResponse(BaseModel):
    """Complete analysis for a single community."""

    community_id: str
    community_name: str
    population: int
    risk_score: Annotated[float, Field(ge=0.0, le=1.0)]
    risk_level: str
    zone_type: Literal["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE", "UNAFFECTED"]
    time_to_impact: Optional[float] = None
    action: str
    direct_risk_level: Optional[str] = None
    affected_services: list[str] = []
    relocation_site: Optional[str] = None
    relocation_urgency: Optional[str] = None
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)]
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    confidence_components: ConfidenceComponentsResponse
    confidence_explanation: str
    confidence_caveats: list[str]
    cascade_path: Optional[str] = None


class HazardSummaryResponse(BaseModel):
    """Summary statistics for the hazard analysis."""

    hazard_id: str
    hazard_type: str
    hazard_intensity: float
    hazard_probability: float
    total_communities: int
    directly_affected: int
    cascade_shadow: int
    unaffected: int
    total_population_at_risk: int
    highest_risk_community: str
    highest_risk_score: float
    evacuation_recommended: int
    shelter_in_place: int
    monitor_only: int
    relocation_required: int


class CascadePathSummaryResponse(BaseModel):
    """Cascade path summary."""

    path_id: str
    nodes: list[dict]
    propagation_strength: float
    total_propagation_time: float


class RelocationSiteSummaryResponse(BaseModel):
    """Relocation site summary."""

    site_id: str
    site_name: str
    composite_score: float
    capacity: int
    allocated_communities: int
    allocated_population: int
    hazard_safety_score: float
    livelihood_score: float
    infrastructure_score: float
    school_score: float
    health_score: float
    distance_penalty: float


class SHARMIResponse(BaseModel):
    """Complete SHARMI analysis response."""

    hazard_id: str
    hazard_type: str
    analysis_timestamp: str
    summary: HazardSummaryResponse
    community_analyses: list[CommunityAnalysisResponse]
    cascade_paths_summary: list[CascadePathSummaryResponse]
    relocation_sites_summary: list[RelocationSiteSummaryResponse]
    overall_explanation: str
    prototype_note: str = (
        "This is a deterministic synthetic prototype for SIH demonstration. "
        "All scores, classifications, and recommendations use synthetic models "
        "with prototype parameters. Results are for officer decision-support only "
        "and are NOT statistically calibrated. Do not use for real emergency decisions."
    )


# Decision override schemas (re-exported for convenience)
class OverrideDecision(str, Enum):
    ACCEPT = "ACCEPT"
    MODIFY = "MODIFY"
    REJECT = "REJECT"


class DecisionCategory(str, Enum):
    SHADOW_ZONE = "SHADOW_ZONE"
    ACTION_RECOMMENDATION = "ACTION_RECOMMENDATION"
    RELOCATION = "RELOCATION"
    CONFIDENCE = "CONFIDENCE"
    TIME_TO_IMPACT = "TIME_TO_IMPACT"


class SHARMIOverrideRequest(BaseModel):
    """Request schema for SHARMI decision override."""

    hazard_id: Annotated[str, Field(description="Hazard ID")]
    community_id: Annotated[str, Field(description="Community ID")]
    officer_id: Annotated[str, Field(description="Officer ID")]
    officer_name: Annotated[str, Field(description="Officer name")]
    category: DecisionCategory
    decision: OverrideDecision
    justification: Annotated[str, Field(min_length=1, description="Justification for override")]
    modified_recommendation: Optional[str] = None


class SHARMIOverrideResponse(BaseModel):
    """Response schema for SHARMI decision override."""

    audit_id: str
    final_recommendation: str
    decision: OverrideDecision
    timestamp: str


class SHARMIAuditEntry(BaseModel):
    """Audit log entry."""

    audit_id: str
    timestamp: str
    hazard_id: str
    hazard_type: str
    community_id: str
    community_name: str
    category: DecisionCategory
    officer_id: str
    officer_name: str
    decision: OverrideDecision
    original_recommendation: str
    final_recommendation: str
    justification: str
    zone_type: str
    risk_level: Optional[str] = None
    time_to_impact: Optional[float] = None
    confidence_score: Optional[float] = None
    confidence_level: Optional[str] = None


class SHARMIAuditRequest(BaseModel):
    """Request schema for audit log query."""

    hazard_id: Optional[str] = None
    community_id: Optional[str] = None
    officer_id: Optional[str] = None
    category: Optional[DecisionCategory] = None
    decision: Optional[OverrideDecision] = None
    limit: Annotated[int, Field(ge=1, le=1000, default=100)] = 100
    offset: Annotated[int, Field(ge=0, default=0)] = 0


class SHARMIAuditResponse(BaseModel):
    """Response schema for audit log query."""

    entries: list[SHARMIAuditEntry]
    total: int
    limit: int
    offset: int


class SHARMIAuditSummaryResponse(BaseModel):
    """Response schema for audit summary."""

    total_entries: int
    by_decision: dict[str, int]
    by_category: dict[str, int]
    by_officer: dict[str, int]
    note: str = "This is a synthetic prototype audit log. Data is not persisted across restarts."