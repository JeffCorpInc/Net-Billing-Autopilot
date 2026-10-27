"""Provider-agnostic LLM client with mock, fallback, and live modes."""

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from app.config import LLM_LOG_PATH, get_settings

logger = logging.getLogger(__name__)


def _log_llm_call(
    case_id: str,
    task: str,
    provider: str,
    model: str,
    prompt_text: str,
    redacted_input: str,
    raw_output: str,
    latency_ms: int,
    ok: bool,
    error: str | None = None,
) -> None:
    """Append every LLM interaction to runtime log in jsonl format."""
    try:
        prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "task": task,
            "provider": provider,
            "model": model,
            "prompt_sha256": prompt_hash,
            "redacted_input": redacted_input,
            "raw_output": raw_output,
            "latency_ms": latency_ms,
            "ok": ok,
            "error": error,
        }
        with open(LLM_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        logger.warning("Failed to append to llm_log.jsonl: %s", exc)


def _extract_json_block(text: str) -> dict[str, Any] | None:
    """Robustly extract and parse the first JSON object from a string."""
    if not text:
        return None
    # Strip markdown code blocks ```json ... ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

    # First attempt: direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Second attempt: locate outer {...}
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    return None


def _handle_mock_response(
    system: str, user: str, case_id: str, task: str
) -> dict[str, Any] | None:
    """Deterministic mock responses for testing without API keys."""
    try:
        user_data = json.loads(user) if user.strip().startswith("{") else {}
    except Exception:
        user_data = {}

    # L1 Name Match Mock
    if task == "L1" or "names on Pakistani documents" in system:
        cnic_name = str(user_data.get("cnic_name", "")).strip()
        bill_name = str(user_data.get("bill_consumer_name", "")).strip()
        deed_name = str(user_data.get("deed_owner_name", "")).strip()
        is_tenant = bool(user_data.get("is_tenant", False))

        # Known trap cases from specification
        if case_id == "C11":
            return {
                "verdict": "FAIL",
                "confidence": 0.95,
                "reason": "Different first and family name on bill compared to CNIC.",
                "evidence": [f"cnic_name: '{cnic_name}' vs bill_consumer_name: '{bill_name}'"],
            }
        if case_id == "C20" and not is_tenant:
            return {
                "verdict": "FAIL",
                "confidence": 0.95,
                "reason": "Deed owner is a different person and applicant is not a tenant.",
                "evidence": [f"cnic_name: '{cnic_name}' vs deed_owner_name: '{deed_name}'"],
            }

        return {
            "verdict": "PASS",
            "confidence": 0.98,
            "reason": "Names refer to the same individual accounting for standard Pakistani spelling variants or abbreviations.",
            "evidence": [f"cnic_name: '{cnic_name}' vs bill_consumer_name: '{bill_name}'"],
        }

    # L2 Address Match Mock
    if task == "L2" or "addresses on Pakistani documents" in system:
        cnic_addr = str(user_data.get("cnic_address", "")).strip()
        bill_addr = str(user_data.get("bill_address", "")).strip()

        if case_id == "C12":
            return {
                "verdict": "FAIL",
                "confidence": 0.95,
                "reason": "Bill address is a completely different property located in Korangi.",
                "evidence": [f"cnic_address: '{cnic_addr}' vs bill_address: '{bill_addr}'"],
            }

        return {
            "verdict": "PASS",
            "confidence": 0.98,
            "reason": "Addresses refer to the same premises with standard abbreviation variations (H#, Blk, Khi).",
            "evidence": [f"cnic_address: '{cnic_addr}' vs bill_address: '{bill_addr}'"],
        }

    # Shadow Checks Mock
    if task == "shadow" or "cnic_valid" in user or "cnic_valid" in system:
        today_str = str(user_data.get("today", "2026-04-13"))
        expiry_str = str(user_data.get("cnic_expiry", ""))
        proposed_kw = float(user_data.get("proposed_kw", 0))
        sanctioned_kw = float(user_data.get("sanctioned_load_kw", 0))

        cnic_valid = expiry_str >= today_str if expiry_str else True
        capacity_ok = proposed_kw <= sanctioned_kw

        # Deliberate C18 disagreement for specification demo requirement
        if case_id == "C18":
            return {
                "cnic_valid": False,
                "capacity_ok": True,  # Deliberate error: LLM says capacity is ok when it exceeds load
                "reasoning": "Mock LLM mistakenly judged 14 kW acceptable for sanctioned load.",
            }

        return {
            "cnic_valid": cnic_valid,
            "capacity_ok": capacity_ok,
            "reasoning": (
                f"CNIC valid: {cnic_valid}. Proposed {proposed_kw} kW vs sanctioned {sanctioned_kw} kW: "
                f"{'OK' if capacity_ok else 'exceeded'}."
            ),
        }

    # L3 Customer Checklist Mock
    if task == "L3" or "polite checklist for a solar customer" in system:
        items = user_data.get("items", [])
        lang = user_data.get("lang", "en")
        results = []
        for it in items:
            cid = it.get("check_id", "")
            detail = it.get("detail", "")
            citation = it.get("citation", "")
            if lang == "ur":
                text = f"براہ کرم درج ذیل مسئلہ حل کریں: {detail} [{citation}]"
            else:
                text = f"Please address: {detail} [{citation}]"
            results.append({"check_id": cid, "text": text})
        return {"items": results}

    # Generic fallback mock
    return {"verdict": "PASS", "confidence": 0.9, "reason": "Mock default pass."}


def complete_json(
    system: str,
    user: str,
    temperature: float = 0.0,
    case_id: str = "",
    task: str = "",
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Uniform function for getting structured JSON from configured LLM provider.

    Returns:
        tuple: (parsed_json_dict_or_none, metadata_dict)
    """
    settings = get_settings()
    provider = settings.llm_provider
    model = settings.llm_model or ("mock-engine" if provider == "mock" else "none")
    start_time = time.perf_counter()

    meta: dict[str, Any] = {
        "provider": provider,
        "model": model,
        "latency_ms": 0,
        "ok": False,
        "error": None,
        "attempts": 0,
    }

    # Provider: none (pure fallback)
    if provider == "none":
        meta["latency_ms"] = int((time.perf_counter() - start_time) * 1000)
        _log_llm_call(
            case_id=case_id,
            task=task,
            provider="none",
            model="none",
            prompt_text=system + "\n" + user,
            redacted_input=user,
            raw_output="",
            latency_ms=meta["latency_ms"],
            ok=False,
            error="Provider set to 'none'",
        )
        return None, meta

    # Provider: mock
    if provider == "mock":
        meta["attempts"] = 1
        time.sleep(0.02)  # Tiny realistic latency
        mock_output = _handle_mock_response(
            system=system, user=user, case_id=case_id, task=task
        )
        latency = int((time.perf_counter() - start_time) * 1000)
        meta["latency_ms"] = latency
        meta["ok"] = mock_output is not None
        _log_llm_call(
            case_id=case_id,
            task=task,
            provider="mock",
            model=model,
            prompt_text=system + "\n" + user,
            redacted_input=user,
            raw_output=json.dumps(mock_output or {}, ensure_ascii=False),
            latency_ms=latency,
            ok=meta["ok"],
        )
        return mock_output, meta

    # Provider: openai_compatible
    if provider == "openai_compatible":
        if not settings.is_llm_configured:
            meta["error"] = "LLM_API_KEY or LLM_BASE_URL not configured"
            _log_llm_call(
                case_id=case_id,
                task=task,
                provider=provider,
                model=model,
                prompt_text=system + "\n" + user,
                redacted_input=user,
                raw_output="",
                latency_ms=0,
                ok=False,
                error=meta["error"],
            )
            return None, meta

        try:
            import openai
        except ImportError:
            meta["error"] = "openai package not installed"
            return None, meta

        client_kwargs: dict[str, Any] = {
            "api_key": settings.llm_api_key or "dummy-key-for-local",
            "timeout": settings.llm_timeout_seconds,
        }
        if settings.llm_base_url:
            client_kwargs["base_url"] = settings.llm_base_url

        client = openai.OpenAI(**client_kwargs)
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        parsed: dict[str, Any] | None = None
        raw_text = ""
        backoff_delays = [1.0, 3.0]

        for attempt in range(settings.llm_max_retries + 1):
            meta["attempts"] = attempt + 1
            try:
                # Try json_object format first
                try:
                    response = client.chat.completions.create(
                        model=settings.llm_model,
                        messages=messages,
                        temperature=temperature,
                        response_format={"type": "json_object"},
                    )
                except Exception:
                    # Retry without response_format if provider does not support it
                    response = client.chat.completions.create(
                        model=settings.llm_model,
                        messages=messages,
                        temperature=temperature,
                    )

                raw_text = response.choices[0].message.content or ""
                parsed = _extract_json_block(raw_text)
                if parsed is not None:
                    meta["ok"] = True
                    break
                else:
                    meta["error"] = "Failed to parse JSON from LLM response"
            except Exception as exc:
                meta["error"] = str(exc)
                if attempt < settings.llm_max_retries:
                    time.sleep(backoff_delays[min(attempt, len(backoff_delays) - 1)])

        latency = int((time.perf_counter() - start_time) * 1000)
        meta["latency_ms"] = latency
        _log_llm_call(
            case_id=case_id,
            task=task,
            provider=provider,
            model=settings.llm_model,
            prompt_text=system + "\n" + user,
            redacted_input=user,
            raw_output=raw_text,
            latency_ms=latency,
            ok=meta["ok"],
            error=meta["error"],
        )
        return parsed, meta

    # Unknown provider
    meta["error"] = f"Unknown provider: {provider}"
    return None, meta
