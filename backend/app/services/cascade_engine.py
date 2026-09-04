"""SHARMI Phase 3 — Infrastructure Cascade Engine.

Graph-based dependency engine using NetworkX to simulate how infrastructure
failures propagate through dependency relationships.

This is a deterministic prototype for the SIH demo. The propagation threshold
and dependency weights are synthetic demonstration parameters, not calibrated
real-world infrastructure failure probabilities.
"""

from dataclasses import dataclass
from typing import Literal

import networkx as nx

from ..models.domain import Dependency, Hazard, InfrastructureNode
from ..services.data_loader import get_data_loader


# Propagation threshold — deterministic prototype rule
# A dependency propagates failure when weight >= CASCADE_THRESHOLD
# This threshold is a deterministic prototype rule for demonstrating
# dependency propagation. It is not a calibrated failure probability.
CASCADE_THRESHOLD: float = 0.70


@dataclass(frozen=True)
class CascadeNode:
    """A node in the cascade path."""
    node_id: str
    node_type: str  # "hazard" | "infrastructure" | "community"
    name: str


@dataclass(frozen=True)
class CascadePath:
    """A single cascade path from hazard to affected node."""
    nodes: list[CascadeNode]
    # Minimum weight along the path (bottleneck strength)
    propagation_strength: float


@dataclass(frozen=True)
class AffectedService:
    """An affected service derived from infrastructure."""
    service_type: str
    infrastructure_id: str
    infrastructure_name: str


@dataclass(frozen=True)
class CascadeSimulationResult:
    """Complete result of a cascade simulation."""
    hazard_id: str
    hazard_type: str
    affected: bool
    affected_node_ids: list[str]
    cascade_paths: list[CascadePath]
    affected_community_ids: list[str]
    affected_services: list[AffectedService]
    explanation: str


def _build_dependency_graph() -> nx.DiGraph:
    """Build a directed graph from the demo dataset dependencies.

    Returns:
        A NetworkX DiGraph with nodes for all entities and weighted edges
        from dependencies.
    """
    loader = get_data_loader()
    dataset = loader.get_dataset()

    graph = nx.DiGraph()

    # Add all nodes with their metadata
    # Hazards use their ID directly
    hazard_ids = {h.id for h in dataset.hazards}
    for hazard in dataset.hazards:
        graph.add_node(hazard.id, node_type="hazard", name=hazard.type.value, hazard_type=hazard.type.value)

    # Infrastructure nodes: if ID collides with hazard, prefix with "INFRA_"
    # Track mapping from original ID to graph node ID
    infra_id_map = {}
    for infra in dataset.infrastructure:
        node_id = infra.id
        if graph.has_node(node_id):
            node_id = f"INFRA_{infra.id}"
        infra_id_map[infra.id] = node_id
        graph.add_node(node_id, node_type="infrastructure", name=infra.name, infra_type=infra.type.value, original_id=infra.id)

    for community in dataset.communities:
        graph.add_node(community.id, node_type="community", name=community.name)

    # Add dependency edges with weights
    # Map source/target using infra_id_map ONLY for infrastructure nodes
    # Hazards and communities keep their original IDs
    for dep in dataset.dependencies:
        # Only remap if the source/target is an infrastructure node (not a hazard)
        if dep.source in hazard_ids:
            source_id = dep.source
        else:
            source_id = infra_id_map.get(dep.source, dep.source)

        if dep.target in hazard_ids:
            target_id = dep.target
        else:
            target_id = infra_id_map.get(dep.target, dep.target)

        graph.add_edge(source_id, target_id, weight=dep.weight)

    return graph


def _get_initial_affected_nodes(graph: nx.DiGraph, hazard_id: str) -> set[str]:
    """Get the initial set of affected nodes starting from the hazard.

    Args:
        graph: The dependency graph
        hazard_id: The hazard to start from

    Returns:
        Set of node IDs initially affected (just the hazard itself)
    """
    if not graph.has_node(hazard_id):
        return set()

    return {hazard_id}


