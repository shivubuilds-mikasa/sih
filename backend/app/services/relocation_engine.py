"""SHARMI Phase 7 — Relocation Optimization Engine.

Optimizes safe relocation routes and destinations for affected populations.
Considers:
- Relocation site capacity and current occupancy
- Distance from hazard zone
- Site safety scores (hazard, livelihood, infrastructure, school, health)
- Community population size
- Zone classification (direct hazard, shadow zone, unaffected)

This is a deterministic prototype for the SIH demo. The optimization uses
a weighted scoring model with synthetic parameters, not a calibrated
real-world evacuation planner. Results are decision-support for officer
review only.
"""

from dataclasses import dataclass
from typing import Literal

from ..models.domain import Community, RelocationSite
from ..services.shadow_zone_engine import analyze_shadow_zones, ZoneType
from ..services.action_engine import generate_action_recommendations
from ..services.data_loader import get_data_loader


# Weight constants for site scoring (synthetic prototype parameters)
WEIGHT_HAZARD_SAFETY: float = 0.35      # Lower hazard_score = safer
WEIGHT_LIVELIHOOD: float = 0.20
WEIGHT_INFRASTRUCTURE: float = 0.20
WEIGHT_SCHOOL_ACCESS: float = 0.15
WEIGHT_HEALTH_ACCESS: float = 0.10

# Distance penalty factor (per km)
DISTANCE_PENALTY_PER_KM: float = 0.02

# Zone priority weights (higher = more urgent)
ZONE_PRIORITY = {
    "DIRECT_HAZARD_ZONE": 1.0,
    "CASCADE_SHADOW_ZONE": 0.8,
    "UNAFFECTED": 0.0,  # No relocation needed
}

# Action urgency weights
ACTION_URGENCY = {
    "EVACUATION_ASSESSMENT": 1.0,
    "PROTECT": 0.9,
    "INSPECT": 0.6,
    "PREPARE": 0.5,
    "MONITOR": 0.1,
}


@dataclass(frozen=True)
class SiteScore:
    """Scored relocation site."""
    site_id: str
    site_name: str
    capacity: int
    distance_km: float
    composite_score: float  # Higher = better suitability
    hazard_safety_score: float  # 1 - hazard_score (higher = safer)
    livelihood_score: float
    infrastructure_score: float
    school_access_score: float
    health_access_score: float
    distance_penalty: float


@dataclass(frozen=True)
class CommunityRelocationPlan:
    """Relocation plan for a single community."""
    community_id: str
    community_name: str
    population: int
    zone_type: ZoneType
    action: str
    urgency_score: float  # Combined zone + action urgency
    assigned_site_id: str | None
    assigned_site_name: str | None
    distance_km: float | None
    explanation: str


@dataclass(frozen=True)
class SiteAllocation:
    """Allocation of communities to a relocation site."""
    site_id: str
    site_name: str
    capacity: int
    allocated_population: int
    remaining_capacity: int
    communities: list[str]  # community IDs
    utilization_pct: float


@dataclass(frozen=True)
class RelocationOptimizationResult:
    """Complete relocation optimization result for a hazard."""
    hazard_id: str
    hazard_type: str
    total_affected_population: int
    plans: list[CommunityRelocationPlan]
    site_allocations: list[SiteAllocation]
    site_scores: list[SiteScore]  # Scored sites for reference
    unallocated_population: int
    explanation: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "hazard_id": self.hazard_id,
            "hazard_type": self.hazard_type,
            "total_affected_population": self.total_affected_population,
            "plans": [p.__dict__ for p in self.plans],
            "site_allocations": [sa.__dict__ for sa in self.site_allocations],
            "unallocated_population": self.unallocated_population,
            "explanation": self.explanation,
            "note": (
                "This is a deterministic synthetic prototype for demonstration. "
                "The optimization uses a weighted scoring model with synthetic "
                "parameters (hazard safety 35%, livelihood 20%, infrastructure 20%, "
                "school 15%, health 10%, distance penalty 2%/km). "
                "Results are decision-support for officer review only — "
                "NOT an automated evacuation order."
            ),
        }


