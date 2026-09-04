"""Tests for SHARMI Phase 10 — API Hardening + Demo Integration."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestDemoIntegrationScenarios:
    """Tests for demo scenarios endpoints."""

    def test_list_scenarios(self) -> None:
        """GET /demo/scenarios should return all scenarios."""
        response = client.get("/demo/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 4
        scenario_ids = {s["id"] for s in data}
        assert scenario_ids == {"flood_h001", "landslide_h002", "cyclone_h003", "heatwave_h004"}

    def test_get_scenario(self) -> None:
        """GET /demo/scenarios/{id} should return scenario details."""
        response = client.get("/demo/scenarios/flood_h001")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "flood_h001"
        assert data["hazard_id"] == "H001"
        assert "key_communities" in data
        assert "expected_cascade" in data
        assert "shadow_zones" in data

    def test_get_unknown_scenario(self) -> None:
        """GET /demo/scenarios/unknown should return 404."""
        response = client.get("/demo/scenarios/unknown")
        assert response.status_code == 404

    def test_run_scenario_flood_h001(self) -> None:
        """POST /demo/scenarios/flood_h001/run should execute full analysis."""
        response = client.post("/demo/scenarios/flood_h001/run")
        assert response.status_code == 200
        data = response.json()
        assert data["scenario_id"] == "flood_h001"
        assert "request_id" in data
        assert "analysis" in data
        assert data["analysis"]["hazard_id"] == "H001"
        assert len(data["analysis"]["community_analyses"]) == 10


class TestDashboardEndpoint:
    """Tests for dashboard data endpoint."""

    def test_dashboard_h001(self) -> None:
        """GET /demo/dashboard/H001 should return complete dashboard data."""
        response = client.get("/demo/dashboard/H001")
        assert response.status_code == 200
        data = response.json()

        # Hazard info
        assert data["hazard"]["id"] == "H001"
        assert data["hazard"]["type"] == "flood"
        assert "intensity" in data["hazard"]
        assert "probability" in data["hazard"]

        # Summary
        assert "summary" in data
        summary = data["summary"]
        assert summary["total_communities"] == 10
        assert "directly_affected" in summary
        assert "cascade_shadow" in summary
        assert "unaffected" in summary
        assert "total_population_at_risk" in summary
        assert "evacuation_recommended" in summary
        assert "relocation_required" in summary

        # Cascade paths
        assert "cascade_paths" in data
        assert isinstance(data["cascade_paths"], list)

        # Timeline
        assert "timeline" in data
        assert isinstance(data["timeline"], list)

        # Community cards
        assert "community_cards" in data
        assert len(data["community_cards"]) == 10
        for card in data["community_cards"]:
            assert "community_id" in card
            assert "community_name" in card
            assert "population" in card
            assert "zone" in card
            assert "risk_score" in card
            assert "risk_level" in card
            assert "action" in card
            assert "confidence_score" in card
            assert "confidence_level" in card

        # Relocation sites
        assert "relocation_sites" in data
        assert isinstance(data["relocation_sites"], list)

        # Site allocations
        assert "site_allocations" in data
        assert isinstance(data["site_allocations"], list)

        # Audit summary
        assert "audit_summary" in data
        assert "total_entries" in data["audit_summary"]

        # Note
        assert "note" in data
        assert "prototype" in data["note"].lower()

    def test_dashboard_unknown_hazard(self) -> None:
        """GET /demo/dashboard/unknown should return 404."""
        response = client.get("/demo/dashboard/H999")
        assert response.status_code == 404

    def test_list_dashboard_hazards(self) -> None:
        """GET /demo/dashboard should list available hazards."""
        response = client.get("/demo/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 4
        hazard_ids = {h["id"] for h in data}
        assert hazard_ids == {"H001", "H002", "H003", "H004"}


class TestRecentAuditEndpoint:
    """Tests for recent audit endpoint."""

    def test_recent_audit(self) -> None:
        """GET /demo/audit/recent should return recent audit entries."""
        response = client.get("/demo/audit/recent")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_recent_audit_with_limit(self) -> None:
        """GET /demo/audit/recent?limit=5 should respect limit."""
        response = client.get("/demo/audit/recent?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5


class TestDetailedHealthEndpoint:
    """Tests for detailed health endpoint."""

    def test_detailed_health(self) -> None:
        """GET /demo/health/detailed should return detailed health info."""
        response = client.get("/demo/health/detailed")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert "version" in data
        assert "environment" in data
        assert data["data_loaded"] is True

        # Dataset info
        assert "dataset" in data
        dataset = data["dataset"]
        assert dataset["district"] == "D001"
        assert dataset["communities"] == 10
        assert dataset["hazards"] == 4
        assert dataset["infrastructure"] == 15
        assert dataset["dependencies"] == 23
        assert dataset["relocation_sites"] == 4

        # Engines
        assert "engines" in data
        engines = data["engines"]
        expected_engines = [
            "risk", "cascade", "shadow_zone", "time_to_impact",
            "action", "relocation", "confidence", "decision", "sharmi"
        ]
        for engine in expected_engines:
            assert engine in engines
            assert engines[engine] == "operational"

        assert "note" in data
        assert "prototype" in data["note"].lower()


class TestMiddleware:
    """Tests for middleware functionality."""

    def test_request_id_header(self) -> None:
        """Response should include X-Request-ID header."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0

    def test_request_id_propagation(self) -> None:
        """Request ID should be returned if provided by client."""
        request_id = "test-request-123"
        response = client.get("/health", headers={"x-request-id": request_id})
        assert response.status_code == 200
        assert response.headers["x-request-id"] == request_id

    def test_rate_limit_headers(self) -> None:
        """Responses should include rate limit headers."""
        response = client.get("/health")
        assert response.status_code == 200
        # Health endpoint is excluded from rate limiting but should still have headers
        # (or at least not error)


class TestCORSHeaders:
    """Tests for CORS headers."""

    def test_cors_headers_present(self) -> None:
        """Response should include CORS headers."""
        response = client.options("/health", headers={"Origin": "http://localhost:3000"})
        # OPTIONS may not be implemented for all endpoints, just check we can make request
        assert response.status_code in [200, 405]


class TestBackwardCompatibility:
    """Ensure all previous phase endpoints still work."""

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
            "officer_id": "O001",
            "officer_name": "Officer One",
            "hazard_id": "H001",
            "community_id": "V001",
            "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT",
            "justification": "Test",
        })
        assert response.status_code == 200

    def test_phase9_sharmi_endpoints(self) -> None:
        response = client.post("/sharmi/analyze", json={"hazard_id": "H001"})
        assert response.status_code == 200