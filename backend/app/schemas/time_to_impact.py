"""Pydantic schemas for SHARMI Phase 5 — Time-to-Impact API."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ImpactTimelineNode(BaseModel):
    """A single node in the impact timeline."""

    node_id: str
    node_type: Literal["hazard", "infrastructure", "community"]
    name: str
    estimated_propagation_time: Annotated[float, Field(ge=0.0, description="Cumulative time from hazard start")]
    predecessor: str | None = Field(default=None, description="Previous node in the cascade path")
    dependency_weight: float | None = Field(default=None, ge=0.0, le=1.0, description="Weight of the dependency edge")
    explanation: str


class ImpactTimelineRequest(BaseModel):
    """Request schema for impact timeline estimation."""

    hazard_id: Annotated[str, Field(description="ID of the hazard to estimate timeline for (e.g., H001)")]


class ImpactTimelineResponse(BaseModel):
    """Response schema for impact timeline estimation."""

    hazard_id: str
    hazard_type: str
    timeline: list[ImpactTimelineNode]
    explanation: str
    note: str = (
        "This is a deterministic synthetic prototype for demonstration. "
        "Estimated propagation time uses the formula: "
        "BASE_DELAY * (1 - dependency_weight), where BASE_DELAY=100 "
        "arbitrary units. Higher weight = faster propagation. "
        "This is NOT a real-world timing prediction and does not represent "
        "minutes, hours, or days. Dependency weights and the propagation "
        "threshold (0.70) are synthetic demonstration parameters."
    )