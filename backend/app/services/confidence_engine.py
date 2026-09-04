"""SHARMI Phase 8a — Confidence Engine.

Quantifies the reliability of each recommendation based on:
- Data quality (completeness of inputs)
- Model coverage (whether all relevant factors are modeled)
- Input completeness (whether all required data is present)
- Cascade path strength (minimum weight along path)
- Time-to-impact certainty (closer to hazard = higher confidence)

This is a deterministic prototype for the SIH demo. The confidence score
is a synthetic metric for decision-support, not a statistically calibrated
reliability measure. Results are for officer review only.
"""

from dataclasses import dataclass
from typing import Literal

from ..models.domain import Community, Hazard
from ..services.shadow_zone_engine import analyze_shadow_zones
from ..services.action_engine import generate_action_recommendations
from ..services.time_to_impact import estimate_impact_timeline
from ..services.cascade_engine import simulate_cascade
from ..services.data_loader import get_data_loader


# Confidence component weights (synthetic prototype parameters)
WEIGHT_DATA_QUALITY: float = 0.25
WEIGHT_MODEL_COVERAGE: float = 0.25
WEIGHT_INPUT_COMPLETENESS: float = 0.20
WEIGHT_CASCADE_STRENGTH: float = 0.20
WEIGHT_TIME_CERTAINTY: float = 0.10

# Thresholds
HIGH_CONFIDENCE_THRESHOLD: float = 0.75
MEDIUM_CONFIDENCE_THRESHOLD: float = 0.50


@dataclass(frozen=True)
class ConfidenceComponents:
    """Individual confidence component scores."""
    data_quality: float
    model_coverage: float
    input_completeness: float
    cascade_strength: float
    time_certainty: float


@dataclass(frozen=True)
class CommunityConfidence:
    """Confidence assessment for a single community's recommendation."""
    community_id: str
    community_name: str
    overall_confidence: float
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    components: ConfidenceComponents
    explanation: str
    caveats: list[str]


@dataclass(frozen=True)
class ConfidenceResult:
    """Complete confidence evaluation for a hazard."""
    hazard_id: str
    hazard_type: str
    community_confidences: list[CommunityConfidence]
    overall_explanation: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "hazard_id": self.hazard_id,
            "hazard_type": self.hazard_type,
            "community_confidences": [cc.__dict__ for cc in self.community_confidences],
            "overall_explanation": self.overall_explanation,
            "note": (
                "This is a deterministic synthetic prototype for demonstration. "
                "Confidence scores use synthetic weights (data quality 25%, model "
                "coverage 25%, input completeness 20%, cascade strength 20%, "
                "time certainty 10%). They are NOT statistically calibrated "
                "reliability measures. Results are for officer review only."
            ),
        }


def _calculate_data_quality(
    community: Community,
    hazard: Hazard,
    cascade_result,
) -> tuple[float, list[str]]:
    """Calculate data quality score for a community."""
    score = 1.0
    caveats = []

    # Check community data completeness
    if community.vulnerability is None or community.vulnerability < 0:
        score -= 0.2
        caveats.append("Missing or invalid community vulnerability")
    if community.population <= 0:
        score -= 0.1
        caveats.append("Invalid population")

    # Check hazard data
    if hazard.intensity is None or hazard.intensity < 0:
        score -= 0.2
        caveats.append("Missing or invalid hazard intensity")
    if hazard.probability is None or hazard.probability < 0:
        score -= 0.1
        caveats.append("Missing or invalid hazard probability")

    # Check cascade data availability
    if not cascade_result.affected_node_ids:
        score -= 0.1
        caveats.append("No cascade data available")

    return max(0.0, score), caveats


def _calculate_model_coverage(
    community: Community,
    zone_type: str,
    cascade_result,
) -> tuple[float, list[str]]:
    """Calculate model coverage score."""
    score = 1.0
    caveats = []

    # Direct hazard zone has full model coverage
    if zone_type == "DIRECT_HAZARD_ZONE":
        pass  # Full coverage
    elif zone_type == "CASCADE_SHADOW_ZONE":
        # Cascade model has limitations
        score -= 0.15
        caveats.append("Cascade propagation model uses synthetic threshold (0.70)")
    else:
        # Unaffected - limited model coverage for this community
        score -= 0.1
        caveats.append("Community not reached by modeled cascade paths")

    # Check if services are modeled
    if not cascade_result.affected_services:
        score -= 0.1
        caveats.append("No affected services modeled")

    return max(0.0, score), caveats


