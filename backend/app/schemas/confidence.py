"""Pydantic schemas for SHARMI Phase 8a — Confidence API."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ConfidenceComponents(BaseModel):
    """Individual confidence component scores."""

    data_quality: Annotated[float, Field(ge=0.0, le=1.0)]
    model_coverage: Annotated[float, Field(ge=0.0, le=1.0)]
    input_completeness: Annotated[float, Field(ge=0.0, le=1.0)]
    cascade_strength: Annotated[float, Field(ge=0.0, le=1.0)]
    time_certainty: Annotated[float, Field(ge=0.0, le=1.0)]


class CommunityConfidence(BaseModel):
    """Confidence assessment for a single community's recommendation."""

    community_id: str
    community_name: str
    overall_confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    components: ConfidenceComponents
    explanation: str
    caveats: list[str]


class ConfidenceRequest(BaseModel):
    """Request schema for confidence evaluation."""

    hazard_id: Annotated[str, Field(description="ID of the hazard to evaluate confidence for (e.g., H001)")]


class ConfidenceResponse(BaseModel):
    """Response schema for confidence evaluation."""

    hazard_id: str
    hazard_type: str
    community_confidences: list[CommunityConfidence]
    overall_explanation: str
    note: str = (
        "This is a deterministic synthetic prototype for demonstration. "
        "Confidence scores use synthetic weights (data quality 25%, model "
        "coverage 25%, input completeness 20%, cascade strength 20%, "
        "time certainty 10%). They are NOT statistically calibrated "
        "reliability measures. Results are for officer review only."
    )