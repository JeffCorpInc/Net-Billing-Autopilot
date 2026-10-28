"""Tests for strict privacy redaction across all 21 synthetic packs."""

import json
import re
from pathlib import Path
import pytest

from app.models import Pack
from app.redact import (
    CNIC_PATTERN,
    REFERENCE_NO_PATTERN,
    build_l1_name_input,
    build_l2_address_input,
    build_l3_checklist_input,
    build_shadow_checks_input,
    scrub_sensitive_text,
)
from app.storage import get_pack

CASES_DIR = Path(__file__).resolve().parent.parent / "data" / "cases"


def test_scrub_sensitive_direct():
    """Verify scrubber removes CNIC formats and 10+ digit reference numbers."""
    text = "CNIC 42101-1234567-1 and unhyphenated 4210112345671 with bill ref 01100000000012."
    scrubbed = scrub_sensitive_text(text)
    assert "42101-1234567-1" not in scrubbed
    assert "4210112345671" not in scrubbed
    assert "01100000000012" not in scrubbed
    assert "[REDACTED]" in scrubbed


def test_no_sensitive_data_in_any_llm_input_across_all_21_cases():
    """Ensure zero CNIC numbers or reference numbers ever appear in any LLM input payload."""
    case_files = sorted(CASES_DIR.glob("*.json"))
    assert len(case_files) == 21

    for cf in case_files:
        case_id = cf.stem
        pack = get_pack(case_id)
        assert pack is not None

        raw_cnic = pack.cnic.cnic_no
        raw_ref = pack.bill.reference_no

        # 1. Test L1 input
        l1_in = build_l1_name_input(pack)
        l1_str = json.dumps(l1_in)
        assert raw_cnic not in l1_str, f"{case_id} CNIC leaked into L1 input"
        assert raw_ref not in l1_str, f"{case_id} Bill ref leaked into L1 input"
        assert not CNIC_PATTERN.search(l1_str)
        assert not REFERENCE_NO_PATTERN.search(l1_str)

        # 2. Test L2 input
        l2_in = build_l2_address_input(pack)
        l2_str = json.dumps(l2_in)
        assert raw_cnic not in l2_str, f"{case_id} CNIC leaked into L2 input"
        assert raw_ref not in l2_str, f"{case_id} Bill ref leaked into L2 input"
        assert not CNIC_PATTERN.search(l2_str)
        assert not REFERENCE_NO_PATTERN.search(l2_str)

        # 3. Test Shadow checks input
        shadow_in = build_shadow_checks_input(pack)
        shadow_str = json.dumps(shadow_in)
        assert raw_cnic not in shadow_str, f"{case_id} CNIC leaked into Shadow input"
        assert raw_ref not in shadow_str, f"{case_id} Bill ref leaked into Shadow input"
        assert not CNIC_PATTERN.search(shadow_str)
        assert not REFERENCE_NO_PATTERN.search(shadow_str)

        # 4. Test L3 checklist input
        mock_issues = [
            {"check_id": "R1", "detail": f"Format invalid {raw_cnic}", "citation": "NADRA"},
            {"check_id": "R3", "detail": f"Ref {raw_ref} exceeded", "citation": "Reg 3"},
        ]
        l3_in = build_l3_checklist_input(mock_issues)
        l3_str = json.dumps(l3_in)
        assert raw_cnic not in l3_str, f"{case_id} CNIC leaked into L3 input"
        assert raw_ref not in l3_str, f"{case_id} Bill ref leaked into L3 input"
        assert not CNIC_PATTERN.search(l3_str)
        assert not REFERENCE_NO_PATTERN.search(l3_str)
