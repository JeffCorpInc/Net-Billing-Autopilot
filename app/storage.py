"""File-based persistence for packs, runtime reports, reviews, and audit trails."""

import json
import shutil
from pathlib import Path
from typing import Any

from app.config import (
    AUDIT_DIR,
    CASES_DIR,
    CUSTOM_CASES_DIR,
    DATA_DIR,
    LOAD_FLOW_THRESHOLD_KW,
    REPORTS_DIR,
    REVIEWS_PATH,
    UPLOADS_DIR,
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
    """Load pack JSON for a given case ID (checks built-in, custom, and bundled cases)."""
    cid = case_id.strip()
    file_path = CASES_DIR / f"{cid}.json"
    if not file_path.exists():
        file_path = CUSTOM_CASES_DIR / f"{cid}.json"
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return Pack.model_validate(json.load(f))
        except Exception:
            pass

    # Guaranteed fallback to pre-bundled benchmark cases
    try:
        from app.bundled_cases import BUNDLED_CASES
        raw_pack = BUNDLED_CASES.get(cid.upper())
        if raw_pack:
            return Pack.model_validate(raw_pack)
    except Exception:
        pass
    return None


def next_custom_case_id() -> str:
    """Generate the next sequential user case ID (U01, U02, ...)."""
    CUSTOM_CASES_DIR.mkdir(parents=True, exist_ok=True)
    existing = []
    for p in CUSTOM_CASES_DIR.glob("U*.json"):
        stem = p.stem
        if stem.startswith("U") and stem[1:].isdigit():
            existing.append(int(stem[1:]))
    next_num = (max(existing) + 1) if existing else 1
    return f"U{next_num:02d}"


def save_custom_pack(pack: Pack) -> Pack:
    """Persist a user-created application pack to data/runtime/custom_cases/."""
    CUSTOM_CASES_DIR.mkdir(parents=True, exist_ok=True)
    file_path = CUSTOM_CASES_DIR / f"{pack.case_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(pack.model_dump(), f, indent=2, ensure_ascii=False)
    return pack


def delete_custom_pack(case_id: str) -> bool:
    """Delete a custom user case (U* only) and its associated runtime artifacts."""
    if not case_id.upper().startswith("U"):
        return False
    pack_file = CUSTOM_CASES_DIR / f"{case_id}.json"
    if not pack_file.exists():
        return False
    pack_file.unlink(missing_ok=True)
    (REPORTS_DIR / f"{case_id}.json").unlink(missing_ok=True)
    (AUDIT_DIR / f"{case_id}.jsonl").unlink(missing_ok=True)
    uploads_dir = UPLOADS_DIR / case_id
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir, ignore_errors=True)
    return True


def list_uploaded_files(case_id: str) -> list[dict[str, Any]]:
    """Return metadata for any uploaded document files for a case."""
    case_uploads = UPLOADS_DIR / case_id
    if not case_uploads.exists():
        return []
    files = []
    for f in sorted(case_uploads.iterdir()):
        if f.is_file():
            files.append({
                "filename": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
            })
    return files


def save_uploaded_file(case_id: str, filename: str, content_bytes: bytes) -> dict[str, Any]:
    """Save an uploaded document file for a case."""
    safe_name = Path(filename).name
    if not safe_name:
        safe_name = "document.pdf"
    case_uploads = UPLOADS_DIR / case_id
    case_uploads.mkdir(parents=True, exist_ok=True)
    target = case_uploads / safe_name
    target.write_bytes(content_bytes)
    return {
        "filename": safe_name,
        "size_kb": round(target.stat().st_size / 1024, 1),
    }


def delete_uploaded_file(case_id: str, filename: str) -> bool:
    """Delete a specific uploaded document file from a case."""
    safe_name = Path(filename).name
    target = UPLOADS_DIR / case_id / safe_name
    if not target.exists() or not target.is_file():
        return False
    target.unlink(missing_ok=True)
    return True


def get_uploaded_file_path(case_id: str, filename: str) -> Path | None:
    """Return path to an uploaded file if it exists."""
    safe_name = Path(filename).name
    target = UPLOADS_DIR / case_id / safe_name
    if target.exists() and target.is_file():
        return target
    return None


