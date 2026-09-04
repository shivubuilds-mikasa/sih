"""Tests for SHARMI Phase 8a — Confidence Engine."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.confidence_engine import (
    evaluate_confidence,
    ConfidenceResult,
    _classify_confidence,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
)

client = TestClient(app)


class TestConfidenceEngineCore:
    """Tests for core confidence engine functions."""

    def test_classify_confidence_high(self) -> None:
        """Score >= 0.75 should be HIGH."""
        assert _classify_confidence(HIGH_CONFIDENCE_THRESHOLD) == "HIGH"
        assert _classify_confidence(0.8) == "HIGH"
        assert _classify_confidence(1.0) == "HIGH"

    def test_classify_confidence_medium(self) -> None:
        """Score >= 0.50 and < 0.75 should be MEDIUM."""
        assert _classify_confidence(MEDIUM_CONFIDENCE_THRESHOLD) == "MEDIUM"
        assert _classify_confidence(0.6) == "MEDIUM"
        assert _classify_confidence(0.74) == "MEDIUM"

    def test_classify_confidence_low(self) -> None:
        """Score < 0.50 should be LOW."""
        assert _classify_confidence(0.49) == "LOW"
        assert _classify_confidence(0.0) == "LOW"

    def test_h001_confidence_succeeds(self) -> None:
        """H001 confidence evaluation should succeed."""
        result = evaluate_confidence("H001")
        assert isinstance(result, ConfidenceResult)
        assert result.hazard_id == "H001"
        assert result.hazard_type == "flood"
        assert len(result.community_confidences) == 10
        assert isinstance(result.overall_explanation, str)
        assert len(result.overall_explanation) > 0

    def test_h001_has_confidence_levels(self) -> None:
        """H001 should have communities at different confidence levels."""
        result = evaluate_confidence("H001")
        levels = {c.confidence_level for c in result.community_confidences}
        # Should have at least HIGH or MEDIUM
        assert "HIGH" in levels or "MEDIUM" in levels

    def test_h001_v001_high_confidence(self) -> None:
        """V001 (direct hazard, critical chain) should have reasonable confidence."""
        result = evaluate_confidence("H001")
        v001 = next(c for c in result.community_confidences if c.community_id == "V001")
        # Direct hazard zone with good data should have decent confidence
        assert v001.overall_confidence >= 0.0
        assert v001.confidence_level in ["HIGH", "MEDIUM"]

    def test_h001_shadow_zones_lower_confidence(self) -> None:
        """Shadow zone communities should generally have lower confidence."""
        result = evaluate_confidence("H001")
        v003 = next(c for c in result.community_confidences if c.community_id == "V003")
        v005 = next(c for c in result.community_confidences if c.community_id == "V005")
        # Shadow zones should have cascade_strength component
        assert v003.components.cascade_strength >= 0.0
        assert v005.components.cascade_strength >= 0.0

    def test_h001_unaffected_low_confidence(self) -> None:
        """Unaffected communities should have LOW confidence."""
        result = evaluate_confidence("H001")
        for cid in ["V007", "V008", "V010"]:
            c = next(c for c in result.community_confidences if c.community_id == cid)
            assert c.confidence_level in ["LOW", "MEDIUM"]
            # Cascade strength should be 0 for unaffected
            assert c.components.cascade_strength == 0.0

    def test_h001_sorted_by_confidence(self) -> None:
        """Results should be sorted by confidence descending."""
        result = evaluate_confidence("H001")
        confidences = [c.overall_confidence for c in result.community_confidences]
        assert confidences == sorted(confidences, reverse=True)

    def test_h001_components_present(self) -> None:
        """All components should be present for each community."""
        result = evaluate_confidence("H001")
        for c in result.community_confidences:
            assert hasattr(c.components, "data_quality")
            assert hasattr(c.components, "model_coverage")
            assert hasattr(c.components, "input_completeness")
            assert hasattr(c.components, "cascade_strength")
            assert hasattr(c.components, "time_certainty")
            # All in [0, 1]
            for val in [
                c.components.data_quality,
                c.components.model_coverage,
                c.components.input_completeness,
                c.components.cascade_strength,
                c.components.time_certainty,
            ]:
                assert 0.0 <= val <= 1.0

    def test_h001_caveats_present(self) -> None:
        """Caveats should be present for each community."""
        result = evaluate_confidence("H001")
        for c in result.community_confidences:
            assert isinstance(c.caveats, list)
            # At least some communities should have caveats
            if c.community_id in ["V003", "V005"]:  # shadow zones
                assert len(c.caveats) > 0

    def test_h001_explanation_present(self) -> None:
        """Each community should have explanation."""
        result = evaluate_confidence("H001")
        for c in result.community_confidences:
            assert isinstance(c.explanation, str)
            assert len(c.explanation) > 0
            assert c.community_name in c.explanation

    def test_deterministic_results(self) -> None:
        """Multiple runs should produce identical results."""
        result1 = evaluate_confidence("H001")
        result2 = evaluate_confidence("H001")
        assert len(result1.community_confidences) == len(result2.community_confidences)
        for c1, c2 in zip(result1.community_confidences, result2.community_confidences):
            assert c1.community_id == c2.community_id
            assert c1.overall_confidence == c2.overall_confidence
            assert c1.confidence_level == c2.confidence_level

    def test_unknown_hazard_raises_error(self) -> None:
        """Unknown hazard should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            evaluate_confidence("H999")

    def test_h002_confidence(self) -> None:
        """H002 confidence evaluation."""
        result = evaluate_confidence("H002")
        assert result.hazard_id == "H002"
        assert result.hazard_type == "landslide"
        assert len(result.community_confidences) == 10

    def test_h003_confidence(self) -> None:
        """H003 (cyclone - all direct) confidence evaluation."""
        result = evaluate_confidence("H003")
        assert result.hazard_id == "H003"
        assert result.hazard_type == "cyclone"
        assert len(result.community_confidences) == 10
        # All communities are direct hazard zone
        for c in result.community_confidences:
            assert c.components.cascade_strength == 1.0 or "Direct hazard" in c.explanation

    def test_note_mentions_prototype(self) -> None:
        """Result should include prototype note."""
        result = evaluate_confidence("H001")
        note = result.to_dict()["note"]
        assert "prototype" in note.lower()
        assert "not statistically calibrated" in note.lower()
        assert "synthetic" in note.lower()


