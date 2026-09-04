"""SHARMI Phase 9 — End-to-End Decision Engine.

Orchestrates the complete SHARMI analysis pipeline:
1. Risk Calculation (Phase 2)
2. Cascade Simulation (Phase 3)
3. Shadow Zone Analysis (Phase 4)
4. Time-to-Impact Estimation (Phase 5)
5. Action Recommendations (Phase 6)
6. Relocation Optimization (Phase 7)
7. Confidence Evaluation (Phase 8a)

Provides a single unified analysis endpoint for officers.

This is a deterministic prototype for the SIH demo.
"""

from dataclasses import dataclass
from typing import Literal
from datetime import datetime, UTC

from ..models.domain import Hazard, Community, HazardType
from ..services.data_loader import get_data_loader
from ..services.risk_engine import calculate_risk_score, calculate_direct_risk, classify_risk
from ..services.cascade_engine import simulate_cascade
from ..services.shadow_zone_engine import analyze_shadow_zones, ZoneClassification
from ..services.time_to_impact import estimate_impact_timeline
from ..services.action_engine import generate_action_recommendations, CommunityAction
from ..services.relocation_engine import optimize_relocation, CommunityRelocationPlan
from ..services.confidence_engine import evaluate_confidence, CommunityConfidence
from ..services.decision_service import (
    submit_override, get_audit_log, get_audit_summary,
    OverrideRequest, OverrideDecision, DecisionCategory
)


@dataclass(frozen=True)
class CommunityAnalysis:
    """Complete analysis for a single community."""
    community_id: str
    community_name: str
    population: int
    risk_score: float
    risk_level: str
    zone_type: Literal["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE", "UNAFFECTED"]
    time_to_impact: float | None
    action: str
    direct_risk_level: str | None
    affected_services: list[str]
    relocation_site: str | None
    relocation_urgency: str | None
    confidence_score: float
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    confidence_components: dict[str, float]
    confidence_explanation: str
    confidence_caveats: list[str]
    cascade_path: str | None = None


@dataclass(frozen=True)
class HazardSummary:
    """Summary statistics for the hazard analysis."""
    hazard_id: str
    hazard_type: str
    hazard_intensity: float
    hazard_probability: float
    total_communities: int
    directly_affected: int
    cascade_shadow: int
    unaffected: int
    total_population_at_risk: int
    highest_risk_community: str
    highest_risk_score: float
    evacuation_recommended: int
    shelter_in_place: int
    monitor_only: int
    relocation_required: int


@dataclass(frozen=True)
class SHARMIAnalysisResult:
    """Complete SHARMI analysis result for a hazard."""
    hazard_id: str
    hazard_type: str
    analysis_timestamp: str
    summary: HazardSummary
    community_analyses: list[CommunityAnalysis]
    cascade_paths_summary: list[dict]
    relocation_sites_summary: list[dict]
    overall_explanation: str
    prototype_note: str = (
        "This is a deterministic synthetic prototype for SIH demonstration. "
        "All scores, classifications, and recommendations use synthetic models "
        "with prototype parameters. Results are for officer decision-support only "
        "and are NOT statistically calibrated. Do not use for real emergency decisions."
    )