def _calculate_input_completeness(
    community: Community,
    hazard: Hazard,
    cascade_result,
    timeline_result,
) -> tuple[float, list[str]]:
    """Calculate input completeness score."""
    score = 1.0
    caveats = []

    # Check if community is in cascade timeline
    in_timeline = any(n.node_id == community.id for n in timeline_result.timeline)
    if not in_timeline and community.id in cascade_result.affected_community_ids:
        # Affected by cascade but not in timeline
        score -= 0.2
        caveats.append("Community affected by cascade but missing time-to-impact estimate")

    # Check vulnerability data
    if community.vulnerability <= 0.3:
        score -= 0.05
        caveats.append("Low vulnerability - model may underestimate resilience")

    # Check infrastructure data for served services
    loader = get_data_loader()
    dataset = loader.get_dataset()
    served_infra = [i for i in dataset.infrastructure if community.id in i.serves]
    if not served_infra:
        score -= 0.1
        caveats.append("Community has no mapped infrastructure dependencies")

    return max(0.0, score), caveats


def _calculate_cascade_strength(
    community_id: str,
    cascade_result,
    zone_type: str,
) -> tuple[float, list[str]]:
    """Calculate cascade path strength score."""
    caveats = []

    if zone_type == "DIRECT_HAZARD_ZONE":
        # Direct exposure - no cascade path needed
        return 1.0, ["Direct hazard exposure (no cascade dependency)"]

    if zone_type == "CASCADE_SHADOW_ZONE":
        # Find the cascade path to this community
        for path in cascade_result.cascade_paths:
            community_nodes = [n for n in path.nodes if n.node_type == "community"]
            for cn in community_nodes:
                if cn.node_id == community_id:
                    # Use propagation strength (minimum weight along path)
                    strength = path.propagation_strength
                    if strength < 0.8:
                        caveats.append(f"Cascade path has moderate strength ({strength:.2f})")
                    elif strength < 0.9:
                        caveats.append(f"Cascade path has good strength ({strength:.2f})")
                    return strength, caveats

        # Fallback
        return 0.5, ["Cascade path strength could not be determined"]

    # Unaffected
    return 0.0, ["No cascade path to this community"]


def _calculate_time_certainty(
    community_id: str,
    timeline_result,
    zone_type: str,
) -> tuple[float, list[str]]:
    """Calculate time-to-impact certainty score."""
    caveats = []

    # Find community in timeline
    for node in timeline_result.timeline:
        if node.node_id == community_id and node.node_type == "community":
            time = node.estimated_propagation_time
            # Closer to hazard = higher certainty
            if time <= 50:
                return 0.9, [f"Short time-to-impact ({time:.1f}) - higher certainty"]
            elif time <= 150:
                return 0.7, [f"Medium time-to-impact ({time:.1f}) - moderate certainty"]
            else:
                return 0.5, [f"Long time-to-impact ({time:.1f}) - lower certainty"]

    if zone_type == "DIRECT_HAZARD_ZONE":
        return 0.8, ["Direct exposure - immediate impact assumed"]
    elif zone_type == "CASCADE_SHADOW_ZONE":
        return 0.3, ["Cascade shadow zone - no specific time estimate available"]
    else:
        return 0.0, ["Unaffected community - no time estimate applicable"]


def _classify_confidence(score: float) -> Literal["HIGH", "MEDIUM", "LOW"]:
    """Classify confidence score into level."""
    if score >= HIGH_CONFIDENCE_THRESHOLD:
        return "HIGH"
    if score >= MEDIUM_CONFIDENCE_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def _generate_community_explanation(
    community: Community,
    zone_type: str,
    components: ConfidenceComponents,
    caveats: list[str],
) -> str:
    """Generate explanation for community confidence."""
    parts = [
        f"{community.name} ({community.id}) confidence: {components.data_quality:.0%} data, "
        f"{components.model_coverage:.0%} coverage, {components.input_completeness:.0%} inputs, "
        f"{components.cascade_strength:.0%} cascade, {components.time_certainty:.0%} time."
    ]
    if caveats:
        parts.append("Caveats: " + "; ".join(caveats))
    return " ".join(parts)


