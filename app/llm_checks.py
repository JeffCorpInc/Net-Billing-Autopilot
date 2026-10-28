"""LLM semantic checks (L1 name match, L2 address match, shadow checks, fuzzy fallback)."""

import json
import re
from typing import Any
import rapidfuzz

from app.config import get_settings
from app.llm_client import complete_json
from app.models import CheckResult, Pack
from app.prompts import (
    L1_NAME_MATCH_SYSTEM,
    L2_ADDRESS_MATCH_SYSTEM,
    SHADOW_CHECKS_SYSTEM,
)
from app.redact import (
    build_l1_name_input,
    build_l2_address_input,
    build_shadow_checks_input,
)


def normalize_name(text: str) -> str:
    """Normalize Pakistani names by expanding common variants and abbreviations."""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)

    # Name expansions
    replacements = [
        (r"\b(mohammad|mohd|m)\b", "muhammad"),
        (r"\b(sayed|s)\b", "syed"),
        (r"\b(abd)\b", "abdul"),
        (r"\b(mr|mrs|dr|haji|engr)\b", ""),
    ]
    for pattern, repl in replacements:
        t = re.sub(pattern, repl, t)
    return " ".join(t.split())


def normalize_address(text: str) -> str:
    """Normalize Karachi addresses by expanding abbreviations and removing noise."""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)

    replacements = [
        (r"\b(h#|h-|h\.no|house|plot)\b", "house"),
        (r"\b(blk|b-|block)\b", "block"),
        (r"\b(st|street)\b", "street"),
        (r"\b(ph|phase)\b", "phase"),
        (r"\b(sec|sector)\b", "sector"),
        (r"\b(rd|road)\b", "road"),
        (r"\bgulshan-e-iqbal\b", "gulshan iqbal"),
        (r"\b(khi|karachi)\b", "karachi"),
    ]
    for pattern, repl in replacements:
        t = re.sub(pattern, repl, t)
    return " ".join(t.split())


def compute_name_fuzzy_score(cnic_name: str, bill_name: str, deed_name: str, is_tenant: bool) -> float:
    """Calculate minimum normalized token set ratio across compared document names."""
    c_norm = normalize_name(cnic_name)
    b_norm = normalize_name(bill_name)
    scores = [rapidfuzz.fuzz.token_set_ratio(c_norm, b_norm)]

    if not is_tenant and deed_name:
        d_norm = normalize_name(deed_name)
        scores.append(rapidfuzz.fuzz.token_set_ratio(c_norm, d_norm))

    return round(float(min(scores)), 1)


def compute_address_fuzzy_score(cnic_addr: str, bill_addr: str, deed_addr: str) -> float:
    """Calculate minimum normalized token set ratio across compared property addresses."""
    c_norm = normalize_address(cnic_addr)
    b_norm = normalize_address(bill_addr)
    d_norm = normalize_address(deed_addr)

    scores = [
        rapidfuzz.fuzz.token_set_ratio(c_norm, b_norm),
        rapidfuzz.fuzz.token_set_ratio(c_norm, d_norm),
    ]
    return round(float(min(scores)), 1)


def score_to_fallback_verdict(score: float) -> str:
    """Convert fuzzy score to verdict in fallback mode."""
    if score >= 85.0:
        return "PASS"
    if score >= 60.0:
        return "UNSURE"
    return "FAIL"


def run_l1_name_check(pack: Pack) -> CheckResult:
    """Run L1 Name Match check via LLM, mock, or fuzzy fallback."""
    settings = get_settings()
    user_payload = build_l1_name_input(pack)
    user_json = json.dumps(user_payload, ensure_ascii=False)

    fuzzy_score = compute_name_fuzzy_score(
        cnic_name=pack.cnic.name,
        bill_name=pack.bill.consumer_name,
        deed_name=pack.ownership.owner_name,
        is_tenant=pack.is_tenant,
    )

    llm_out, meta = complete_json(
        system=L1_NAME_MATCH_SYSTEM,
        user=user_json,
        temperature=0.0,
        case_id=pack.case_id,
        task="L1",
    )

    # Validate output
    if llm_out and isinstance(llm_out, dict) and "verdict" in llm_out:
        verdict = llm_out["verdict"].upper()
        if verdict not in ["PASS", "FAIL", "UNSURE"]:
            verdict = score_to_fallback_verdict(fuzzy_score)
        confidence = float(llm_out.get("confidence", 0.95))
        reason = str(llm_out.get("reason", "Name consistency verified across documents."))
        evidence = llm_out.get("evidence", [])
        source = "mock-llm" if meta.get("provider") == "mock" else "llm"
    else:
        # Fallback mode
        verdict = score_to_fallback_verdict(fuzzy_score)
        confidence = round(fuzzy_score / 100.0, 2)
        reason = f"Fuzzy score {fuzzy_score}% calculated via normalized token comparison."
        evidence = [f"Fuzzy token score: {fuzzy_score}%"]
        source = "fuzzy-fallback"

    llm_metadata = {
        "verdict": verdict,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence,
        "fuzzy_score": fuzzy_score,
        "latency_ms": meta.get("latency_ms", 0),
        "model": meta.get("model", ""),
        "provider": meta.get("provider", ""),
    }

    return CheckResult(
        id="L1",
        key="name_match",
        name="Name consistency",
        status=verdict,
        detail=reason,
        citation="Applicant Identity Verification",
        source=source,
        data={
            "fuzzy_score": fuzzy_score,
            "is_tenant": pack.is_tenant,
            "cnic_name": pack.cnic.name,
            "bill_name": pack.bill.consumer_name,
            "deed_name": pack.ownership.owner_name,
        },
        llm=llm_metadata,
    )


