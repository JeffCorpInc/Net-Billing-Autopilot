"""Tests for Phase 6: Polish, accessibility, documentation, and regulatory compliance."""

from pathlib import Path
from starlette.testclient import TestClient

from app.config import BASE_DIR
from app.main import app

client = TestClient(app)


def test_readme_file_exists_and_contains_core_sections():
    readme_path = BASE_DIR / "README.md"
    assert readme_path.exists()
    content = readme_path.read_text(encoding="utf-8")

    assert "NetBill Assist" in content
    assert "DATA722" in content
    assert "SRO 251(I)/2026" in content
    assert "K-Electric Net Billing Guidelines" in content
    assert "The 6 Hard Architectural Boundaries" in content
    assert "R1: CNIC Format" in content
    assert "R7: Document Completeness" in content
    assert "Two-Layer Redaction Architecture" in content
    assert "Faithfulness Gate" in content
    assert "ReportLab" in content
    assert "Faker seed 722" in content or "seed 722" in content


def test_about_page_comprehensive_regulatory_content():
    response = client.get("/about")
    assert response.status_code == 200
    html = response.text

    # Regulatory citations
    assert "SRO 251(I)/2026" in html
    assert "Regulation 3(5)" in html
    assert "5 working days" in html
    assert "3 working days" in html
    assert "13 April 2026" in html or "2026-04-13" in html

    # Hard boundary 1: human gate
    assert "The Human Gate" in html
    assert "Zero Autonomous Action" in html

    # Rules R1 to R7
    assert "R1 · CNIC Format" in html
    assert "R2 · CNIC Expiry" in html
    assert "R3 · Capacity Cap" in html
    assert "R4 · 3-Phase Requirement" in html
    assert "R5 · Connected Load" in html
    assert "R6 · Load-Flow Study" in html
    assert "R7 · Required Documents Completeness" in html

    # Redaction & Karachi semantics
    assert "Two-Layer Privacy" in html
    assert "Karachi Urban Semantics" in html


def test_accessibility_landmarks_and_skip_link():
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    assert 'id="main-content"' in html
    assert 'href="#main-content"' in html
    assert "Skip to main content" in html
