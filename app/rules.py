"""Deterministic regulatory rules engine (R1-R7) for NEPRA 2026 regulations."""

import re
from datetime import date
from typing import Any

from app.config import DOC_LABELS, FEE_PER_KW_RS, LOAD_FLOW_THRESHOLD_KW
from app.models import CheckResult, Pack


def check_r1_cnic_format(pack: Pack) -> CheckResult:
    r"""R1: CNIC format verification (regex ^\d{5}-\d{7}-\d$)."""
    pattern = r"^\d{5}-\d{7}-\d$"

    cnic_no = pack.cnic.cnic_no.strip()
    is_valid = bool(re.match(pattern, cnic_no))

    if is_valid:
        detail = f"CNIC format is valid ({cnic_no})"
        status = "PASS"
    else:
        detail = (
            f"Invalid CNIC format: '{cnic_no}'. Expected 13 digits with hyphens (e.g. 42101-1234567-1)."
        )
        status = "FAIL"

    return CheckResult(
        id="R1",
        key="cnic_format",
        name="CNIC format",
        status=status,
        detail=detail,
        citation="NADRA CNIC format",
        source="code",
        data={"cnic_no": cnic_no, "valid": is_valid},
    )


def check_r2_cnic_expiry(pack: Pack, today: date | None = None) -> CheckResult:
    """R2: CNIC validity / expiry check (expiry >= today)."""
    if today is None:
        today = date.today()

    expiry_str = pack.cnic.expiry.strip()
    try:
        expiry_date = date.fromisoformat(expiry_str)
        is_valid = expiry_date >= today
        days_diff = (expiry_date - today).days

        if is_valid:
            detail = f"CNIC is valid until {expiry_str} ({days_diff} days remaining)"
            status = "PASS"
        else:
            days_ago = abs(days_diff)
            detail = f"CNIC expired on {expiry_str} ({days_ago} days ago). Valid unexpired CNIC required."
            status = "FAIL"
    except Exception:
        status = "FAIL"
        detail = f"Invalid CNIC expiry date format: '{expiry_str}'. Expected YYYY-MM-DD."
        days_diff = -999

    return CheckResult(
        id="R2",
        key="cnic_expiry",
        name="CNIC validity",
        status=status,
        detail=detail,
        citation="Installer policy",
        source="code",
        data={"expiry": expiry_str, "today": today.isoformat(), "days_remaining": days_diff},
    )


def check_r3_capacity(pack: Pack) -> CheckResult:
    """R3: System capacity constraint (proposed_kw <= sanctioned_load_kw)."""
    proposed = pack.system.proposed_kw
    sanctioned = pack.bill.sanctioned_load_kw
    is_pass = proposed <= sanctioned

    if is_pass:
        detail = f"Proposed {proposed:.1f} kW is within the sanctioned load of {sanctioned:.1f} kW"
        status = "PASS"
    else:
        detail = (
            f"Proposed {proposed:.1f} kW exceeds the sanctioned load of {sanctioned:.1f} kW"
        )
        status = "FAIL"

    return CheckResult(
        id="R3",
        key="capacity",
        name="System size",
        status=status,
        detail=detail,
        citation="Reg. 3(2)",
        source="code",
        data={"proposed_kw": proposed, "sanctioned_load_kw": sanctioned},
    )


def check_r4_connection_phase(pack: Pack) -> CheckResult:
    """R4: Connection phase check (must be 3-phase)."""
    phase = pack.bill.connection_phase.strip().lower()
    is_three_phase = phase == "3-phase"

    if is_three_phase:
        detail = "3-phase connection verified"
        status = "PASS"
    else:
        detail = (
            f"Ineligible connection type: '{pack.bill.connection_phase}'. "
            "3-phase connection is strictly required under NEPRA regulations."
        )
        status = "FAIL"

    return CheckResult(
        id="R4",
        key="connection_phase",
        name="Connection type",
        status=status,
        detail=detail,
        citation="Reg. 2(1)(v)",
        source="code",
        data={"connection_phase": pack.bill.connection_phase},
    )


def check_r5_required_docs(pack: Pack) -> CheckResult:
    """R5: Document completeness against K-Electric checklist."""
    base_docs = [
        "cnic",
        "bill",
        "ownership",
        "single_line_diagram",
        "affidavit",
        "vendor_checklist",
        "inverter_datasheet",
        "inverter_settings_letter",
    ]
    required = list(base_docs)

    if pack.is_tenant:
        required.append("noc")

    if pack.system.proposed_kw >= LOAD_FLOW_THRESHOLD_KW:
        required.append("load_flow_study")

    if pack.applicant_type == "commercial" and pack.system.proposed_kw >= LOAD_FLOW_THRESHOLD_KW:
        required.append("ntn")
        required.append("form_29")

    present_set = set(pack.docs_present)
    missing = [doc for doc in required if doc not in present_set]
    is_complete = len(missing) == 0

    if is_complete:
        detail = f"All {len(required)} required documents are present in pack"
        status = "PASS"
    else:
        missing_labels = [DOC_LABELS.get(d, d) for d in missing]
        detail = f"Missing {len(missing)} required document(s): {', '.join(missing_labels)}"
        status = "FAIL"

    return CheckResult(
        id="R5",
        key="required_docs",
        name="Required documents",
        status=status,
        detail=detail,
        citation="Reg. 3(3), 3(4), Sch. II & V; KE Guidelines",
        source="code",
        data={
            "required": required,
            "missing": missing,
            "present_count": len(pack.docs_present),
            "required_count": len(required),
        },
    )


def check_r6_fee(pack: Pack) -> CheckResult:
    """R6: Regulatory fee estimate (Informational)."""
    proposed = pack.system.proposed_kw
    fee = int(proposed * FEE_PER_KW_RS)
    detail = f"Estimated NEPRA fee: Rs {fee:,} ({proposed:.1f} kW × Rs {FEE_PER_KW_RS:,})"

    return CheckResult(
        id="R6",
        key="fee",
        name="Fee estimate",
        status="INFO",
        detail=detail,
        citation="Schedule-IV",
        source="code",
        data={"proposed_kw": proposed, "fee_rs": fee, "rate_per_kw": FEE_PER_KW_RS},
    )


def check_r7_connected_load(pack: Pack) -> CheckResult:
    """R7: Connected load constraint (connected_load_kw <= sanctioned_load_kw)."""
    connected = pack.bill.connected_load_kw
    sanctioned = pack.bill.sanctioned_load_kw
    is_pass = connected <= sanctioned

    if is_pass:
        detail = (
            f"Connected load ({connected:.1f} kW) does not exceed sanctioned load ({sanctioned:.1f} kW)"
        )
        status = "PASS"
    else:
        detail = (
            f"Connected load ({connected:.1f} kW) exceeds sanctioned load ({sanctioned:.1f} kW). "
            "Regularise the connected load with K-Electric before applying."
        )
        status = "FAIL"

    return CheckResult(
        id="R7",
        key="connected_load",
        name="Connected load",
        status=status,
        detail=detail,
        citation="KE Guidelines",
        source="code",
        data={"connected_load_kw": connected, "sanctioned_load_kw": sanctioned},
    )


def run_code_rules(pack: Pack, today: date | None = None) -> list[CheckResult]:
    """Execute all deterministic rules R1-R7 in sequential order."""
    return [
        check_r1_cnic_format(pack),
        check_r2_cnic_expiry(pack, today=today),
        check_r3_capacity(pack),
        check_r4_connection_phase(pack),
        check_r5_required_docs(pack),
        check_r6_fee(pack),
        check_r7_connected_load(pack),
    ]
