"""File-based persistence for packs, runtime reports, reviews, and audit trails."""

import json
from pathlib import Path
from typing import Any

from app.config import (
    AUDIT_DIR,
    CASES_DIR,
    LOAD_FLOW_THRESHOLD_KW,
    REPORTS_DIR,
    REVIEWS_PATH,
)
from app.models import CaseReport, CaseSummary, Pack


def get_required_docs_count(pack: Pack) -> int:
    """Calculate total required documents count based on regulatory rules."""
    count = 8  # Base 8 documents
    if pack.is_tenant:
        count += 1  # Owner's NOC
    if pack.system.proposed_kw >= LOAD_FLOW_THRESHOLD_KW:
        count += 1  # Load-flow study
    if pack.applicant_type == "commercial" and pack.system.proposed_kw >= LOAD_FLOW_THRESHOLD_KW:
        count += 2  # NTN certificate and Form 29
    return count


def load_reviews() -> dict[str, Any]:
    """Load reviews map from runtime JSON."""
    if not REVIEWS_PATH.exists():
        return {}
    try:
        with open(REVIEWS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_review(case_id: str, staff_name: str, note: str = "") -> dict[str, Any]:
    """Save staff review record."""
    reviews = load_reviews()
    record = {
        "case_id": case_id,
        "staff_name": staff_name,
        "note": note,
    }
    reviews[case_id] = record
    with open(REVIEWS_PATH, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)
    return record


def get_pack(case_id: str) -> Pack | None:
    """Load pack JSON for a given case ID."""
    file_path = CASES_DIR / f"{case_id}.json"
    if not file_path.exists():
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Pack.model_validate(data)
    except Exception:
        return None


def get_latest_report(case_id: str) -> CaseReport | None:
    """Load latest CaseReport if available."""
    report_file = REPORTS_DIR / f"{case_id}.json"
    if not report_file.exists():
        return None
    try:
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CaseReport.model_validate(data)
    except Exception:
        return None


def save_report(report: CaseReport) -> None:
    """Save case report to runtime storage."""
    report_file = REPORTS_DIR / f"{report.case_id}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)


def list_case_summaries() -> list[CaseSummary]:
    """List all cases with summary statistics for the dashboard."""
    summaries = []
    reviews = load_reviews()

    # Iterate C01 to C21 in order
    case_files = sorted(CASES_DIR.glob("*.json"), key=lambda p: p.stem)
    for path in case_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            pack = Pack.model_validate(raw)
            report = get_latest_report(pack.case_id)
            is_reviewed = pack.case_id in reviews

            overall = report.overall if report else "PENDING"
            readiness = report.readiness_score if report else 0.0

            summary = CaseSummary(
                case_id=pack.case_id,
                category=pack.category,
                description=pack.description,
                applicant_name=pack.cnic.name,
                proposed_kw=pack.system.proposed_kw,
                sanctioned_load_kw=pack.bill.sanctioned_load_kw,
                docs_present_count=len(pack.docs_present),
                docs_required_count=get_required_docs_count(pack),
                overall=overall,
                readiness=readiness,
                reviewed=is_reviewed,
            )
            summaries.append(summary)
        except Exception:
            continue

    return summaries


def get_audit_trail(case_id: str) -> list[dict[str, Any]]:
    """Retrieve audit log lines for a specific case."""
    audit_file = AUDIT_DIR / f"{case_id}.jsonl"
    if not audit_file.exists():
        return []
    entries = []
    with open(audit_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    return entries