def evaluate_confidence(hazard_id: str) -> ConfidenceResult:
    """
    Evaluate confidence for all community recommendations for a hazard.

    Args:
        hazard_id: The hazard ID to evaluate (e.g., "H001")

    Returns:
        ConfidenceResult with per-community confidence assessments

    Raises:
        ValueError: If hazard_id is not found
    """
    loader = get_data_loader()
    dataset = loader.get_dataset()

    # Find the hazard
    hazard = next((h for h in dataset.hazards if h.id == hazard_id), None)
    if hazard is None:
        raise ValueError(f"Hazard {hazard_id} not found in dataset")

    # Get all required analyses
    shadow_result = analyze_shadow_zones(hazard_id)
    action_result = generate_action_recommendations(hazard_id)
    timeline_result = estimate_impact_timeline(hazard_id)
    cascade_result = simulate_cascade(hazard_id)

    # Build lookups
    action_lookup = {r.community_id: r.action for r in action_result.recommendations}
    zone_lookup = {}
    for cls in shadow_result.directly_affected + shadow_result.cascade_shadow + shadow_result.unaffected:
        zone_lookup[cls.community_id] = cls.zone_type

    community_confidences = []
    all_caveats = []

    for community in dataset.communities:
        zone_type = zone_lookup.get(community.id, "UNAFFECTED")
        action = action_lookup.get(community.id, "MONITOR")

        # Calculate each component
        data_quality, dq_caveats = _calculate_data_quality(community, hazard, cascade_result)
        model_coverage, mc_caveats = _calculate_model_coverage(community, zone_type, cascade_result)
        input_completeness, ic_caveats = _calculate_input_completeness(
            community, hazard, cascade_result, timeline_result
        )
        cascade_strength, cs_caveats = _calculate_cascade_strength(community.id, cascade_result, zone_type)
        time_certainty, tc_caveats = _calculate_time_certainty(community.id, timeline_result, zone_type)

        all_caveats.extend(dq_caveats + mc_caveats + ic_caveats + cs_caveats + tc_caveats)

        # Compute weighted overall confidence
        overall = (
            WEIGHT_DATA_QUALITY * data_quality
            + WEIGHT_MODEL_COVERAGE * model_coverage
            + WEIGHT_INPUT_COMPLETENESS * input_completeness
            + WEIGHT_CASCADE_STRENGTH * cascade_strength
            + WEIGHT_TIME_CERTAINTY * time_certainty
        )
        overall = round(overall, 4)

        confidence_level = _classify_confidence(overall)

        components = ConfidenceComponents(
            data_quality=round(data_quality, 4),
            model_coverage=round(model_coverage, 4),
            input_completeness=round(input_completeness, 4),
            cascade_strength=round(cascade_strength, 4),
            time_certainty=round(time_certainty, 4),
        )

        explanation = _generate_community_explanation(
            community, zone_type, components,
            dq_caveats + mc_caveats + ic_caveats + cs_caveats + tc_caveats
        )

        community_confidences.append(CommunityConfidence(
            community_id=community.id,
            community_name=community.name,
            overall_confidence=overall,
            confidence_level=confidence_level,
            components=components,
            explanation=explanation,
            caveats=dq_caveats + mc_caveats + ic_caveats + cs_caveats + tc_caveats,
        ))

    # Sort by confidence descending
    community_confidences.sort(key=lambda c: c.overall_confidence, reverse=True)

    # Overall explanation
    high_count = sum(1 for c in community_confidences if c.confidence_level == "HIGH")
    medium_count = sum(1 for c in community_confidences if c.confidence_level == "MEDIUM")
    low_count = sum(1 for c in community_confidences if c.confidence_level == "LOW")

    overall_explanation = (
        f"Confidence evaluation for {hazard.type.value} {hazard_id}: "
        f"{high_count} HIGH, {medium_count} MEDIUM, {low_count} LOW confidence. "
        f"Components weighted: data quality {WEIGHT_DATA_QUALITY:.0%}, "
        f"model coverage {WEIGHT_MODEL_COVERAGE:.0%}, input completeness {WEIGHT_INPUT_COMPLETENESS:.0%}, "
        f"cascade strength {WEIGHT_CASCADE_STRENGTH:.0%}, time certainty {WEIGHT_TIME_CERTAINTY:.0%}."
    )

    return ConfidenceResult(
        hazard_id=hazard_id,
        hazard_type=hazard.type.value,
        community_confidences=community_confidences,
        overall_explanation=overall_explanation,
    )