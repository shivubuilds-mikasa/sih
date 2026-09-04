"""SHARMI Phase 6 — Action Recommendation Engine.

Provides explainable prototype recommendations for an officer based on:
- Direct risk level
- Cascade impact (shadow zone classification)
- Affected services (healthcare, water, power, access, education)
- Time-to-impact estimation
- Affected communities

This engine does NOT make autonomous emergency decisions. It provides
decision-support recommendations for human review. The categories are:

- MONITOR: Low risk, no immediate action needed, continue observation
- PREPARE: Moderate risk, prepare resources and contingency plans
- INSPECT: Specific infrastructure/services need inspection
- PROTECT: High risk, protective measures needed for population/assets
- EVACUATION_ASSESSMENT: Critical risk, assess evacuation feasibility (NOT an evacuation order)

All recommendations are deterministic, explainable, and marked as prototype.
"""

from dataclasses import dataclass
from typing import Literal

from ..models.domain import Community, Hazard
from ..services.cascade_engine import simulate_cascade
from ..services.shadow_zone_engine import analyze_shadow_zones
from ..services.time_to_impact import estimate_impact_timeline
from ..services.risk_engine import calculate_direct_risk
from ..services.data_loader import get_data_loader

# Action categories
ActionCategory = Literal["MONITOR", "PREPARE", "INSPECT", "PROTECT", "EVACUATION_ASSESSMENT"]

# Time-to-impact thresholds for recommendation logic (arbitrary prototype units)
TIME_THRESHOLD_CRITICAL: float = 50.0   # Very short time → EVACUATION_ASSESSMENT
TIME_THRESHOLD_HIGH: float = 100.0      # Short time → PROTECT
TIME_THRESHOLD_MEDIUM: float = 200.0    # Medium time → PREPARE
# Above MEDIUM → MONITOR

# Risk score thresholds (from risk_engine)
RISK_THRESHOLD_HIGH: float = 0.60
RISK_THRESHOLD_MEDIUM: float = 0.30


@dataclass(frozen=True)
class CommunityAction:
    """Action recommendation for a single community."""
    community_id: str
    community_name: str
    zone_type: str  # DIRECT_HAZARD_ZONE, CASCADE_SHADOW_ZONE, UNAFFECTED
    action: ActionCategory
    confidence: float  # 0.0 - 1.0, synthetic prototype confidence
    rationale: str
    direct_risk_level: str | None = None
    time_to_impact: float | None = None
    affected_services: list[str] | None = None
    cascade_path: list[str] | None = None


@dataclass(frozen=True)
class ActionRecommendationResult:
    """Complete action recommendations for a hazard."""
    hazard_id: str
    hazard_type: str
    recommendations: list[CommunityAction]
    explanation: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "hazard_id": self.hazard_id,
            "hazard_type": self.hazard_type,
            "recommendations": [rec.__dict__ for rec in self.recommendations],
            "explanation": self.explanation,
            "note": (
                "This is a deterministic synthetic prototype for demonstration. "
                "Recommendations are decision-support for officer review only — "
                "NOT autonomous emergency orders. The engine does not directly order "
                "evacuation; EVACUATION_ASSESSMENT means assess feasibility only. "
                "All thresholds (risk, time-to-impact) are synthetic prototype parameters."
            ),
        }


def _get_direct_risk_for_community(
    community: Community,
    hazard: Hazard,
) -> tuple[float, str]:
    """Get direct risk score and level for a community from a hazard."""
    # Exposure: 1.0 if community in hazard's affected_communities, else 0.0
    exposure = 1.0 if community.id in hazard.affected_communities else 0.0
    result = calculate_direct_risk(
        hazard_intensity=hazard.intensity,
        exposure=exposure,
        vulnerability=community.vulnerability,
    )
    return result.risk_score, result.risk_level


def _get_time_to_impact_for_community(
    hazard_id: str,
    community_id: str,
) -> float | None:
    """Get estimated time-to-impact for a specific community from a hazard."""
    try:
        timeline_result = estimate_impact_timeline(hazard_id)
        for node in timeline_result.timeline:
            if node.node_id == community_id:
                return node.estimated_propagation_time
    except ValueError:
        pass
    return None


def _get_affected_services_for_community(
    hazard_id: str,
    community_id: str,
) -> list[str]:
    """Get affected service types for a community from cascade simulation."""
    cascade_result = simulate_cascade(hazard_id)
    services = []
    for svc in cascade_result.affected_services:
        # Check if this service's infrastructure serves the community
        loader = get_data_loader()
        dataset = loader.get_dataset()
        infra = next((i for i in dataset.infrastructure if i.id == svc.infrastructure_id), None)
        if infra and community_id in infra.serves:
            services.append(svc.service_type)
    return list(set(services))