def run_full_analysis(hazard_id: str) -> SHARMIAnalysisResult:
    """
    Run the complete SHARMI analysis pipeline for a hazard.

    Args:
        hazard_id: The hazard ID to analyze (e.g., "H001")

    Returns:
        SHARMIAnalysisResult with complete analysis

    Raises:
        ValueError: If hazard_id is not found
    """
    loader = get_data_loader()
    dataset = loader.get_dataset()

    # Find the hazard
    hazard = next((h for h in dataset.hazards if h.id == hazard_id), None)
    if hazard is None:
        raise ValueError(f"Hazard {hazard_id} not found in dataset")

    # ===== PHASE 2: Risk Calculation =====
    # Use the same exposure rule as the risk API: exposure = 1.0 if community in hazard.affected_communities else 0.0
    exposed_community_ids = set(hazard.affected_communities)
    risk_lookup = {}
    for community in dataset.communities:
        exposure = 1.0 if community.id in exposed_community_ids else 0.0
        risk_res = calculate_direct_risk(
            hazard_intensity=hazard.intensity,
            exposure=exposure,
            vulnerability=community.vulnerability,
        )
        risk_lookup[community.id] = risk_res

    # ===== PHASE 3: Cascade Simulation =====
    cascade_result = simulate_cascade(hazard_id)

    # ===== PHASE 4: Shadow Zone Analysis =====
    shadow_result = analyze_shadow_zones(hazard_id)
    zone_lookup = {}
    for cls in shadow_result.directly_affected + shadow_result.cascade_shadow + shadow_result.unaffected:
        zone_lookup[cls.community_id] = cls

    # ===== PHASE 5: Time-to-Impact =====
    timeline_result = estimate_impact_timeline(hazard_id)
    timeline_lookup = {
        n.node_id: n.estimated_propagation_time
        for n in timeline_result.timeline
        if n.node_type == "community"
    }

    # ===== PHASE 6: Action Recommendations =====
    action_result = generate_action_recommendations(hazard_id)
    action_lookup = {r.community_id: r for r in action_result.recommendations}

    # ===== PHASE 7: Relocation Optimization =====
    relocation_result = optimize_relocation(hazard_id)
    relocation_lookup = {p.community_id: p for p in relocation_result.plans}
    site_scores_lookup = {s.site_id: s for s in relocation_result.site_scores}

    # ===== PHASE 8a: Confidence Evaluation =====
    confidence_result = evaluate_confidence(hazard_id)
    confidence_lookup = {c.community_id: c for c in confidence_result.community_confidences}

    # ===== BUILD COMMUNITY ANALYSES =====
    community_analyses = []

    for community in dataset.communities:
        # Risk info
        risk_info = risk_lookup.get(community.id)
        risk_score = risk_info.risk_score if risk_info else 0.0
        risk_level = risk_info.risk_level if risk_info else "LOW"

        # Zone info
        zone_info = zone_lookup.get(community.id)
        zone_type = zone_info.zone_type if zone_info else "UNAFFECTED"

        # Time to impact
        time_to_impact = timeline_lookup.get(community.id)

        # Action info
        action_info = action_lookup.get(community.id)
        action = action_info.action if action_info else "MONITOR"
        direct_risk_level = action_info.direct_risk_level if action_info else None
        affected_services = action_info.affected_services if action_info and action_info.affected_services else []

        # Relocation info
        relocation_info = relocation_lookup.get(community.id)
        relocation_site = relocation_info.assigned_site_id if relocation_info else None
        # Convert urgency_score (float) to urgency category string
        if relocation_info and relocation_info.urgency_score is not None:
            urgency = relocation_info.urgency_score
            if urgency > 0:
                if urgency >= 0.8:
                    relocation_urgency = "CRITICAL"
                elif urgency >= 0.6:
                    relocation_urgency = "HIGH"
                elif urgency >= 0.4:
                    relocation_urgency = "MEDIUM"
                else:
                    relocation_urgency = "LOW"
            else:
                relocation_urgency = None
        else:
            relocation_urgency = None

        # Confidence info
        confidence_info = confidence_lookup.get(community.id)
        if confidence_info:
            confidence_score = confidence_info.overall_confidence
            confidence_level = confidence_info.confidence_level
            confidence_components = {
                "data_quality": confidence_info.components.data_quality,
                "model_coverage": confidence_info.components.model_coverage,
                "input_completeness": confidence_info.components.input_completeness,
                "cascade_strength": confidence_info.components.cascade_strength,
                "time_certainty": confidence_info.components.time_certainty,
            }
            confidence_explanation = confidence_info.explanation
            confidence_caveats = confidence_info.caveats
        else:
            confidence_score = 0.0
            confidence_level = "LOW"
            confidence_components = {
                "data_quality": 0.0,
                "model_coverage": 0.0,
                "input_completeness": 0.0,
                "cascade_strength": 0.0,
                "time_certainty": 0.0,
            }
            confidence_explanation = "No confidence data available"
            confidence_caveats = ["Community not in confidence evaluation"]

        # Cascade path info
        cascade_path = None
        if zone_type == "CASCADE_SHADOW_ZONE":
            for path in cascade_result.cascade_paths:
                community_nodes = [n for n in path.nodes if n.node_type == "community"]
                for cn in community_nodes:
                    if cn.node_id == community.id:
                        cascade_path = " → ".join(n.node_id for n in path.nodes)
                        break
                if cascade_path:
                    break

        community_analyses.append(CommunityAnalysis(
            community_id=community.id,
            community_name=community.name,
            population=community.population,
            risk_score=risk_score,
            risk_level=risk_level,
            zone_type=zone_type,
            time_to_impact=time_to_impact,
            action=action,
            direct_risk_level=direct_risk_level,
            affected_services=affected_services,
            relocation_site=relocation_site,
            relocation_urgency=relocation_urgency,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            confidence_components=confidence_components,
            confidence_explanation=confidence_explanation,
            confidence_caveats=confidence_caveats,
            cascade_path=cascade_path,
        ))

    # Sort by risk score descending
    community_analyses.sort(key=lambda c: c.risk_score, reverse=True)

    # ===== BUILD SUMMARY =====
    directly_affected = len(shadow_result.directly_affected)
    cascade_shadow = len(shadow_result.cascade_shadow)
    unaffected = len(shadow_result.unaffected)

    total_population_at_risk = sum(
        c.population for c in community_analyses
        if c.zone_type in ["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE"]
    )

    highest = community_analyses[0] if community_analyses else None
    highest_risk_community = highest.community_id if highest else "N/A"
    highest_risk_score = highest.risk_score if highest else 0.0

    evacuation_recommended = sum(1 for c in community_analyses if c.action == "EVACUATE_IMMEDIATE")
    shelter_in_place = sum(1 for c in community_analyses if c.action == "SHELTER_IN_PLACE")
    monitor_only = sum(1 for c in community_analyses if c.action == "MONITOR")
    relocation_required = sum(1 for c in community_analyses if c.relocation_site is not None)

    summary = HazardSummary(
        hazard_id=hazard_id,
        hazard_type=hazard.type.value,
        hazard_intensity=hazard.intensity,
        hazard_probability=hazard.probability,
        total_communities=len(dataset.communities),
        directly_affected=directly_affected,
        cascade_shadow=cascade_shadow,
        unaffected=unaffected,
        total_population_at_risk=total_population_at_risk,
        highest_risk_community=highest_risk_community,
        highest_risk_score=highest_risk_score,
        evacuation_recommended=evacuation_recommended,
        shelter_in_place=shelter_in_place,
        monitor_only=monitor_only,
        relocation_required=relocation_required,
    )

    # ===== CASCADE PATHS SUMMARY =====
    cascade_paths_summary = []
    for i, path in enumerate(cascade_result.cascade_paths):
        cascade_paths_summary.append({
            "path_id": f"path_{i}",
            "nodes": [{"id": n.node_id, "type": n.node_type} for n in path.nodes],
            "propagation_strength": path.propagation_strength,
            "total_propagation_time": 0.0,  # Not available in cascade path
        })

    # ===== RELOCATION SITES SUMMARY =====
    relocation_sites_summary = []
    for site_score in relocation_result.site_scores:
        allocated = [p for p in relocation_result.plans if p.assigned_site_id == site_score.site_id]
        relocation_sites_summary.append({
            "site_id": site_score.site_id,
            "site_name": site_score.site_name,
            "composite_score": site_score.composite_score,
            "capacity": site_score.capacity,
            "allocated_communities": len(allocated),
            "allocated_population": sum(p.population for p in allocated),
            "hazard_safety_score": site_score.hazard_safety_score,
            "livelihood_score": site_score.livelihood_score,
            "infrastructure_score": site_score.infrastructure_score,
            "school_score": site_score.school_access_score,
            "health_score": site_score.health_access_score,
            "distance_penalty": site_score.distance_penalty,
        })

    # ===== OVERALL EXPLANATION =====
    overall_explanation = (
        f"SHARMI analysis for {hazard.type.value} {hazard_id} "
        f"(intensity={hazard.intensity:.2f}, probability={hazard.probability:.2f}): "
        f"{directly_affected} directly affected, {cascade_shadow} in cascade shadow, "
        f"{unaffected} unaffected. {total_population_at_risk} population at risk. "
        f"{evacuation_recommended} evacuate, {shelter_in_place} shelter-in-place, "
        f"{monitor_only} monitor, {relocation_required} need relocation. "
        f"Highest risk: {highest_risk_community} ({highest_risk_score:.3f})."
    )

    return SHARMIAnalysisResult(
        hazard_id=hazard_id,
        hazard_type=hazard.type.value,
        analysis_timestamp=datetime.now(UTC).isoformat(),
        summary=summary,
        community_analyses=community_analyses,
        cascade_paths_summary=cascade_paths_summary,
        relocation_sites_summary=relocation_sites_summary,
        overall_explanation=overall_explanation,
    )


