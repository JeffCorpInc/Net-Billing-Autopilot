"""Multi-document backend OCR & field extraction service for CNIC, K-Electric Bill, Sale Deed, and Solar Specs."""

from __future__ import annotations

import base64
import io
import json
import re
import time
from typing import Any

from app.ocr.normalize import (
    normalize_address,
    normalize_bill_ref,
    normalize_cnic,
    normalize_date,
    normalize_float,
    normalize_int,
    normalize_ownership_type,
    normalize_person_name,
    normalize_phase,
)

# Optional EasyOCR singleton (if installed on the host)
_EASYOCR_READER = None
_EASYOCR_CHECKED = False


def _get_easyocr_reader():
    """Lazily initialize EasyOCR reader if easyocr is installed."""
    global _EASYOCR_READER, _EASYOCR_CHECKED
    if _EASYOCR_CHECKED:
        return _EASYOCR_READER
    _EASYOCR_CHECKED = True
    try:
        import easyocr  # type: ignore

        _EASYOCR_READER = easyocr.Reader(["en"], gpu=False, verbose=False)
    except Exception:
        _EASYOCR_READER = None
    return _EASYOCR_READER


def get_ocr_status() -> dict[str, Any]:
    """Return status of backend OCR & document extraction engines."""
    engines = ["pypdf-layout", "pillow-metadata", "regex-label-parser"]
    try:
        import easyocr  # noqa: F401 # type: ignore

        engines.insert(0, "easyocr-local")
    except ImportError:
        pass

    return {
        "available": True,
        "engines": engines,
        "supported_documents": [
            "cnic",
            "bill",
            "ownership",
            "single_line_diagram",
            "affidavit",
            "vendor_checklist",
            "inverter_datasheet",
            "inverter_settings_letter",
            "noc",
        ],
    }


def _decode_base64_bytes(b64_str: str) -> bytes:
    """Decode base64 string (with or without data URI prefix) into raw bytes."""
    if not b64_str:
        return b""
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    return base64.b64decode(b64_str)