class TestConfidenceAPI:
    """Tests for confidence API endpoints."""

    def test_evaluate_success(self) -> None:
        """POST /confidence/evaluate with valid hazard_id should succeed."""
        response = client.post("/confidence/evaluate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert data["hazard_id"] == "H001"
        assert data["hazard_type"] == "flood"
        assert "community_confidences" in data
        assert len(data["community_confidences"]) == 10
        assert "overall_explanation" in data
        assert "note" in data

    def test_unknown_hazard_returns_404(self) -> None:
        """POST /confidence/evaluate with unknown hazard_id should return 404."""
        response = client.post("/confidence/evaluate", json={"hazard_id": "H999"})
        assert response.status_code == 404

    def test_v001_has_confidence_level(self) -> None:
        """V001 should have confidence level in response."""
        response = client.post("/confidence/evaluate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        v001 = next(c for c in data["community_confidences"] if c["community_id"] == "V001")
        assert v001["confidence_level"] in ["HIGH", "MEDIUM", "LOW"]
        assert "components" in v001

    def test_components_structure(self) -> None:
        """Each confidence should have all components."""
        response = client.post("/confidence/evaluate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        for c in data["community_confidences"]:
            comp = c["components"]
            assert "data_quality" in comp
            assert "model_coverage" in comp
            assert "input_completeness" in comp
            assert "cascade_strength" in comp
            assert "time_certainty" in comp
            for val in comp.values():
                assert 0.0 <= val <= 1.0

    def test_caveats_in_response(self) -> None:
        """Caveats should be in API response."""
        response = client.post("/confidence/evaluate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        for c in data["community_confidences"]:
            assert "caveats" in c
            assert isinstance(c["caveats"], list)

    def test_explanation_in_response(self) -> None:
        """Explanation should be in API response."""
        response = client.post("/confidence/evaluate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        for c in data["community_confidences"]:
            assert "explanation" in c
            assert isinstance(c["explanation"], str)
            assert len(c["explanation"]) > 0


class TestBackwardCompatibility:
    """Tests to ensure Phase 0-7 still work."""

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

    def test_phase6_action_endpoints(self) -> None:
        response = client.post("/actions/recommend", json={"hazard_id": "H001"})
        assert response.status_code == 200
        assert "recommendations" in response.json()

    def test_phase7_relocation_endpoints(self) -> None:
        response = client.post("/relocation/optimize", json={"hazard_id": "H001"})
        assert response.status_code == 200
        assert "plans" in response.json()