def _propagate_failure(graph: nx.DiGraph, initial_nodes: set[str]) -> tuple[set[str], list[CascadePath]]:
    """Propagate failure through the dependency graph using threshold rule.

    Uses BFS from initial nodes, only traversing edges with weight >= CASCADE_THRESHOLD.

    Args:
        graph: The dependency graph
        initial_nodes: Set of node IDs that are initially affected

    Returns:
        Tuple of (all_affected_node_ids, cascade_paths)
    """
    affected = set(initial_nodes)
    visited = set(initial_nodes)
    cascade_paths = []

    # BFS queue: (current_node, path_so_far)
    from collections import deque
    queue = deque()

    for start in initial_nodes:
        queue.append((start, [start]))

    while queue:
        current, path = queue.popleft()

        # Get outgoing edges with weight >= threshold
        for successor in graph.successors(current):
            edge_data = graph.get_edge_data(current, successor)
            weight = edge_data.get("weight", 0.0) if edge_data else 0.0

            if weight < CASCADE_THRESHOLD:
                continue  # Edge below threshold does not propagate

            if successor in visited:
                continue  # Already processed, prevents cycles

            visited.add(successor)
            affected.add(successor)

            # Build cascade path
            new_path = path + [successor]

            # Convert to CascadePath using original IDs (strip INFRA_ prefix)
            cascade_nodes = []
            for node_id in new_path:
                node_data = graph.nodes[node_id]
                # Use original ID for output
                display_id = node_id[6:] if node_id.startswith("INFRA_") else node_id
                cascade_nodes.append(CascadeNode(
                    node_id=display_id,
                    node_type=node_data.get("node_type", "unknown"),
                    name=node_data.get("name", display_id)
                ))

            # Propagation strength = minimum weight along the path
            path_weights = []
            for i in range(len(new_path) - 1):
                u, v = new_path[i], new_path[i + 1]
                edge = graph.get_edge_data(u, v)
                path_weights.append(edge.get("weight", 0.0) if edge else 0.0)

            prop_strength = min(path_weights) if path_weights else 1.0

            cascade_paths.append(CascadePath(
                nodes=cascade_nodes,
                propagation_strength=prop_strength
            ))

            # Continue BFS from this node
            queue.append((successor, new_path))

    return affected, cascade_paths


def _identify_affected_services(
    graph: nx.DiGraph,
    affected_infra_ids: set[str]
) -> list[AffectedService]:
    """Identify affected services from affected infrastructure nodes.

    Args:
        graph: The dependency graph
        affected_infra_ids: Set of affected infrastructure node IDs

    Returns:
        List of affected services
    """
    loader = get_data_loader()
    dataset = loader.get_dataset()

    # Build lookup for infrastructure info
    infra_lookup = {infra.id: infra for infra in dataset.infrastructure}

    services = []
    for infra_id in affected_infra_ids:
        infra = infra_lookup.get(infra_id)
        if infra:
            # Map infrastructure type to service label
            service_map = {
                "road": "access",
                "bridge": "access",
                "pump": "water_supply",
                "hospital": "healthcare",
                "school": "education",
                "power_substation": "power",
                "water_supply": "water_supply",
            }
            service_type = service_map.get(infra.type.value, infra.type.value)
            services.append(AffectedService(
                service_type=service_type,
                infrastructure_id=infra.id,
                infrastructure_name=infra.name
            ))

    return services


def _identify_affected_communities(
    graph: nx.DiGraph,
    affected_node_ids: set[str]
) -> list[str]:
    """Identify affected community IDs from affected nodes.

    Args:
        graph: The dependency graph
        affected_node_ids: Set of all affected node IDs

    Returns:
        List of affected community IDs
    """
    affected_communities = []
    for node_id in affected_node_ids:
        if graph.has_node(node_id):
            node_data = graph.nodes[node_id]
            if node_data.get("node_type") == "community":
                affected_communities.append(node_id)
    return affected_communities


