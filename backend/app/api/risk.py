"""Phase 2 Risk Engine API endpoints."""

from fastapi import APIRouter, HTTPException

from ..schemas.risk import (
    RankedRiskResponse,
    RankedCommunityRisk,
    RiskCalculateRequest,
    RiskCalculateResponse,
)
from ..services.data_loader import get_data_loader
from ..services.risk_engine import calculate_direct_risk, WEIGHT_HAZARD_INTENSITY, WEIGHT_EXPOSURE, WEIGHT_VULNERABILITY

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/calculate", response_model=RiskCalculateResponse)
def calculate_risk(request: RiskCalculateRequest) -> RiskCalculateResponse:
    """Calculate direct risk score from hazard intensity, exposure, and vulnerability.

    All inputs must be normalized values in [0, 1].
    """
    result = calculate_direct_risk(
        hazard_intensity=request.hazard_intensity,
        exposure=request.exposure,
        vulnerability=request.vulnerability,
    )
    return RiskCalculateResponse(**result.to_dict())


@router.get("/ranked", response_model=RankedRiskResponse)
def get_ranked_risk() -> RankedRiskResponse:
    """Get communities ranked by direct risk from the primary demo hazard (H001 - flood).

    Uses a simple deterministic prototype exposure rule:
    - If community is in H001's affected_communities → exposure = 1.0
    - Otherwise → exposure = 0.0

    This is a synthetic prototype rule, NOT a realistic geospatial exposure model.
    """
    loader = get_data_loader()
    dataset = loader.get_dataset()

    # Primary demo hazard for Phase 2
    h001 = next((h for h in dataset.hazards if h.id == "H001"), None)
    if h001 is None:
        raise HTTPException(status_code=500, detail="Primary hazard H001 not found in dataset")

    exposed_community_ids = set(h001.affected_communities)

    ranked = []
    for community in dataset.communities:
        # Simple deterministic exposure rule for prototype
        exposure = 1.0 if community.id in exposed_community_ids else 0.0

        result = calculate_direct_risk(
            hazard_intensity=h001.intensity,
            exposure=exposure,
            vulnerability=community.vulnerability,
        )

        ranked.append(RankedCommunityRisk(
            community_id=community.id,
            community_name=community.name,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
        ))

    # Sort descending by risk score
    ranked.sort(key=lambda x: x.risk_score, reverse=True)

    return RankedRiskResponse(
        hazard_id=h001.id,
        hazard_type=h001.type.value,
        hazard_intensity=h001.intensity,
        exposure_rule="exposure = 1.0 if community in H001.affected_communities else 0.0 (prototype rule)",
        communities=ranked,
        note="This is a deterministic synthetic prototype rule. Exposure is NOT derived from real GIS data. The SHARMI direct-risk model is a transparent baseline, not a scientifically calibrated forecast.",
    )