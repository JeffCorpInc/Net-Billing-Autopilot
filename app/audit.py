"""Audit logging and review trail management for compliance accountability."""

import json
from datetime import datetime, timezone
from typing import Any

from app.config import AUDIT_DIR
from app.storage import load_reviews, save_review


def log_audit_event(case_id: str, event_type: str, details: dict[str, Any]) -> dict[str, Any]:
    """Append event to the immutable case audit trail."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    audit_file = AUDIT_DIR / f"{case_id}.jsonl"

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "event": event_type,
        "details": details,
    }

    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return record


def get_case_audit_trail(case_id: str) -> list[dict[str, Any]]:
    """Retrieve full chronological audit trail for a case."""
    audit_file = AUDIT_DIR / f"{case_id}.jsonl"
    if not audit_file.exists():
        return []

    entries = []
    try:
        with open(audit_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception:
        pass
    return entries


def record_staff_review(case_id: str, staff_name: str, note: str = "") -> dict[str, Any]:
    """Store staff review record and record audit trail event."""
    review = save_review(case_id=case_id, staff_name=staff_name, note=note)
    log_audit_event(
        case_id=case_id,
        event_type="staff_review",
        details={"staff_name": staff_name, "note": note},
    )
    return review