def submit_decision_override(
    hazard_id: str,
    community_id: str,
    officer_id: str,
    officer_name: str,
    category: DecisionCategory,
    decision: OverrideDecision,
    justification: str,
    modified_recommendation: str | None = None,
) -> dict:
    """
    Submit an officer override for a specific community decision.

    This is a convenience wrapper around the decision service.
    """
    request = OverrideRequest(
        officer_id=officer_id,
        officer_name=officer_name,
        hazard_id=hazard_id,
        community_id=community_id,
        category=category,
        decision=decision,
        justification=justification,
        modified_recommendation=modified_recommendation,
    )
    result = submit_override(request)
    return {
        "audit_id": result.audit_id,
        "final_recommendation": result.final_recommendation,
        "decision": result.decision.value,
        "timestamp": result.timestamp.isoformat(),
    }


def get_decision_audit(
    hazard_id: str | None = None,
    community_id: str | None = None,
    officer_id: str | None = None,
    category: DecisionCategory | None = None,
    decision: OverrideDecision | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Get audit log entries as dictionaries."""
    entries = get_audit_log(
        hazard_id=hazard_id,
        community_id=community_id,
        officer_id=officer_id,
        category=category,
        decision=decision,
        limit=limit,
        offset=offset,
    )
    return [e.to_dict() for e in entries]


def get_audit_log_summary() -> dict:
    """Get audit log summary statistics."""
    return get_audit_summary()