"""Phase 5 Time-to-Impact API endpoints."""

from fastapi import APIRouter, HTTPException

from ..schemas.time_to_impact import (
    ImpactTimelineRequest,
    ImpactTimelineResponse,
    ImpactTimelineNode,
)
from ..services.time_to_impact import estimate_impact_timeline

router = APIRouter(prefix="/impact", tags=["impact"])


def _to_timeline_node(node) -> ImpactTimelineNode:
    """Convert a ImpactTimelineNode dataclass to Pydantic model."""
    return ImpactTimelineNode(
        node_id=node.node_id,
        node_type=node.node_type,
        name=node.name,
        estimated_propagation_time=node.estimated_propagation_time,
        predecessor=node.predecessor,
        dependency_weight=node.dependency_weight,
        explanation=node.explanation,
    )


@router.post("/timeline", response_model=ImpactTimelineResponse)
def estimate_timeline(request: ImpactTimelineRequest) -> ImpactTimelineResponse:
    """
    Estimate impact timeline for a hazard.

    Provides a deterministic synthetic estimate of propagation order and
    timing through infrastructure dependencies. Uses the formula:
    BASE_DELAY * (1 - dependency_weight) where BASE_DELAY=100 arbitrary units.

    This is a prototype for demo ordering only — NOT a real-world timing prediction.
    """
    try:
        result = estimate_impact_timeline(request.hazard_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ImpactTimelineResponse(
        hazard_id=result.hazard_id,
        hazard_type=result.hazard_type,
        timeline=[_to_timeline_node(n) for n in result.timeline],
        explanation=result.explanation,
    )