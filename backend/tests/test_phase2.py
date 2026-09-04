"""Tests for SHARMI Phase 2 — Direct Risk Engine."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.risk_engine import (
    calculate_direct_risk,
    calculate_risk_score,
    classify_risk,
    WEIGHT_HAZARD_INTENSITY,
    WEIGHT_EXPOSURE,
    WEIGHT_VULNERABILITY,
)

client = TestClient(app)


class TestRiskEngineCore:
    """Tests for core risk engine functions."""

    def test_known_calculation(self) -> None:
        """Test a known calculation: 0.50*0.8 + 0.30*0.6 + 0.20*0.7 = 0.71"""
        # 0.50 * 0.8 = 0.40
        # 0.30 * 0.6 = 0.18
        # 0.20 * 0.7 = 0.14
        # Total = 0.72
        result = calculate_direct_risk(0.8, 0.6, 0.7)
        expected = (
            WEIGHT_HAZARD_INTENSITY * 0.8
            + WEIGHT_EXPOSURE * 0.6
            + WEIGHT_VULNERABILITY * 0.7
        )
        assert round(result.risk_score, 4) == round(expected, 4)
        assert result.risk_level == "HIGH"  # 0.72 > 0.60

    def test_all_zero_inputs(self) -> None:
        """All inputs zero should produce score 0, level LOW."""
        result = calculate_direct_risk(0.0, 0.0, 0.0)
        assert result.risk_score == 0.0
        assert result.risk_level == "LOW"

    def test_all_one_inputs(self) -> None:
        """All inputs one should produce score 1.0, level HIGH."""
        result = calculate_direct_risk(1.0, 1.0, 1.0)
        assert result.risk_score == 1.0
        assert result.risk_level == "HIGH"

    def test_low_classification_boundary(self) -> None:
        """Score exactly 0.29 should be LOW."""
        result = calculate_direct_risk(0.29, 0.0, 0.0)  # 0.50*0.29 = 0.145 -> wait, this doesn't hit 0.29
        # Let me use exact values: score = 0.50*h + 0.30*e + 0.20*v = 0.29
        # If h=0.58, e=0, v=0 -> 0.29
        result = calculate_direct_risk(0.58, 0.0, 0.0)
        assert round(result.risk_score, 4) == 0.29
        assert result.risk_level == "LOW"

    def test_medium_lower_boundary(self) -> None:
        """Score exactly 0.30 should be MEDIUM."""
        result = calculate_direct_risk(0.60, 0.0, 0.0)  # 0.50 * 0.60 = 0.30
        assert round(result.risk_score, 4) == 0.30
        assert result.risk_level == "MEDIUM"

    def test_medium_upper_boundary(self) -> None:
        """Score exactly 0.59 should be MEDIUM."""
        # 0.50 * 1.0 + 0.30 * 0.3 = 0.5 + 0.09 = 0.59
        result = calculate_direct_risk(1.0, 0.3, 0.0)
        assert round(result.risk_score, 4) == 0.59
        assert result.risk_level == "MEDIUM"

    def test_high_lower_boundary(self) -> None:
        """Score exactly 0.60 should be HIGH."""
        result = calculate_direct_risk(1.0, 0.33333333, 0.0)  # 0.50 + 0.1 = 0.60
        # Let's be precise: 0.50*1.0 + 0.30*0.333... = 0.50 + 0.10 = 0.60
        result = calculate_direct_risk(1.0, 1/3, 0.0)
        assert round(result.risk_score, 4) == 0.60
        assert result.risk_level == "HIGH"

    def test_high_upper_boundary(self) -> None:
        """Score exactly 1.00 should be HIGH."""
        result = calculate_direct_risk(1.0, 1.0, 1.0)
        assert result.risk_score == 1.0
        assert result.risk_level == "HIGH"

    def test_invalid_hazard_intensity_rejected(self) -> None:
        """hazard_intensity > 1 should raise ValueError."""
        with pytest.raises(ValueError, match="hazard_intensity"):
            calculate_direct_risk(1.1, 0.5, 0.5)

    def test_invalid_exposure_rejected(self) -> None:
        """exposure < 0 should raise ValueError."""
        with pytest.raises(ValueError, match="exposure"):
            calculate_direct_risk(0.5, -0.1, 0.5)

    def test_invalid_vulnerability_rejected(self) -> None:
        """vulnerability > 1 should raise ValueError."""
        with pytest.raises(ValueError, match="vulnerability"):
            calculate_direct_risk(0.5, 0.5, 1.5)

    def test_classify_risk_directly(self) -> None:
        """Test classify_risk function directly."""
        assert classify_risk(0.0) == "LOW"
        assert classify_risk(0.29) == "LOW"
        assert classify_risk(0.30) == "MEDIUM"
        assert classify_risk(0.59) == "MEDIUM"
        assert classify_risk(0.60) == "HIGH"
        assert classify_risk(1.0) == "HIGH"

    def test_result_contains_all_fields(self) -> None:
        """RiskResult should contain all expected fields."""
        result = calculate_direct_risk(0.5, 0.5, 0.5)
        d = result.to_dict()
        assert "risk_score" in d
        assert "risk_level" in d
        assert "components" in d
        assert "weights" in d
        assert "explanation" in d
        assert set(d["components"].keys()) == {"hazard_intensity", "exposure", "vulnerability"}
        assert set(d["weights"].keys()) == {"hazard_intensity", "exposure", "vulnerability"}

    def test_explanation_mentions_inputs(self) -> None:
        """Explanation should mention the actual input characteristics."""
        result = calculate_direct_risk(0.9, 0.9, 0.9)
        assert "high hazard intensity" in result.explanation
        assert "high exposure" in result.explanation
        assert "elevated community vulnerability" in result.explanation
        assert "SHARMI baseline weighted model" in result.explanation

        result = calculate_direct_risk(0.1, 0.1, 0.1)
        assert "low hazard intensity" in result.explanation
        assert "low exposure" in result.explanation
        assert "low community vulnerability" in result.explanation


class TestRiskAPI:
    """Tests for risk API endpoints."""

    def test_calculate_success(self) -> None:
        """POST /risk/calculate with valid inputs should succeed."""
        response = client.post("/risk/calculate", json={
            "hazard_intensity": 0.78,
            "exposure": 1.0,
            "vulnerability": 0.65,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
        assert 0.0 <= data["risk_score"] <= 1.0
        assert "components" in data
        assert "weights" in data
        assert "explanation" in data

    def test_calculate_validation_error_high(self) -> None:
        """POST /risk/calculate with hazard_intensity > 1 should fail."""
        response = client.post("/risk/calculate", json={
            "hazard_intensity": 1.1,
            "exposure": 0.5,
            "vulnerability": 0.5,
        })
        assert response.status_code == 422

    def test_calculate_validation_error_low(self) -> None:
        """POST /risk/calculate with exposure < 0 should fail."""
        response = client.post("/risk/calculate", json={
            "hazard_intensity": 0.5,
            "exposure": -0.1,
            "vulnerability": 0.5,
        })
        assert response.status_code == 422

    def test_calculate_validation_error_non_numeric(self) -> None:
        """POST /risk/calculate with non-numeric should fail."""
        response = client.post("/risk/calculate", json={
            "hazard_intensity": "high",
            "exposure": 0.5,
            "vulnerability": 0.5,
        })
        assert response.status_code == 422

    def test_ranked_endpoint_returns_communities(self) -> None:
        """GET /risk/ranked should return a list of communities."""
        response = client.get("/risk/ranked")
        assert response.status_code == 200
        data = response.json()
        assert "communities" in data
        assert isinstance(data["communities"], list)
        assert len(data["communities"]) >= 8

    def test_ranked_results_sorted_descending(self) -> None:
        """Ranked results should be sorted descending by risk_score."""
        response = client.get("/risk/ranked")
        data = response.json()
        communities = data["communities"]
        scores = [c["risk_score"] for c in communities]
        assert scores == sorted(scores, reverse=True)

    def test_v001_is_directly_exposed_to_h001(self) -> None:
        """V001 should have exposure=1.0 because it's in H001's affected_communities."""
        response = client.get("/risk/ranked")
        data = response.json()
        v001_entry = next((c for c in data["communities"] if c["community_id"] == "V001"), None)
        assert v001_entry is not None
        # With exposure=1.0, hazard=0.78, vuln=0.65:
        # score = 0.50*0.78 + 0.30*1.0 + 0.20*0.65 = 0.39 + 0.30 + 0.13 = 0.82
        assert v001_entry["risk_score"] == pytest.approx(0.82, rel=1e-3)
        assert v001_entry["risk_level"] == "HIGH"

    def test_non_exposed_communities_have_lower_risk(self) -> None:
        """Communities not in H001 should have lower risk (exposure=0)."""
        response = client.get("/risk/ranked")
        data = response.json()
        v003_entry = next((c for c in data["communities"] if c["community_id"] == "V003"), None)
        assert v003_entry is not None
        # V003 is not in H001 affected list
        # score = 0.50*0.78 + 0.30*0.0 + 0.20*0.48 = 0.39 + 0.0 + 0.096 = 0.486
        assert v003_entry["risk_score"] == pytest.approx(0.486, rel=1e-3)
        assert v003_entry["risk_level"] == "MEDIUM"

    def test_ranked_response_includes_metadata(self) -> None:
        """Ranked response should include hazard metadata and note."""
        response = client.get("/risk/ranked")
        data = response.json()
        assert data["hazard_id"] == "H001"
        assert data["hazard_type"] == "flood"
        assert data["hazard_intensity"] == 0.78
        assert "exposure_rule" in data
        assert "note" in data
        assert "prototype" in data["note"].lower()

    def test_health_endpoint_still_works(self) -> None:
        """GET /health should still work after Phase 2 changes."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "sharmi-backend"

    def test_phase1_endpoints_still_work(self) -> None:
        """Phase 1 endpoints should still work."""
        response = client.get("/demo/communities")
        assert response.status_code == 200
        assert len(response.json()) >= 8

        response = client.get("/demo/communities/V001")
        assert response.status_code == 200
        assert response.json()["id"] == "V001"

        response = client.get("/demo/communities/INVALID")
        assert response.status_code == 404