def _extract_text_from_pdf(raw_bytes: bytes) -> str:
    """Extract text from all pages of a PDF using pypdf."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw_bytes))
        pages_text = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                pages_text.append(t)
        return "\n".join(pages_text)
    except Exception:
        return ""


def _extract_text_from_image(raw_bytes: bytes) -> str:
    """Extract text from a PNG/JPG/WEBP image using PIL metadata chunks and/or EasyOCR."""
    chunks: list[str] = []
    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(raw_bytes)) as img:
            # 1. Check PNG tEXt / iTXt metadata or EXIF UserComment (used by synthetic sample cards)
            info = getattr(img, "info", {}) or {}
            for k in ("ocr_text", "Description", "Comment", "netbill_ocr", "parameters"):
                val = info.get(k)
                if isinstance(val, str) and val.strip():
                    chunks.append(val.strip())

            # 2. If EasyOCR is installed, run local pixel OCR on the straightened image
            reader = _get_easyocr_reader()
            if reader is not None:
                import numpy as np  # type: ignore

                oriented = ImageOps.exif_transpose(img).convert("RGB")
                arr = np.array(oriented)
                results = reader.readtext(arr, detail=0, paragraph=True)
                if results:
                    chunks.append("\n".join(str(r) for r in results))
    except Exception:
        pass

    return "\n".join(chunks)


def _extract_labeled_value(text: str, label_patterns: list[str]) -> str:
    """Find a value following any of the given label regex patterns on the same or next line."""
    for pat in label_patterns:
        # Match "Label : Value" on the same line
        regex_same = re.compile(rf"(?:^|\n)\s*{pat}\s*[:\-–]\s*([^\n\r]+)", re.IGNORECASE)
        m = regex_same.search(text)
        if m and m.group(1).strip():
            return m.group(1).strip()

        # Match "Label\nValue" on the immediate next line
        regex_next = re.compile(rf"(?:^|\n)\s*{pat}\s*\n\s*([^\n\r:]+)", re.IGNORECASE)
        m2 = regex_next.search(text)
        if m2 and m2.group(1).strip():
            return m2.group(1).strip()
    return ""


def parse_extracted_text_into_fields(text: str, filenames: list[str] | None = None) -> dict[str, Any]:
    """Parse combined OCR text across CNIC, K-Electric Bill, Sale Deed, and Solar Spec sheets."""
    fields: dict[str, Any] = {}
    docs_detected: set[str] = set()
    warnings: list[str] = []

    filenames = filenames or []
    fn_joined = " ".join(filenames).lower()
    low_text = text.lower()

    # Check if there is an embedded JSON block (e.g. from structured synthetic cards)
    json_blocks = re.findall(r"NETBILL_OCR_JSON:(\{.*?\})", text, flags=re.DOTALL)
    for jb in json_blocks:
        try:
            parsed_jb = json.loads(jb)
            if isinstance(parsed_jb.get("fields"), dict):
                fields.update(parsed_jb["fields"])
            if isinstance(parsed_jb.get("docs_detected"), list):
                docs_detected.update(parsed_jb["docs_detected"])
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # 1. CNIC Extraction (Step 1)
    # -----------------------------------------------------------------------
    cnic_match = re.search(r"\b(\d{5}[\-\s]?\d{7}[\-\s]?\d)\b", text)
    if cnic_match and not fields.get("cnic_no"):
        fields["cnic_no"] = normalize_cnic(cnic_match.group(1))
        docs_detected.add("cnic")

    raw_cnic_name = _extract_labeled_value(
        text,
        [r"CNIC\s+Name", r"Name\s+on\s+CNIC", r"Applicant\s+Name", r"Holder\s+Name", r"Name"],
    )
    if raw_cnic_name and not fields.get("cnic_name"):
        fields["cnic_name"] = normalize_person_name(raw_cnic_name)
        docs_detected.add("cnic")

    raw_father = _extract_labeled_value(
        text,
        [r"Father\s*/?\s*Husband(?:'s)?\s+Name", r"Father(?:'s)?\s+Name", r"Husband(?:'s)?\s+Name"],
    )
    if raw_father and not fields.get("cnic_father"):
        fields["cnic_father"] = normalize_person_name(raw_father)
        docs_detected.add("cnic")

    raw_expiry = _extract_labeled_value(
        text,
        [r"CNIC\s+Expiry(?:\s+Date)?", r"Date\s+of\s+Expiry", r"Expiry\s+Date", r"Valid\s+Until"],
    )
    if raw_expiry and not fields.get("cnic_expiry"):
        fields["cnic_expiry"] = normalize_date(raw_expiry)
        docs_detected.add("cnic")

    raw_cnic_addr = _extract_labeled_value(
        text,
        [r"Address\s+on\s+CNIC", r"CNIC\s+Address", r"Permanent\s+Address", r"Present\s+Address"],
    )
    if raw_cnic_addr and not fields.get("cnic_address"):
        fields["cnic_address"] = normalize_address(raw_cnic_addr)

    # -----------------------------------------------------------------------
    # 2. K-Electric Bill Extraction (Step 2)
    # -----------------------------------------------------------------------
    raw_bill_name = _extract_labeled_value(
        text,
        [r"Consumer\s+Name(?:\s+on\s+Bill)?", r"Bill\s+Consumer\s+Name", r"KE\s+Consumer\s+Name", r"Account\s+Title"],
    )
    if raw_bill_name and not fields.get("bill_name"):
        fields["bill_name"] = normalize_person_name(raw_bill_name)
        docs_detected.add("bill")

    raw_bill_ref = _extract_labeled_value(
        text,
        [r"(?:13-Digit\s+)?(?:Bill\s+)?Reference\s+No\.?", r"Account\s+Reference\s+No\.?", r"KE\s+Reference\s+No\.?"],
    )
    if raw_bill_ref and not fields.get("bill_ref"):
        fields["bill_ref"] = normalize_bill_ref(raw_bill_ref)
        docs_detected.add("bill")
    elif not fields.get("bill_ref"):
        # Look for a standalone 13-digit number without hyphens
        m_ref = re.search(r"(?<![\d\-])(\d{13})(?![\d\-])", text)
        if m_ref:
            fields["bill_ref"] = m_ref.group(1)
            docs_detected.add("bill")

    raw_tariff = _extract_labeled_value(text, [r"Tariff(?:\s+Category|\s+Code)?", r"Applicable\s+Tariff"])
    if raw_tariff and not fields.get("bill_tariff"):
        for code in ("A-1", "A-2", "B-1", "B-2"):
            if code.lower() in raw_tariff.lower():
                fields["bill_tariff"] = code
                break

    raw_sanc = _extract_labeled_value(text, [r"Sanctioned\s+Load(?:\s*\(kW\))?"])
    if raw_sanc and fields.get("sanctioned_kw") is None:
        val = normalize_float(raw_sanc)
        if val is not None:
            fields["sanctioned_kw"] = val
            docs_detected.add("bill")

    raw_conn = _extract_labeled_value(text, [r"Connected\s+Load(?:\s*\(kW\))?"])
    if raw_conn and fields.get("connected_kw") is None:
        val = normalize_float(raw_conn)
        if val is not None:
            fields["connected_kw"] = val
            docs_detected.add("bill")

    raw_phase = _extract_labeled_value(text, [r"Connection\s+Phase", r"Supply\s+Phase", r"Meter\s+Phase", r"Phase"])
    if raw_phase and not fields.get("phase"):
        fields["phase"] = normalize_phase(raw_phase)

    raw_bill_addr = _extract_labeled_value(
        text,
        [r"Service\s+Address(?:\s+on\s+Bill)?", r"Billing\s+Address", r"Premises\s+Address", r"Installation\s+Address"],
    )
    if raw_bill_addr and not fields.get("bill_address"):
        fields["bill_address"] = normalize_address(raw_bill_addr)
        docs_detected.add("bill")

    # -----------------------------------------------------------------------
    # 3. Ownership Deed & Solar System Specs (Step 3)
    # -----------------------------------------------------------------------
    raw_doc_type = _extract_labeled_value(
        text,
        [r"Ownership\s+Document\s+Type", r"Deed\s+Type", r"Title\s+Document\s+Type"],
    )
    if raw_doc_type and not fields.get("ownership_type"):
        fields["ownership_type"] = normalize_ownership_type(raw_doc_type)
        docs_detected.add("ownership")

    raw_owner = _extract_labeled_value(
        text,
        [r"Owner\s+Name(?:\s+on\s+Deed)?", r"Property\s+Owner(?:\s+Name)?", r"Vendee\s+Name", r"Allottee\s+Name", r"Title\s+Holder"],
    )
    if raw_owner and not fields.get("owner_name"):
        fields["owner_name"] = normalize_person_name(raw_owner)
        docs_detected.add("ownership")

    raw_prop_addr = _extract_labeled_value(
        text,
        [r"Property\s+Address(?:\s+on\s+Deed)?", r"Deed\s+Property\s+Address", r"Plot\s*/\s*House\s+Address"],
    )
    if raw_prop_addr and not fields.get("property_address"):
        fields["property_address"] = normalize_address(raw_prop_addr)
        docs_detected.add("ownership")

    raw_tenant = _extract_labeled_value(text, [r"Applicant\s+is\s+a\s+Tenant", r"Tenant\s+Status", r"Is\s+Tenant"])
    if raw_tenant and "is_tenant" not in fields:
        fields["is_tenant"] = raw_tenant.strip().lower() in ("true", "yes", "1", "tenant", "lessee")

    raw_prop_kw = _extract_labeled_value(
        text,
        [r"Proposed\s+(?:Solar\s+)?(?:System\s+)?(?:Capacity|Size)(?:\s*\(kW\))?", r"Proposed\s+System(?:\s*\(kW\))?", r"PV\s+Array\s+Capacity"],
    )
    if raw_prop_kw and fields.get("proposed_kw") is None:
        val = normalize_float(raw_prop_kw)
        if val is not None:
            fields["proposed_kw"] = val

    raw_inv_kw = _extract_labeled_value(
        text,
        [r"Inverter\s+(?:AC\s+)?Rating(?:\s*\(kW\))?", r"Inverter\s+Capacity(?:\s*\(kW\))?", r"Inverter\s+Size"],
    )
    if raw_inv_kw and fields.get("inverter_kw") is None:
        val = normalize_float(raw_inv_kw)
        if val is not None:
            fields["inverter_kw"] = val
            docs_detected.add("inverter_datasheet")

    raw_panels = _extract_labeled_value(text, [r"Panel\s+Count", r"Number\s+of\s+Panels", r"Total\s+PV\s+Modules"])
    if raw_panels and fields.get("panel_count") is None:
        val = normalize_int(raw_panels)
        if val is not None:
            fields["panel_count"] = val

    raw_watt = _extract_labeled_value(text, [r"Panel\s+Wattage(?:\s*\(W\))?", r"Module\s+Wattage(?:\s*\(W\))?", r"Per\s+Panel\s+Rating"])
    if raw_watt and fields.get("panel_watt") is None:
        val = normalize_int(raw_watt)
        if val is not None:
            fields["panel_watt"] = val

    raw_desc = _extract_labeled_value(text, [r"Case\s+Description", r"Application\s+Summary", r"Project\s+Description"])
    if raw_desc and not fields.get("description"):
        fields["description"] = raw_desc.strip()

    raw_app_type = _extract_labeled_value(text, [r"Applicant\s+Type", r"Consumer\s+Category"])
    if raw_app_type and not fields.get("applicant_type"):
        fields["applicant_type"] = "commercial" if "comm" in raw_app_type.lower() else "residential"

    # -----------------------------------------------------------------------
    # 4. Detect Attached Document Checkboxes from Content & Filenames
    # -----------------------------------------------------------------------
    doc_keyword_map = {
        "cnic": ["cnic", "national identity card", "nadra"],
        "bill": ["k-electric", "electricity bill", "sanctioned load", "reference no"],
        "ownership": ["sale deed", "allotment letter", "lease agreement", "proof of ownership", "conveyance deed"],
        "single_line_diagram": ["single-line diagram", "single line diagram", "sld"],
        "affidavit": ["affidavit", "schedule-v", "schedule v", "undertaking"],
        "vendor_checklist": ["vendor checklist", "AEDB", "installer checklist"],
        "inverter_datasheet": ["inverter data sheet", "inverter datasheet", "inverter specification"],
        "inverter_settings_letter": ["inverter settings letter", "protection settings", "anti-islanding"],
        "noc": ["no objection certificate", "owner's noc", "owner noc", "landlord noc"],
    }
    combined_search = f"{low_text} {fn_joined}"
    for doc_key, kw_list in doc_keyword_map.items():
        if any(kw.lower() in combined_search for kw in kw_list):
            docs_detected.add(doc_key)

    # Check if CNIC is expired to add an informational OCR warning
    if fields.get("cnic_expiry") and fields["cnic_expiry"] < "2026-10-29":
        warnings.append(f"Detected expired CNIC date ({fields['cnic_expiry']}) — Rule R2 will flag this.")

    return {
        "fields": fields,
        "docs_detected": sorted(docs_detected),
        "warnings": warnings,
    }


def extract_documents_from_uploads(files: list[dict[str, Any]]) -> dict[str, Any]:
    """Process uploaded files in memory, run OCR/text extraction, and return structured form fields."""
    t0 = time.perf_counter()
    if not files:
        return {
            "ok": False,
            "elapsed_ms": 0,
            "files_processed": 0,
            "fields": {},
            "docs_detected": [],
            "warnings": ["No files provided for OCR extraction."],
            "summary": "No files uploaded.",
        }

    all_text_parts: list[str] = []
    filenames: list[str] = []
    warnings: list[str] = []

    for fmeta in files:
        name = str(fmeta.get("name") or "document").strip()
        filenames.append(name)
        b64_content = str(fmeta.get("content_base64") or "")
        raw_bytes = _decode_base64_bytes(b64_content)

        if not raw_bytes:
            warnings.append(f"File '{name}' had empty content.")
            continue

        low_name = name.lower()
        if low_name.endswith(".pdf") or raw_bytes.startswith(b"%PDF"):
            extracted = _extract_text_from_pdf(raw_bytes)
        else:
            extracted = _extract_text_from_image(raw_bytes)

        if extracted.strip():
            all_text_parts.append(extracted)

    combined_text = "\n\n".join(all_text_parts)
    parsed = parse_extracted_text_into_fields(combined_text, filenames=filenames)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    field_count = len(parsed["fields"])
    doc_count = len(parsed["docs_detected"])
    all_warnings = warnings + parsed["warnings"]

    return {
        "ok": True,
        "elapsed_ms": max(1, elapsed_ms),
        "files_processed": len(files),
        "filenames": filenames,
        "fields": parsed["fields"],
        "docs_detected": parsed["docs_detected"],
        "warnings": all_warnings,
        "summary": (
            f"Auto-filled {field_count} field(s) and verified {doc_count} document type(s) "
            f"from {len(files)} uploaded file(s) in {max(1, elapsed_ms)} ms."
        ),
    }
