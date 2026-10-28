"""Data redaction engine: strict allow-listing and regex sanitization before LLM invocation."""

import json
import re
from datetime import date
from typing import Any

from app.models import Pack

# Regex patterns for sensitive identifiers:
# - CNIC numbers: 5-7-1 digits with or without hyphens (e.g. 42101-1234567-1, 4210112345671)
# - Electricity bill reference numbers: 10+ consecutive digits (e.g. 01100000000012)
CNIC_PATTERN = re.compile(r"\b\d{5}-?\d{7}-?\d\b")
REFERENCE_NO_PATTERN = re.compile(r"\b\d{10,}\b")


def scrub_sensitive_text(text: str) -> str:
    """Scrub CNIC numbers and long reference digit strings from text."""
    if not isinstance(text, str):
        return text
    scrubbed = CNIC_PATTERN.sub("[REDACTED]", text)
    scrubbed = REFERENCE_NO_PATTERN.sub("[REDACTED]", scrubbed)
    return scrubbed


def sanitize_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively scrub all string values in a dictionary."""
    sanitized: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, str):
            sanitized[k] = scrub_sensitive_text(v)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [
                scrub_sensitive_text(i) if isinstance(i, str) else i for i in v
            ]
        else:
            sanitized[k] = v
    return sanitized


def build_l1_name_input(pack: Pack) -> dict[str, Any]:
    """Build redacted input for L1 Name Match check."""
    raw = {
        "cnic_name": pack.cnic.name,
        "bill_consumer_name": pack.bill.consumer_name,
        "deed_owner_name": pack.ownership.owner_name,
        "is_tenant": pack.is_tenant,
    }
    return sanitize_dict(raw)


def build_l2_address_input(pack: Pack) -> dict[str, Any]:
    """Build redacted input for L2 Address Match check."""
    raw = {
        "cnic_address": pack.cnic.address,
        "bill_address": pack.bill.address,
        "deed_address": pack.ownership.property_address,
    }
    return sanitize_dict(raw)


def build_shadow_checks_input(pack: Pack, today: date | None = None) -> dict[str, Any]:
    """Build redacted input for R2/R3 Shadow Checks."""
    if today is None:
        today = date.today()
    raw = {
        "cnic_expiry": pack.cnic.expiry,
        "today": today.isoformat(),
        "proposed_kw": pack.system.proposed_kw,
        "sanctioned_load_kw": pack.bill.sanctioned_load_kw,
    }
    return sanitize_dict(raw)


def build_l3_checklist_input(failed_issues: list[dict[str, str]], lang: str = "en") -> dict[str, Any]:
    """Build redacted input for L3 Customer Checklist."""
    sanitized_items = []
    for issue in failed_issues:
        sanitized_items.append({
            "check_id": issue.get("check_id", ""),
            "detail": scrub_sensitive_text(issue.get("detail", "")),
            "citation": scrub_sensitive_text(issue.get("citation", "")),
        })
    return {"lang": lang, "items": sanitized_items}
