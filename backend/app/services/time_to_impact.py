"""SHARMI Phase 5 — Time-to-Impact Estimation Engine.

Provides a transparent prototype estimate for the order/timing of cascade impacts.
This is NOT a real disaster prediction — it is a deterministic synthetic model
for the SIH demo.

The model assigns a propagation delay to each dependency based on a documented
synthetic rule:

    estimated_propagation_time = BASE_DELAY * (1 - dependency_weight)

Where BASE_DELAY is a synthetic constant (set to 100 arbitrary time units).
Higher dependency weight → shorter propagation delay (stronger dependency =
faster failure transmission).

This is a deterministic prototype rule for demonstrating ordered progression.
It is not derived from real infrastructure physics or calibrated to real-world
timing. The output unit is abstract "time units" — not minutes, hours, or days.

The critical path must show ordered progression:
H001 → R012 → P003 → V001
with increasing estimated cumulative impact time.
"""

from dataclasses import dataclass
from typing import Literal

from ..models.domain import Dependency, Hazard
from ..services.cascade_engine import simulate_cascade, _build_dependency_graph, CASCADE_THRESHOLD
from ..services.data_loader import get_data_loader


# Synthetic base delay constant (arbitrary time units)
# This is a prototype parameter, not a real-world timing calibration.
BASE_DELAY: float = 100.0


@dataclass(frozen=True)
class ImpactTimelineNode:
    """A single node in the impact timeline."""
    node_id: str
    node_type: str  # "hazard" | "infrastructure" | "community"
    name: str
    estimated_propagation_time: float  # Cumulative from hazard start
    predecessor: str | None
    dependency_weight: float | None
    explanation: str


@dataclass(frozen=True)
class ImpactTimelineResult:
    """Complete impact timeline result for a hazard."""
    hazard_id: str
    hazard_type: str
    timeline: list[ImpactTimelineNode]
    explanation: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "hazard_id": self.hazard_id,
            "hazard_type": self.hazard_type,
            "timeline": [node.__dict__ for node in self.timeline],
            "explanation": self.explanation,
            "note": (
                "This is a deterministic synthetic prototype for demonstration. "
                "Estimated propagation time uses the formula: "
                "BASE_DELAY * (1 - dependency_weight), where BASE_DELAY=100 "
                "arbitrary units. Higher weight = faster propagation. "
                "This is NOT a real-world timing prediction and does not represent "
                "minutes, hours, or days. Dependency weights and the propagation "
                "threshold (0.70) are synthetic demonstration parameters."
            ),
        }


def _calculate_edge_delay(weight: float) -> float:
    """
    Calculate propagation delay for a single dependency edge.

    Synthetic rule: delay = BASE_DELAY * (1 - weight)
    - Weight 1.0 → delay 0 (instant propagation)
    - Weight 0.7 → delay 30
    - Weight 0.0 → delay 100 (maximum)

    This is a deterministic prototype rule, not physics-based.
    """
    return BASE_DELAY * (1.0 - weight)


