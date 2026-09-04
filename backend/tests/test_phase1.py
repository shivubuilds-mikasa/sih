"""Tests for SHARMI Phase 1 — Demo data, domain models, data loading, and APIs."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.domain import (
    Community,
    Dependency,
    DemoDataset,
    Hazard,
    HazardType,
    InfrastructureNode,
    InfrastructureType,
    RelocationSite,
)
from app.services.data_loader import DataLoader

client = TestClient(app)


class TestDataLoading:
    """Tests for demo data loading and validation."""

    def test_demo_data_loads_successfully(self) -> None:
        """Demo data should load without errors."""
        loader = DataLoader()
        dataset = loader.load()
        assert isinstance(dataset, DemoDataset)

    def test_all_communities_validate(self) -> None:
        """All communities should pass validation."""
        loader = DataLoader()
        dataset = loader.load()
        assert len(dataset.communities) >= 8
        for community in dataset.communities:
            assert isinstance(community, Community)
            assert community.id.startswith("V")

    def test_all_hazards_validate(self) -> None:
        """All hazards should pass validation."""
        loader = DataLoader()
        dataset = loader.load()
        assert len(dataset.hazards) >= 1
        for hazard in dataset.hazards:
            assert isinstance(hazard, Hazard)
            assert hazard.type in HazardType

    def test_all_infrastructure_nodes_validate(self) -> None:
        """All infrastructure nodes should pass validation."""
        loader = DataLoader()
        dataset = loader.load()
        assert len(dataset.infrastructure) >= 10
        for node in dataset.infrastructure:
            assert isinstance(node, InfrastructureNode)
            assert node.type in InfrastructureType

    def test_all_dependencies_validate(self) -> None:
        """All dependencies should pass validation."""
        loader = DataLoader()
        dataset = loader.load()
        assert len(dataset.dependencies) >= 1
        for dep in dataset.dependencies:
            assert isinstance(dep, Dependency)

    def test_all_relocation_sites_validate(self) -> None:
        """All relocation sites should pass validation."""
        loader = DataLoader()
        dataset = loader.load()
        assert len(dataset.relocation_sites) >= 3
        for site in dataset.relocation_sites:
            assert isinstance(site, RelocationSite)

    def test_district_metadata(self) -> None:
        """District metadata should be present and correct."""
        loader = DataLoader()
        dataset = loader.load()
        assert dataset.district.id == "D001"
        assert dataset.district.name == "Shivapur"
        assert "synthetic" in dataset.district.description.lower()


class TestReferentialIntegrity:
    """Tests for ID referential integrity across the dataset."""

    def test_community_ids_exist(self) -> None:
        """All community IDs referenced should exist."""
        loader = DataLoader()
        dataset = loader.load()
        community_ids = {c.id for c in dataset.communities}

        for hazard in dataset.hazards:
            for comm_id in hazard.affected_communities:
                assert comm_id in community_ids, f"Hazard {hazard.id} references unknown community {comm_id}"

        for node in dataset.infrastructure:
            for comm_id in node.serves:
                assert comm_id in community_ids, f"Infrastructure {node.id} references unknown community {comm_id}"

    def test_infrastructure_ids_exist(self) -> None:
        """All infrastructure IDs referenced in dependencies should exist."""
        loader = DataLoader()
        dataset = loader.load()
        infra_ids = {i.id for i in dataset.infrastructure}
        community_ids = {c.id for c in dataset.communities}
        valid_targets = infra_ids | community_ids

        for dep in dataset.dependencies:
            assert dep.source in infra_ids, f"Dependency source {dep.source} not found in infrastructure"
            assert dep.target in valid_targets, f"Dependency target {dep.target} not found in infrastructure or communities"

    def test_critical_demo_chain_exists(self) -> None:
        """Verify the critical demo chain for Phase 3 cascade exists."""
        loader = DataLoader()
        dataset = loader.load()
        community_ids = {c.id for c in dataset.communities}
        infra_ids = {i.id for i in dataset.infrastructure}

        # H001 flood hazard exists
        h001 = next((h for h in dataset.hazards if h.id == "H001"), None)
        assert h001 is not None, "H001 flood hazard missing"
        assert h001.type == HazardType.FLOOD

        # V001 Village A exists
        v001 = next((c for c in dataset.communities if c.id == "V001"), None)
        assert v001 is not None, "V001 Village A missing"
        assert "V001" in h001.affected_communities

        # Road 12 (R012) exists
        r012 = next((i for i in dataset.infrastructure if i.id == "R012"), None)
        assert r012 is not None, "R012 Road 12 missing"
        assert "V001" in r012.serves

        # Pump 3 (P003) exists
        p003 = next((i for i in dataset.infrastructure if i.id == "P003"), None)
        assert p003 is not None, "P003 Pump 3 missing"
        assert "V001" in p003.serves

        # Dependency chain: H001 -> R012 -> P003 -> V001
        dep_h001_r012 = next((d for d in dataset.dependencies if d.source == "H001" and d.target == "R012"), None)
        assert dep_h001_r012 is not None, "Dependency H001 -> R012 missing"
        assert dep_h001_r012.weight > 0.8

        dep_r012_p003 = next((d for d in dataset.dependencies if d.source == "R012" and d.target == "P003"), None)
        assert dep_r012_p003 is not None, "Dependency R012 -> P003 missing"
        assert dep_r012_p003.weight > 0.7

        dep_p003_v001 = next((d for d in dataset.dependencies if d.source == "P003" and d.target == "V001"), None)
        assert dep_p003_v001 is not None, "Dependency P003 -> V001 missing"
        assert dep_p003_v001.weight > 0.8

    def test_relocation_sites_distinct_profiles(self) -> None:
        """Relocation sites should have distinct profiles for meaningful comparison."""
        loader = DataLoader()
        dataset = loader.load()
        sites = dataset.relocation_sites

        # Site A (RS01) - high hazard, lower infrastructure
        rs01 = next((s for s in sites if s.id == "RS01"), None)
        assert rs01 is not None
        assert rs01.hazard_score > 0.7
        assert rs01.infrastructure_score < 0.55

        # Site B (RS02) - safe, good infrastructure, good access
        rs02 = next((s for s in sites if s.id == "RS02"), None)
        assert rs02 is not None
        assert rs02.hazard_score < 0.25
        assert rs02.infrastructure_score > 0.8
        assert rs02.school_access > 0.85
        assert rs02.health_access > 0.8

        # Site C (RS03) - moderate
        rs03 = next((s for s in sites if s.id == "RS03"), None)
        assert rs03 is not None
        assert 0.2 < rs03.hazard_score < 0.35
        assert 0.6 < rs03.infrastructure_score < 0.75

        # Site D (RS04) - very safe but far and poor access
        rs04 = next((s for s in sites if s.id == "RS04"), None)
        assert rs04 is not None
        assert rs04.hazard_score < 0.15
        assert rs04.distance_km > 30


class TestAPIEndpoints:
    """Tests for Phase 1 API endpoints."""

    def test_get_communities(self) -> None:
        """GET /demo/communities should return all communities."""
        response = client.get("/demo/communities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 8
        assert all("id" in c for c in data)

    def test_get_single_community(self) -> None:
        """GET /demo/communities/{id} should return one community."""
        response = client.get("/demo/communities/V001")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "V001"
        assert data["name"] == "Village A"
        assert data["population"] == 1200

    def test_get_nonexistent_community_returns_404(self) -> None:
        """GET /demo/communities/{invalid_id} should return 404."""
        response = client.get("/demo/communities/INVALID")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_hazards(self) -> None:
        """GET /demo/hazards should return all hazards."""
        response = client.get("/demo/hazards")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all("type" in h for h in data)

    def test_get_infrastructure(self) -> None:
        """GET /demo/infrastructure should return all infrastructure nodes."""
        response = client.get("/demo/infrastructure")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 10
        assert all("type" in i for i in data)

    def test_get_dependencies(self) -> None:
        """GET /demo/dependencies should return all dependencies."""
        response = client.get("/demo/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert all("source" in d and "target" in d for d in data)

    def test_get_relocation_sites(self) -> None:
        """GET /demo/relocation/sites should return all relocation sites."""
        response = client.get("/demo/relocation/sites")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
        assert all("capacity" in r for r in data)

    def test_health_endpoint_still_works(self) -> None:
        """GET /health should still work after Phase 1 changes."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "sharmi-backend"