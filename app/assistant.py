"""Interactive AI Onboarding Copilot (Chatbot Assistant) for New Application & Custom User Cases.

Enforces Hard Boundaries:
1. Code decides all deterministic rules (R1-R7) and fuzzy pre-checks on live draft state first.
2. Strict two-layer PII redaction (CNIC and 13-digit bill reference numbers never leave the server).
3. LLM explains what is wrong, mismatched, or missing in plain language and guides the user to fix it.
"""

import json
import re
from datetime import date
from typing import Any

from app.config import DOC_LABELS, LOAD_FLOW_THRESHOLD_KW
from app.llm_checks import compute_address_fuzzy_score, compute_name_fuzzy_score
from app.llm_client import complete_json
from app.redact import sanitize_dict, scrub_sensitive_text


ASSISTANT_SYSTEM_PROMPT = """You are the NetBill Assist AI Copilot for rooftop-solar net-billing onboarding in Karachi, Pakistan under NEPRA (Prosumer) Regulations 2026 (SRO 251(I)/2026) and K-Electric Net-Billing Guidelines (13 Apr 2026).

Your role is to help the user or onboarding staff member understand:
1. Which form fields are incomplete or missing.
2. Which entries violate deterministic rules (R1 CNIC format, R2 CNIC expiry, R3 Proposed kW <= Sanctioned Load kW, R4 3-Phase required, R5 Connected Load <= Sanctioned Load, R7 Required documents).
3. Whether there are Name (L1) or Address (L2) mismatches across the CNIC, K-Electric Bill, and Ownership Deed.
4. How to fix each issue step-by-step.

STRICT RULES:
- Base your guidance strictly on the `detected_issues` and `missing_fields` provided by the deterministic code engine in the JSON input.
- Never invent or override regulatory limits.
- Keep your response concise, friendly, and structured with clear bullet points.
- Return valid JSON only with this exact schema:
{
  "reply": "Markdown-formatted helpful explanation addressing the user's question and listing what is wrong or mismatched and how to fix it.",
  "next_steps": ["Short actionable fix 1", "Short actionable fix 2"]
}
"""