def run_l2_address_check(pack: Pack) -> CheckResult:
    """Run L2 Address Match check via LLM, mock, or fuzzy fallback."""
    settings = get_settings()
    user_payload = build_l2_address_input(pack)
    user_json = json.dumps(user_payload, ensure_ascii=False)

    fuzzy_score = compute_address_fuzzy_score(
        cnic_addr=pack.cnic.address,
        bill_addr=pack.bill.address,
        deed_addr=pack.ownership.property_address,
    )

    llm_out, meta = complete_json(
        system=L2_ADDRESS_MATCH_SYSTEM,
        user=user_json,
        temperature=0.0,
        case_id=pack.case_id,
        task="L2",
    )

    if llm_out and isinstance(llm_out, dict) and "verdict" in llm_out:
        verdict = llm_out["verdict"].upper()
        if verdict not in ["PASS", "FAIL", "UNSURE"]:
            verdict = score_to_fallback_verdict(fuzzy_score)
        confidence = float(llm_out.get("confidence", 0.95))
        reason = str(llm_out.get("reason", "Address consistency verified for Karachi property."))
        evidence = llm_out.get("evidence", [])
        source = "mock-llm" if meta.get("provider") == "mock" else "llm"
    else:
        verdict = score_to_fallback_verdict(fuzzy_score)
        confidence = round(fuzzy_score / 100.0, 2)
        reason = f"Fuzzy score {fuzzy_score}% calculated via normalized address token comparison."
        evidence = [f"Fuzzy token score: {fuzzy_score}%"]
        source = "fuzzy-fallback"

    llm_metadata = {
        "verdict": verdict,
        "confidence": confidence,
        "reason": reason,
        "evidence": evidence,
        "fuzzy_score": fuzzy_score,
        "latency_ms": meta.get("latency_ms", 0),
        "model": meta.get("model", ""),
        "provider": meta.get("provider", ""),
    }

    return CheckResult(
        id="L2",
        key="address_match",
        name="Address consistency",
        status=verdict,
        detail=reason,
        citation="Premises Verification",
        source=source,
        data={
            "fuzzy_score": fuzzy_score,
            "cnic_address": pack.cnic.address,
            "bill_address": pack.bill.address,
            "deed_address": pack.ownership.property_address,
        },
        llm=llm_metadata,
    )


def run_shadow_checks(pack: Pack) -> list[dict[str, Any]]:
    """Run research shadow checks (R2 expiry and R3 capacity via LLM). Never affects hard verdicts."""
    settings = get_settings()
    if settings.llm_provider == "none":
        return []

    user_payload = build_shadow_checks_input(pack)
    user_json = json.dumps(user_payload, ensure_ascii=False)

    llm_out, meta = complete_json(
        system=SHADOW_CHECKS_SYSTEM,
        user=user_json,
        temperature=0.0,
        case_id=pack.case_id,
        task="shadow",
    )

    if not llm_out or not isinstance(llm_out, dict):
        return []

    # Ground truth code answers
    code_r2_ok = pack.cnic.expiry >= "2026-04-13"
    code_r3_ok = pack.system.proposed_kw <= pack.bill.sanctioned_load_kw

    llm_r2_ok = bool(llm_out.get("cnic_valid", True))
    llm_r3_ok = bool(llm_out.get("capacity_ok", True))
    reasoning = str(llm_out.get("reasoning", ""))

    shadow_results = [
        {
            "check": "R2 (CNIC Expiry)",
            "code_verdict": code_r2_ok,
            "llm_verdict": llm_r2_ok,
            "agree": code_r2_ok == llm_r2_ok,
            "note": "Agreed" if code_r2_ok == llm_r2_ok else "Disagreement",
            "reasoning": reasoning,
        },
        {
            "check": "R3 (Capacity Limit)",
            "code_verdict": code_r3_ok,
            "llm_verdict": llm_r3_ok,
            "agree": code_r3_ok == llm_r3_ok,
            "note": (
                "Agreed"
                if code_r3_ok == llm_r3_ok
                else f"LLM said capacity OK, code found {pack.system.proposed_kw} kW > {pack.bill.sanctioned_load_kw} kW → code decides"
            ),
            "reasoning": reasoning,
        },
    ]

    return shadow_results
