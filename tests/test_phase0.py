"""Phase 0 Sanity Tests: verifying routes, health check, and templates."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create FastAPI TestClient instance."""
    return TestClient(app)


def test_health_check(client):
    """Verify /api/health returns valid JSON with mock provider."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["llm_provider"] == "mock"
    assert data["mode"] == "mock"


def test_dashboard_page(client):
    """Verify dashboard loads with brand header and active page context."""
    res = client.get("/")
    assert res.status_code == 200
    assert "NetBill Assist" in res.text
    assert "Solar Onboarding Assistant" in res.text


def test_about_page(client):
    """Verify about page loads with regulatory citations."""
    res = client.get("/about")
    assert res.status_code == 200
    assert "NEPRA (Prosumer) Regulations 2026" in res.text
    assert "The Human Gate" in res.text


def test_case_page(client):
    """Verify case page loads with case ID placeholder."""
    res = client.get("/case/C01")
    assert res.status_code == 200
    assert "Case C01" in res.text


def test_evaluate_page(client):
    """Verify evaluate page loads."""
    res = client.get("/evaluate")
    assert res.status_code == 200
    assert "Evaluation" in res.text
