"""SHARMI Phase 8b — Decision Service (Officer Override + Audit Log).

Provides override capability for field officers and logs all decisions
for accountability and audit trail.

This is a deterministic prototype for the SIH demo. Decision overrides
are logged with full context for review.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Literal
from uuid import uuid4

from ..models.domain import HazardType
from ..services.data_loader import get_data_loader


class OverrideDecision(str, Enum):
    """Possible override decisions by an officer."""
    ACCEPT = "ACCEPT"
    MODIFY = "MODIFY"
    REJECT = "REJECT"


class DecisionCategory(str, Enum):
    """Category of decision being made."""
    SHADOW_ZONE = "SHADOW_ZONE"
    ACTION_RECOMMENDATION = "ACTION_RECOMMENDATION"
    RELOCATION = "RELOCATION"
    CONFIDENCE = "CONFIDENCE"
    TIME_TO_IMPACT = "TIME_TO_IMPACT"


@dataclass(frozen=True)
class DecisionContext:
    """Context captured at decision time."""
    hazard_id: str
    hazard_type: HazardType
    community_id: str
    community_name: str
    original_recommendation: str
    zone_type: str
    risk_level: str | None = None
    time_to_impact: float | None = None
    confidence_score: float | None = None
    confidence_level: str | None = None


@dataclass(frozen=True)
class OverrideRequest:
    """Officer override request."""
    officer_id: str
    officer_name: str
    decision: OverrideDecision
    justification: str
    modified_recommendation: str | None = None
    # Context fields (populated by service)
    hazard_id: str = ""
    community_id: str = ""
    category: DecisionCategory = DecisionCategory.ACTION_RECOMMENDATION


@dataclass(frozen=True)
class AuditEntry:
    """Single audit log entry."""
    audit_id: str
    timestamp: datetime
    hazard_id: str
    hazard_type: HazardType
    community_id: str
    community_name: str
    category: DecisionCategory
    officer_id: str
    officer_name: str
    decision: OverrideDecision
    original_recommendation: str
    final_recommendation: str
    justification: str
    zone_type: str
    risk_level: str | None
    time_to_impact: float | None
    confidence_score: float | None
    confidence_level: str | None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp.isoformat(),
            "hazard_id": self.hazard_id,
            "hazard_type": self.hazard_type.value,
            "community_id": self.community_id,
            "community_name": self.community_name,
            "category": self.category.value,
            "officer_id": self.officer_id,
            "officer_name": self.officer_name,
            "decision": self.decision.value,
            "original_recommendation": self.original_recommendation,
            "final_recommendation": self.final_recommendation,
            "justification": self.justification,
            "zone_type": self.zone_type,
            "risk_level": self.risk_level,
            "time_to_impact": self.time_to_impact,
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
        }


@dataclass
class OverrideResult:
    """Result of an override operation."""
    audit_id: str
    final_recommendation: str
    decision: OverrideDecision
    timestamp: datetime
    note: str = (
        "This is a deterministic synthetic prototype for demonstration. "
        "Override decisions are logged for audit purposes only. "
        "Officer accountability is simulated."
    )


# In-memory audit log (prototype - would use persistent storage in production)
_AUDIT_LOG: list[AuditEntry] = []


def _get_decision_context(
    hazard_id: str,
    community_id: str,
    category: DecisionCategory,
) -> DecisionContext:
    """Build decision context from existing analyses."""
    loader = get_data_loader()
    dataset = loader.get_dataset()

    hazard = next((h for h in dataset.hazards if h.id == hazard_id), None)
    community = next((c for c in dataset.communities if c.id == community_id), None)

    if hazard is None:
        raise ValueError(f"Hazard {hazard_id} not found")
    if community is None:
        raise ValueError(f"Community {community_id} not found")

    # Import analysis services
    from ..services.shadow_zone_engine import analyze_shadow_zones
    from ..services.action_engine import generate_action_recommendations
    from ..services.relocation_engine import optimize_relocation
    from ..services.confidence_engine import evaluate_confidence
    from ..services.time_to_impact import estimate_impact_timeline

    # Get zone type
    shadow_result = analyze_shadow_zones(hazard_id)
    zone_type = "UNAFFECTED"
    for cls in shadow_result.directly_affected + shadow_result.cascade_shadow + shadow_result.unaffected:
        if cls.community_id == community_id:
            zone_type = cls.zone_type
            break

    # Get original recommendation based on category
    if category == DecisionCategory.ACTION_RECOMMENDATION:
        action_result = generate_action_recommendations(hazard_id)
        rec = next((r for r in action_result.recommendations if r.community_id == community_id), None)
        original = rec.action if rec else "MONITOR"
        risk_level = rec.direct_risk_level if rec else None
        time_to_impact = rec.time_to_impact if rec else None

    elif category == DecisionCategory.SHADOW_ZONE:
        original = zone_type
        risk_level = None
        time_to_impact = None

    elif category == DecisionCategory.RELOCATION:
        relocation_result = optimize_relocation(hazard_id)
        plan = next((p for p in relocation_result.plans if p.community_id == community_id), None)
        original = f"RELOCATE_TO_{plan.assigned_site_id}" if plan and plan.assigned_site_id else "NO_RELOCATION"
        risk_level = None
        time_to_impact = None

    elif category == DecisionCategory.CONFIDENCE:
        confidence_result = evaluate_confidence(hazard_id)
        conf = next((c for c in confidence_result.community_confidences if c.community_id == community_id), None)
        original = f"CONFIDENCE_{conf.confidence_level}" if conf else "CONFIDENCE_UNKNOWN"
        risk_level = None
        time_to_impact = None
        confidence_score = conf.overall_confidence if conf else None
        confidence_level = conf.confidence_level if conf else None

    elif category == DecisionCategory.TIME_TO_IMPACT:
        timeline_result = estimate_impact_timeline(hazard_id)
        node = next((n for n in timeline_result.timeline if n.node_id == community_id and n.node_type == "community"), None)
        original = f"TIMING_{node.estimated_propagation_time:.1f}" if node else "NOT_IN_TIMELINE"
        risk_level = None
        time_to_impact = node.estimated_propagation_time if node else None
        confidence_score = None
        confidence_level = None

    else:
        original = "UNKNOWN"
        risk_level = None
        time_to_impact = None
        confidence_score = None
        confidence_level = None

    return DecisionContext(
        hazard_id=hazard_id,
        hazard_type=hazard.type,
        community_id=community_id,
        community_name=community.name,
        original_recommendation=original,
        zone_type=zone_type,
        risk_level=risk_level,
        time_to_impact=time_to_impact,
        confidence_score=confidence_score if 'confidence_score' in locals() else None,
        confidence_level=confidence_level if 'confidence_level' in locals() else None,
    )


def submit_override(request: OverrideRequest) -> OverrideResult:
    """
    Submit an officer override decision.

    Args:
        request: OverrideRequest with officer details and decision

    Returns:
        OverrideResult with audit ID and final recommendation

    Raises:
        ValueError: If hazard/community not found or invalid inputs
    """
    # Validate decision
    if request.decision not in OverrideDecision:
        raise ValueError(f"Invalid decision: {request.decision}")

    if request.decision == OverrideDecision.MODIFY and not request.modified_recommendation:
        raise ValueError("MODIFY decision requires modified_recommendation")

    if not request.justification.strip():
        raise ValueError("Justification is required for all override decisions")

    # Build context if not fully provided
    if not request.hazard_id or not request.community_id:
        raise ValueError("hazard_id and community_id are required")

    context = _get_decision_context(
        request.hazard_id,
        request.community_id,
        request.category,
    )

    # Determine final recommendation
    if request.decision == OverrideDecision.ACCEPT:
        final_recommendation = context.original_recommendation
    elif request.decision == OverrideDecision.MODIFY:
        final_recommendation = request.modified_recommendation
    else:  # REJECT
        final_recommendation = "OVERRIDDEN_REJECTED"

    # Create audit entry
    audit_entry = AuditEntry(
        audit_id=str(uuid4())[:8].upper(),
        timestamp=datetime.now(UTC),
        hazard_id=request.hazard_id,
        hazard_type=context.hazard_type,
        community_id=request.community_id,
        community_name=context.community_name,
        category=request.category,
        officer_id=request.officer_id,
        officer_name=request.officer_name,
        decision=request.decision,
        original_recommendation=context.original_recommendation,
        final_recommendation=final_recommendation,
        justification=request.justification.strip(),
        zone_type=context.zone_type,
        risk_level=context.risk_level,
        time_to_impact=context.time_to_impact,
        confidence_score=context.confidence_score,
        confidence_level=context.confidence_level,
    )

    # Append to audit log
    _AUDIT_LOG.append(audit_entry)

    return OverrideResult(
        audit_id=audit_entry.audit_id,
        final_recommendation=final_recommendation,
        decision=request.decision,
        timestamp=audit_entry.timestamp,
    )


def get_audit_log(
    hazard_id: str | None = None,
    community_id: str | None = None,
    officer_id: str | None = None,
    category: DecisionCategory | None = None,
    decision: OverrideDecision | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEntry]:
    """
    Retrieve audit log entries with optional filters.

    Args:
        hazard_id: Filter by hazard ID
        community_id: Filter by community ID
        officer_id: Filter by officer ID
        category: Filter by decision category
        decision: Filter by override decision
        limit: Maximum entries to return
        offset: Pagination offset

    Returns:
        List of matching AuditEntry objects (newest first)
    """
    filtered = _AUDIT_LOG

    if hazard_id:
        filtered = [e for e in filtered if e.hazard_id == hazard_id]
    if community_id:
        filtered = [e for e in filtered if e.community_id == community_id]
    if officer_id:
        filtered = [e for e in filtered if e.officer_id == officer_id]
    if category:
        filtered = [e for e in filtered if e.category == category]
    if decision:
        filtered = [e for e in filtered if e.decision == decision]

    # Sort by timestamp descending (newest first)
    filtered.sort(key=lambda e: e.timestamp, reverse=True)

    return filtered[offset:offset + limit]


def get_audit_summary() -> dict:
    """Get summary statistics of audit log."""
    total = len(_AUDIT_LOG)
    by_decision = {}
    by_category = {}
    by_officer = {}

    for entry in _AUDIT_LOG:
        by_decision[entry.decision.value] = by_decision.get(entry.decision.value, 0) + 1
        by_category[entry.category.value] = by_category.get(entry.category.value, 0) + 1
        by_officer[entry.officer_id] = by_officer.get(entry.officer_id, 0) + 1

    return {
        "total_entries": total,
        "by_decision": by_decision,
        "by_category": by_category,
        "by_officer": by_officer,
        "note": "This is a synthetic prototype audit log. Data is not persisted across restarts.",
    }


def clear_audit_log() -> int:
    """Clear the audit log (for testing only). Returns count of cleared entries."""
    count = len(_AUDIT_LOG)
    _AUDIT_LOG.clear()
    return count