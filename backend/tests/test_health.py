"""Tests for health check endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200() -> None:
    """GET /health should return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_expected_json() -> None:
    """GET /health should return the expected JSON payload."""
    response = client.get("/health")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "sharmi-backend"


def test_root_returns_service_name() -> None:
    """GET / should return the service name."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
