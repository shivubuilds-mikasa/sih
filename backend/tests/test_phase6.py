"""Tests for SHARMI Phase 6 — Action Recommendation Engine."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.action_engine import (
    generate_action_recommendations,
    ActionRecommendationResult,
    _determine_action,
    TIME_THRESHOLD_CRITICAL,
    TIME_THRESHOLD_HIGH,
    TIME_THRESHOLD_MEDIUM,
)
from app.models.domain import Community

client = TestClient(app)


class TestActionEngineCore:
    """Tests for core action recommendation engine functions."""

    def test_determine_action_direct_high_critical_time(self) -> None:
        """DIRECT_HAZARD_ZONE + HIGH risk + critical time -> EVACUATION_ASSESSMENT."""
        action, confidence, rationale = _determine_action(
            zone_type="DIRECT_HAZARD_ZONE",
            direct_risk_level="HIGH",
            time_to_impact=TIME_THRESHOLD_CRITICAL - 10,  # Below critical threshold
            affected_services=[],
            is_critical_infra_affected=False,
        )
        assert action == "EVACUATION_ASSESSMENT"
        assert confidence > 0.8
        assert "EVACUATION_ASSESSMENT" in rationale
        assert "HIGH" in rationale

    def test_determine_action_direct_high_short_time(self) -> None:
        """DIRECT_HAZARD_ZONE + HIGH risk + short time -> PROTECT."""
        action, confidence, rationale = _determine_action(
            zone_type="DIRECT_HAZARD_ZONE",
            direct_risk_level="HIGH",
            time_to_impact=TIME_THRESHOLD_HIGH - 10,  # Below high threshold
            affected_services=[],
            is_critical_infra_affected=False,
        )
        assert action == "PROTECT"
        assert confidence > 0.75
        assert "PROTECT" in rationale

    def test_determine_action_direct_high_long_time(self) -> None:
        """DIRECT_HAZARD_ZONE + HIGH risk + longer time -> PREPARE."""
        action, confidence, rationale = _determine_action(
            zone_type="DIRECT_HAZARD_ZONE",
            direct_risk_level="HIGH",
            time_to_impact=TIME_THRESHOLD_HIGH + 50,
            affected_services=[],
            is_critical_infra_affected=False,
        )
        assert action == "PREPARE"
        assert "PREPARE" in rationale

    def test_determine_action_direct_medium_short_time(self) -> None:
        """DIRECT_HAZARD_ZONE + MEDIUM risk + short time -> PROTECT."""
        action, confidence, rationale = _determine_action(
            zone_type="DIRECT_HAZARD_ZONE",
            direct_risk_level="MEDIUM",
            time_to_impact=TIME_THRESHOLD_HIGH - 10,
            affected_services=[],
            is_critical_infra_affected=False,
        )
        assert action == "PROTECT"

    def test_determine_action_direct_medium_long_time(self) -> None:
        """DIRECT_HAZARD_ZONE + MEDIUM risk + long time -> PREPARE."""
        action, confidence, rationale = _determine_action(
            zone_type="DIRECT_HAZARD_ZONE",
            direct_risk_level="MEDIUM",
            time_to_impact=TIME_THRESHOLD_HIGH + 50,
            affected_services=[],
            is_critical_infra_affected=False,
        )
        assert action == "PREPARE"

    def test_determine_action_direct_low(self) -> None:
        """DIRECT_HAZARD_ZONE + LOW risk -> MONITOR."""
        action, confidence, rationale = _determine_action(
            zone_type="DIRECT_HAZARD_ZONE",
            direct_risk_level="LOW",
            time_to_impact=None,
            affected_services=[],
            is_critical_infra_affected=False,
        )
        assert action == "MONITOR"
        assert "MONITOR" in rationale

    def test_determine_action_shadow_critical_service_short_time(self) -> None:
        """CASCADE_SHADOW_ZONE + critical service + short time -> PROTECT."""
        action, confidence, rationale = _determine_action(
            zone_type="CASCADE_SHADOW_ZONE",
            direct_risk_level=None,
            time_to_impact=TIME_THRESHOLD_HIGH - 10,
            affected_services=["healthcare", "access"],
            is_critical_infra_affected=True,
        )
        assert action == "PROTECT"
        assert "healthcare" in rationale or "water_supply" in rationale

    def test_determine_action_shadow_critical_service_long_time(self) -> None:
        """CASCADE_SHADOW_ZONE + critical service + long time -> INSPECT."""
        action, confidence, rationale = _determine_action(
            zone_type="CASCADE_SHADOW_ZONE",
            direct_risk_level=None,
            time_to_impact=TIME_THRESHOLD_MEDIUM + 50,
            affected_services=["healthcare"],
            is_critical_infra_affected=True,
        )
        assert action == "INSPECT"
        assert "INSPECT" in rationale

    def test_determine_action_shadow_services_medium_time(self) -> None:
        """CASCADE_SHADOW_ZONE + services + medium time -> PREPARE."""
        action, confidence, rationale = _determine_action(
            zone_type="CASCADE_SHADOW_ZONE",
            direct_risk_level=None,
            time_to_impact=TIME_THRESHOLD_MEDIUM - 10,
            affected_services=["power", "access"],
            is_critical_infra_affected=False,
        )
        assert action == "PREPARE"

    def test_determine_action_shadow_services_long_time(self) -> None:
        """CASCADE_SHADOW_ZONE + services + long time -> INSPECT."""
        action, confidence, rationale = _determine_action(
            zone_type="CASCADE_SHADOW_ZONE",
            direct_risk_level=None,
            time_to_impact=TIME_THRESHOLD_MEDIUM + 50,
            affected_services=["power"],
            is_critical_infra_affected=False,
        )
        assert action == "INSPECT"

    def test_determine_action_shadow_no_services_medium_time(self) -> None:
        """CASCADE_SHADOW_ZONE + no services + medium time -> PREPARE."""
        action, confidence, rationale = _determine_action(
            zone_type="CASCADE_SHADOW_ZONE",
            direct_risk_level=None,
            time_to_impact=TIME_THRESHOLD_MEDIUM - 10,
            affected_services=[],
            is_critical_infra_affected=False,
        )
        assert action == "PREPARE"

    def test_determine_action_shadow_no_services_long_time(self) -> None:
        """CASCADE_SHADOW_ZONE + no services + long time -> MONITOR."""
        action, confidence, rationale = _determine_action(
            zone_type="CASCADE_SHADOW_ZONE",
            direct_risk_level=None,
            time_to_impact=TIME_THRESHOLD_MEDIUM + 50,
            affected_services=[],
            is_critical_infra_affected=False,
        )
        assert action == "MONITOR"

    def test_determine_action_unaffected(self) -> None:
        """UNAFFECTED -> MONITOR."""
        action, confidence, rationale = _determine_action(
            zone_type="UNAFFECTED",
            direct_risk_level=None,
            time_to_impact=None,
            affected_services=[],
            is_critical_infra_affected=False,
        )
        assert action == "MONITOR"
        assert confidence >= 0.85
        assert "UNAFFECTED" in rationale

    def test_h001_recommendations_succeed(self) -> None:
        """H001 should generate recommendations for all communities."""
        result = generate_action_recommendations("H001")
        assert isinstance(result, ActionRecommendationResult)
        assert result.hazard_id == "H001"
        assert result.hazard_type == "flood"
        assert len(result.recommendations) == 10  # All 10 communities
        assert isinstance(result.explanation, str)
        assert len(result.explanation) > 0

    def test_h001_has_evacuation_assessment(self) -> None:
        """H001 should have EVACUATION_ASSESSMENT for V001 (critical chain)."""
        result = generate_action_recommendations("H001")
        actions = {r.community_id: r.action for r in result.recommendations}
        # V001 is in critical chain H001->R012->P003->V001 with short time
        assert actions.get("V001") == "EVACUATION_ASSESSMENT"

    def test_h001_has_protect_for_direct_high(self) -> None:
        """H001 direct high-risk communities should get PROTECT."""
        result = generate_action_recommendations("H001")
        actions = {r.community_id: r.action for r in result.recommendations}
        # V002, V004, V006, V009 are directly exposed
        # They have varying vulnerabilities; check at least some are PROTECT or higher
        direct_communities = ["V001", "V002", "V004", "V006", "V009"]
        high_priority = ["EVACUATION_ASSESSMENT", "PROTECT"]
        # At least some direct communities should have elevated actions
        elevated = [c for c in direct_communities if actions.get(c) in high_priority]
        assert len(elevated) > 0

    def test_h001_has_shadow_zone_actions(self) -> None:
        """H001 cascade shadow communities should have appropriate actions."""
        result = generate_action_recommendations("H001")
        actions = {r.community_id: r.action for r in result.recommendations}
        zones = {r.community_id: r.zone_type for r in result.recommendations}

        # V003 and V005 are cascade shadow for H001
        assert zones.get("V003") == "CASCADE_SHADOW_ZONE"
        assert zones.get("V005") == "CASCADE_SHADOW_ZONE"
        # They should have at least INSPECT or PREPARE
        for cid in ["V003", "V005"]:
            assert actions.get(cid) in ["INSPECT", "PREPARE", "PROTECT"]

    def test_h001_unaffected_are_monitor(self) -> None:
        """H001 unaffected communities should be MONITOR."""
        result = generate_action_recommendations("H001")
        actions = {r.community_id: r.action for r in result.recommendations}
        zones = {r.community_id: r.zone_type for r in result.recommendations}

        # V007, V008, V010 are unaffected for H001
        for cid in ["V007", "V008", "V010"]:
            assert zones.get(cid) == "UNAFFECTED"
            assert actions.get(cid) == "MONITOR"

    def test_h002_recommendations(self) -> None:
        """H002 (landslide) recommendations."""
        result = generate_action_recommendations("H002")
        assert result.hazard_id == "H002"
        assert result.hazard_type == "landslide"
        assert len(result.recommendations) == 10

    def test_h003_recommendations(self) -> None:
        """H003 (cyclone) - all communities directly exposed."""
        result = generate_action_recommendations("H003")
        assert result.hazard_id == "H003"
        assert result.hazard_type == "cyclone"
        assert len(result.recommendations) == 10
        # All communities should be DIRECT_HAZARD_ZONE
        for rec in result.recommendations:
            assert rec.zone_type == "DIRECT_HAZARD_ZONE"

    def test_h004_recommendations(self) -> None:
        """H004 (heatwave) - all communities directly exposed."""
        result = generate_action_recommendations("H004")
        assert result.hazard_id == "H004"
        assert result.hazard_type == "heatwave"
        assert len(result.recommendations) == 10
        for rec in result.recommendations:
            assert rec.zone_type == "DIRECT_HAZARD_ZONE"

    def test_unknown_hazard_raises_error(self) -> None:
        """Unknown hazard should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            generate_action_recommendations("H999")

    def test_results_are_deterministic(self) -> None:
        """Multiple runs should produce identical results."""
        result1 = generate_action_recommendations("H001")
        result2 = generate_action_recommendations("H001")

        assert len(result1.recommendations) == len(result2.recommendations)
        for r1, r2 in zip(result1.recommendations, result2.recommendations):
            assert r1.community_id == r2.community_id
            assert r1.action == r2.action
            assert r1.confidence == r2.confidence
            assert r1.zone_type == r2.zone_type

    def test_recommendations_sorted_by_priority(self) -> None:
        """Recommendations should be sorted by action priority."""
        result = generate_action_recommendations("H001")
        priority_order = {
            "EVACUATION_ASSESSMENT": 0,
            "PROTECT": 1,
            "INSPECT": 2,
            "PREPARE": 3,
            "MONITOR": 4,
        }
        actions = [r.action for r in result.recommendations]
        priorities = [priority_order[a] for a in actions]
        assert priorities == sorted(priorities)

    def test_explanation_contains_action_counts(self) -> None:
        """Explanation should summarize action counts."""
        result = generate_action_recommendations("H001")
        assert "EVACUATION_ASSESSMENT" in result.explanation
        assert "PROTECT" in result.explanation or "PREPARE" in result.explanation
        assert "MONITOR" in result.explanation

    def test_note_mentions_prototype(self) -> None:
        """Result should include prototype note."""
        result = generate_action_recommendations("H001")
        note = result.to_dict()["note"]
        assert "prototype" in note.lower()
        assert "not autonomous" in note.lower()
        assert "evacuation_assessment" in note.lower()


