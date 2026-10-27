"""Test API endpoints and pack validation for Phase 1."""

import hashlib
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Pack
from make_cases import CASES_DIR, EXPECTED_CSV, generate_all_cases


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_cases_endpoint_returns_21(client):
    """Verify /api/cases returns exactly 21 cases."""
    res = client.get("/api/cases")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 21
    case_ids = [c["case_id"] for c in data]
    assert case_ids == [f"C{i:02d}" for i in range(1, 22)]


def test_pack_schema_validation(client):
    """Verify every case JSON on disk validates against Pack schema."""
    case_files = sorted(CASES_DIR.glob("*.json"))
    assert len(case_files) == 21

    for cf in case_files:
        with open(cf, "r", encoding="utf-8") as f:
            raw = f.read()
        pack = Pack.model_validate_json(raw)
        assert pack.case_id.startswith("C")
        assert pack.category in ["clean", "trap"]
        assert pack.system.proposed_kw > 0
        assert len(pack.docs_present) >= 5


def test_case_detail_endpoint(client):
    """Verify /api/cases/{id} returns pack and structure."""
    res = client.get("/api/cases/C01")
    assert res.status_code == 200
    data = res.json()
    assert "pack" in data
    assert data["pack"]["case_id"] == "C01"
    assert data["pack"]["category"] == "clean"

    # Test 404 for unknown case
    res_404 = client.get("/api/cases/C99")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()


def test_reproducible_make_cases():
    """Verify running make_cases.py twice gives identical files."""
    def hash_directory():
        h = hashlib.sha256()
        for f in sorted(CASES_DIR.glob("*.json")):
            h.update(f.read_bytes())
        if EXPECTED_CSV.exists():
            h.update(EXPECTED_CSV.read_bytes())
        return h.hexdigest()

    generate_all_cases()
    hash1 = hash_directory()
    generate_all_cases()
    hash2 = hash_directory()
    assert hash1 == hash2, "make_cases.py must be strictly reproducible"


def test_c09_capacity_exceeded(client):
    """Verify C09 trap pack has proposed_kw > sanctioned_load_kw."""
    res = client.get("/api/cases/C09")
    assert res.status_code == 200
    pack = res.json()["pack"]
    assert pack["system"]["proposed_kw"] == 12.0
    assert pack["bill"]["sanctioned_load_kw"] == 10.0
    assert pack["system"]["proposed_kw"] > pack["bill"]["sanctioned_load_kw"]
