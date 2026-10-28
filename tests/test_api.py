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
    """Verify /api/cases includes all 21 benchmark cases C01..C21."""
    res = client.get("/api/cases")
    assert res.status_code == 200
    data = res.json()
    builtin_ids = [c["case_id"] for c in data if c["case_id"].startswith("C")]
    assert len(builtin_ids) == 21
    assert builtin_ids == [f"C{i:02d}" for i in range(1, 22)]


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


def test_create_and_delete_custom_case(client):
    """Verify creating a custom application pack via POST /api/cases, viewing it, and deleting it."""
    # Check /new page renders
    page_res = client.get("/new")
    assert page_res.status_code == 200
    assert "Customer Onboarding Form" in page_res.text

    payload = {
        "description": "Unit test custom case",
        "applicant_type": "residential",
        "is_tenant": False,
        "docs_present": [
            "cnic", "bill", "ownership", "single_line_diagram",
            "affidavit", "vendor_checklist", "inverter_datasheet", "inverter_settings_letter"
        ],
        "cnic": {
            "name": "Tariq Jamil",
            "father_name": "Abdul Jamil",
            "cnic_no": "42301-1122334-5",
            "expiry": "2030-12-31",
            "address": "House 10, Phase 5, DHA, Karachi",
        },
        "bill": {
            "consumer_name": "Tariq Jamil",
            "reference_no": "0400011223344",
            "sanctioned_load_kw": 10.0,
            "connected_load_kw": 8.0,
            "tariff": "A-1",
            "connection_phase": "3-phase",
            "address": "House 10, Phase 5, DHA, Karachi",
        },
        "ownership": {
            "type": "sale_deed",
            "owner_name": "Tariq Jamil",
            "property_address": "House 10, Phase 5, DHA, Karachi",
        },
        "system": {
            "proposed_kw": 9.9,
            "inverter_kw": 10.0,
            "panel_count": 18,
            "panel_watt": 550,
        },
    }

    create_res = client.post("/api/cases", json=payload)
    assert create_res.status_code == 200
    created = create_res.json()
    case_id = created["case_id"]
    assert case_id.startswith("U")
    assert created["report"]["overall"] == "READY"

    try:
        # Verify upload endpoint works with base64 content
        import base64
        sample_pdf_b64 = base64.b64encode(b"%PDF-1.4 fake scan bytes").decode("ascii")
        up_res = client.post(
            f"/api/cases/{case_id}/upload",
            json={"files": [{"name": "cnic_scan.pdf", "size": 24, "content_base64": sample_pdf_b64}]},
        )
        assert up_res.status_code == 200
        assert len(up_res.json()["files"]) == 1

        # Verify uploaded file can be viewed/downloaded
        view_res = client.get(f"/api/cases/{case_id}/files/cnic_scan.pdf")
        assert view_res.status_code == 200
        assert view_res.content == b"%PDF-1.4 fake scan bytes"

        # Verify edit page renders pre-populated
        edit_page_res = client.get(f"/case/{case_id}/edit")
        assert edit_page_res.status_code == 200
        assert "Update Customer" in edit_page_res.text

        # Verify PUT /api/cases/{case_id} updates the pack and re-runs checks
        payload["system"]["proposed_kw"] = 14.0  # Exceeds 10.0 kW sanctioned load -> NOT_READY
        put_res = client.put(f"/api/cases/{case_id}", json=payload)
        assert put_res.status_code == 200
        assert put_res.json()["report"]["overall"] == "NOT_READY"

        # Verify deleting individual uploaded file works
        del_file_res = client.delete(f"/api/cases/{case_id}/files/cnic_scan.pdf")
        assert del_file_res.status_code == 200
        assert len(del_file_res.json()["files"]) == 0

        # Verify case detail page renders
        case_page_res = client.get(f"/case/{case_id}")
        assert case_page_res.status_code == 200
        assert "Tariq Jamil" in case_page_res.text

        # Built-in cases cannot be edited or deleted
        bad_put = client.put("/api/cases/C01", json=payload)
        assert bad_put.status_code == 400
        bad_del = client.delete("/api/cases/C01")
        assert bad_del.status_code == 400
    finally:
        # Clean up custom case so other tests see exactly 21 cases
        del_res = client.delete(f"/api/cases/{case_id}")
        assert del_res.status_code == 200

