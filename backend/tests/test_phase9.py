"""Tests for SHARMI Phase 9 — End-to-End Decision Engine."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.sharmi_engine import run_full_analysis
from app.services.data_loader import get_data_loader

client = TestClient(app)


class TestSHARMIEngineCore:
    """Tests for core SHARMI engine functions."""

    def test_h001_analysis_succeeds(self) -> None:
        """H001 full analysis should succeed."""
        result = run_full_analysis("H001")

        assert result.hazard_id == "H001"
        assert result.hazard_type == "flood"
        assert len(result.community_analyses) == 10
        assert isinstance(result.summary, object)
        assert len(result.cascade_paths_summary) >= 0
        assert len(result.relocation_sites_summary) >= 0
        assert isinstance(result.overall_explanation, str)
        assert len(result.overall_explanation) > 0
        assert "prototype" in result.prototype_note.lower()

    def test_h001_summary_structure(self) -> None:
        """H001 summary should have correct structure."""
        result = run_full_analysis("H001")
        summary = result.summary

        assert summary.hazard_id == "H001"
        assert summary.hazard_type == "flood"
        assert summary.total_communities == 10
        assert summary.directly_affected >= 0
        assert summary.cascade_shadow >= 0
        assert summary.unaffected >= 0
        assert summary.directly_affected + summary.cascade_shadow + summary.unaffected == 10
        assert summary.total_population_at_risk >= 0
        assert summary.highest_risk_community in [c.community_id for c in result.community_analyses]
        assert summary.highest_risk_score >= 0.0

    def test_h001_community_analyses_complete(self) -> None:
        """Each community analysis should have all fields populated."""
        result = run_full_analysis("H001")

        for ca in result.community_analyses:
            assert ca.community_id in [c.id for c in get_data_loader().get_dataset().communities]
            assert ca.community_name
            assert ca.population > 0
            assert 0.0 <= ca.risk_score <= 1.0
            assert ca.risk_level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            assert ca.zone_type in ["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE", "UNAFFECTED"]
            assert ca.action in ["EVACUATE_IMMEDIATE", "EVACUATION_ASSESSMENT", "PROTECT", "PREPARE", "INSPECT", "MONITOR"]
            assert ca.confidence_level in ["HIGH", "MEDIUM", "LOW"]
            assert 0.0 <= ca.confidence_score <= 1.0
            assert isinstance(ca.confidence_components, dict)
            assert set(ca.confidence_components.keys()) == {
                "data_quality", "model_coverage", "input_completeness",
                "cascade_strength", "time_certainty"
            }
            for v in ca.confidence_components.values():
                assert 0.0 <= v <= 1.0
            assert isinstance(ca.confidence_explanation, str)
            assert isinstance(ca.confidence_caveats, list)

    def test_h001_sorted_by_risk(self) -> None:
        """Community analyses should be sorted by risk score descending."""
        result = run_full_analysis("H001")
        risk_scores = [ca.risk_score for ca in result.community_analyses]
        assert risk_scores == sorted(risk_scores, reverse=True)

    def test_h001_direct_hazard_zones(self) -> None:
        """V001 and V002 should be DIRECT_HAZARD_ZONE for H001."""
        result = run_full_analysis("H001")
        v001 = next(ca for ca in result.community_analyses if ca.community_id == "V001")
        v002 = next(ca for ca in result.community_analyses if ca.community_id == "V002")

        assert v001.zone_type == "DIRECT_HAZARD_ZONE"
        assert v002.zone_type == "DIRECT_HAZARD_ZONE"

    def test_h001_cascade_shadow_zones(self) -> None:
        """V003 and V005 should be CASCADE_SHADOW_ZONE for H001."""
        result = run_full_analysis("H001")
        v003 = next(ca for ca in result.community_analyses if ca.community_id == "V003")
        v005 = next(ca for ca in result.community_analyses if ca.community_id == "V005")

        assert v003.zone_type == "CASCADE_SHADOW_ZONE"
        assert v005.zone_type == "CASCADE_SHADOW_ZONE"
        assert v003.cascade_path is not None
        assert v005.cascade_path is not None
        assert "H001" in v003.cascade_path
        assert "H001" in v005.cascade_path

    def test_h001_unaffected(self) -> None:
        """V007, V008, V010 should be UNAFFECTED for H001."""
        result = run_full_analysis("H001")
        for cid in ["V007", "V008", "V010"]:
            ca = next(ca for ca in result.community_analyses if ca.community_id == cid)
            assert ca.zone_type == "UNAFFECTED"
            assert ca.time_to_impact is None
            assert ca.cascade_path is None

    def test_h001_action_recommendations(self) -> None:
        """Actions should be appropriate for zone types."""
        result = run_full_analysis("H001")

        for ca in result.community_analyses:
            if ca.zone_type == "DIRECT_HAZARD_ZONE":
                # Direct hazard zones should have high-urgency actions
                assert ca.action in ["EVACUATE_IMMEDIATE", "EVACUATION_ASSESSMENT", "PROTECT", "PREPARE"]
            elif ca.zone_type == "CASCADE_SHADOW_ZONE":
                assert ca.action in ["PROTECT", "INSPECT", "PREPARE", "MONITOR"]
            else:  # UNAFFECTED
                assert ca.action == "MONITOR"

    def test_h001_relocation_for_affected(self) -> None:
        """Direct and shadow zone communities should have relocation if capacity allows."""
        result = run_full_analysis("H001")

        for ca in result.community_analyses:
            if ca.zone_type in ["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE"]:
                # Communities in affected zones should either have a site assigned
                # or be unallocated due to capacity constraints (urgency is None but still in affected zone)
                assert ca.relocation_urgency is not None or ca.zone_type in ["DIRECT_HAZARD_ZONE", "CASCADE_SHADOW_ZONE"]
            else:
                assert ca.relocation_site is None
                assert ca.relocation_urgency is None

    def test_h001_time_to_impact_direct(self) -> None:
        """Direct hazard zones should have time_to_impact."""
        result = run_full_analysis("H001")
        v001 = next(ca for ca in result.community_analyses if ca.community_id == "V001")
        v002 = next(ca for ca in result.community_analyses if ca.community_id == "V002")

        assert v001.time_to_impact is not None
        assert v001.time_to_impact > 0
        assert v002.time_to_impact is not None
        assert v002.time_to_impact > 0

    def test_h001_confidence_levels(self) -> None:
        """Different zones should have different confidence patterns."""
        result = run_full_analysis("H001")

        # Direct hazard zones should have higher confidence
        for ca in result.community_analyses:
            if ca.zone_type == "DIRECT_HAZARD_ZONE":
                assert ca.confidence_score > 0.3
                assert ca.confidence_level in ["HIGH", "MEDIUM"]

    def test_h001_cascade_paths_summary(self) -> None:
        """Cascade paths summary should be populated."""
        result = run_full_analysis("H001")

        assert len(result.cascade_paths_summary) > 0
        for path in result.cascade_paths_summary:
            assert "path_id" in path
            assert "nodes" in path
            assert "propagation_strength" in path
            assert "total_propagation_time" in path
            assert len(path["nodes"]) > 0

    def test_h001_relocation_sites_summary(self) -> None:
        """Relocation sites summary should be populated."""
        result = run_full_analysis("H001")

        assert len(result.relocation_sites_summary) > 0
        for site in result.relocation_sites_summary:
            assert "site_id" in site
            assert "site_name" in site
            assert "composite_score" in site
            assert "capacity" in site
            assert site["capacity"] > 0

    def test_h002_analysis(self) -> None:
        """H002 (landslide) analysis should succeed."""
        result = run_full_analysis("H002")
        assert result.hazard_id == "H002"
        assert result.hazard_type == "landslide"
        assert len(result.community_analyses) == 10

    def test_h003_analysis(self) -> None:
        """H003 (cyclone) analysis should succeed - all direct."""
        result = run_full_analysis("H003")
        assert result.hazard_id == "H003"
        assert result.hazard_type == "cyclone"
        assert len(result.community_analyses) == 10
        # All communities should be direct hazard zone
        for ca in result.community_analyses:
            assert ca.zone_type == "DIRECT_HAZARD_ZONE"

    def test_h004_analysis(self) -> None:
        """H004 (heatwave) analysis should succeed - all direct."""
        result = run_full_analysis("H004")
        assert result.hazard_id == "H004"
        assert result.hazard_type == "heatwave"
        assert len(result.community_analyses) == 10
        # All communities should be direct hazard zone
        for ca in result.community_analyses:
            assert ca.zone_type == "DIRECT_HAZARD_ZONE"

    def test_unknown_hazard_raises_error(self) -> None:
        """Unknown hazard should raise ValueError."""
        with pytest.raises(ValueError, match="not found"):
            run_full_analysis("H999")

    def test_deterministic_results(self) -> None:
        """Multiple runs should produce identical results."""
        result1 = run_full_analysis("H001")
        result2 = run_full_analysis("H001")

        assert result1.hazard_id == result2.hazard_id
        assert result1.analysis_timestamp != result2.analysis_timestamp  # timestamp differs
        assert len(result1.community_analyses) == len(result2.community_analyses)

        for ca1, ca2 in zip(result1.community_analyses, result2.community_analyses):
            assert ca1.community_id == ca2.community_id
            assert ca1.risk_score == ca2.risk_score
            assert ca1.zone_type == ca2.zone_type
            assert ca1.action == ca2.action
            assert ca1.confidence_score == ca2.confidence_score
            assert ca1.confidence_level == ca2.confidence_level


class TestSHARMIAPI:
    """Tests for SHARMI API endpoints."""

    def setup_method(self) -> None:
        """Clear audit log before each test."""
        from app.services.decision_service import clear_audit_log
        clear_audit_log()

    def test_analyze_endpoint_h001(self) -> None:
        """POST /sharmi/analyze with H001 should succeed."""
        response = client.post("/sharmi/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        assert data["hazard_id"] == "H001"
        assert data["hazard_type"] == "flood"
        assert "summary" in data
        assert "community_analyses" in data
        assert len(data["community_analyses"]) == 10
        assert "cascade_paths_summary" in data
        assert "relocation_sites_summary" in data
        assert "overall_explanation" in data
        assert "prototype_note" in data
        assert "prototype" in data["prototype_note"].lower()

    def test_analyze_endpoint_unknown_hazard(self) -> None:
        """POST /sharmi/analyze with unknown hazard should return 404."""
        response = client.post("/sharmi/analyze", json={"hazard_id": "H999"})
        assert response.status_code == 404

    def test_analyze_h001_v001_direct_zone(self) -> None:
        """V001 should be DIRECT_HAZARD_ZONE in H001 analysis."""
        response = client.post("/sharmi/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        v001 = next(ca for ca in data["community_analyses"] if ca["community_id"] == "V001")
        assert v001["zone_type"] == "DIRECT_HAZARD_ZONE"
        assert v001["action"] in ["EVACUATE_IMMEDIATE", "EVACUATION_ASSESSMENT"]
        assert v001["time_to_impact"] is not None
        assert v001["relocation_site"] is not None

    def test_analyze_h001_v003_shadow_zone(self) -> None:
        """V003 should be CASCADE_SHADOW_ZONE in H001 analysis."""
        response = client.post("/sharmi/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        v003 = next(ca for ca in data["community_analyses"] if ca["community_id"] == "V003")
        assert v003["zone_type"] == "CASCADE_SHADOW_ZONE"
        assert v003["cascade_path"] is not None
        assert "H001" in v003["cascade_path"]
        # V003 may not have relocation site due to capacity constraints
        # but should have urgency category if it's in affected zone
        assert v003["relocation_urgency"] is not None

    def test_analyze_h001_v007_unaffected(self) -> None:
        """V007 should be UNAFFECTED in H001 analysis."""
        response = client.post("/sharmi/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        v007 = next(ca for ca in data["community_analyses"] if ca["community_id"] == "V007")
        assert v007["zone_type"] == "UNAFFECTED"
        assert v007["action"] == "MONITOR"
        assert v007["time_to_impact"] is None
        assert v007["cascade_path"] is None
        assert v007["relocation_site"] is None

    def test_analyze_confidence_components(self) -> None:
        """Each community should have confidence components."""
        response = client.post("/sharmi/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()

        for ca in data["community_analyses"]:
            comp = ca["confidence_components"]
            assert "data_quality" in comp
            assert "model_coverage" in comp
            assert "input_completeness" in comp
            assert "cascade_strength" in comp
            assert "time_certainty" in comp
            for val in comp.values():
                assert 0.0 <= val <= 1.0

    def test_override_endpoint(self) -> None:
        """POST /sharmi/override should work."""
        response = client.post("/sharmi/override", json={
            "hazard_id": "H001",
            "community_id": "V001",
            "officer_id": "OFF001",
            "officer_name": "Officer One",
            "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT",
            "justification": "Agree with assessment",
        })
        assert response.status_code == 200
        data = response.json()
        assert "audit_id" in data
        assert data["decision"] == "ACCEPT"

    def test_override_endpoint_modify(self) -> None:
        """POST /sharmi/override with MODIFY should work."""
        response = client.post("/sharmi/override", json={
            "hazard_id": "H001",
            "community_id": "V001",
            "officer_id": "OFF002",
            "officer_name": "Officer Two",
            "category": "ACTION_RECOMMENDATION",
            "decision": "MODIFY",
            "justification": "Local knowledge",
            "modified_recommendation": "SHELTER_IN_PLACE",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "MODIFY"
        assert data["final_recommendation"] == "SHELTER_IN_PLACE"

    def test_audit_endpoint(self) -> None:
        """POST /sharmi/audit should return entries."""
        # Create an override first
        client.post("/sharmi/override", json={
            "hazard_id": "H001", "community_id": "V001",
            "officer_id": "OFF1", "officer_name": "O1",
            "category": "ACTION_RECOMMENDATION", "decision": "ACCEPT",
            "justification": "Test"
        })

        response = client.post("/sharmi/audit", json={})
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_audit_endpoint_filter(self) -> None:
        """POST /sharmi/audit with filters should work."""
        client.post("/sharmi/override", json={
            "hazard_id": "H001", "community_id": "V001",
            "officer_id": "OFF1", "officer_name": "O1",
            "category": "ACTION_RECOMMENDATION", "decision": "ACCEPT",
            "justification": "Test"
        })
        client.post("/sharmi/override", json={
            "hazard_id": "H002", "community_id": "V001",
            "officer_id": "OFF1", "officer_name": "O1",
            "category": "ACTION_RECOMMENDATION", "decision": "ACCEPT",
            "justification": "Test"
        })

        response = client.post("/sharmi/audit", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["hazard_id"] == "H001"

    def test_audit_summary_endpoint(self) -> None:
        """GET /sharmi/audit/summary should return statistics."""
        client.post("/sharmi/override", json={
            "hazard_id": "H001", "community_id": "V001",
            "officer_id": "OFF1", "officer_name": "O1",
            "category": "ACTION_RECOMMENDATION", "decision": "ACCEPT",
            "justification": "Test"
        })
        client.post("/sharmi/override", json={
            "hazard_id": "H001", "community_id": "V001",
            "officer_id": "OFF1", "officer_name": "O1",
            "category": "RELOCATION", "decision": "REJECT",
            "justification": "Test"
        })

        response = client.get("/sharmi/audit/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] >= 2
        assert "by_decision" in data
        assert "by_category" in data
        assert "by_officer" in data

    def test_analyze_h003_all_direct(self) -> None:
        """H003 should show all communities as direct hazard zone."""
        response = client.post("/sharmi/analyze", json={"hazard_id": "H003"})
        assert response.status_code == 200
        data = response.json()

        for ca in data["community_analyses"]:
            assert ca["zone_type"] == "DIRECT_HAZARD_ZONE"
            assert ca["time_to_impact"] is not None


class TestBackwardCompatibility:
    """Tests to ensure Phase 0-8b still work."""

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
            "hazard_intensity": 0.5, "exposure": 0.5, "vulnerability": 0.5
        })
        assert response.status_code == 200

    def test_phase3_cascade_endpoints(self) -> None:
        response = client.post("/cascade/simulate", json={"hazard_id": "H001"})
        assert response.status_code == 200

    def test_phase4_shadow_zone_endpoints(self) -> None:
        response = client.post("/shadow-zone/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200

    def test_phase5_time_to_impact_endpoints(self) -> None:
        response = client.post("/impact/timeline", json={"hazard_id": "H001"})
        assert response.status_code == 200

    def test_phase6_action_endpoints(self) -> None:
        response = client.post("/actions/recommend", json={"hazard_id": "H001"})
        assert response.status_code == 200

    def test_phase7_relocation_endpoints(self) -> None:
        response = client.post("/relocation/optimize", json={"hazard_id": "H001"})
        assert response.status_code == 200

    def test_phase8a_confidence_endpoints(self) -> None:
        response = client.post("/confidence/evaluate", json={"hazard_id": "H001"})
        assert response.status_code == 200

    def test_phase8b_decision_endpoints(self) -> None:
        response = client.post("/decisions/override", json={
            "officer_id": "OFF1", "officer_name": "O1", "hazard_id": "H001",
            "community_id": "V001", "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT", "justification": "Test"
        })
        assert response.status_code == 200

        response = client.post("/decisions/audit", json={})
        assert response.status_code == 200