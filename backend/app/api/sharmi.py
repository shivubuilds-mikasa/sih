"""Phase 9 SHARMI End-to-End Decision Engine API endpoints."""

from fastapi import APIRouter, HTTPException

from ..schemas.sharmi import (
    SHARMIRequest,
    SHARMIResponse,
    CommunityAnalysisResponse,
    HazardSummaryResponse,
    CascadePathSummaryResponse,
    RelocationSiteSummaryResponse,
    ConfidenceComponentsResponse,
    SHARMIOverrideRequest,
    SHARMIOverrideResponse,
    SHARMIAuditRequest,
    SHARMIAuditResponse,
    SHARMIAuditEntry,
    SHARMIAuditSummaryResponse,
    OverrideDecision,
    DecisionCategory,
)
from ..services.sharmi_engine import (
    run_full_analysis,
    submit_decision_override,
    get_decision_audit,
    get_audit_log_summary,
)
from ..services.decision_service import (
    OverrideDecision as ServiceOverrideDecision,
    DecisionCategory as ServiceDecisionCategory,
)

router = APIRouter(prefix="/sharmi", tags=["sharmi"])


def _to_community_analysis_response(ca) -> CommunityAnalysisResponse:
    """Convert CommunityAnalysis dataclass to Pydantic model."""
    return CommunityAnalysisResponse(
        community_id=ca.community_id,
        community_name=ca.community_name,
        population=ca.population,
        risk_score=ca.risk_score,
        risk_level=ca.risk_level,
        zone_type=ca.zone_type,
        time_to_impact=ca.time_to_impact,
        action=ca.action,
        direct_risk_level=ca.direct_risk_level,
        affected_services=ca.affected_services,
        relocation_site=ca.relocation_site,
        relocation_urgency=ca.relocation_urgency,
        confidence_score=ca.confidence_score,
        confidence_level=ca.confidence_level,
        confidence_components=ConfidenceComponentsResponse(
            data_quality=ca.confidence_components["data_quality"],
            model_coverage=ca.confidence_components["model_coverage"],
            input_completeness=ca.confidence_components["input_completeness"],
            cascade_strength=ca.confidence_components["cascade_strength"],
            time_certainty=ca.confidence_components["time_certainty"],
        ),
        confidence_explanation=ca.confidence_explanation,
        confidence_caveats=ca.confidence_caveats,
        cascade_path=ca.cascade_path,
    )


def _to_hazard_summary_response(hs) -> HazardSummaryResponse:
    """Convert HazardSummary dataclass to Pydantic model."""
    return HazardSummaryResponse(
        hazard_id=hs.hazard_id,
        hazard_type=hs.hazard_type,
        hazard_intensity=hs.hazard_intensity,
        hazard_probability=hs.hazard_probability,
        total_communities=hs.total_communities,
        directly_affected=hs.directly_affected,
        cascade_shadow=hs.cascade_shadow,
        unaffected=hs.unaffected,
        total_population_at_risk=hs.total_population_at_risk,
        highest_risk_community=hs.highest_risk_community,
        highest_risk_score=hs.highest_risk_score,
        evacuation_recommended=hs.evacuation_recommended,
        shelter_in_place=hs.shelter_in_place,
        monitor_only=hs.monitor_only,
        relocation_required=hs.relocation_required,
    )


def _to_cascade_path_summary(cps) -> CascadePathSummaryResponse:
    """Convert cascade path dict to Pydantic model."""
    return CascadePathSummaryResponse(**cps)


def _to_relocation_site_summary(rss) -> RelocationSiteSummaryResponse:
    """Convert relocation site dict to Pydantic model."""
    return RelocationSiteSummaryResponse(**rss)


