"""Merge engine: calculate overall verdict, readiness score, and persist CaseReport."""

import json
from datetime import datetime, timezone
from typing import Any

from app.config import AUDIT_DIR, get_settings
from app.models import CaseReport, CheckResult, Pack
from app.storage import save_report


def build_case_report(
    pack: Pack,
    rule_results: list[CheckResult],
    llm_results: list[CheckResult] | None = None,
    shadow_checks: list[dict[str, Any]] | None = None,
) -> CaseReport:
    """Combine deterministic rules and LLM checks to determine final status."""
    settings = get_settings()
    llm_results = llm_results or []
    shadow_checks = shadow_checks or []

    all_results = list(rule_results) + list(llm_results)

    critical_keys = {
        "cnic_format",
        "cnic_expiry",
        "capacity",
        "connection_phase",
        "required_docs",
        "connected_load",
        "name_match",
        "address_match",
    }

    # Add placeholder PENDING L1/L2 if not yet executed
    existing_keys = {r.key for r in all_results}
    if "name_match" not in existing_keys:
        all_results.append(
            CheckResult(
                id="L1",
                key="name_match",
                name="Name consistency",
                status="PENDING",
                detail="Pending Phase 3 LLM evaluation",
                citation="Applicant Identity Verification",
                source="mock-llm",
            )
        )
    if "address_match" not in existing_keys:
        all_results.append(
            CheckResult(
                id="L2",
                key="address_match",
                name="Address consistency",
                status="PENDING",
                detail="Pending Phase 3 LLM evaluation",
                citation="Premises Verification",
                source="mock-llm",
            )
        )

    critical_results = [r for r in all_results if r.key in critical_keys]
    has_fail = any(r.status == "FAIL" for r in critical_results)
    has_unsure = any(r.status == "UNSURE" for r in critical_results)

    if has_fail:
        overall = "NOT_READY"
    elif has_unsure:
        overall = "NEEDS_REVIEW"
    else:
        overall = "READY"

    pass_count = sum(1 for r in critical_results if r.status == "PASS")
    readiness_score = round((pass_count / 8.0) * 100.0, 1)

    report = CaseReport(
        case_id=pack.case_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        mode=settings.mode,
        overall=overall,
        readiness_score=readiness_score,
        results=all_results,
        shadow_checks=shadow_checks,
    )

    save_report(report)

    # Append to audit trail
    try:
        audit_file = AUDIT_DIR / f"{pack.case_id}.jsonl"
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "checks_run",
            "mode": settings.mode,
            "overall": overall,
            "readiness_score": readiness_score,
            "pass_count": pass_count,
            "total_checks": len(all_results),
        }
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return report
