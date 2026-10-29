"""Tests for backend OCR normalization and multi-document auto-extraction."""

import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ocr.normalize import (
    fix_ocr_digits,
    normalize_bill_ref,
    normalize_cnic,
    normalize_date,
    normalize_float,
    normalize_person_name,
)
from app.ocr.service import parse_extracted_text_into_fields
from tools.make_ocr_samples import generate_all_ocr_samples


@pytest.fixture
def client():
    return TestClient(app)


def test_ocr_normalize_functions():
    """Verify OCR character fixes, CNIC formatting, date parsing, and name cleaning."""
    assert fix_ocr_digits("423O1-76S432I-3") == "42301-7654321-3"
    assert normalize_cnic("423O1 76S432I 3") == "42301-7654321-3"
    assert normalize_bill_ref("O4OOO12345678") == "0400012345678"
    assert normalize_date("15.08.2031") == "2031-08-15"
    assert normalize_date("2031-08-15") == "2031-08-15"
    assert normalize_person_name("  muhammad   tariq  khan ") == "Muhammad Tariq Khan"
    assert normalize_float("10.0 kW") == 10.0


def test_parse_labeled_text_across_all_documents():
    """Verify regex label parser extracts CNIC, Bill, Sale Deed, and Solar System fields from raw OCR text."""
    raw_ocr_text = """
    Name on CNIC: Muhammad Tariq Khan
    Father / Husband Name: Abdul Majeed Khan
    CNIC Number: 42301-7654321-3
    CNIC Expiry Date: 15.08.2031
    Address on CNIC: House 42-C, Phase 6, DHA, Karachi

    Consumer Name on Bill: M. Tariq Khan
    13-Digit Bill Reference No: 0400012345678
    Tariff Category: A-1
    Sanctioned Load (kW): 10.0 kW
    Connected Load (kW): 8.5 kW
    Connection Phase: 3-Phase
    Service Address on Bill: H# 42-C, Ph-6 DHA Khi

    Ownership Document Type: Sale Deed
    Owner Name on Deed: Muhammad Tariq Khan
    Property Address on Deed: House 42-C, Phase 6, DHA, Karachi
    Proposed System Size (kW): 9.9 kW
    Inverter Rating (kW): 10.0 kW
    Panel Count: 18
    Panel Wattage (W): 550 W
    """
    parsed = parse_extracted_text_into_fields(raw_ocr_text, filenames=["cnic.pdf", "bill.pdf", "deed.pdf"])
    fields = parsed["fields"]

    assert fields["cnic_name"] == "Muhammad Tariq Khan"
    assert fields["cnic_father"] == "Abdul Majeed Khan"
    assert fields["cnic_no"] == "42301-7654321-3"
    assert fields["cnic_expiry"] == "2031-08-15"
    assert fields["bill_ref"] == "0400012345678"
    assert fields["sanctioned_kw"] == 10.0
    assert fields["connected_kw"] == 8.5
    assert fields["phase"] == "3-phase"
    assert fields["ownership_type"] == "sale_deed"
    assert fields["owner_name"] == "Muhammad Tariq Khan"
    assert fields["proposed_kw"] == 9.9
    assert fields["inverter_kw"] == 10.0
    assert fields["panel_count"] == 18
    assert fields["panel_watt"] == 550
    assert "cnic" in parsed["docs_detected"]
    assert "bill" in parsed["docs_detected"]
    assert "ownership" in parsed["docs_detected"]


def test_ocr_api_endpoints_with_generated_samples(client):
    """Verify /api/ocr/status and /api/ocr/extract on generated PDF and PNG sample files."""
    status_res = client.get("/api/ocr/status")
    assert status_res.status_code == 200
    assert status_res.json()["available"] is True

    sample_paths = generate_all_ocr_samples()
    assert len(sample_paths) >= 9

    # Upload individual PDF + PNG files to /api/ocr/extract
    clean_dir = Path(__file__).resolve().parent.parent / "data" / "ocr_samples" / "clean_pack"
    files_to_send = [
        clean_dir / "01_CNIC_Card_Tariq_Khan.png",
        clean_dir / "02_KE_Electricity_Bill.pdf",
        clean_dir / "03_Sale_Deed_Ownership.png",
        clean_dir / "04_Solar_System_SLD_Specs.pdf",
    ]
    payload_files = []
    for fp in files_to_send:
        b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
        payload_files.append({"name": fp.name, "size": fp.stat().st_size, "content_base64": b64})

    ext_res = client.post("/api/ocr/extract", json={"files": payload_files})
    assert ext_res.status_code == 200
    data = ext_res.json()
    assert data["ok"] is True
    assert data["files_processed"] == 4

    f = data["fields"]
    assert f["cnic_name"] == "Muhammad Tariq Khan"
    assert f["cnic_no"] == "42301-7654321-3"
    assert f["bill_ref"] == "0400012345678"
    assert f["sanctioned_kw"] == 10.0
    assert f["owner_name"] == "Muhammad Tariq Khan"
    assert f["proposed_kw"] == 9.9
    assert len(data["docs_detected"]) >= 8
