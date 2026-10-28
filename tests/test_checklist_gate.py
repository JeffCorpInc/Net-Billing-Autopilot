"""Tests for customer checklist generation and faithfulness gate enforcement."""

import pytest
from app.checklist import verify_faithfulness_gate, generate_customer_checklist
from app.models import CaseReport, CheckResult


def test_gate_accepts_valid_output():
    """Verify gate passes when all check_ids match and numbers are faithful."""
    input_issues = [
        {"check_id": "R3", "detail": "Proposed 14.0 kW exceeds sanctioned load 10.0 kW", "citation": "Reg. 3(2)"},
        {"check_id": "R2", "detail": "CNIC expired on 2026-02-15 (45 days ago)", "citation": "Installer policy"},
    ]
    llm_items = [
        {"check_id": "R3", "text": "Please adjust system capacity from 14.0 kW to sanctioned 10.0 kW limit. [Reg. 3(2)]"},
        {"check_id": "R2", "text": "Please renew your CNIC expired 45 days ago on 2026-02-15. [Installer policy]"},
    ]
    passed, reason = verify_faithfulness_gate(input_issues, llm_items)
    assert passed is True
    assert reason is None


def test_gate_rejects_extraneous_check_id():
    """Verify gate rejects when an extra hallucinated check_id is introduced."""
    input_issues = [
        {"check_id": "R3", "detail": "Proposed 12 kW exceeds sanctioned load 10 kW", "citation": "Reg. 3(2)"},
    ]
    llm_items = [
        {"check_id": "R3", "text": "Reduce capacity to 10 kW. [Reg. 3(2)]"},
        {"check_id": "R99", "text": "Hallucinated issue. [Invented]"},
    ]
    passed, reason = verify_faithfulness_gate(input_issues, llm_items)
    assert passed is False
    assert "count mismatch" in reason.lower() or "extraneous" in reason.lower()


def test_gate_rejects_missing_check_id():
    """Verify gate rejects when an input issue check_id is omitted."""
    input_issues = [
        {"check_id": "R3", "detail": "Proposed 14 kW exceeds 10 kW", "citation": "Reg. 3(2)"},
        {"check_id": "R2", "detail": "CNIC expired", "citation": "Installer policy"},
    ]
    llm_items = [
        {"check_id": "R3", "text": "Reduce capacity to 10 kW. [Reg. 3(2)]"},
    ]
    passed, reason = verify_faithfulness_gate(input_issues, llm_items)
    assert passed is False
    assert "count mismatch" in reason.lower() or "missing" in reason.lower()


def test_gate_rejects_invented_number():
    """Verify gate rejects when output text contains numbers not in the issue or citation."""
    input_issues = [
        {"check_id": "R3", "detail": "Proposed 12 kW exceeds sanctioned load 10 kW", "citation": "Reg. 3(2)"},
    ]
    # 5000 is an invented number not present in detail or citation
    llm_items = [
        {"check_id": "R3", "text": "Please pay an unapproved penalty of 5000 Rs. [Reg. 3(2)]"},
    ]
    passed, reason = verify_faithfulness_gate(input_issues, llm_items)
    assert passed is False
    assert "hallucinated numbers" in reason.lower()
    assert "5000" in reason


def test_clean_case_skips_llm():
    """Verify clean case returns standard passing checklist without calling LLM."""
    report = CaseReport(
        case_id="C01",
        timestamp="2026-04-13T10:00:00Z",
        mode="mock",
        overall="READY",
        readiness_score=100.0,
        results=[
            CheckResult(id="R1", key="cnic_format", name="CNIC", status="PASS", detail="OK", citation="NADRA"),
            CheckResult(id="R3", key="capacity", name="Capacity", status="PASS", detail="OK", citation="Reg 3"),
        ],
    )
    res_en = generate_customer_checklist("C01", report, lang="en")
    assert res_en.gate == "skipped"
    assert "All checks passed" in res_en.items[0].text

    res_ur = generate_customer_checklist("C01", report, lang="ur")
    assert res_ur.gate == "skipped"
    assert "تمام جانچ" in res_ur.items[0].text


def test_audit_trail_checks_run_details_structure():
    """Verify every audit entry (including checks_run) exposes details.mode."""
    from starlette.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r_check = client.post("/api/check/C01?use_llm=false")
    assert r_check.status_code == 200

    r_audit = client.get("/api/audit/C01")
    assert r_audit.status_code == 200
    entries = r_audit.json().get("entries", [])
    assert len(entries) > 0
    for entry in entries:
        assert isinstance(entry.get("details"), dict)
        if entry.get("event") == "checks_run":
            assert "mode" in entry["details"]
            assert "overall" in entry["details"]
            assert "readiness_score" in entry["details"]