def _determine_action(
    zone_type: str,
    direct_risk_level: str | None,
    time_to_impact: float | None,
    affected_services: list[str],
    is_critical_infra_affected: bool,
) -> tuple[ActionCategory, float, str]:
    """
    Determine action category based on multiple factors.

    Returns: (action, confidence, rationale)
    """

    # Critical infrastructure affected boosts urgency
    critical_services = {"healthcare", "water_supply"}
    has_critical_service = any(s in critical_services for s in affected_services)

    # Start with base rationale parts
    rationale_parts = []

    # DIRECT_HAZARD_ZONE logic
    if zone_type == "DIRECT_HAZARD_ZONE":
        if direct_risk_level == "HIGH":
            if time_to_impact is not None and time_to_impact <= TIME_THRESHOLD_CRITICAL:
                # Very high risk + very short time → evacuation assessment
                rationale = (
                    f"Directly exposed community with HIGH direct risk and very short "
                    f"estimated time-to-impact ({time_to_impact:.1f} units). "
                    f"EVACUATION_ASSESSMENT recommended (assess feasibility only)."
                )
                return "EVACUATION_ASSESSMENT", 0.85, rationale
            elif time_to_impact is not None and time_to_impact <= TIME_THRESHOLD_HIGH:
                # High risk + short time → protect
                rationale = (
                    f"Directly exposed community with HIGH direct risk and short "
                    f"estimated time-to-impact ({time_to_impact:.1f} units). "
                    f"PROTECT: implement protective measures for population and assets."
                )
                return "PROTECT", 0.80, rationale
            else:
                # High risk, longer time → prepare
                time_str = f"{time_to_impact:.1f}" if time_to_impact is not None else "unknown"
                rationale = (
                    f"Directly exposed community with HIGH direct risk. "
                    f"Estimated time-to-impact: {time_str} units. "
                    f"PREPARE: ready resources and contingency plans."
                )
                return "PREPARE", 0.75, rationale

        elif direct_risk_level == "MEDIUM":
            if time_to_impact is not None and time_to_impact <= TIME_THRESHOLD_HIGH:
                rationale = (
                    f"Directly exposed community with MEDIUM direct risk and short "
                    f"time-to-impact ({time_to_impact:.1f}). PROTECT recommended."
                )
                return "PROTECT", 0.70, rationale
            else:
                rationale = (
                    f"Directly exposed community with MEDIUM direct risk. "
                    f"PREPARE: ready resources and monitor developments."
                )
                return "PREPARE", 0.65, rationale

        else:  # LOW direct risk
            rationale = (
                f"Directly exposed community with LOW direct risk. "
                f"MONITOR: continue observation, no immediate action needed."
            )
            return "MONITOR", 0.60, rationale

    # CASCADE_SHADOW_ZONE logic
    elif zone_type == "CASCADE_SHADOW_ZONE":
        if has_critical_service and time_to_impact is not None and time_to_impact <= TIME_THRESHOLD_HIGH:
            rationale = (
                f"Community in CASCADE SHADOW ZONE (indirect risk via infrastructure failure). "
                f"Critical service affected: {', '.join(s for s in affected_services if s in critical_services)}. "
                f"Short time-to-impact ({time_to_impact:.1f}). PROTECT recommended."
            )
            return "PROTECT", 0.75, rationale

        elif has_critical_service:
            rationale = (
                f"Community in CASCADE SHADOW ZONE with critical service disruption: "
                f"{', '.join(s for s in affected_services if s in critical_services)}. "
                f"INSPECT: verify infrastructure status and service continuity."
            )
            return "INSPECT", 0.70, rationale

        elif affected_services and time_to_impact is not None and time_to_impact <= TIME_THRESHOLD_MEDIUM:
            rationale = (
                f"Community in CASCADE SHADOW ZONE with affected services: {', '.join(affected_services)}. "
                f"Medium time-to-impact ({time_to_impact:.1f}). PREPARE recommended."
            )
            return "PREPARE", 0.65, rationale

        elif affected_services:
            rationale = (
                f"Community in CASCADE SHADOW ZONE with affected services: {', '.join(affected_services)}. "
                f"INSPECT: check infrastructure and service status."
            )
            return "INSPECT", 0.60, rationale

        else:
            # Cascade shadow but no specific services identified for this community
            if time_to_impact is not None and time_to_impact <= TIME_THRESHOLD_MEDIUM:
                rationale = (
                    f"Community in CASCADE SHADOW ZONE (indirect risk). "
                    f"Time-to-impact: {time_to_impact:.1f}. PREPARE recommended."
                )
                return "PREPARE", 0.55, rationale
            else:
                rationale = (
                    f"Community in CASCADE SHADOW ZONE (indirect risk via dependency chain). "
                    f"MONITOR: track cascade progression and infrastructure status."
                )
                return "MONITOR", 0.50, rationale

    # UNAFFECTED logic
    else:  # UNAFFECTED
        rationale = (
            f"Community classified as UNAFFECTED — not directly exposed and not reached "
            f"via cascade above threshold. MONITOR: routine observation only."
        )
        return "MONITOR", 0.90, rationale