def _get_cascade_edges_in_order(hazard_id: str) -> list[tuple[str, str, float]]:
    """
    Get cascade edges in topological order from hazard outward.

    Returns list of (source, target, weight) for edges that propagate.
    Only includes edges where weight >= CASCADE_THRESHOLD.
    Follows the actual cascade propagation paths (like cascade_engine).
    """
    graph = _build_dependency_graph()

    # Verify hazard exists
    if not graph.has_node(hazard_id):
        raise ValueError(f"Hazard {hazard_id} not found in dataset")

    # Get cascade simulation to know which nodes are affected
    cascade_result = simulate_cascade(hazard_id)
    affected_nodes = set()

    # Map original IDs back to graph node IDs (handle INFRA_ prefix)
    hazard_ids = {h.id for h in get_data_loader().get_dataset().hazards}
    infra_id_map = {}
    for infra in get_data_loader().get_dataset().infrastructure:
        node_id = infra.id
        if graph.has_node(node_id) and node_id in hazard_ids:
            node_id = f"INFRA_{infra.id}"
        infra_id_map[infra.id] = node_id

    for node_id in cascade_result.affected_node_ids:
        if node_id in hazard_ids:
            affected_nodes.add(node_id)
        else:
            graph_id = infra_id_map.get(node_id, node_id)
            affected_nodes.add(graph_id)

    # BFS from hazard to collect edges in propagation order
    # Only add edge when target is first visited (like cascade_engine)
    from collections import deque
    visited = set([hazard_id])
    queue = deque([hazard_id])
    edges_in_order = []

    while queue:
        current = queue.popleft()

        for successor in graph.successors(current):
            edge_data = graph.get_edge_data(current, successor)
            weight = edge_data.get("weight", 0.0) if edge_data else 0.0

            if weight < CASCADE_THRESHOLD:
                continue

            if successor not in affected_nodes:
                continue

            # Only process if not visited yet (prevents cycle back-edges)
            if successor in visited:
                continue

            visited.add(successor)

            # Get original IDs for output
            source_orig = current[6:] if current.startswith("INFRA_") else current
            target_orig = successor[6:] if successor.startswith("INFRA_") else successor

            edges_in_order.append((source_orig, target_orig, weight))

            queue.append(successor)

    return edges_in_order


def _build_timeline(
    hazard_id: str,
    hazard_type: str,
    cascade_edges: list[tuple[str, str, float]],
) -> list[ImpactTimelineNode]:
    """Build the timeline nodes with cumulative propagation times."""
    # Build node lookup for metadata
    graph = _build_dependency_graph()

    def get_node_info(node_id: str) -> tuple[str, str]:
        """Get (node_type, name) for a node."""
        if node_id in graph:
            node_data = graph.nodes[node_id]
            return node_data.get("node_type", "unknown"), node_data.get("name", node_id)
        # Check with INFRA_ prefix
        prefixed = f"INFRA_{node_id}"
        if prefixed in graph:
            node_data = graph.nodes[prefixed]
            return node_data.get("node_type", "unknown"), node_data.get("name", node_id)
        return "unknown", node_id

    # Track cumulative time per node
    cumulative_time = {hazard_id: 0.0}
    timeline_nodes = []

    # Add hazard as starting point
    hazard_node_type, hazard_name = get_node_info(hazard_id)
    timeline_nodes.append(ImpactTimelineNode(
        node_id=hazard_id,
        node_type=hazard_node_type,
        name=hazard_name,
        estimated_propagation_time=0.0,
        predecessor=None,
        dependency_weight=None,
        explanation=f"Origin hazard {hazard_id} ({hazard_type}) starts at time 0.",
    ))

    # Process edges in order
    for source, target, weight in cascade_edges:
        source_time = cumulative_time.get(source, 0.0)
        edge_delay = _calculate_edge_delay(weight)
        target_time = source_time + edge_delay
        cumulative_time[target] = target_time

        target_type, target_name = get_node_info(target)

        explanation = (
            f"{target_name} ({target}) reached from {source} "
            f"via dependency weight {weight:.2f}. "
            f"Propagation delay: {edge_delay:.1f} time units "
            f"(BASE_DELAY * (1 - {weight:.2f})). "
            f"Cumulative time: {target_time:.1f}."
        )

        timeline_nodes.append(ImpactTimelineNode(
            node_id=target,
            node_type=target_type,
            name=target_name,
            estimated_propagation_time=round(target_time, 1),
            predecessor=source,
            dependency_weight=weight,
            explanation=explanation,
        ))

    return timeline_nodes


