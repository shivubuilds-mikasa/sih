"""Phase 3 Cascade Engine API endpoints."""

from fastapi import APIRouter, HTTPException

from ..schemas.cascade import (
    CascadeSimulateRequest,
    CascadeSimulationResponse,
)
from ..services.cascade_engine import simulate_cascade

router = APIRouter(prefix="/cascade", tags=["cascade"])


@router.post("/simulate", response_model=CascadeSimulationResponse)
def simulate_cascade_endpoint(request: CascadeSimulateRequest) -> CascadeSimulationResponse:
    """Simulate infrastructure cascade failure from a hazard.

    Identifies all downstream infrastructure and communities affected
    through dependency relationships above the propagation threshold.
    """
    try:
        result = simulate_cascade(request.hazard_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return CascadeSimulationResponse(
        hazard_id=result.hazard_id,
        hazard_type=result.hazard_type,
        affected=result.affected,
        affected_node_ids=result.affected_node_ids,
        cascade_paths=[
            {"nodes": [{"node_id": n.node_id, "node_type": n.node_type, "name": n.name} for n in path.nodes],
             "propagation_strength": path.propagation_strength}
            for path in result.cascade_paths
        ],
        affected_community_ids=result.affected_community_ids,
        affected_services=[
            {"service_type": s.service_type, "infrastructure_id": s.infrastructure_id, "infrastructure_name": s.infrastructure_name}
            for s in result.affected_services
        ],
        explanation=result.explanation,
    )