def inspect_draft_state(draft: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    """Run deterministic and fuzzy diagnostics on a live (possibly incomplete) form or saved pack."""
    if today is None:
        today = date.today()

    cnic = draft.get("cnic") or {}
    bill = draft.get("bill") or {}
    ownership = draft.get("ownership") or {}
    system = draft.get("system") or {}
    docs_present = set(draft.get("docs_present") or [])
    is_tenant = bool(draft.get("is_tenant", False))
    applicant_type = str(draft.get("applicant_type") or "residential")

    missing_fields: list[dict[str, str]] = []
    detected_issues: list[dict[str, str]] = []

    def req_str(val: Any, field_id: str, label: str) -> str:
        s = str(val or "").strip()
        if not s:
            missing_fields.append({"field_id": field_id, "label": label})
        return s

    cnic_name = req_str(cnic.get("name"), "f-cnic-name", "Name on CNIC")
    cnic_father = req_str(cnic.get("father_name"), "f-cnic-father", "Father / Husband Name")
    cnic_no = req_str(cnic.get("cnic_no"), "f-cnic-no", "CNIC Number")
    cnic_expiry = req_str(cnic.get("expiry"), "f-cnic-expiry", "CNIC Expiry Date")
    cnic_addr = req_str(cnic.get("address"), "f-cnic-address", "Address on CNIC")

    bill_name = req_str(bill.get("consumer_name"), "f-bill-name", "Consumer Name on Bill")
    bill_ref = req_str(bill.get("reference_no"), "f-bill-ref", "13-Digit Bill Reference No")
    bill_addr = req_str(bill.get("address"), "f-bill-address", "Service Address on Bill")
    phase = str(bill.get("connection_phase") or "3-phase").strip()

    owner_name = req_str(ownership.get("owner_name"), "f-owner-name", "Owner Name on Deed")
    prop_addr = req_str(ownership.get("property_address"), "f-property-address", "Property Address on Deed")

    # Numeric fields
    def parse_num(val: Any, field_id: str, label: str) -> float | None:
        if val is None or str(val).strip() == "":
            missing_fields.append({"field_id": field_id, "label": label})
            return None
        try:
            num = float(val)
            if num <= 0:
                missing_fields.append({"field_id": field_id, "label": label})
                return None
            return num
        except Exception:
            missing_fields.append({"field_id": field_id, "label": label})
            return None

    sanctioned_kw = parse_num(bill.get("sanctioned_load_kw"), "f-sanctioned-kw", "Sanctioned Load (kW)")
    connected_kw = parse_num(bill.get("connected_load_kw"), "f-connected-kw", "Connected Load (kW)")
    proposed_kw = parse_num(system.get("proposed_kw"), "f-proposed-kw", "Proposed System Size (kW)")
    inverter_kw = parse_num(system.get("inverter_kw"), "f-inverter-kw", "Inverter Rating (kW)")

    # R1: CNIC Format Check (checked in Python before redaction!)
    if cnic_no:
        if not re.match(r"^\d{5}-\d{7}-\d$", cnic_no):
            detected_issues.append({
                "rule_id": "R1",
                "field_id": "f-cnic-no",
                "severity": "error",
                "title": "Invalid CNIC Format",
                "message": "CNIC number must be 13 digits formatted with hyphens as XXXXX-XXXXXXX-X.",
                "fix": "Edit the CNIC Number field to include hyphens (e.g., 42301-7654321-3).",
            })

    # Bill Reference Number Format Warning
    if bill_ref and not re.match(r"^\d{13}$", bill_ref):
        detected_issues.append({
            "rule_id": "BILL-REF",
            "field_id": "f-bill-ref",
            "severity": "warning",
            "title": "K-Electric Reference Number Format",
            "message": f"Entered bill reference has {len(bill_ref)} characters instead of a standard 13-digit K-Electric account number.",
            "fix": "Enter the 13-digit K-Electric account/reference number without spaces or dashes.",
        })

    # R2: CNIC Expiry Check
    if cnic_expiry:
        try:
            exp_d = date.fromisoformat(cnic_expiry)
            if exp_d < today:
                days_ago = (today - exp_d).days
                detected_issues.append({
                    "rule_id": "R2",
                    "field_id": "f-cnic-expiry",
                    "severity": "error",
                    "title": "Expired CNIC",
                    "message": f"CNIC expired on {cnic_expiry} ({days_ago} days ago).",
                    "fix": "Provide a renewed, unexpired NADRA CNIC and update the CNIC Expiry Date field.",
                })
        except Exception:
            detected_issues.append({
                "rule_id": "R2",
                "field_id": "f-cnic-expiry",
                "severity": "error",
                "title": "Invalid Expiry Date",
                "message": f"Could not parse expiry date '{cnic_expiry}'.",
                "fix": "Select a valid YYYY-MM-DD date in the CNIC Expiry Date field.",
            })

    # R3: System Capacity vs Sanctioned Load
    if proposed_kw is not None and sanctioned_kw is not None:
        if proposed_kw > sanctioned_kw:
            detected_issues.append({
                "rule_id": "R3",
                "field_id": "f-proposed-kw",
                "severity": "error",
                "title": "System Exceeds Sanctioned Load",
                "message": f"Proposed solar size ({proposed_kw} kW) exceeds K-Electric sanctioned load ({sanctioned_kw} kW) under NEPRA Reg. 3(2).",
                "fix": f"Reduce Proposed System (kW) to {sanctioned_kw} kW or less, OR apply to K-Electric for a sanctioned load extension first.",
            })

    # R4: Connection Phase
    if phase.lower() != "3-phase":
        detected_issues.append({
            "rule_id": "R4",
            "field_id": "f-phase",
            "severity": "error",
            "title": "Single-Phase Connection Ineligible",
            "message": f"Connection phase is set to '{phase}'. NEPRA net-billing requires a 3-phase supply.",
            "fix": "Customer must upgrade their K-Electric meter from 1-phase to 3-phase before filing.",
        })

    # R5: Connected Load vs Sanctioned Load
    if connected_kw is not None and sanctioned_kw is not None:
        if connected_kw > sanctioned_kw:
            detected_issues.append({
                "rule_id": "R5",
                "field_id": "f-connected-kw",
                "severity": "error",
                "title": "Connected Load Exceeds Sanctioned Load",
                "message": f"Bill connected load ({connected_kw} kW) is higher than sanctioned load ({sanctioned_kw} kW).",
                "fix": "Regularize connected load with K-Electric so Connected Load <= Sanctioned Load.",
            })

    # R7: Required Documents Check
    req_docs = [
        "cnic", "bill", "ownership", "single_line_diagram",
        "affidavit", "vendor_checklist", "inverter_datasheet", "inverter_settings_letter"
    ]
    if is_tenant:
        req_docs.append("noc")
    if proposed_kw is not None and proposed_kw >= LOAD_FLOW_THRESHOLD_KW:
        req_docs.append("load_flow_study")
        if applicant_type == "commercial":
            req_docs.extend(["ntn", "form_29"])

    missing_docs = [DOC_LABELS.get(d, d) for d in req_docs if d not in docs_present]
    if missing_docs:
        detected_issues.append({
            "rule_id": "R7",
            "field_id": "f-file-upload",
            "severity": "error",
            "title": f"Missing {len(missing_docs)} Required Document(s)",
            "message": f"Missing checked documents: {', '.join(missing_docs)}.",
            "fix": f"In Step 4, check and attach: {', '.join(missing_docs)}.",
        })

    # L1: Cross-Document Name Consistency Pre-Check
    if cnic_name and bill_name:
        name_score = compute_name_fuzzy_score(cnic_name, bill_name, owner_name, is_tenant)
        if name_score < 60.0:
            detected_issues.append({
                "rule_id": "L1",
                "field_id": "f-bill-name",
                "severity": "error",
                "title": "Name Mismatch Across Documents",
                "message": (
                    f"CNIC Name ('{cnic_name}'), Bill Consumer Name ('{bill_name}')"
                    + (f", and Deed Owner Name ('{owner_name}')" if not is_tenant and owner_name else "")
                    + f" have low similarity ({name_score}%)."
                ),
                "fix": "Ensure the K-Electric bill and ownership deed are in the applicant's name, or check 'Applicant is a Tenant' and attach an Owner NOC if renting.",
            })
        elif name_score < 85.0:
            detected_issues.append({
                "rule_id": "L1",
                "field_id": "f-bill-name",
                "severity": "warning",
                "title": "Partial Name Variation (Needs Staff Review)",
                "message": f"Names ('{cnic_name}' vs '{bill_name}') have moderate similarity ({name_score}%).",
                "fix": "Verify whether this is a spelling/honorific variation or a different family member.",
            })

    # L2: Cross-Document Address Consistency Pre-Check
    if cnic_addr and bill_addr and prop_addr:
        addr_score = compute_address_fuzzy_score(cnic_addr, bill_addr, prop_addr)
        if addr_score < 60.0:
            detected_issues.append({
                "rule_id": "L2",
                "field_id": "f-bill-address",
                "severity": "error",
                "title": "Property Address Mismatch",
                "message": f"Addresses across CNIC, K-Electric Bill, and Ownership Deed do not match ({addr_score}% similarity).",
                "fix": "Ensure the K-Electric Bill service address and Ownership Deed property address refer to the same installation premises.",
            })
        elif addr_score < 80.0:
            detected_issues.append({
                "rule_id": "L2",
                "field_id": "f-bill-address",
                "severity": "warning",
                "title": "Address Abbreviation / Variation",
                "message": f"Addresses have minor differences ({addr_score}% similarity).",
                "fix": "Confirm house/plot number and block/phase match between the K-Electric bill and title deed.",
            })

    return {
        "missing_fields": missing_fields,
        "detected_issues": detected_issues,
        "summary": {
            "applicant_type": applicant_type,
            "is_tenant": is_tenant,
            "cnic_name": cnic_name,
            "bill_name": bill_name,
            "owner_name": owner_name,
            "cnic_address": cnic_addr,
            "bill_address": bill_addr,
            "property_address": prop_addr,
            "proposed_kw": proposed_kw,
            "sanctioned_kw": sanctioned_kw,
            "connected_kw": connected_kw,
            "phase": phase,
            "docs_checked_count": len(docs_present),
            "docs_required_count": len(req_docs),
        },
    }


def run_assistant_chat(
    case_id: str,
    draft_state: dict[str, Any],
    user_message: str = "",
) -> dict[str, Any]:
    """Inspect draft/case state, scrub all PII, query LLM (or fallback), and return structured guidance."""
    diagnostics = inspect_draft_state(draft_state)

    # Scrub sensitive CNIC / 13-digit reference numbers from both diagnostics and user message
    redacted_payload = sanitize_dict({
        "user_message": scrub_sensitive_text(user_message or "Check my application entries and tell me what is wrong or mismatched."),
        "missing_fields": diagnostics["missing_fields"],
        "detected_issues": diagnostics["detected_issues"],
        "application_summary": diagnostics["summary"],
    })

    user_json = json.dumps(redacted_payload, ensure_ascii=False)

    parsed, meta = complete_json(
        system=ASSISTANT_SYSTEM_PROMPT,
        user=user_json,
        temperature=0.2,
        case_id=case_id or "DRAFT",
        task="assistant_chat",
    )

    if parsed and isinstance(parsed.get("reply"), str) and parsed["reply"].strip():
        reply_text = scrub_sensitive_text(parsed["reply"].strip())
        next_steps = [
            scrub_sensitive_text(str(s))
            for s in (parsed.get("next_steps") or [])
            if s
        ]
        source = "llm" if meta.get("provider") not in ("mock", "none") else "mock-llm"
    else:
        # Deterministic fallback if live LLM is unreachable or quota-limited
        fallback = _build_deterministic_reply(diagnostics, user_message)
        reply_text = fallback["reply"]
        next_steps = fallback["next_steps"]
        source = "deterministic-fallback"

    return {
        "reply": reply_text,
        "next_steps": next_steps,
        "issues": diagnostics["detected_issues"],
        "missing_fields": diagnostics["missing_fields"],
        "issue_count": len(diagnostics["detected_issues"]) + len(diagnostics["missing_fields"]),
        "source": source,
        "model": meta.get("model", "fallback"),
        "latency_ms": meta.get("latency_ms", 0),
    }


def _build_deterministic_reply(diagnostics: dict[str, Any], user_message: str) -> dict[str, Any]:
    """Build a clear, rule-accurate response if the external LLM is offline."""
    issues = diagnostics["detected_issues"]
    missing = diagnostics["missing_fields"]

    if not issues and not missing:
        return {
            "reply": (
                "All entered fields and documents look **100% compliant** with NEPRA (Prosumer) Regulations 2026 "
                "and K-Electric Net-Billing Guidelines! Your CNIC format/expiry, 3-phase supply, system size, "
                "and cross-document names/addresses all pass."
            ),
            "next_steps": ["Click Save / Create Application to generate the compliant Draft PDF."],
        }

    parts = []
    if missing:
        labels = ", ".join(m["label"] for m in missing[:5])
        more = f" (+{len(missing) - 5} more)" if len(missing) > 5 else ""
        parts.append(f"**Incomplete Fields ({len(missing)}):** Please fill in {labels}{more}.")

    if issues:
        parts.append(f"**Detected Compliance & Mismatch Issues ({len(issues)}):**")
        for idx, iss in enumerate(issues, 1):
            parts.append(f"{idx}. **[{iss['rule_id']}] {iss['title']}:** {iss['message']}\n   ↳ *How to fix:* {iss['fix']}")

    return {
        "reply": "\n\n".join(parts),
        "next_steps": [iss["fix"] for iss in issues[:3]],
    }