def generate_action_recommendations(hazard_id: str) -> ActionRecommendationResult:
    """
    Generate action recommendations for all communities for a given hazard.

    Args:
        hazard_id: The hazard ID to analyze (e.g., "H001")

    Returns:
        ActionRecommendationResult with per-community recommendations

    Raises:
        ValueError: If hazard_id is not found
    """
    loader = get_data_loader()
    dataset = loader.get_dataset()

    # Find the hazard
    hazard = next((h for h in dataset.hazards if h.id == hazard_id), None)
    if hazard is None:
        raise ValueError(f"Hazard {hazard_id} not found in dataset")

    # Get shadow zone analysis
    shadow_result = analyze_shadow_zones(hazard_id)

    # Get timeline for time-to-impact info
    timeline_result = estimate_impact_timeline(hazard_id)

    # Build lookup for time-to-impact by community
    time_lookup = {}
    for node in timeline_result.timeline:
        if node.node_type == "community":
            time_lookup[node.node_id] = node.estimated_propagation_time

    # Build lookup for cascade paths
    path_lookup = {}
    for path in shadow_result.cascade_shadow:
        if path.cascade_path:
            path_lookup[path.community_id] = path.cascade_path

    # Get affected services per community from cascade
    cascade_result = simulate_cascade(hazard_id)

    # Build lookup for services per community
    services_lookup = {}
    for svc in cascade_result.affected_services:
        infra = next((i for i in dataset.infrastructure if i.id == svc.infrastructure_id), None)
        if infra:
            for comm_id in infra.serves:
                if comm_id not in services_lookup:
                    services_lookup[comm_id] = []
                services_lookup[comm_id].append(svc.service_type)

    # Build all community actions
    recommendations = []

    # Combine all zone classifications
    all_classifications = (
        shadow_result.directly_affected
        + shadow_result.cascade_shadow
        + shadow_result.unaffected
    )

    for classification in all_classifications:
        community = next((c for c in dataset.communities if c.id == classification.community_id), None)
        if not community:
            continue

        direct_risk_score, direct_risk_level = _get_direct_risk_for_community(community, hazard)
        time_to_impact = time_lookup.get(classification.community_id)
        affected_services = services_lookup.get(classification.community_id, [])
        cascade_path = path_lookup.get(classification.community_id)

        # Determine if critical infrastructure is affected for this community
        critical_services = {"healthcare", "water_supply"}
        is_critical_infra_affected = any(s in critical_services for s in affected_services)

        action, confidence, rationale = _determine_action(
            zone_type=classification.zone_type,
            direct_risk_level=direct_risk_level if classification.zone_type == "DIRECT_HAZARD_ZONE" else None,
            time_to_impact=time_to_impact,
            affected_services=affected_services,
            is_critical_infra_affected=is_critical_infra_affected,
        )

        recommendations.append(CommunityAction(
            community_id=classification.community_id,
            community_name=classification.community_name,
            zone_type=classification.zone_type,
            action=action,
            confidence=confidence,
            rationale=rationale,
            direct_risk_level=direct_risk_level if classification.zone_type == "DIRECT_HAZARD_ZONE" else None,
            time_to_impact=time_to_impact,
            affected_services=affected_services if affected_services else None,
            cascade_path=cascade_path,
        ))

    # Sort: EVACUATION_ASSESSMENT first, then PROTECT, INSPECT, PREPARE, MONITOR
    action_priority = {
        "EVACUATION_ASSESSMENT": 0,
        "PROTECT": 1,
        "INSPECT": 2,
        "PREPARE": 3,
        "MONITOR": 4,
    }
    recommendations.sort(key=lambda r: (action_priority.get(r.action, 5), r.community_id))

    # Generate overall explanation
    action_counts = {}
    for rec in recommendations:
        action_counts[rec.action] = action_counts.get(rec.action, 0) + 1

    explanation_parts = [
        f"Action recommendations for {hazard.type.value} {hazard_id}:"
    ]
    for action in ["EVACUATION_ASSESSMENT", "PROTECT", "INSPECT", "PREPARE", "MONITOR"]:
        if action in action_counts:
            explanation_parts.append(f"  {action}: {action_counts[action]} communities")

    explanation = "\n".join(explanation_parts)
    explanation += (
        f"\n\nRecommendations are based on: zone classification (direct/shadow/unaffected), "
        f"direct risk level, estimated time-to-impact, and affected critical services. "
        f"All thresholds are synthetic prototype parameters."
    )

    return ActionRecommendationResult(
        hazard_id=hazard_id,
        hazard_type=hazard.type.value,
        recommendations=recommendations,
        explanation=explanation,
    )