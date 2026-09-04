"""SHARMI Phase 4 — Cascade Shadow Zone Engine.

Identifies communities that are NOT directly affected by a hazard but become
at risk through infrastructure dependency cascade propagation.

This is SHARMI's primary differentiator: finding "shadow zones" where danger
arrives indirectly through infrastructure failure chains rather than direct
hazard exposure.

The classification is:
- DIRECT_HAZARD_ZONE: Community directly listed in hazard's affected_communities
- CASCADE_SHADOW_ZONE: Community NOT directly affected but reached via cascade
- UNAFFECTED: Community not directly affected and not reached via cascade

This is a deterministic prototype using synthetic dependency weights and
thresholds. The results are explainable decision-support, not scientifically
calibrated hazard boundaries.
"""

from dataclasses import dataclass
from typing import Literal

from ..models.domain import Community, Hazard
from ..services.cascade_engine import simulate_cascade, CASCADE_THRESHOLD
from ..services.data_loader import get_data_loader
from ..services.risk_engine import calculate_direct_risk


ZoneType = Literal["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE", "UNAFFECTED"]


@dataclass(frozen=True)
class ZoneClassification:
    """Classification of a community's zone type with explanation."""
    community_id: str
    community_name: str
    zone_type: ZoneType
    direct_hazard_exposure: bool
    cascade_affected: bool
    cascade_path: list[str] | None
    explanation: str


@dataclass(frozen=True)
class ShadowZoneResult:
    """Complete shadow zone analysis result for a hazard."""
    hazard_id: str
    hazard_type: str
    directly_affected: list[ZoneClassification]
    cascade_shadow: list[ZoneClassification]
    unaffected: list[ZoneClassification]
    explanation: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "hazard_id": self.hazard_id,
            "hazard_type": self.hazard_type,
            "directly_affected": [zc.__dict__ for zc in self.directly_affected],
            "cascade_shadow": [zc.__dict__ for zc in self.cascade_shadow],
            "unaffected": [zc.__dict__ for zc in self.unaffected],
            "explanation": self.explanation,
            "note": (
                "Shadow Zone means an area affected indirectly through dependency "
                "propagation in the prototype. It does not represent a scientifically "
                "validated hazard boundary. The cascade threshold (0.70) and "
                "dependency weights are synthetic demonstration parameters."
            ),
        }


def _get_hazard_direct_exposure(hazard: Hazard) -> set[str]:
    """Get the set of community IDs directly affected by the hazard."""
    return set(hazard.affected_communities)


def _get_cascade_affected_communities(hazard_id: str) -> tuple[set[str], dict[str, list[str]]]:
    """
    Get communities affected through cascade and their paths.

    Returns:
        Tuple of (affected_community_set, community_to_path_dict)
    """
    cascade_result = simulate_cascade(hazard_id)
    affected_communities = set(cascade_result.affected_community_ids)

    # Build path mapping: community_id -> path (list of node IDs)
    path_map = {}
    for path in cascade_result.cascade_paths:
        community_nodes = [n for n in path.nodes if n.node_type == "community"]
        for community_node in community_nodes:
            # Path from hazard to this community
            path_nodes = [n.node_id for n in path.nodes]
            path_map[community_node.node_id] = path_nodes

    return affected_communities, path_map


def _classify_community(
    community: Community,
    hazard: Hazard,
    direct_exposure: set[str],
    cascade_affected: set[str],
    cascade_paths: dict[str, list[str]],
) -> ZoneClassification:
    """Classify a single community into zone type."""
    is_directly_exposed = community.id in direct_exposure
    is_cascade_affected = community.id in cascade_affected
    cascade_path = cascade_paths.get(community.id) if is_cascade_affected else None

    if is_directly_exposed:
        zone_type: ZoneType = "DIRECT_HAZARD_ZONE"
        explanation = (
            f"{community.name} ({community.id}) is directly exposed to "
            f"{hazard.type.value} {hazard.id} (listed in hazard's affected_communities). "
            f"Direct risk assessment applies."
        )
    elif is_cascade_affected:
        zone_type = "CASCADE_SHADOW_ZONE"
        path_str = " → ".join(cascade_path) if cascade_path else "unknown path"
        explanation = (
            f"{community.name} ({community.id}) is NOT directly exposed to "
            f"{hazard.type.value} {hazard.id} but IS reached through infrastructure "
            f"cascade propagation: {path_str}. This is a CASCADE SHADOW ZONE — "
            f"danger arrives indirectly via dependency failure chain."
        )
    else:
        zone_type = "UNAFFECTED"
        explanation = (
            f"{community.name} ({community.id}) is neither directly exposed to "
            f"{hazard.type.value} {hazard.id} nor reached through cascade "
            f"propagation above the threshold ({CASCADE_THRESHOLD})."
        )

    return ZoneClassification(
        community_id=community.id,
        community_name=community.name,
        zone_type=zone_type,
        direct_hazard_exposure=is_directly_exposed,
        cascade_affected=is_cascade_affected,
        cascade_path=cascade_path,
        explanation=explanation,
    )