def _calculate_site_scores(sites: list[RelocationSite]) -> list[SiteScore]:
    """Calculate composite scores for all relocation sites."""
    scores = []
    for site in sites:
        # Hazard safety: inverse of hazard_score (lower hazard = higher safety)
        hazard_safety = 1.0 - site.hazard_score

        # Distance penalty (linear)
        distance_penalty = min(1.0, site.distance_km * DISTANCE_PENALTY_PER_KM)

        # Composite score (higher = better)
        composite = (
            WEIGHT_HAZARD_SAFETY * hazard_safety
            + WEIGHT_LIVELIHOOD * site.livelihood_score
            + WEIGHT_INFRASTRUCTURE * site.infrastructure_score
            + WEIGHT_SCHOOL_ACCESS * site.school_access
            + WEIGHT_HEALTH_ACCESS * site.health_access
            - distance_penalty
        )

        # Clamp to [0, 1]
        composite = max(0.0, min(1.0, composite))

        scores.append(SiteScore(
            site_id=site.id,
            site_name=site.name,
            capacity=site.capacity,
            distance_km=site.distance_km,
            composite_score=round(composite, 4),
            hazard_safety_score=round(hazard_safety, 4),
            livelihood_score=site.livelihood_score,
            infrastructure_score=site.infrastructure_score,
            school_access_score=site.school_access,
            health_access_score=site.health_access,
            distance_penalty=round(distance_penalty, 4),
        ))

    # Sort by composite score descending (best first)
    scores.sort(key=lambda s: s.composite_score, reverse=True)
    return scores


def _calculate_urgency_score(zone_type: ZoneType, action: str) -> float:
    """Calculate combined urgency score for a community."""
    zone_priority = ZONE_PRIORITY.get(zone_type, 0.0)
    action_urgency = ACTION_URGENCY.get(action, 0.1)
    # Combined: zone priority * action urgency
    return round(zone_priority * action_urgency, 4)


def _allocate_communities_to_sites(
    communities_needing_relocation: list[CommunityRelocationPlan],
    site_scores: list[SiteScore],
) -> tuple[list[CommunityRelocationPlan], list[SiteAllocation], int]:
    """
    Allocate communities to sites based on urgency and site scores.

    Greedy algorithm: sort communities by urgency descending, assign each
    to the best available site that has capacity.
    """
    # Sort communities by urgency descending
    sorted_communities = sorted(
        communities_needing_relocation,
        key=lambda c: c.urgency_score,
        reverse=True
    )

    # Track site capacities
    site_capacities = {s.site_id: s.capacity for s in site_scores}
    site_allocations_map = {s.site_id: {"communities": [], "allocated": 0} for s in site_scores}
    site_lookup = {s.site_id: s for s in site_scores}

    updated_plans = []
    unallocated_pop = 0

    for plan in sorted_communities:
        assigned_site = None

        # Find best site with capacity
        for site_score in site_scores:
            if site_capacities[site_score.site_id] >= plan.population:
                assigned_site = site_score
                break

        if assigned_site:
            # Assign community to this site
            site_capacities[assigned_site.site_id] -= plan.population
            site_allocations_map[assigned_site.site_id]["communities"].append(plan.community_id)
            site_allocations_map[assigned_site.site_id]["allocated"] += plan.population

            updated_plans.append(CommunityRelocationPlan(
                community_id=plan.community_id,
                community_name=plan.community_name,
                population=plan.population,
                zone_type=plan.zone_type,
                action=plan.action,
                urgency_score=plan.urgency_score,
                assigned_site_id=assigned_site.site_id,
                assigned_site_name=assigned_site.site_name,
                distance_km=assigned_site.distance_km,
                explanation=(
                    f"Assigned to {assigned_site.site_name} ({assigned_site.site_id}) "
                    f"at {assigned_site.distance_km} km. "
                    f"Site composite score: {assigned_site.composite_score:.2f}. "
                    f"Community urgency: {plan.urgency_score:.2f}."
                ),
            ))
        else:
            # No site has capacity
            unallocated_pop += plan.population
            updated_plans.append(CommunityRelocationPlan(
                community_id=plan.community_id,
                community_name=plan.community_name,
                population=plan.population,
                zone_type=plan.zone_type,
                action=plan.action,
                urgency_score=plan.urgency_score,
                assigned_site_id=None,
                assigned_site_name=None,
                distance_km=None,
                explanation=(
                    f"NO AVAILABLE SITE WITH CAPACITY for {plan.population} people. "
                    f"Community urgency: {plan.urgency_score:.2f}. "
                    f"All sites at capacity or insufficient remaining space."
                ),
            ))

    # Build site allocations
    site_allocations = []
    for site_score in site_scores:
        alloc = site_allocations_map[site_score.site_id]
        allocated = alloc["allocated"]
        remaining = site_score.capacity - allocated
        site_allocations.append(SiteAllocation(
            site_id=site_score.site_id,
            site_name=site_score.site_name,
            capacity=site_score.capacity,
            allocated_population=allocated,
            remaining_capacity=remaining,
            communities=alloc["communities"],
            utilization_pct=round((allocated / site_score.capacity) * 100, 1) if site_score.capacity > 0 else 0.0,
        ))

    return updated_plans, site_allocations, unallocated_pop