def _generate_explanation(
    hazard_id: str,
    hazard_type: str,
    timeline: list[ImpactTimelineNode],
) -> str:
    """Generate human-readable explanation of the timeline."""
    if len(timeline) <= 1:
        return f"Hazard {hazard_id} ({hazard_type}) has no downstream dependencies above the propagation threshold."

    # Find the critical path (longest timeline to a community)
    community_nodes = [n for n in timeline if n.node_type == "community"]
    if community_nodes:
        latest = max(community_nodes, key=lambda n: n.estimated_propagation_time)
        path_nodes = []
        for node in timeline:
            if node.estimated_propagation_time <= latest.estimated_propagation_time:
                path_nodes.append(f"{node.name} ({node.node_id}) at t={node.estimated_propagation_time:.1f}")

        path_str = " → ".join(path_nodes)
        return (
            f"Flood {hazard_id} propagates through infrastructure dependencies. "
            f"Estimated propagation timeline: {path_str}. "
            f"Times are synthetic (BASE_DELAY * (1 - weight)) for demo ordering only."
        )
    else:
        infra_nodes = [n for n in timeline if n.node_type == "infrastructure"]
        if infra_nodes:
            path_str = " → ".join(f"{n.name} ({n.node_id}) at t={n.estimated_propagation_time:.1f}" for n in infra_nodes)
            return f"Flood {hazard_id} propagates through infrastructure: {path_str}. No communities reached."
        else:
            return f"Hazard {hazard_id} ({hazard_type}) has no downstream dependencies above the propagation threshold."


# Synthetic direct hazard-to-community dependency weight
# Used for communities directly affected by hazard (no infrastructure cascade)
DIRECT_HAZARD_WEIGHT: float = 0.90


def estimate_impact_timeline(hazard_id: str) -> ImpactTimelineResult:
    """
    Estimate impact timeline for a given hazard.

    Args:
        hazard_id: The hazard ID to analyze (e.g., "H001")

    Returns:
        ImpactTimelineResult with ordered timeline nodes

    Raises:
        ValueError: If hazard_id is not found
    """
    loader = get_data_loader()
    dataset = loader.get_dataset()

    # Find the hazard
    hazard = next((h for h in dataset.hazards if h.id == hazard_id), None)
    if hazard is None:
        raise ValueError(f"Hazard {hazard_id} not found in dataset")

    # Get cascade edges in order
    cascade_edges = _get_cascade_edges_in_order(hazard_id)

    # Get communities that are directly affected by the hazard
    # but NOT already reached via cascade (to avoid duplicates)
    # These will get direct hazard-to-community edges with synthetic weight
    graph = _build_dependency_graph()

    # Find communities already in cascade_edges
    cascade_reached_communities = set()
    for _, target, _ in cascade_edges:
        # Check if target is a community
        target_type, _ = _get_node_type_and_name(target, graph)
        if target_type == "community":
            cascade_reached_communities.add(target)

    # Add direct hazard-to-community edges for directly affected communities
    # that aren't already reached via cascade
    direct_community_edges = []
    for community_id in hazard.affected_communities:
        if community_id not in cascade_reached_communities:
            direct_community_edges.append((hazard_id, community_id, DIRECT_HAZARD_WEIGHT))

    # Combine cascade edges and direct edges (cascade edges first for proper ordering)
    all_edges = cascade_edges + direct_community_edges

    # Build timeline
    timeline = _build_timeline(hazard_id, hazard.type.value, all_edges)

    # Generate explanation
    explanation = _generate_explanation(hazard_id, hazard.type.value, timeline)

    return ImpactTimelineResult(
        hazard_id=hazard_id,
        hazard_type=hazard.type.value,
        timeline=timeline,
        explanation=explanation,
    )


def _get_node_type_and_name(node_id: str, graph) -> tuple[str, str]:
    """Get (node_type, name) for a node from the graph."""
    if node_id in graph:
        node_data = graph.nodes[node_id]
        return node_data.get("node_type", "unknown"), node_data.get("name", node_id)
    # Check with INFRA_ prefix
    prefixed = f"INFRA_{node_id}"
    if prefixed in graph:
        node_data = graph.nodes[prefixed]
        return node_data.get("node_type", "unknown"), node_data.get("name", node_id)
    return "unknown", node_id