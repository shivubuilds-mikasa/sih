"""Pydantic schemas for SHARMI Phase 6 — Action Recommendation API."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class CommunityAction(BaseModel):
    """Action recommendation for a single community."""

    community_id: str
    community_name: str
    zone_type: Literal["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE", "UNAFFECTED"]
    action: Literal["MONITOR", "PREPARE", "INSPECT", "PROTECT", "EVACUATION_ASSESSMENT"]
    confidence: Annotated[float, Field(ge=0.0, le=1.0, description="Synthetic prototype confidence score")]
    rationale: str
    direct_risk_level: Literal["LOW", "MEDIUM", "HIGH"] | None = Field(
        default=None, description="Direct risk level (only for DIRECT_HAZARD_ZONE)"
    )
    time_to_impact: float | None = Field(
        default=None, ge=0.0, description="Estimated time-to-impact in arbitrary units"
    )
    affected_services: list[str] | None = Field(
        default=None, description="Affected service types for this community"
    )
    cascade_path: list[str] | None = Field(
        default=None, description="Cascade path for shadow zone communities"
    )


class ActionRecommendationRequest(BaseModel):
    """Request schema for action recommendations."""

    hazard_id: Annotated[str, Field(description="ID of the hazard to generate recommendations for (e.g., H001)")]


class ActionRecommendationResponse(BaseModel):
    """Response schema for action recommendations."""

    hazard_id: str
    hazard_type: str
    recommendations: list[CommunityAction]
    explanation: str
    note: str = (
        "This is a deterministic synthetic prototype for demonstration. "
        "Recommendations are decision-support for officer review only — "
        "NOT autonomous emergency orders. The engine does not directly order "
        "evacuation; EVACUATION_ASSESSMENT means assess feasibility only. "
        "All thresholds (risk, time-to-impact) are synthetic prototype parameters."
    )