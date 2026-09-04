"""Tests for SHARMI Phase 3 — Infrastructure Cascade Engine."""

import pytest
from fastapi.testclient import TestClient
import networkx as nx

from app.main import app
from app.services.cascade_engine import (
    CASCADE_THRESHOLD,
    simulate_cascade,
    _build_dependency_graph,
    _propagate_failure,
    _identify_affected_communities,
    _identify_affected_services,
)
from app.services.data_loader import get_data_loader

client = TestClient(app)


class TestCascadeEngineCore:
    """Tests for core cascade engine functions."""

    def test_graph_construction_succeeds(self) -> None:
        """Graph construction should succeed and produce a valid DiGraph."""
        graph = _build_dependency_graph()
        assert isinstance(graph, nx.DiGraph)
        assert graph.number_of_nodes() > 0
        assert graph.number_of_edges() > 0

    def test_expected_nodes_present(self) -> None:
        """Expected demo nodes should be present in the graph."""
        graph = _build_dependency_graph()

        # Critical chain nodes
        assert graph.has_node("H001")
        assert graph.has_node("R012")
        assert graph.has_node("P003")
        assert graph.has_node("V001")

    def test_critical_dependency_edges_exist(self) -> None:
        """Critical dependency edges for the demo chain should exist."""
        graph = _build_dependency_graph()

        # H001 -> R012
        assert graph.has_edge("H001", "R012")
        edge_data = graph.get_edge_data("H001", "R012")
        assert edge_data is not None
        assert edge_data.get("weight") == pytest.approx(0.85)

        # R012 -> P003
        assert graph.has_edge("R012", "P003")
        edge_data = graph.get_edge_data("R012", "P003")
        assert edge_data is not None
        assert edge_data.get("weight") == pytest.approx(0.78)

        # P003 -> V001
        assert graph.has_edge("P003", "V001")
        edge_data = graph.get_edge_data("P003", "V001")
        assert edge_data is not None
        assert edge_data.get("weight") == pytest.approx(0.88)

    def test_h001_is_flood(self) -> None:
        """H001 should be a flood hazard."""
        graph = _build_dependency_graph()
        assert graph.nodes["H001"].get("node_type") == "hazard"

    def test_r012_is_road(self) -> None:
        """R012 should be a road infrastructure."""
        graph = _build_dependency_graph()
        assert graph.nodes["R012"].get("node_type") == "infrastructure"
        assert graph.nodes["R012"].get("infra_type") == "road"

    def test_p003_is_pump(self) -> None:
        """P003 should be a pump infrastructure."""
        graph = _build_dependency_graph()
        assert graph.nodes["P003"].get("node_type") == "infrastructure"
        assert graph.nodes["P003"].get("infra_type") == "pump"

    def test_v001_is_community(self) -> None:
        """V001 should be a community."""
        graph = _build_dependency_graph()
        assert graph.nodes["V001"].get("node_type") == "community"

    def test_h001_simulation_succeeds(self) -> None:
        """H001 simulation should succeed and return a result."""
        result = simulate_cascade("H001")
        assert result.hazard_id == "H001"
        assert result.hazard_type == "flood"
        assert result.affected is True
        assert isinstance(result.affected_node_ids, list)
        assert isinstance(result.cascade_paths, list)
        assert isinstance(result.affected_community_ids, list)
        assert isinstance(result.affected_services, list)
        assert isinstance(result.explanation, str)

    def test_critical_path_detected(self) -> None:
        """Critical path H001 -> R012 -> P003 -> V001 should be detected."""
        result = simulate_cascade("H001")

        # Check that the ordered path exists in cascade_paths
        found_path = False
        for path in result.cascade_paths:
            node_ids = [n.node_id for n in path.nodes]
            if node_ids == ["H001", "R012", "P003", "V001"]:
                found_path = True
                break

        assert found_path, "Critical path H001 -> R012 -> P003 -> V001 not found in cascade paths"

    def test_v001_in_affected_communities(self) -> None:
        """V001 should be among affected communities for H001."""
        result = simulate_cascade("H001")
        assert "V001" in result.affected_community_ids

    def test_p003_in_affected_infrastructure(self) -> None:
        """P003 should be identified as affected infrastructure."""
        result = simulate_cascade("H001")
        assert "P003" in result.affected_node_ids

    def test_affected_services_returned(self) -> None:
        """Appropriate affected service information should be returned."""
        result = simulate_cascade("H001")

        # Should have water_supply service from P003 (pump)
        service_types = [s.service_type for s in result.affected_services]
        assert "water_supply" in service_types

    def test_threshold_prevents_low_weight_propagation(self) -> None:
        """Dependencies below threshold should not propagate."""
        # All demo dependencies have weight >= 0.70, so we construct a test graph
        graph = nx.DiGraph()
        graph.add_node("A", node_type="hazard", name="Hazard A")
        graph.add_node("B", node_type="infrastructure", name="Infra B", infra_type="road")
        graph.add_node("C", node_type="community", name="Community C")
        graph.add_edge("A", "B", weight=0.60)  # Below threshold
        graph.add_edge("B", "C", weight=0.80)  # Above threshold

        initial = {"A"}
        affected, paths = _propagate_failure(graph, initial)

        # B should NOT be affected because A->B weight (0.60) < 0.70
        # Therefore C should also NOT be affected
        assert "B" not in affected
        assert "C" not in affected
        assert "A" in affected
        assert len(paths) == 0

    def test_unknown_hazard_raises_error(self) -> None:
        """Unknown hazard should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            simulate_cascade("H999")

    def test_cycles_do_not_cause_infinite_traversal(self) -> None:
        """Cyclic graph should not cause infinite propagation."""
        # Construct a graph with a cycle
        graph = nx.DiGraph()
        graph.add_node("A", node_type="hazard", name="Hazard A")
        graph.add_node("B", node_type="infrastructure", name="Infra B", infra_type="road")
        graph.add_node("C", node_type="infrastructure", name="Infra C", infra_type="pump")
        graph.add_edge("A", "B", weight=0.85)
        graph.add_edge("B", "C", weight=0.85)
        graph.add_edge("C", "B", weight=0.85)  # Cycle: B -> C -> B

        initial = {"A"}
        affected, paths = _propagate_failure(graph, initial)

        # Should terminate and not loop infinitely
        assert "B" in affected
        assert "C" in affected
        assert "A" in affected
        # Should not have duplicated paths from cycles
        # BFS with visited set should prevent infinite loop

    def test_results_are_deterministic(self) -> None:
        """Multiple runs should produce identical results."""
        result1 = simulate_cascade("H001")
        result2 = simulate_cascade("H001")

        assert result1.affected_node_ids == result2.affected_node_ids
        assert result1.affected_community_ids == result2.affected_community_ids
        assert len(result1.cascade_paths) == len(result2.cascade_paths)

        # Paths should be in same order
        for p1, p2 in zip(result1.cascade_paths, result2.cascade_paths):
            assert [n.node_id for n in p1.nodes] == [n.node_id for n in p2.nodes]


class TestCascadeAPI:
    """Tests for cascade API endpoints."""

    def test_simulate_success(self) -> None:
        """POST /cascade/simulate with valid hazard_id should succeed."""
        response = client.post("/cascade/simulate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert data["hazard_id"] == "H001"
        assert data["hazard_type"] == "flood"
        assert data["affected"] is True
        assert "affected_node_ids" in data
        assert "cascade_paths" in data
        assert "affected_community_ids" in data
        assert "affected_services" in data
        assert "explanation" in data
        assert "note" in data

    def test_unknown_hazard_returns_404(self) -> None:
        """POST /cascade/simulate with unknown hazard_id should return 404."""
        response = client.post("/cascade/simulate", json={"hazard_id": "H999"})
        assert response.status_code == 404

    def test_critical_chain_in_api_response(self) -> None:
        """API response for H001 should contain the critical chain."""
        response = client.post("/cascade/simulate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        # Check affected nodes include the chain
        assert "H001" in data["affected_node_ids"]
        assert "R012" in data["affected_node_ids"]
        assert "P003" in data["affected_node_ids"]
        assert "V001" in data["affected_node_ids"]

        # Check V001 in affected communities
        assert "V001" in data["affected_community_ids"]

        # Check cascade path exists with correct order
        found_path = False
        for path in data["cascade_paths"]:
            node_ids = [n["node_id"] for n in path["nodes"]]
            if node_ids == ["H001", "R012", "P003", "V001"]:
                found_path = True
                # Check propagation strength is the minimum weight
                assert path["propagation_strength"] == pytest.approx(min(0.85, 0.78, 0.88))
                break

        assert found_path, "Critical path not found in API response"

    def test_v001_explanation_mentions_chain(self) -> None:
        """Explanation should mention the critical chain for H001."""
        response = client.post("/cascade/simulate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        explanation = data["explanation"]
        assert "H001" in explanation
        assert "R012" in explanation or "Road 12" in explanation
        assert "P003" in explanation or "Pump 3" in explanation
        assert "V001" in explanation or "Village A" in explanation

    def test_affected_services_structure(self) -> None:
        """Affected services should have correct structure."""
        response = client.post("/cascade/simulate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        services = data["affected_services"]
        assert len(services) > 0

        for service in services:
            assert "service_type" in service
            assert "infrastructure_id" in service
            assert "infrastructure_name" in service

    def test_note_in_response(self) -> None:
        """Response should include prototype note."""
        response = client.post("/cascade/simulate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert "prototype" in data["note"].lower()
        assert "threshold" in data["note"].lower() or "demonstration" in data["note"].lower()


class TestBackwardCompatibility:
    """Tests to ensure Phase 0, 1, 2 still work."""

    def test_health_endpoint(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_phase1_endpoints(self) -> None:
        response = client.get("/demo/communities")
        assert response.status_code == 200
        assert len(response.json()) >= 8

        response = client.get("/demo/hazards")
        assert response.status_code == 200
        assert len(response.json()) >= 4

        response = client.get("/demo/infrastructure")
        assert response.status_code == 200
        assert len(response.json()) >= 10

        response = client.get("/demo/dependencies")
        assert response.status_code == 200
        assert len(response.json()) >= 20

        response = client.get("/demo/relocation/sites")
        assert response.status_code == 200
        assert len(response.json()) >= 4

    def test_phase2_risk_endpoints(self) -> None:
        response = client.post("/risk/calculate", json={
            "hazard_intensity": 0.5,
            "exposure": 0.5,
            "vulnerability": 0.5
        })
        assert response.status_code == 200

        response = client.get("/risk/ranked")
        assert response.status_code == 200
        assert "communities" in response.json()
        assert len(response.json()["communities"]) >= 8