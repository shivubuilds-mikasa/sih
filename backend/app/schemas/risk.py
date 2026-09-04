"""Pydantic schemas for SHARMI Phase 2 — Risk Engine API."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class RiskComponents(BaseModel):
    """Component values used in risk calculation."""

    hazard_intensity: Annotated[float, Field(ge=0.0, le=1.0)]
    exposure: Annotated[float, Field(ge=0.0, le=1.0)]
    vulnerability: Annotated[float, Field(ge=0.0, le=1.0)]


class RiskWeights(BaseModel):
    """Weights used in risk calculation."""

    hazard_intensity: Annotated[float, Field(ge=0.0, le=1.0)]
    exposure: Annotated[float, Field(ge=0.0, le=1.0)]
    vulnerability: Annotated[float, Field(ge=0.0, le=1.0)]


class RiskCalculateRequest(BaseModel):
    """Request schema for direct risk calculation."""

    hazard_intensity: Annotated[float, Field(ge=0.0, le=1.0, description="Normalized hazard intensity [0, 1]")]
    exposure: Annotated[float, Field(ge=0.0, le=1.0, description="Normalized exposure [0, 1]")]
    vulnerability: Annotated[float, Field(ge=0.0, le=1.0, description="Normalized community vulnerability [0, 1]")]


class RiskCalculateResponse(BaseModel):
    """Response schema for direct risk calculation."""

    risk_score: Annotated[float, Field(ge=0.0, le=1.0)]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    components: RiskComponents
    weights: RiskWeights
    explanation: str


class RankedCommunityRisk(BaseModel):
    """A single community's ranked risk entry."""

    community_id: str
    community_name: str
    risk_score: Annotated[float, Field(ge=0.0, le=1.0)]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]


class RankedRiskResponse(BaseModel):
    """Response schema for ranked risk list."""

    hazard_id: str
    hazard_type: str
    hazard_intensity: float
    exposure_rule: str
    communities: list[RankedCommunityRisk]
    note: str