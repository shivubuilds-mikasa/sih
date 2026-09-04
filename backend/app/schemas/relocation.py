"""Pydantic schemas for SHARMI Phase 7 — Relocation Optimization API."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class SiteScore(BaseModel):
    """Scored relocation site."""

    site_id: str
    site_name: str
    capacity: int
    distance_km: Annotated[float, Field(ge=0.0)]
    composite_score: Annotated[float, Field(ge=0.0, le=1.0)]
    hazard_safety_score: Annotated[float, Field(ge=0.0, le=1.0)]
    livelihood_score: Annotated[float, Field(ge=0.0, le=1.0)]
    infrastructure_score: Annotated[float, Field(ge=0.0, le=1.0)]
    school_access_score: Annotated[float, Field(ge=0.0, le=1.0)]
    health_access_score: Annotated[float, Field(ge=0.0, le=1.0)]
    distance_penalty: Annotated[float, Field(ge=0.0, le=1.0)]


class CommunityRelocationPlan(BaseModel):
    """Relocation plan for a single community."""

    community_id: str
    community_name: str
    population: Annotated[int, Field(gt=0)]
    zone_type: Literal["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE", "UNAFFECTED"]
    action: Literal["MONITOR", "PREPARE", "INSPECT", "PROTECT", "EVACUATION_ASSESSMENT"]
    urgency_score: Annotated[float, Field(ge=0.0, le=1.0)]
    assigned_site_id: str | None = Field(default=None)
    assigned_site_name: str | None = Field(default=None)
    distance_km: float | None = Field(default=None, ge=0.0)
    explanation: str


class SiteAllocation(BaseModel):
    """Allocation of communities to a relocation site."""

    site_id: str
    site_name: str
    capacity: Annotated[int, Field(gt=0)]
    allocated_population: Annotated[int, Field(ge=0)]
    remaining_capacity: Annotated[int, Field(ge=0)]
    communities: list[str]
    utilization_pct: Annotated[float, Field(ge=0.0, le=100.0)]


class RelocationOptimizationRequest(BaseModel):
    """Request schema for relocation optimization."""

    hazard_id: Annotated[str, Field(description="ID of the hazard to optimize relocation for (e.g., H001)")]


class RelocationOptimizationResponse(BaseModel):
    """Response schema for relocation optimization."""

    hazard_id: str
    hazard_type: str
    total_affected_population: int
    plans: list[CommunityRelocationPlan]
    site_allocations: list[SiteAllocation]
    unallocated_population: Annotated[int, Field(ge=0)]
    explanation: str
    note: str = (
        "This is a deterministic synthetic prototype for demonstration. "
        "The optimization uses a weighted scoring model with synthetic "
        "parameters (hazard safety 35%, livelihood 20%, infrastructure 20%, "
        "school 15%, health 10%, distance penalty 2%/km). "
        "Results are decision-support for officer review only — "
        "NOT an automated evacuation order."
    )