def get_latest_report(case_id: str) -> CaseReport | None:
    """Load latest CaseReport if available (checks runtime directory, bundled data, or calculates on-the-fly)."""
    cid = case_id.strip().upper()
    report_file = REPORTS_DIR / f"{cid}.json"
    if report_file.exists():
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                return CaseReport.model_validate(json.load(f))
        except Exception:
            pass

    bundled_file = DATA_DIR / "runtime" / "reports" / f"{cid}.json"
    if bundled_file.exists():
        try:
            with open(bundled_file, "r", encoding="utf-8") as f:
                return CaseReport.model_validate(json.load(f))
        except Exception:
            pass

    # Check pre-bundled reports in memory
    try:
        from app.bundled_cases import BUNDLED_REPORTS
        raw_rep = BUNDLED_REPORTS.get(cid)
        if raw_rep:
            return CaseReport.model_validate(raw_rep)
    except Exception:
        pass

    # Calculate on-the-fly if benchmark case
    if cid.startswith("C"):
        pack = get_pack(cid)
        if pack:
            from app.merge import build_case_report
            from app.rules import run_code_rules

            rule_results = run_code_rules(pack)
            report = build_case_report(pack=pack, rule_results=rule_results)
            try:
                save_report(report)
            except Exception:
                pass
            return report

    return None


def save_report(report: CaseReport) -> None:
    """Save case report to runtime storage."""
    report_file = REPORTS_DIR / f"{report.case_id}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)


def list_case_summaries(include_custom: bool = True) -> list[CaseSummary]:
    """List all cases with summary statistics for the dashboard."""
    summaries = []
    reviews = load_reviews()
    seen_ids = set()

    # 1. Custom user cases (U*)
    if include_custom and CUSTOM_CASES_DIR.exists():
        for path in sorted(CUSTOM_CASES_DIR.glob("U*.json"), key=lambda p: p.stem, reverse=True):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    pack = Pack.model_validate(json.load(f))
                report = get_latest_report(pack.case_id)
                seen_ids.add(pack.case_id)
                summaries.append(
                    CaseSummary(
                        case_id=pack.case_id,
                        category=pack.category,
                        description=pack.description,
                        applicant_name=pack.cnic.name,
                        proposed_kw=pack.system.proposed_kw,
                        sanctioned_load_kw=pack.bill.sanctioned_load_kw,
                        docs_present_count=len(pack.docs_present),
                        docs_required_count=get_required_docs_count(pack),
                        overall=report.overall if report else "READY",
                        readiness=report.readiness_score if report else 100.0,
                        reviewed=pack.case_id in reviews,
                    )
                )
            except Exception:
                continue

    # 2. Builtin benchmark cases (C01 to C21) from filesystem if present
    try:
        builtin_files = sorted(CASES_DIR.glob("*.json"), key=lambda p: p.stem)
        for path in builtin_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    pack = Pack.model_validate(json.load(f))
                report = get_latest_report(pack.case_id)
                seen_ids.add(pack.case_id)
                summaries.append(
                    CaseSummary(
                        case_id=pack.case_id,
                        category=pack.category,
                        description=pack.description,
                        applicant_name=pack.cnic.name,
                        proposed_kw=pack.system.proposed_kw,
                        sanctioned_load_kw=pack.bill.sanctioned_load_kw,
                        docs_present_count=len(pack.docs_present),
                        docs_required_count=get_required_docs_count(pack),
                        overall=report.overall if report else "READY",
                        readiness=report.readiness_score if report else 100.0,
                        reviewed=pack.case_id in reviews,
                    )
                )
            except Exception:
                continue
    except Exception:
        pass

    # 3. Guaranteed fallback: ensure all 21 benchmark cases are present from bundled data
    try:
        from app.bundled_cases import BUNDLED_CASES
        for cid in sorted(BUNDLED_CASES.keys()):
            if cid not in seen_ids:
                pack = Pack.model_validate(BUNDLED_CASES[cid])
                report = get_latest_report(cid)
                seen_ids.add(cid)
                summaries.append(
                    CaseSummary(
                        case_id=pack.case_id,
                        category=pack.category,
                        description=pack.description,
                        applicant_name=pack.cnic.name,
                        proposed_kw=pack.system.proposed_kw,
                        sanctioned_load_kw=pack.bill.sanctioned_load_kw,
                        docs_present_count=len(pack.docs_present),
                        docs_required_count=get_required_docs_count(pack),
                        overall=report.overall if report else "READY",
                        readiness=report.readiness_score if report else 100.0,
                        reviewed=cid in reviews,
                    )
                )
    except Exception:
        pass

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
