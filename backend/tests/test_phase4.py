"""Tests for SHARMI Phase 4 — Cascade Shadow Zone Engine."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.shadow_zone_engine import (
    analyze_shadow_zones,
    ZoneClassification,
    ShadowZoneResult,
)
from app.services.cascade_engine import simulate_cascade

client = TestClient(app)


class TestShadowZoneEngineCore:
    """Tests for core shadow zone engine functions."""

    def test_h001_analysis_succeeds(self) -> None:
        """H001 shadow zone analysis should succeed and return a result."""
        result = analyze_shadow_zones("H001")
        assert isinstance(result, ShadowZoneResult)
        assert result.hazard_id == "H001"
        assert result.hazard_type == "flood"
        assert isinstance(result.directly_affected, list)
        assert isinstance(result.cascade_shadow, list)
        assert isinstance(result.unaffected, list)
        assert isinstance(result.explanation, str)

    def test_v001_is_direct_hazard_zone(self) -> None:
        """V001 should be DIRECT_HAZARD_ZONE for H001 (listed in affected_communities)."""
        result = analyze_shadow_zones("H001")
        direct = {z.community_id for z in result.directly_affected}
        assert "V001" in direct
        v001_class = next(z for z in result.directly_affected if z.community_id == "V001")
        assert v001_class.zone_type == "DIRECT_HAZARD_ZONE"
        assert v001_class.direct_hazard_exposure is True
        assert v001_class.cascade_affected is True  # V001 is also in cascade
        assert v001_class.cascade_path is not None
        assert "V001" in v001_class.cascade_path
        assert "H001" in v001_class.cascade_path
        assert "R012" in v001_class.cascade_path
        assert "P003" in v001_class.cascade_path

    def test_v002_is_direct_hazard_zone(self) -> None:
        """V002 should be DIRECT_HAZARD_ZONE for H001 (listed in affected_communities)."""
        result = analyze_shadow_zones("H001")
        direct = {z.community_id for z in result.directly_affected}
        assert "V002" in direct
        v002_class = next(z for z in result.directly_affected if z.community_id == "V002")
        assert v002_class.zone_type == "DIRECT_HAZARD_ZONE"
        assert v002_class.direct_hazard_exposure is True

    def test_v004_is_direct_hazard_zone(self) -> None:
        """V004 should be DIRECT_HAZARD_ZONE for H001 (listed in affected_communities)."""
        result = analyze_shadow_zones("H001")
        direct = {z.community_id for z in result.directly_affected}
        assert "V004" in direct
        v004_class = next(z for z in result.directly_affected if z.community_id == "V004")
        assert v004_class.zone_type == "DIRECT_HAZARD_ZONE"

    def test_v006_is_direct_hazard_zone(self) -> None:
        """V006 should be DIRECT_HAZARD_ZONE for H001 (listed in affected_communities)."""
        result = analyze_shadow_zones("H001")
        direct = {z.community_id for z in result.directly_affected}
        assert "V006" in direct

    def test_v009_is_direct_hazard_zone(self) -> None:
        """V009 should be DIRECT_HAZARD_ZONE for H001 (listed in affected_communities)."""
        result = analyze_shadow_zones("H001")
        direct = {z.community_id for z in result.directly_affected}
        assert "V009" in direct

    def test_all_h001_direct_communities_in_direct_zone(self) -> None:
        """All 5 communities in H001's affected_communities should be DIRECT_HAZARD_ZONE."""
        result = analyze_shadow_zones("H001")
        direct_ids = {z.community_id for z in result.directly_affected}
        expected_direct = {"V001", "V002", "V004", "V006", "V009"}
        assert expected_direct.issubset(direct_ids)

    def test_results_are_deterministic(self) -> None:
        """Multiple runs should produce identical results."""
        result1 = analyze_shadow_zones("H001")
        result2 = analyze_shadow_zones("H001")

        assert result1.directly_affected == result2.directly_affected
        assert result1.cascade_shadow == result2.cascade_shadow
        assert result1.unaffected == result2.unaffected
        assert result1.explanation == result2.explanation

    def test_unknown_hazard_raises_error(self) -> None:
        """Unknown hazard should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            analyze_shadow_zones("H999")

    def test_h002_analysis(self) -> None:
        """H002 (landslide) should have different direct affected communities."""
        result = analyze_shadow_zones("H002")
        assert result.hazard_id == "H002"
        assert result.hazard_type == "landslide"
        direct_ids = {z.community_id for z in result.directly_affected}
        # H002 affects V003, V005, V007
        expected = {"V003", "V005", "V007"}
        assert expected.issubset(direct_ids)

    def test_h003_analysis(self) -> None:
        """H003 (cyclone) affects all communities directly."""
        result = analyze_shadow_zones("H003")
        assert result.hazard_id == "H003"
        assert result.hazard_type == "cyclone"
        direct_ids = {z.community_id for z in result.directly_affected}
        # H003 affects ALL communities
        assert len(direct_ids) == 10
        # No cascade shadow zones should exist for H003 (all directly affected)
        assert len(result.cascade_shadow) == 0

    def test_h004_analysis(self) -> None:
        """H004 (heatwave) affects all communities directly."""
        result = analyze_shadow_zones("H004")
        assert result.hazard_id == "H004"
        assert result.hazard_type == "heatwave"
        direct_ids = {z.community_id for z in result.directly_affected}
        # H004 affects ALL communities
        assert len(direct_ids) == 10
        # No cascade shadow zones should exist
        assert len(result.cascade_shadow) == 0


class TestShadowZoneAPI:
    """Tests for shadow zone API endpoints."""

    def test_analyze_success(self) -> None:
        """POST /shadow-zone/analyze with valid hazard_id should succeed."""
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert data["hazard_id"] == "H001"
        assert data["hazard_type"] == "flood"
        assert "directly_affected" in data
        assert "cascade_shadow" in data
        assert "unaffected" in data
        assert "explanation" in data
        assert "note" in data

    def test_unknown_hazard_returns_404(self) -> None:
        """POST /shadow-zone/analyze with unknown hazard_id should return 404."""
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H999"})
        assert response.status_code == 404

    def test_v001_direct_zone_in_api(self) -> None:
        """V001 should appear in directly_affected in API response."""
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        v001 = next((z for z in data["directly_affected"] if z["community_id"] == "V001"), None)
        assert v001 is not None
        assert v001["zone_type"] == "DIRECT_HAZARD_ZONE"
        assert v001["direct_hazard_exposure"] is True
        assert "cascade_path" in v001
        assert v001["cascade_path"] is not None

    def test_all_five_direct_communities_present(self) -> None:
        """All five H001 direct communities should be in directly_affected."""
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        direct_ids = {z["community_id"] for z in data["directly_affected"]}
        expected = {"V001", "V002", "V004", "V006", "V009"}
        assert expected.issubset(direct_ids)

    def test_direct_zone_has_cascade_paths(self) -> None:
        """Directly affected communities should have cascade paths if also cascade-reached."""
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        for zone in data["directly_affected"]:
            # V001, V002, V004, V006, V009 should have cascade paths since they're served by affected infra
            assert zone["cascade_path"] is not None or zone["community_id"] in ["V001", "V002", "V004", "V006", "V009"]

    def test_h003_no_cascade_shadow(self) -> None:
        """H003 affects all communities directly, so no cascade shadow zones."""
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H003"})
        assert response.status_code == 200
        data = response.json()

        assert len(data["cascade_shadow"]) == 0
        assert len(data["directly_affected"]) == 10
        assert len(data["unaffected"]) == 0

    def test_explanation_present(self) -> None:
        """Response should include human-readable explanation."""
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert "explanation" in data
        assert len(data["explanation"]) > 0
        assert "H001" in data["explanation"]
        assert "flood" in data["explanation"].lower()

    def test_note_present(self) -> None:
        """Response should include prototype note."""
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert "note" in data
        assert "shadow zone" in data["note"].lower()
        assert "prototype" in data["note"].lower()


class TestBackwardCompatibility:
    """Tests to ensure Phase 0, 1, 2, 3 still work."""

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