def _generate_overall_explanation(
    hazard: Hazard,
    directly_affected: list[ZoneClassification],
    cascade_shadow: list[ZoneClassification],
    unaffected: list[ZoneClassification],
) -> str:
    """Generate overall explanation for the shadow zone analysis."""
    direct_count = len(directly_affected)
    shadow_count = len(cascade_shadow)
    unaffected_count = len(unaffected)

    if shadow_count == 0:
        return (
            f"{hazard.type.value.capitalize()} {hazard.id} directly affects {direct_count} communities. "
            f"No cascade shadow zones detected (no communities reached indirectly via "
            f"infrastructure dependencies above threshold {CASCADE_THRESHOLD}). "
            f"{unaffected_count} communities remain unaffected."
        )

    shadow_names = [z.community_name for z in cascade_shadow]
    direct_names = [z.community_name for z in directly_affected]

    return (
        f"{hazard.type.value.capitalize()} {hazard.id} directly affects {direct_count} communities: "
        f"{', '.join(direct_names)}. "
        f"Additionally, {shadow_count} communities are in CASCADE SHADOW ZONES — "
        f"not directly hit by the hazard but endangered through infrastructure failure "
        f"propagation: {', '.join(shadow_names)}. "
        f"{unaffected_count} communities are unaffected. "
        f"Shadow zones represent indirect risk via dependency chains, not direct hazard exposure."
    )


def analyze_shadow_zones(hazard_id: str) -> ShadowZoneResult:
    """
    Analyze cascade shadow zones for a given hazard.

    Args:
        hazard_id: The hazard ID to analyze (e.g., "H001")

    Returns:
        ShadowZoneResult with all communities classified

    Raises:
        ValueError: If hazard_id is not found
    """
    loader = get_data_loader()
    dataset = loader.get_dataset()

    # Find the hazard
    hazard = next((h for h in dataset.hazards if h.id == hazard_id), None)
    if hazard is None:
        raise ValueError(f"Hazard {hazard_id} not found in dataset")

    # Get direct exposure set
    direct_exposure = _get_hazard_direct_exposure(hazard)

    # Get cascade-affected communities and their paths
    cascade_affected, cascade_paths = _get_cascade_affected_communities(hazard_id)

    # Classify all communities
    directly_affected = []
    cascade_shadow = []
    unaffected = []

    for community in dataset.communities:
        classification = _classify_community(
            community=community,
            hazard=hazard,
            direct_exposure=direct_exposure,
            cascade_affected=cascade_affected,
            cascade_paths=cascade_paths,
        )

        if classification.zone_type == "DIRECT_HAZARD_ZONE":
            directly_affected.append(classification)
        elif classification.zone_type == "CASCADE_SHADOW_ZONE":
            cascade_shadow.append(classification)
        else:
            unaffected.append(classification)

    # Sort each category by community ID for deterministic output
    directly_affected.sort(key=lambda x: x.community_id)
    cascade_shadow.sort(key=lambda x: x.community_id)
    unaffected.sort(key=lambda x: x.community_id)

    explanation = _generate_overall_explanation(
        hazard, directly_affected, cascade_shadow, unaffected
    )

    return ShadowZoneResult(
        hazard_id=hazard_id,
        hazard_type=hazard.type.value,
        directly_affected=directly_affected,
        cascade_shadow=cascade_shadow,
        unaffected=unaffected,
        explanation=explanation,
    )