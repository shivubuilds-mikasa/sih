"""Phase 6 Action Recommendation API endpoints."""

from fastapi import APIRouter, HTTPException

from ..schemas.action import (
    ActionRecommendationRequest,
    ActionRecommendationResponse,
    CommunityAction,
)
from ..services.action_engine import generate_action_recommendations

router = APIRouter(prefix="/actions", tags=["actions"])


def _to_community_action(rec) -> CommunityAction:
    """Convert a CommunityAction dataclass to Pydantic model."""
    return CommunityAction(
        community_id=rec.community_id,
        community_name=rec.community_name,
        zone_type=rec.zone_type,
        action=rec.action,
        confidence=rec.confidence,
        rationale=rec.rationale,
        direct_risk_level=rec.direct_risk_level,
        time_to_impact=rec.time_to_impact,
        affected_services=rec.affected_services,
        cascade_path=rec.cascade_path,
    )


@router.post("/recommend", response_model=ActionRecommendationResponse)
def recommend_actions(request: ActionRecommendationRequest) -> ActionRecommendationResponse:
    """
    Generate action recommendations for all communities for a given hazard.

    Provides explainable prototype recommendations based on:
    - Zone classification (direct hazard / cascade shadow / unaffected)
    - Direct risk level
    - Estimated time-to-impact
    - Affected critical services

    Action categories:
    - MONITOR: Low risk, continue observation
    - PREPARE: Moderate risk, ready resources and contingency plans
    - INSPECT: Verify infrastructure/service status
    - PROTECT: High risk, implement protective measures
    - EVACUATION_ASSESSMENT: Critical risk, assess evacuation feasibility (NOT an order)

    This is a deterministic synthetic prototype for decision-support only.
    """
    try:
        result = generate_action_recommendations(request.hazard_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ActionRecommendationResponse(
        hazard_id=result.hazard_id,
        hazard_type=result.hazard_type,
        recommendations=[_to_community_action(r) for r in result.recommendations],
        explanation=result.explanation,
    )