@router.post("/analyze", response_model=SHARMIResponse)
def analyze_hazard(request: SHARMIRequest) -> SHARMIResponse:
    """
    Run complete SHARMI analysis for a hazard.

    Orchestrates the full pipeline:
    1. Risk Calculation (Phase 2)
    2. Cascade Simulation (Phase 3)
    3. Shadow Zone Analysis (Phase 4)
    4. Time-to-Impact Estimation (Phase 5)
    5. Action Recommendations (Phase 6)
    6. Relocation Optimization (Phase 7)
    7. Confidence Evaluation (Phase 8a)

    Returns unified analysis for all communities with summary statistics.

    This is a deterministic synthetic prototype for demonstration.
    """
    try:
        result = run_full_analysis(request.hazard_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return SHARMIResponse(
        hazard_id=result.hazard_id,
        hazard_type=result.hazard_type,
        analysis_timestamp=result.analysis_timestamp,
        summary=_to_hazard_summary_response(result.summary),
        community_analyses=[_to_community_analysis_response(ca) for ca in result.community_analyses],
        cascade_paths_summary=[_to_cascade_path_summary(cps) for cps in result.cascade_paths_summary],
        relocation_sites_summary=[_to_relocation_site_summary(rss) for rss in result.relocation_sites_summary],
        overall_explanation=result.overall_explanation,
    )


@router.post("/override", response_model=SHARMIOverrideResponse)
def submit_sharmi_override(request: SHARMIOverrideRequest) -> SHARMIOverrideResponse:
    """
    Submit an officer override decision within SHARMI analysis context.

    Allows officers to accept/modify/reject any aspect of the analysis:
    - ACTION_RECOMMENDATION: Accept/modify/reject action recommendation
    - SHADOW_ZONE: Override shadow zone classification
    - RELOCATION: Override relocation assignment
    - CONFIDENCE: Override confidence assessment
    - TIME_TO_IMPACT: Override time-to-impact estimate

    All overrides are logged for audit trail.

    This is a deterministic synthetic prototype for demonstration.
    """
    try:
        # Convert enum strings to service enums
        category = ServiceDecisionCategory(request.category)
        decision = ServiceOverrideDecision(request.decision)

        result = submit_decision_override(
            hazard_id=request.hazard_id,
            community_id=request.community_id,
            officer_id=request.officer_id,
            officer_name=request.officer_name,
            category=category,
            decision=decision,
            justification=request.justification,
            modified_recommendation=request.modified_recommendation,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return SHARMIOverrideResponse(**result)


@router.post("/audit", response_model=SHARMIAuditResponse)
def query_sharmi_audit(request: SHARMIAuditRequest) -> SHARMIAuditResponse:
    """
    Query the SHARMI audit log with optional filters.

    Supports filtering by hazard, community, officer, category, and decision.
    Returns paginated results (newest first).

    This is a deterministic synthetic prototype for demonstration.
    """
    # Convert enum strings to service enums
    category = ServiceDecisionCategory(request.category) if request.category else None
    decision = ServiceOverrideDecision(request.decision) if request.decision else None

    entries = get_decision_audit(
        hazard_id=request.hazard_id,
        community_id=request.community_id,
        officer_id=request.officer_id,
        category=category,
        decision=decision,
        limit=request.limit,
        offset=request.offset,
    )

    # Get total count
    all_entries = get_decision_audit(
        hazard_id=request.hazard_id,
        community_id=request.community_id,
        officer_id=request.officer_id,
        category=category,
        decision=decision,
        limit=10000,
        offset=0,
    )

    return SHARMIAuditResponse(
        entries=[SHARMIAuditEntry(**e) for e in entries],
        total=len(all_entries),
        limit=request.limit,
        offset=request.offset,
    )


@router.get("/audit/summary", response_model=SHARMIAuditSummaryResponse)
def get_sharmi_audit_summary() -> SHARMIAuditSummaryResponse:
    """
    Get SHARMI audit log summary statistics.

    Returns counts by decision type, category, and officer.

    This is a deterministic synthetic prototype for demonstration.
    """
    summary = get_audit_log_summary()
    return SHARMIAuditSummaryResponse(**summary)