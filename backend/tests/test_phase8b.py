"""Tests for SHARMI Phase 8b — Decision Service (Officer Override + Audit Log)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.decision_service import (
    submit_override,
    get_audit_log,
    get_audit_summary,
    clear_audit_log,
    OverrideDecision,
    DecisionCategory,
    OverrideRequest,
)
from app.services.data_loader import get_data_loader

client = TestClient(app)


class TestDecisionServiceCore:
    """Tests for core decision service functions."""

    def setup_method(self) -> None:
        """Clear audit log before each test."""
        clear_audit_log()

    def test_override_accept(self) -> None:
        """ACCEPT decision should keep original recommendation."""
        request = OverrideRequest(
            officer_id="OFF001",
            officer_name="Officer One",
            hazard_id="H001",
            community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION,
            decision=OverrideDecision.ACCEPT,
            justification="Agree with system recommendation",
        )
        result = submit_override(request)

        assert result.decision == OverrideDecision.ACCEPT
        assert result.audit_id is not None
        assert len(result.audit_id) == 8
        assert result.final_recommendation == "EVACUATION_ASSESSMENT"

    def test_override_modify(self) -> None:
        """MODIFY decision should use modified recommendation."""
        request = OverrideRequest(
            officer_id="OFF002",
            officer_name="Officer Two",
            hazard_id="H001",
            community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION,
            decision=OverrideDecision.MODIFY,
            justification="Local conditions require shelter-in-place",
            modified_recommendation="SHELTER_IN_PLACE",
        )
        result = submit_override(request)

        assert result.decision == OverrideDecision.MODIFY
        assert result.final_recommendation == "SHELTER_IN_PLACE"

    def test_override_reject(self) -> None:
        """REJECT decision should mark as overridden."""
        request = OverrideRequest(
            officer_id="OFF003",
            officer_name="Officer Three",
            hazard_id="H001",
            community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION,
            decision=OverrideDecision.REJECT,
            justification="False alarm - water receding",
        )
        result = submit_override(request)

        assert result.decision == OverrideDecision.REJECT
        assert result.final_recommendation == "OVERRIDDEN_REJECTED"

    def test_modify_requires_modified_recommendation(self) -> None:
        """MODIFY decision without modified_recommendation should fail."""
        request = OverrideRequest(
            officer_id="OFF004",
            officer_name="Officer Four",
            hazard_id="H001",
            community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION,
            decision=OverrideDecision.MODIFY,
            justification="Want to modify",
            modified_recommendation=None,
        )
        with pytest.raises(ValueError, match="MODIFY decision requires modified_recommendation"):
            submit_override(request)

    def test_empty_justification_rejected(self) -> None:
        """Empty justification should be rejected."""
        request = OverrideRequest(
            officer_id="OFF005",
            officer_name="Officer Five",
            hazard_id="H001",
            community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION,
            decision=OverrideDecision.ACCEPT,
            justification="   ",
        )
        with pytest.raises(ValueError, match="Justification is required"):
            submit_override(request)

    def test_unknown_hazard_raises_error(self) -> None:
        """Unknown hazard should raise ValueError."""
        request = OverrideRequest(
            officer_id="OFF006",
            officer_name="Officer Six",
            hazard_id="H999",
            community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION,
            decision=OverrideDecision.ACCEPT,
            justification="Test",
        )
        with pytest.raises(ValueError, match="not found"):
            submit_override(request)

    def test_unknown_community_raises_error(self) -> None:
        """Unknown community should raise ValueError."""
        request = OverrideRequest(
            officer_id="OFF007",
            officer_name="Officer Seven",
            hazard_id="H001",
            community_id="V999",
            category=DecisionCategory.ACTION_RECOMMENDATION,
            decision=OverrideDecision.ACCEPT,
            justification="Test",
        )
        with pytest.raises(ValueError, match="not found"):
            submit_override(request)

    def test_shadow_zone_category(self) -> None:
        """SHADOW_ZONE category should work."""
        request = OverrideRequest(
            officer_id="OFF008",
            officer_name="Officer Eight",
            hazard_id="H001",
            community_id="V003",
            category=DecisionCategory.SHADOW_ZONE,
            decision=OverrideDecision.MODIFY,
            justification="Field observation confirms direct flooding",
            modified_recommendation="DIRECT_HAZARD_ZONE",
        )
        result = submit_override(request)

        assert result.decision == OverrideDecision.MODIFY
        assert result.final_recommendation == "DIRECT_HAZARD_ZONE"

    def test_relocation_category(self) -> None:
        """RELOCATION category should work."""
        request = OverrideRequest(
            officer_id="OFF009",
            officer_name="Officer Nine",
            hazard_id="H001",
            community_id="V001",
            category=DecisionCategory.RELOCATION,
            decision=OverrideDecision.MODIFY,
            justification="Better road access to RS02",
            modified_recommendation="RELOCATE_TO_RS02",
        )
        result = submit_override(request)

        assert result.decision == OverrideDecision.MODIFY
        assert result.final_recommendation == "RELOCATE_TO_RS02"

    def test_confidence_category(self) -> None:
        """CONFIDENCE category should work."""
        request = OverrideRequest(
            officer_id="OFF010",
            officer_name="Officer Ten",
            hazard_id="H001",
            community_id="V001",
            category=DecisionCategory.CONFIDENCE,
            decision=OverrideDecision.MODIFY,
            justification="Local knowledge increases confidence",
            modified_recommendation="CONFIDENCE_HIGH",
        )
        result = submit_override(request)

        assert result.decision == OverrideDecision.MODIFY

    def test_time_to_impact_category(self) -> None:
        """TIME_TO_IMPACT category should work."""
        request = OverrideRequest(
            officer_id="OFF011",
            officer_name="Officer Eleven",
            hazard_id="H001",
            community_id="V001",
            category=DecisionCategory.TIME_TO_IMPACT,
            decision=OverrideDecision.MODIFY,
            justification="Upstream gauge shows faster rise",
            modified_recommendation="TIMING_15.0",
        )
        result = submit_override(request)

        assert result.decision == OverrideDecision.MODIFY

    def test_audit_log_captures_all_fields(self) -> None:
        """Audit log should capture all relevant fields."""
        request = OverrideRequest(
            officer_id="OFF012",
            officer_name="Officer Twelve",
            hazard_id="H001",
            community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION,
            decision=OverrideDecision.ACCEPT,
            justification="Standard protocol",
        )
        submit_override(request)

        entries = get_audit_log()
        assert len(entries) == 1

        entry = entries[0]
        assert entry.audit_id is not None
        assert entry.hazard_id == "H001"
        assert entry.hazard_type == "flood"
        assert entry.community_id == "V001"
        assert entry.community_name == "Village A"
        assert entry.category == DecisionCategory.ACTION_RECOMMENDATION
        assert entry.officer_id == "OFF012"
        assert entry.officer_name == "Officer Twelve"
        assert entry.decision == OverrideDecision.ACCEPT
        assert entry.original_recommendation == "EVACUATION_ASSESSMENT"
        assert entry.final_recommendation == "EVACUATION_ASSESSMENT"
        assert entry.justification == "Standard protocol"
        assert entry.zone_type == "DIRECT_HAZARD_ZONE"
        assert entry.risk_level is not None

    def test_audit_log_multiple_entries(self) -> None:
        """Multiple overrides should all be logged."""
        for i in range(3):
            request = OverrideRequest(
                officer_id=f"OFF{i:03d}",
                officer_name=f"Officer {i}",
                hazard_id="H001",
                community_id="V001",
                category=DecisionCategory.ACTION_RECOMMENDATION,
                decision=OverrideDecision.ACCEPT,
                justification=f"Override {i}",
            )
            submit_override(request)

        entries = get_audit_log()
        assert len(entries) == 3

    def test_audit_log_newest_first(self) -> None:
        """Audit log should return newest entries first."""
        for i in range(3):
            request = OverrideRequest(
                officer_id=f"OFF{i:03d}",
                officer_name=f"Officer {i}",
                hazard_id="H001",
                community_id="V001",
                category=DecisionCategory.ACTION_RECOMMENDATION,
                decision=OverrideDecision.ACCEPT,
                justification=f"Override {i}",
            )
            submit_override(request)

        entries = get_audit_log()
        # Should be in reverse chronological order
        assert entries[0].officer_id == "OFF002"
        assert entries[1].officer_id == "OFF001"
        assert entries[2].officer_id == "OFF000"

    def test_audit_filter_by_hazard(self) -> None:
        """Filter audit log by hazard_id."""
        submit_override(OverrideRequest(
            officer_id="OFF1", officer_name="O1", hazard_id="H001", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))
        submit_override(OverrideRequest(
            officer_id="OFF2", officer_name="O2", hazard_id="H002", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))

        h001_entries = get_audit_log(hazard_id="H001")
        h002_entries = get_audit_log(hazard_id="H002")

        assert len(h001_entries) == 1
        assert len(h002_entries) == 1
        assert h001_entries[0].hazard_id == "H001"
        assert h002_entries[0].hazard_id == "H002"

    def test_audit_filter_by_community(self) -> None:
        """Filter audit log by community_id."""
        submit_override(OverrideRequest(
            officer_id="OFF1", officer_name="O1", hazard_id="H001", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))
        submit_override(OverrideRequest(
            officer_id="OFF2", officer_name="O2", hazard_id="H001", community_id="V002",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))

        v001_entries = get_audit_log(community_id="V001")
        v002_entries = get_audit_log(community_id="V002")

        assert len(v001_entries) == 1
        assert len(v002_entries) == 1

    def test_audit_filter_by_officer(self) -> None:
        """Filter audit log by officer_id."""
        submit_override(OverrideRequest(
            officer_id="OFF1", officer_name="O1", hazard_id="H001", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))
        submit_override(OverrideRequest(
            officer_id="OFF2", officer_name="O2", hazard_id="H001", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))

        off1_entries = get_audit_log(officer_id="OFF1")
        off2_entries = get_audit_log(officer_id="OFF2")

        assert len(off1_entries) == 1
        assert len(off2_entries) == 1

    def test_audit_filter_by_category(self) -> None:
        """Filter audit log by category."""
        submit_override(OverrideRequest(
            officer_id="OFF1", officer_name="O1", hazard_id="H001", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))
        submit_override(OverrideRequest(
            officer_id="OFF2", officer_name="O2", hazard_id="H001", community_id="V001",
            category=DecisionCategory.RELOCATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))

        action_entries = get_audit_log(category=DecisionCategory.ACTION_RECOMMENDATION)
        reloc_entries = get_audit_log(category=DecisionCategory.RELOCATION)

        assert len(action_entries) == 1
        assert len(reloc_entries) == 1

    def test_audit_filter_by_decision(self) -> None:
        """Filter audit log by decision type."""
        submit_override(OverrideRequest(
            officer_id="OFF1", officer_name="O1", hazard_id="H001", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))
        submit_override(OverrideRequest(
            officer_id="OFF2", officer_name="O2", hazard_id="H001", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.REJECT,
            justification="Test"
        ))

        accept_entries = get_audit_log(decision=OverrideDecision.ACCEPT)
        reject_entries = get_audit_log(decision=OverrideDecision.REJECT)

        assert len(accept_entries) == 1
        assert len(reject_entries) == 1

    def test_audit_pagination(self) -> None:
        """Audit log pagination should work."""
        for i in range(5):
            submit_override(OverrideRequest(
                officer_id=f"OFF{i}", officer_name=f"O{i}", hazard_id="H001", community_id="V001",
                category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
                justification=f"Test {i}"
            ))

        page1 = get_audit_log(limit=2, offset=0)
        page2 = get_audit_log(limit=2, offset=2)
        page3 = get_audit_log(limit=2, offset=4)

        assert len(page1) == 2
        assert len(page2) == 2
        assert len(page3) == 1

    def test_audit_summary(self) -> None:
        """Audit summary should aggregate correctly."""
        submit_override(OverrideRequest(
            officer_id="OFF1", officer_name="O1", hazard_id="H001", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))
        submit_override(OverrideRequest(
            officer_id="OFF1", officer_name="O1", hazard_id="H001", community_id="V001",
            category=DecisionCategory.ACTION_RECOMMENDATION, decision=OverrideDecision.REJECT,
            justification="Test"
        ))
        submit_override(OverrideRequest(
            officer_id="OFF2", officer_name="O2", hazard_id="H001", community_id="V001",
            category=DecisionCategory.RELOCATION, decision=OverrideDecision.ACCEPT,
            justification="Test"
        ))

        summary = get_audit_summary()

        assert summary["total_entries"] == 3
        assert summary["by_decision"]["ACCEPT"] == 2
        assert summary["by_decision"]["REJECT"] == 1
        assert summary["by_category"]["ACTION_RECOMMENDATION"] == 2
        assert summary["by_category"]["RELOCATION"] == 1
        assert summary["by_officer"]["OFF1"] == 2
        assert summary["by_officer"]["OFF2"] == 1


class TestDecisionAPI:
    """Tests for decision API endpoints."""

    def setup_method(self) -> None:
        """Clear audit log before each test."""
        clear_audit_log()

    def test_override_endpoint_accept(self) -> None:
        """POST /decisions/override with ACCEPT should succeed."""
        response = client.post("/decisions/override", json={
            "officer_id": "OFF001",
            "officer_name": "Officer One",
            "hazard_id": "H001",
            "community_id": "V001",
            "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT",
            "justification": "Agree with system",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "ACCEPT"
        assert data["final_recommendation"] == "EVACUATION_ASSESSMENT"
        assert "audit_id" in data
        assert "timestamp" in data

    def test_override_endpoint_modify(self) -> None:
        """POST /decisions/override with MODIFY should succeed."""
        response = client.post("/decisions/override", json={
            "officer_id": "OFF002",
            "officer_name": "Officer Two",
            "hazard_id": "H001",
            "community_id": "V001",
            "category": "ACTION_RECOMMENDATION",
            "decision": "MODIFY",
            "justification": "Local conditions differ",
            "modified_recommendation": "SHELTER_IN_PLACE",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "MODIFY"
        assert data["final_recommendation"] == "SHELTER_IN_PLACE"

    def test_override_endpoint_reject(self) -> None:
        """POST /decisions/override with REJECT should succeed."""
        response = client.post("/decisions/override", json={
            "officer_id": "OFF003",
            "officer_name": "Officer Three",
            "hazard_id": "H001",
            "community_id": "V001",
            "category": "ACTION_RECOMMENDATION",
            "decision": "REJECT",
            "justification": "False alarm",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "REJECT"
        assert data["final_recommendation"] == "OVERRIDDEN_REJECTED"

    def test_override_endpoint_invalid_hazard(self) -> None:
        """POST /decisions/override with unknown hazard should return 400."""
        response = client.post("/decisions/override", json={
            "officer_id": "OFF001",
            "officer_name": "Officer One",
            "hazard_id": "H999",
            "community_id": "V001",
            "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT",
            "justification": "Test",
        })
        assert response.status_code == 400

    def test_override_endpoint_missing_modified_recommendation(self) -> None:
        """POST /decisions/override MODIFY without modified_recommendation should return 400."""
        response = client.post("/decisions/override", json={
            "officer_id": "OFF001",
            "officer_name": "Officer One",
            "hazard_id": "H001",
            "community_id": "V001",
            "category": "ACTION_RECOMMENDATION",
            "decision": "MODIFY",
            "justification": "Test",
        })
        assert response.status_code == 400

    def test_override_endpoint_empty_justification(self) -> None:
        """POST /decisions/override with empty justification should return 422 (validation error)."""
        response = client.post("/decisions/override", json={
            "officer_id": "OFF001",
            "officer_name": "Officer One",
            "hazard_id": "H001",
            "community_id": "V001",
            "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT",
            "justification": "",
        })
        # Pydantic validates min_length=1 before service is called
        assert response.status_code == 422

    def test_override_endpoint_all_categories(self) -> None:
        """All decision categories should work via API."""
        categories = [
            "SHADOW_ZONE",
            "ACTION_RECOMMENDATION",
            "RELOCATION",
            "CONFIDENCE",
            "TIME_TO_IMPACT",
        ]
        for cat in categories:
            response = client.post("/decisions/override", json={
                "officer_id": "OFF001",
                "officer_name": "Officer One",
                "hazard_id": "H001",
                "community_id": "V001",
                "category": cat,
                "decision": "ACCEPT",
                "justification": f"Test {cat}",
            })
            assert response.status_code == 200, f"Category {cat} failed"

    def test_audit_endpoint(self) -> None:
        """POST /decisions/audit should return paginated entries."""
        # Create some entries
        for i in range(3):
            client.post("/decisions/override", json={
                "officer_id": f"OFF{i}",
                "officer_name": f"Officer {i}",
                "hazard_id": "H001",
                "community_id": "V001",
                "category": "ACTION_RECOMMENDATION",
                "decision": "ACCEPT",
                "justification": f"Test {i}",
            })

        response = client.post("/decisions/audit", json={})
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 3
        assert data["total"] == 3
        assert data["limit"] == 100
        assert data["offset"] == 0

    def test_audit_endpoint_with_filters(self) -> None:
        """POST /decisions/audit with filters should work."""
        client.post("/decisions/override", json={
            "officer_id": "OFF1", "officer_name": "O1", "hazard_id": "H001",
            "community_id": "V001", "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT", "justification": "Test"
        })
        client.post("/decisions/override", json={
            "officer_id": "OFF2", "officer_name": "O2", "hazard_id": "H002",
            "community_id": "V001", "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT", "justification": "Test"
        })

        response = client.post("/decisions/audit", json={"hazard_id": "H001"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 1
        assert data["entries"][0]["hazard_id"] == "H001"

    def test_audit_endpoint_pagination(self) -> None:
        """POST /decisions/audit pagination should work."""
        for i in range(5):
            client.post("/decisions/override", json={
                "officer_id": f"OFF{i}", "officer_name": f"O{i}",
                "hazard_id": "H001", "community_id": "V001",
                "category": "ACTION_RECOMMENDATION", "decision": "ACCEPT",
                "justification": f"Test {i}"
            })

        response = client.post("/decisions/audit", json={"limit": 2, "offset": 0})
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 2
        assert data["total"] == 5

    def test_audit_summary_endpoint(self) -> None:
        """GET /decisions/audit/summary should return statistics."""
        client.post("/decisions/override", json={
            "officer_id": "OFF1", "officer_name": "O1", "hazard_id": "H001",
            "community_id": "V001", "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT", "justification": "Test"
        })
        client.post("/decisions/override", json={
            "officer_id": "OFF1", "officer_name": "O1", "hazard_id": "H001",
            "community_id": "V001", "category": "ACTION_RECOMMENDATION",
            "decision": "REJECT", "justification": "Test"
        })
        client.post("/decisions/override", json={
            "officer_id": "OFF2", "officer_name": "O2", "hazard_id": "H001",
            "community_id": "V001", "category": "RELOCATION",
            "decision": "ACCEPT", "justification": "Test"
        })

        response = client.get("/decisions/audit/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 3
        assert data["by_decision"]["ACCEPT"] == 2
        assert data["by_decision"]["REJECT"] == 1
        assert data["by_category"]["ACTION_RECOMMENDATION"] == 2
        assert data["by_category"]["RELOCATION"] == 1
        assert data["by_officer"]["OFF1"] == 2
        assert data["by_officer"]["OFF2"] == 1

    def test_clear_audit_endpoint(self) -> None:
        """DELETE /decisions/audit should clear log."""
        client.post("/decisions/override", json={
            "officer_id": "OFF1", "officer_name": "O1", "hazard_id": "H001",
            "community_id": "V001", "category": "ACTION_RECOMMENDATION",
            "decision": "ACCEPT", "justification": "Test"
        })

        response = client.delete("/decisions/audit")
        assert response.status_code == 200
        assert response.json()["cleared"] == 1

        # Verify log is empty
        response = client.post("/decisions/audit", json={})
        assert response.json()["total"] == 0


class TestBackwardCompatibility:
    """Tests to ensure Phase 0-8a still work."""

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

    def test_phase3_cascade_endpoints(self) -> None:
        response = client.post("/cascade/simulate", json={"hazard_id": "H001"})
        assert response.status_code == 200
        assert "cascade_paths" in response.json()

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