"""Phase 8a Confidence API endpoints."""

from fastapi import APIRouter, HTTPException

from ..schemas.confidence import (
    ConfidenceRequest,
    ConfidenceResponse,
    CommunityConfidence,
    ConfidenceComponents,
)
from ..services.confidence_engine import evaluate_confidence

router = APIRouter(prefix="/confidence", tags=["confidence"])


def _to_community_confidence(cc) -> CommunityConfidence:
    """Convert a CommunityConfidence dataclass to Pydantic model."""
    return CommunityConfidence(
        community_id=cc.community_id,
        community_name=cc.community_name,
        overall_confidence=cc.overall_confidence,
        confidence_level=cc.confidence_level,
        components=ConfidenceComponents(
            data_quality=cc.components.data_quality,
            model_coverage=cc.components.model_coverage,
            input_completeness=cc.components.input_completeness,
            cascade_strength=cc.components.cascade_strength,
            time_certainty=cc.components.time_certainty,
        ),
        explanation=cc.explanation,
        caveats=cc.caveats,
    )


@router.post("/evaluate", response_model=ConfidenceResponse)
def evaluate_confidence_endpoint(request: ConfidenceRequest) -> ConfidenceResponse:
    """
    Evaluate confidence for all community recommendations for a hazard.

    Provides per-community confidence scores based on:
    - Data quality (25%): Completeness of input data
    - Model coverage (25%): Whether all relevant factors are modeled
    - Input completeness (20%): Whether all required data is present
    - Cascade strength (20%): Minimum weight along cascade path
    - Time certainty (10%): Proximity to hazard in time-to-impact

    Classification: HIGH (>=0.75), MEDIUM (>=0.50), LOW (<0.50)

    This is a deterministic synthetic prototype for decision-support only.
    """
    try:
        result = evaluate_confidence(request.hazard_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ConfidenceResponse(
        hazard_id=result.hazard_id,
        hazard_type=result.hazard_type,
        community_confidences=[_to_community_confidence(cc) for cc in result.community_confidences],
        overall_explanation=result.overall_explanation,
    )