class TestActionAPI:
    """Tests for action recommendation API endpoints."""

    def test_recommend_success(self) -> None:
        """POST /actions/recommend with valid hazard_id should succeed."""
        response = client.post("/actions/recommend", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert data["hazard_id"] == "H001"
        assert data["hazard_type"] == "flood"
        assert "recommendations" in data
        assert len(data["recommendations"]) == 10
        assert "explanation" in data
        assert "note" in data

    def test_unknown_hazard_returns_404(self) -> None:
        """POST /actions/recommend with unknown hazard_id should return 404."""
        response = client.post("/actions/recommend", json={"hazard_id": "H999"})
        assert response.status_code == 404

    def test_v001_evacuation_assessment_in_api(self) -> None:
        """API response for H001 should have EVACUATION_ASSESSMENT for V001."""
        response = client.post("/actions/recommend", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        v001_rec = next(r for r in data["recommendations"] if r["community_id"] == "V001")
        assert v001_rec["action"] == "EVACUATION_ASSESSMENT"
        assert v001_rec["zone_type"] == "DIRECT_HAZARD_ZONE"
        assert v001_rec["confidence"] > 0.8

    def test_shadow_zone_communities_have_cascade_path(self) -> None:
        """Shadow zone communities should include cascade path in response."""
        response = client.post("/actions/recommend", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        v003_rec = next(r for r in data["recommendations"] if r["community_id"] == "V003")
        assert v003_rec["zone_type"] == "CASCADE_SHADOW_ZONE"
        assert v003_rec["cascade_path"] is not None
        assert len(v003_rec["cascade_path"]) > 0
        assert "H001" in v003_rec["cascade_path"]
        assert "V003" in v003_rec["cascade_path"]

    def test_unaffected_are_monitor(self) -> None:
        """Unaffected communities should be MONITOR."""
        response = client.post("/actions/recommend", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        for cid in ["V007", "V008", "V010"]:
            rec = next(r for r in data["recommendations"] if r["community_id"] == cid)
            assert rec["action"] == "MONITOR"
            assert rec["zone_type"] == "UNAFFECTED"

    def test_direct_risk_level_present_for_direct_zone(self) -> None:
        """Direct hazard zone communities should have direct_risk_level."""
        response = client.post("/actions/recommend", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        for cid in ["V001", "V002", "V004", "V006", "V009"]:
            rec = next(r for r in data["recommendations"] if r["community_id"] == cid)
            assert rec["direct_risk_level"] in ["LOW", "MEDIUM", "HIGH"]

    def test_time_to_impact_present_for_reached_communities(self) -> None:
        """Communities in timeline should have time_to_impact."""
        response = client.post("/actions/recommend", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        # V001 is in timeline
        v001_rec = next(r for r in data["recommendations"] if r["community_id"] == "V001")
        assert v001_rec["time_to_impact"] is not None
        assert v001_rec["time_to_impact"] > 0

    def test_affected_services_present(self) -> None:
        """Communities with affected services should have them listed."""
        response = client.post("/actions/recommend", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        # V001 is served by P003 (water_supply) and R012 (access)
        v001_rec = next(r for r in data["recommendations"] if r["community_id"] == "V001")
        assert v001_rec["affected_services"] is not None
        assert len(v001_rec["affected_services"]) > 0


class TestBackwardCompatibility:
    """Tests to ensure Phase 0-5 still work."""

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

    def test_phase5_time_to_impact_endpoints(self) -> None:
        response = client.post("/impact/timeline", json={"hazard_id": "H001"})
        assert response.status_code == 200
        assert "timeline" in response.json()
        assert "explanation" in response.json()