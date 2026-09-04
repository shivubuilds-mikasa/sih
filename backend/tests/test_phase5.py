"""Tests for SHARMI Phase 5 — Time-to-Impact Engine."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.time_to_impact import (
    estimate_impact_timeline,
    ImpactTimelineResult,
    BASE_DELAY,
    _calculate_edge_delay,
)

client = TestClient(app)


class TestTimeToImpactEngineCore:
    """Tests for core time-to-impact engine functions."""

    def test_edge_delay_calculation(self) -> None:
        """Test the synthetic delay formula: BASE_DELAY * (1 - weight)."""
        # Weight 1.0 -> delay 0
        assert _calculate_edge_delay(1.0) == pytest.approx(0.0)
        # Weight 0.7 -> delay 30
        assert _calculate_edge_delay(0.7) == pytest.approx(30.0)
        # Weight 0.85 -> delay 15
        assert _calculate_edge_delay(0.85) == pytest.approx(15.0)
        # Weight 0.0 -> delay 100
        assert _calculate_edge_delay(0.0) == pytest.approx(BASE_DELAY)

    def test_h001_timeline_succeeds(self) -> None:
        """H001 timeline estimation should succeed."""
        result = estimate_impact_timeline("H001")
        assert isinstance(result, ImpactTimelineResult)
        assert result.hazard_id == "H001"
        assert result.hazard_type == "flood"
        assert isinstance(result.timeline, list)
        assert len(result.timeline) >= 1
        assert isinstance(result.explanation, str)

    def test_h001_first_node_is_hazard_at_time_zero(self) -> None:
        """First timeline node should be H001 at time 0."""
        result = estimate_impact_timeline("H001")
        first = result.timeline[0]
        assert first.node_id == "H001"
        assert first.node_type == "hazard"
        assert first.estimated_propagation_time == 0.0
        assert first.predecessor is None
        assert first.dependency_weight is None

    def test_critical_chain_order_h001_r012_p003_v001(self) -> None:
        """Critical chain should appear in order with increasing times."""
        result = estimate_impact_timeline("H001")
        node_ids = [n.node_id for n in result.timeline]

        # Check order: H001 -> R012 -> P003 -> V001
        h001_idx = node_ids.index("H001")
        r012_idx = node_ids.index("R012")
        p003_idx = node_ids.index("P003")
        v001_idx = node_ids.index("V001")

        assert h001_idx < r012_idx < p003_idx < v001_idx

    def test_increasing_cumulative_times(self) -> None:
        """Cumulative times should strictly increase along the critical chain."""
        result = estimate_impact_timeline("H001")

        # Find nodes in the chain
        nodes = {n.node_id: n for n in result.timeline}
        h001 = nodes["H001"]
        r012 = nodes["R012"]
        p003 = nodes["P003"]
        v001 = nodes["V001"]

        assert h001.estimated_propagation_time == 0.0
        assert r012.estimated_propagation_time > h001.estimated_propagation_time
        assert p003.estimated_propagation_time > r012.estimated_propagation_time
        assert v001.estimated_propagation_time > p003.estimated_propagation_time

    def test_dependency_weights_match_dataset(self) -> None:
        """Dependency weights in timeline should match dataset values."""
        result = estimate_impact_timeline("H001")
        nodes = {n.node_id: n for n in result.timeline}

        # H001 -> R012 weight 0.85
        assert nodes["R012"].dependency_weight == pytest.approx(0.85)
        # R012 -> P003 weight 0.78
        assert nodes["P003"].dependency_weight == pytest.approx(0.78)
        # P003 -> V001 weight 0.88
        assert nodes["V001"].dependency_weight == pytest.approx(0.88)

    def test_predecessor_links_correct(self) -> None:
        """Predecessor links should form the correct chain."""
        result = estimate_impact_timeline("H001")
        nodes = {n.node_id: n for n in result.timeline}

        assert nodes["R012"].predecessor == "H001"
        assert nodes["P003"].predecessor == "R012"
        assert nodes["V001"].predecessor == "P003"

    def test_results_are_deterministic(self) -> None:
        """Multiple runs should produce identical results."""
        result1 = estimate_impact_timeline("H001")
        result2 = estimate_impact_timeline("H001")

        assert len(result1.timeline) == len(result2.timeline)
        for n1, n2 in zip(result1.timeline, result2.timeline):
            assert n1.node_id == n2.node_id
            assert n1.estimated_propagation_time == n2.estimated_propagation_time
            assert n1.predecessor == n2.predecessor
            assert n1.dependency_weight == n2.dependency_weight

    def test_unknown_hazard_raises_error(self) -> None:
        """Unknown hazard should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            estimate_impact_timeline("H999")

    def test_h002_timeline(self) -> None:
        """H002 (landslide) should have timeline with directly affected communities."""
        result = estimate_impact_timeline("H002")
        assert result.hazard_id == "H002"
        assert result.hazard_type == "landslide"
        node_ids = [n.node_id for n in result.timeline]
        assert "H002" in node_ids
        # H002 has no infrastructure dependencies but has directly affected communities
        # These should now be included with direct hazard-to-community edges
        assert "V003" in node_ids
        assert "V005" in node_ids
        assert "V007" in node_ids
        # All communities should have time_to_impact = 10.0 (BASE_DELAY * (1 - 0.9))
        for node in result.timeline:
            if node.node_type == "community":
                assert node.estimated_propagation_time == 10.0

    def test_h003_timeline(self) -> None:
        """H003 (cyclone) should have timeline but all communities directly affected."""
        result = estimate_impact_timeline("H003")
        assert result.hazard_id == "H003"
        assert result.hazard_type == "cyclone"

    def test_h004_timeline(self) -> None:
        """H004 (heatwave) should have timeline."""
        result = estimate_impact_timeline("H004")
        assert result.hazard_id == "H004"
        assert result.hazard_type == "heatwave"

    def test_explanation_mentions_chain(self) -> None:
        """Explanation should mention the critical chain for H001."""
        result = estimate_impact_timeline("H001")
        assert "H001" in result.explanation
        assert "R012" in result.explanation or "Road 12" in result.explanation
        assert "P003" in result.explanation or "Pump 3" in result.explanation
        assert "V001" in result.explanation or "Village A" in result.explanation

    def test_explanation_mentions_synthetic(self) -> None:
        """Explanation should note synthetic nature."""
        result = estimate_impact_timeline("H001")
        assert "synthetic" in result.explanation.lower() or "prototype" in result.explanation.lower()