def _generate_explanation(
    hazard_id: str,
    hazard_type: str,
    plans: list[CommunityRelocationPlan],
    site_allocations: list[SiteAllocation],
    unallocated: int,
) -> str:
    """Generate human-readable explanation."""
    # Count communities by zone
    zone_counts = {}
    action_counts = {}
    for plan in plans:
        zone_counts[plan.zone_type] = zone_counts.get(plan.zone_type, 0) + 1
        action_counts[plan.action] = action_counts.get(plan.action, 0) + 1

    parts = [
        f"Relocation optimization for {hazard_type} {hazard_id}:"
    ]

    # Site allocation summary
    total_capacity = sum(s.capacity for s in site_allocations)
    total_allocated = sum(s.allocated_population for s in site_allocations)
    parts.append(f"  Total site capacity: {total_capacity}, Allocated: {total_allocated}")

    if unallocated > 0:
        parts.append(f"  WARNING: {unallocated} people could not be allocated (insufficient capacity)")

    # Zone breakdown
    for zone in ["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE", "UNAFFECTED"]:
        if zone in zone_counts:
            parts.append(f"  {zone}: {zone_counts[zone]} communities")

    # Action breakdown
    for action in ["EVACUATION_ASSESSMENT", "PROTECT", "INSPECT", "PREPARE", "MONITOR"]:
        if action in action_counts:
            parts.append(f"  {action}: {action_counts[action]} communities")

    # Top site
    if site_allocations:
        best_site = max(site_allocations, key=lambda s: s.allocated_population)
        if best_site.allocated_population > 0:
            parts.append(f"  Primary site: {best_site.site_name} ({best_site.allocated_population}/{best_site.capacity})")

    return "\n".join(parts)


def optimize_relocation(hazard_id: str) -> RelocationOptimizationResult:
    """
    Optimize relocation for communities affected by a hazard.

    Args:
        hazard_id: The hazard ID to optimize relocation for (e.g., "H001")

    Returns:
        RelocationOptimizationResult with plans and site allocations

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

    # Get action recommendations
    action_result = generate_action_recommendations(hazard_id)

    # Build lookup for action by community
    action_lookup = {r.community_id: r.action for r in action_result.recommendations}

    # Get site scores
    site_scores = _calculate_site_scores(dataset.relocation_sites)

    # Build plans for communities needing relocation (DIRECT_HAZARD_ZONE and CASCADE_SHADOW_ZONE)
    communities_needing_relocation = []
    total_affected_pop = 0

    for classification in shadow_result.directly_affected + shadow_result.cascade_shadow:
        community = next((c for c in dataset.communities if c.id == classification.community_id), None)
        if not community:
            continue

        action = action_lookup.get(classification.community_id, "MONITOR")
        urgency = _calculate_urgency_score(classification.zone_type, action)

        if classification.zone_type in ("DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE"):
            total_affected_pop += community.population

        communities_needing_relocation.append(CommunityRelocationPlan(
            community_id=community.id,
            community_name=community.name,
            population=community.population,
            zone_type=classification.zone_type,
            action=action,
            urgency_score=urgency,
            assigned_site_id=None,
            assigned_site_name=None,
            distance_km=None,
            explanation=f"Pending allocation. Zone: {classification.zone_type}, Action: {action}, Urgency: {urgency:.2f}",
        ))

    # Allocate
    plans, site_allocations, unallocated = _allocate_communities_to_sites(
        communities_needing_relocation, site_scores
    )

    # Add UNAFFECTED communities with MONITOR (no relocation needed)
    for classification in shadow_result.unaffected:
        community = next((c for c in dataset.communities if c.id == classification.community_id), None)
        if not community:
            continue

        action = action_lookup.get(classification.community_id, "MONITOR")
        plans.append(CommunityRelocationPlan(
            community_id=community.id,
            community_name=community.name,
            population=community.population,
            zone_type=classification.zone_type,
            action=action,
            urgency_score=0.0,
            assigned_site_id=None,
            assigned_site_name=None,
            distance_km=None,
            explanation=f"UNAFFECTED community — no relocation needed. Action: {action}.",
        ))

    # Sort plans: allocated first (by urgency), then unallocated, then unaffected
    def plan_sort_key(p):
        if p.assigned_site_id is not None:
            return (0, -p.urgency_score)
        elif p.zone_type != "UNAFFECTED":
            return (1, -p.urgency_score)
        return (2, 0)

    plans.sort(key=plan_sort_key)

    explanation = _generate_explanation(
        hazard_id, hazard.type.value, plans, site_allocations, unallocated
    )

    return RelocationOptimizationResult(
        hazard_id=hazard_id,
        hazard_type=hazard.type.value,
        total_affected_population=total_affected_pop,
        plans=plans,
        site_allocations=site_allocations,
        site_scores=site_scores,
        unallocated_population=unallocated,
        explanation=explanation,
    )