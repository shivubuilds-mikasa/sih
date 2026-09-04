"""Phase 7 Relocation Optimization API endpoints."""

from fastapi import APIRouter, HTTPException

from ..schemas.relocation import (
    RelocationOptimizationRequest,
    RelocationOptimizationResponse,
    CommunityRelocationPlan,
    SiteAllocation,
)
from ..services.relocation_engine import optimize_relocation

router = APIRouter(prefix="/relocation", tags=["relocation"])


def _to_community_plan(plan) -> CommunityRelocationPlan:
    """Convert a CommunityRelocationPlan dataclass to Pydantic model."""
    return CommunityRelocationPlan(
        community_id=plan.community_id,
        community_name=plan.community_name,
        population=plan.population,
        zone_type=plan.zone_type,
        action=plan.action,
        urgency_score=plan.urgency_score,
        assigned_site_id=plan.assigned_site_id,
        assigned_site_name=plan.assigned_site_name,
        distance_km=plan.distance_km,
        explanation=plan.explanation,
    )


def _to_site_allocation(alloc) -> SiteAllocation:
    """Convert a SiteAllocation dataclass to Pydantic model."""
    return SiteAllocation(
        site_id=alloc.site_id,
        site_name=alloc.site_name,
        capacity=alloc.capacity,
        allocated_population=alloc.allocated_population,
        remaining_capacity=alloc.remaining_capacity,
        communities=alloc.communities,
        utilization_pct=alloc.utilization_pct,
    )


@router.post("/optimize", response_model=RelocationOptimizationResponse)
def optimize_relocation_endpoint(request: RelocationOptimizationRequest) -> RelocationOptimizationResponse:
    """
    Optimize relocation for communities affected by a hazard.

    Considers:
    - Community zone classification (direct hazard, cascade shadow, unaffected)
    - Action recommendations (urgency)
    - Relocation site capacity, safety scores, distance
    - Community population sizes

    Uses a weighted scoring model:
    - Hazard safety: 35%
    - Livelihood: 20%
    - Infrastructure: 20%
    - School access: 15%
    - Health access: 10%
    - Distance penalty: 2% per km

    Allocates communities by urgency (highest first) to best available sites.
    This is a deterministic synthetic prototype for decision-support only.
    """
    try:
        result = optimize_relocation(request.hazard_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RelocationOptimizationResponse(
        hazard_id=result.hazard_id,
        hazard_type=result.hazard_type,
        total_affected_population=result.total_affected_population,
        plans=[_to_community_plan(p) for p in result.plans],
        site_allocations=[_to_site_allocation(sa) for sa in result.site_allocations],
        unallocated_population=result.unallocated_population,
        explanation=result.explanation,
    )