class TestTimeToImpactAPI:
    """Tests for time-to-impact API endpoints."""

    def test_timeline_success(self) -> None:
        """POST /impact/timeline with valid hazard_id should succeed."""
        response = client.post("/impact/timeline", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert data["hazard_id"] == "H001"
        assert data["hazard_type"] == "flood"
        assert "timeline" in data
        assert "explanation" in data
        assert "note" in data

    def test_unknown_hazard_returns_404(self) -> None:
        """POST /impact/timeline with unknown hazard_id should return 404."""
        response = client.post("/impact/timeline", json={"hazard_id": "H999"})
        assert response.status_code == 404

    def test_critical_chain_in_api_response(self) -> None:
        """API response for H001 should contain the critical chain in order."""
        response = client.post("/impact/timeline", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        node_ids = [n["node_id"] for n in data["timeline"]]
        h001_idx = node_ids.index("H001")
        r012_idx = node_ids.index("R012")
        p003_idx = node_ids.index("P003")
        v001_idx = node_ids.index("V001")

        assert h001_idx < r012_idx < p003_idx < v001_idx

    def test_increasing_times_in_api(self) -> None:
        """Cumulative times should increase in API response."""
        response = client.post("/impact/timeline", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        nodes = {n["node_id"]: n for n in data["timeline"]}
        assert nodes["H001"]["estimated_propagation_time"] == 0.0
        assert nodes["R012"]["estimated_propagation_time"] > nodes["H001"]["estimated_propagation_time"]
        assert nodes["P003"]["estimated_propagation_time"] > nodes["R012"]["estimated_propagation_time"]
        assert nodes["V001"]["estimated_propagation_time"] > nodes["P003"]["estimated_propagation_time"]

    def test_dependency_weights_in_api(self) -> None:
        """Dependency weights should be present in API response."""
        response = client.post("/impact/timeline", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        nodes = {n["node_id"]: n for n in data["timeline"]}
        assert nodes["R012"]["dependency_weight"] == pytest.approx(0.85)
        assert nodes["P003"]["dependency_weight"] == pytest.approx(0.78)
        assert nodes["V001"]["dependency_weight"] == pytest.approx(0.88)

    def test_predecessor_links_in_api(self) -> None:
        """Predecessor links should be correct in API response."""
        response = client.post("/impact/timeline", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        nodes = {n["node_id"]: n for n in data["timeline"]}
        assert nodes["R012"]["predecessor"] == "H001"
        assert nodes["P003"]["predecessor"] == "R012"
        assert nodes["V001"]["predecessor"] == "P003"

    def test_explanation_present(self) -> None:
        """Response should include human-readable explanation."""
        response = client.post("/impact/timeline", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert "explanation" in data
        assert len(data["explanation"]) > 0

    def test_note_present(self) -> None:
        """Response should include prototype note."""
        response = client.post("/impact/timeline", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert "note" in data
        assert "prototype" in data["note"].lower()
        assert "synthetic" in data["note"].lower()
        assert "not a real" in data["note"].lower()


class TestBackwardCompatibility:
    """Tests to ensure Phase 0-4 still work."""

    def test_health_endpoint(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_phase1_endpoints(self) -> None:
        response = client.get("/demo/communities")
        assert response.status_code == 200
        assert len(response.json()) >= 8

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

    def test_phase3_cascade_endpoints(self) -> None:
        response = client.post("/cascade/simulate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        assert "cascade_paths" in response.json()

    def test_phase4_shadow_zone_endpoints(self) -> None:
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        assert "directly_affected" in response.json()
        assert "cascade_shadow" in response.json()