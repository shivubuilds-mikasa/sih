"""Phase 4 Cascade Shadow Zone API endpoints."""

from fastapi import APIRouter, HTTPException

from ..schemas.shadow_zone import (
    ShadowZoneAnalyzeRequest,
    ShadowZoneAnalyzeResponse,
    ZoneClassification,
)
from ..services.shadow_zone_engine import analyze_shadow_zones

router = APIRouter(prefix="/shadow-zone", tags=["shadow-zone"])


def _to_zone_classification(zc) -> ZoneClassification:
    """Convert a ZoneClassification dataclass to Pydantic model."""
    return ZoneClassification(
        community_id=zc.community_id,
        community_name=zc.community_name,
        zone_type=zc.zone_type,
        direct_hazard_exposure=zc.direct_hazard_exposure,
        cascade_affected=zc.cascade_affected,
        cascade_path=zc.cascade_path,
        explanation=zc.explanation,
    )


@router.post("/analyze", response_model=ShadowZoneAnalyzeResponse)
def analyze_shadow_zone(request: ShadowZoneAnalyzeRequest) -> ShadowZoneAnalyzeResponse:
    """
    Analyze cascade shadow zones for a hazard.

    Identifies communities in three categories:
    - DIRECT_HAZARD_ZONE: Directly affected by the hazard
    - CASCADE_SHADOW_ZONE: Not directly affected but reached through cascade
    - UNAFFECTED: Neither directly affected nor reached via cascade

    This is SHARMI's primary differentiator — finding zones endangered
    indirectly by infrastructure failure chains.
    """
    try:
        result = analyze_shadow_zones(request.hazard_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ShadowZoneAnalyzeResponse(
        hazard_id=result.hazard_id,
        hazard_type=result.hazard_type,
        directly_affected=[_to_zone_classification(z) for z in result.directly_affected],
        cascade_shadow=[_to_zone_classification(z) for z in result.cascade_shadow],
        unaffected=[_to_zone_classification(z) for z in result.unaffected],
        explanation=result.explanation,
    )