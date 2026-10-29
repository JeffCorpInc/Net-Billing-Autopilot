"""OCR normalization utilities for CNIC, K-Electric Bill, Sale Deed, and Solar System fields."""

from __future__ import annotations

import re
from datetime import datetime

# Digit character confusion map from CNIC_OCR_PROMPT.md (applied only to numeric/ID fields)
_DIGIT_CHAR_MAP = str.maketrans({
    "O": "0",
    "o": "0",
    "D": "0",
    "Q": "0",
    "I": "1",
    "l": "1",
    "|": "1",
    "!": "1",
    "Z": "2",
    "z": "2",
    "S": "5",
    "s": "5",
    "G": "6",
    "B": "8",
})


def fix_ocr_digits(raw: str) -> str:
    """Replace common OCR letter-for-digit confusions in numeric fields."""
    if not raw:
        return ""
    return raw.translate(_DIGIT_CHAR_MAP)


def normalize_cnic(raw: str) -> str:
    """Normalize a raw CNIC string into standard NADRA format XXXXX-XXXXXXX-X."""
    if not raw:
        return ""
    cleaned = fix_ocr_digits(raw.strip())
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) == 13:
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
    return raw.strip()


def normalize_bill_ref(raw: str) -> str:
    """Normalize a K-Electric 13-digit consumer reference number."""
    if not raw:
        return ""
    cleaned = fix_ocr_digits(raw.strip())
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) >= 13:
        return digits[:13]
    return digits or raw.strip()


def normalize_date(raw: str) -> str:
    """Parse DD.MM.YYYY, DD-MM-YYYY, DD/MM/YYYY, or YYYY-MM-DD into ISO YYYY-MM-DD."""
    if not raw:
        return ""
    text = raw.strip()
    # Apply digit fixes only to segments that look numeric
    text_fixed = re.sub(r"[OoDQIl|!ZzSsGB]", lambda m: _DIGIT_CHAR_MAP.get(ord(m.group(0)), m.group(0)), text)

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d %b %Y", "%d %B %Y"):
        try:
            dt = datetime.strptime(text_fixed, fmt)
            if 1920 <= dt.year <= 2060:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Regex fallback for embedded date
    m_iso = re.search(r"\b(20\d{2}|19\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})\b", text_fixed)
    if m_iso:
        y, mo, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m_dmy = re.search(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](20\d{2}|19\d{2})\b", text_fixed)
    if m_dmy:
        d, mo, y = int(m_dmy.group(1)), int(m_dmy.group(2)), int(m_dmy.group(3))
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return text


def normalize_person_name(raw: str) -> str:
    """Clean OCR artifacts from person names while preserving Pakistani spelling and initials."""
    if not raw:
        return ""
    cleaned = re.sub(r"[^A-Za-z\s.\-']", " ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-")
    if not cleaned:
        return ""
    return " ".join(
        w if (w.isupper() and len(w) <= 3) else w.capitalize()
        for w in cleaned.split(" ")
    )


def normalize_address(raw: str) -> str:
    """Collapse extra whitespace and stray linebreaks in extracted addresses."""
    if not raw:
        return ""
    cleaned = re.sub(r"\s+", " ", raw).strip(" ,;:-")
    return cleaned


def normalize_float(raw: str | float | int | None) -> float | None:
    """Extract a clean float value (e.g. '10.0 kW' -> 10.0)."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = fix_ocr_digits(str(raw))
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def normalize_int(raw: str | int | float | None) -> int | None:
    """Extract a clean integer value (e.g. '18 Panels' -> 18)."""
    val = normalize_float(raw)
    return int(round(val)) if val is not None else None


def normalize_phase(raw: str) -> str:
    """Normalize supply phase into '3-phase' or '1-phase'."""
    if not raw:
        return "3-phase"
    low = raw.lower()
    if "1" in low or "single" in low:
        return "1-phase"
    return "3-phase"


def normalize_ownership_type(raw: str) -> str:
    """Map extracted ownership document type to 'sale_deed', 'allotment_letter', or 'lease_agreement'."""
    if not raw:
        return "sale_deed"
    low = raw.lower()
    if "lease" in low or "rent" in low or "tenan" in low:
        return "lease_agreement"
    if "allot" in low or "transfer" in low:
        return "allotment_letter"
    return "sale_deed"
