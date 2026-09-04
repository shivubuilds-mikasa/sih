"""Phase 8b Decision API endpoints (Officer Override + Audit Log)."""

from fastapi import APIRouter, HTTPException

from ..schemas.decision import (
    OverrideRequest,
    OverrideResponse,
    AuditLogRequest,
    AuditLogResponse,
    AuditSummaryResponse,
    AuditEntry,
)
from ..services.decision_service import (
    submit_override,
    get_audit_log,
    get_audit_summary,
    clear_audit_log,
    DecisionCategory,
    OverrideDecision,
)

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("/override", response_model=OverrideResponse)
def submit_override_endpoint(request: OverrideRequest) -> OverrideResponse:
    """
    Submit an officer override decision.

    Allows field officers to accept, modify, or reject system recommendations
    with full justification. All overrides are logged for audit trail.

    Categories:
    - ACTION_RECOMMENDATION: Accept/modify/reject action recommendation
    - SHADOW_ZONE: Override shadow zone classification
    - RELOCATION: Override relocation assignment
    - CONFIDENCE: Override confidence assessment
    - TIME_TO_IMPACT: Override time-to-impact estimate

    This is a deterministic synthetic prototype for demonstration.
    """
    try:
        result = submit_override(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return OverrideResponse(
        audit_id=result.audit_id,
        final_recommendation=result.final_recommendation,
        decision=result.decision,
        timestamp=result.timestamp.isoformat(),
    )


@router.post("/audit", response_model=AuditLogResponse)
def query_audit_log(request: AuditLogRequest) -> AuditLogResponse:
    """
    Query the audit log with optional filters.

    Supports filtering by hazard, community, officer, category, and decision.
    Returns paginated results (newest first).

    This is a deterministic synthetic prototype for demonstration.
    Audit log is in-memory only and not persisted across restarts.
    """
    entries = get_audit_log(
        hazard_id=request.hazard_id,
        community_id=request.community_id,
        officer_id=request.officer_id,
        category=request.category,
        decision=request.decision,
        limit=request.limit,
        offset=request.offset,
    )

    total = len(get_audit_log(
        hazard_id=request.hazard_id,
        community_id=request.community_id,
        officer_id=request.officer_id,
        category=request.category,
        decision=request.decision,
        limit=10000,  # Large limit to get total count
        offset=0,
    ))

    return AuditLogResponse(
        entries=[AuditEntry(**e.to_dict()) for e in entries],
        total=total,
        limit=request.limit,
        offset=request.offset,
    )


@router.get("/audit/summary", response_model=AuditSummaryResponse)
def get_audit_summary_endpoint() -> AuditSummaryResponse:
    """
    Get audit log summary statistics.

    Returns counts by decision type, category, and officer.

    This is a deterministic synthetic prototype for demonstration.
    """
    summary = get_audit_summary()
    return AuditSummaryResponse(**summary)


@router.delete("/audit")
def clear_audit_log_endpoint() -> dict:
    """
    Clear the audit log (for testing only).

    Returns count of cleared entries.
    """
    count = clear_audit_log()
    return {"cleared": count, "note": "Audit log cleared for testing purposes."}