def _generate_explanation(
    hazard_id: str,
    hazard_type: str,
    cascade_paths: list[CascadePath],
    affected_communities: list[str],
    affected_services: list[AffectedService]
) -> str:
    """Generate human-readable explanation of the cascade."""
    if not cascade_paths:
        return f"Hazard {hazard_id} ({hazard_type}) did not propagate to any downstream infrastructure or communities."

    # Find the longest/most significant path for explanation
    # For demo, use the path that reaches a community
    community_paths = [p for p in cascade_paths if any(n.node_type == "community" for n in p.nodes)]

    if community_paths:
        # Use the first path that reaches a community
        primary_path = community_paths[0]
        path_str = " → ".join(f"{n.name} ({n.node_id})" for n in primary_path.nodes)
        community_names = [n.name for n in primary_path.nodes if n.node_type == "community"]
        service_types = list(set(s.service_type for s in affected_services))

        return (
            f"{hazard_type.capitalize()} {hazard_id} propagates through "
            f"{path_str}. "
            f"Affected communities: {', '.join(community_names)}. "
            f"Disrupted services: {', '.join(service_types)}."
        )
    else:
        # No community reached, describe infrastructure impact
        infra_nodes = [n for p in cascade_paths for n in p.nodes if n.node_type == "infrastructure"]
        if infra_nodes:
            unique_infra = list(dict.fromkeys(infra_nodes))  # Preserve order, remove dupes
            path_str = " → ".join(f"{n.name} ({n.node_id})" for n in unique_infra)
            return f"{hazard_type.capitalize()} {hazard_id} propagates through infrastructure: {path_str}. No communities directly reached in this cascade."
        else:
            return f"{hazard_type.capitalize()} {hazard_id} has no downstream dependencies above the propagation threshold."


def simulate_cascade(hazard_id: str) -> CascadeSimulationResult:
    """Run a cascade simulation from the given hazard.

    Args:
        hazard_id: The hazard ID to start the cascade from (e.g., "H001")

    Returns:
        CascadeSimulationResult with all affected nodes, paths, and explanation

    Raises:
        ValueError: If hazard_id is not found in the dataset
    """
    graph = _build_dependency_graph()

    # Verify hazard exists
    if not graph.has_node(hazard_id):
        raise ValueError(f"Hazard {hazard_id} not found in dataset")

    hazard_data = graph.nodes[hazard_id]
    hazard_type = hazard_data.get("hazard_type", hazard_data.get("node_type", "unknown"))

    # Get initial affected nodes
    initial = _get_initial_affected_nodes(graph, hazard_id)

    # Propagate failure
    affected_nodes, cascade_paths = _propagate_failure(graph, initial)

    # Identify affected communities and services
    affected_communities = _identify_affected_communities(graph, affected_nodes)
    affected_infra = {n for n in affected_nodes if graph.has_node(n) and graph.nodes[n].get("node_type") == "infrastructure"}
    affected_services = _identify_affected_services(graph, affected_infra)

    # Generate explanation
    explanation = _generate_explanation(
        hazard_id, hazard_type, cascade_paths, affected_communities, affected_services
    )

    # Return original IDs (without INFRA_ prefix) for affected_node_ids
    original_affected = []
    for node_id in sorted(affected_nodes):
        if node_id.startswith("INFRA_"):
            original_affected.append(node_id[6:])  # Remove INFRA_ prefix
        else:
            original_affected.append(node_id)

    return CascadeSimulationResult(
        hazard_id=hazard_id,
        hazard_type=hazard_type,
        affected=len(affected_nodes) > 1,  # True if propagation occurred beyond hazard
        affected_node_ids=original_affected,
        cascade_paths=cascade_paths,
        affected_community_ids=sorted(affected_communities),
        affected_services=affected_services,
        explanation=explanation,
    )