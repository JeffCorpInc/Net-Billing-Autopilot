"""Generate realistic synthetic OCR test documents (PDF and PNG) in data/ocr_samples/ for testing backend Auto-OCR."""

from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, PngImagePlugin
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "data" / "ocr_samples"


def _write_pdf(path: Path, title: str, subtitle: str, lines: list[tuple[str, str]], ocr_payload: dict) -> None:
    """Create a clean, readable synthetic PDF document with labeled key-value fields."""
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    # Header bar
    c.setFillColorRGB(0.06, 0.09, 0.16)
    c.rect(40, height - 100, width - 80, 60, fill=1, stroke=0)

    c.setFillColorRGB(0.96, 0.62, 0.04)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(55, height - 62, "SAMPLE SYNTHETIC DOCUMENT FOR OCR TESTING — NOT A REAL DOCUMENT")

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(55, height - 84, title)

    c.setFillColorRGB(0.2, 0.25, 0.33)
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(45, height - 122, subtitle)

    y = height - 155
    for label, value in lines:
        c.setFillColorRGB(0.1, 0.12, 0.18)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(230, y, str(value))
        y -= 24

    # Footer machine-readable OCR verification tag
    c.setFont("Courier", 6)
    c.setFillColorRGB(0.65, 0.68, 0.72)
    c.drawString(45, 40, f"NETBILL_OCR_JSON:{json.dumps(ocr_payload)}")

    c.showPage()
    c.save()


def _write_png_card(path: Path, title: str, lines: list[tuple[str, str]], ocr_text: str, ocr_payload: dict) -> None:
    """Create a synthetic 1000x630 PNG document card with embedded OCR text metadata."""
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1000, 630), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Card border & header
    draw.rectangle([20, 20, 980, 610], outline=(203, 213, 225), width=3)
    draw.rectangle([20, 20, 980, 105], fill=(15, 23, 42))
    draw.text((45, 38), "SAMPLE SYNTHETIC CARD — FOR LOCAL OCR TESTING ONLY", fill=(245, 158, 11))
    draw.text((45, 65), title, fill=(255, 255, 255))

    y = 135
    for label, value in lines:
        draw.text((50, y), f"{label}:", fill=(71, 85, 105))
        draw.text((310, y), str(value), fill=(15, 23, 42))
        y += 45

    meta = PngImagePlugin.PngInfo()
    full_text = ocr_text + f"\nNETBILL_OCR_JSON:{json.dumps(ocr_payload)}"
    meta.add_text("ocr_text", full_text)
    meta.add_text("Description", full_text)
    img.save(str(path), "PNG", pnginfo=meta)


def generate_all_ocr_samples() -> list[Path]:
    """Generate both Clean and Trap OCR sample document sets (PDFs + PNGs)."""
    created: list[Path] = []

    # =========================================================================
    # 1. CLEAN COMPLIANT PACK (Muhammad Tariq Khan — 9.9 kW Residential DHA)
    # =========================================================================
    clean_dir = SAMPLES_DIR / "clean_pack"

    cnic_lines = [
        ("Case Description", "Residential 9.9 kW Net-Billing Application — DHA Phase 6 Karachi"),
        ("Applicant Type", "residential"),
        ("Name on CNIC", "Muhammad Tariq Khan"),
        ("Father / Husband Name", "Abdul Majeed Khan"),
        ("CNIC Number", "42301-7654321-3"),
        ("CNIC Expiry Date", "2031-08-15"),
        ("Address on CNIC", "House 42-C, Phase 6, DHA, Karachi"),
    ]
    cnic_payload = {
        "fields": {
            "description": "Residential 9.9 kW Net-Billing Application — DHA Phase 6 Karachi",
            "applicant_type": "residential",
            "cnic_name": "Muhammad Tariq Khan",
            "cnic_father": "Abdul Majeed Khan",
            "cnic_no": "42301-7654321-3",
            "cnic_expiry": "2031-08-15",
            "cnic_address": "House 42-C, Phase 6, DHA, Karachi",
        },
        "docs_detected": ["cnic"],
    }
    cnic_text = "\n".join(f"{k}: {v}" for k, v in cnic_lines)
    p1 = clean_dir / "01_CNIC_Card_Tariq_Khan.pdf"
    p1_png = clean_dir / "01_CNIC_Card_Tariq_Khan.png"
    _write_pdf(p1, "PAKISTAN NATIONAL IDENTITY CARD (SYNTHETIC SAMPLE)", "Step 1 — Applicant CNIC Details", cnic_lines, cnic_payload)
    _write_png_card(p1_png, "SYNTHETIC CNIC CARD — MUHAMMAD TARIQ KHAN", cnic_lines, cnic_text, cnic_payload)
    created.extend([p1, p1_png])

    bill_lines = [
        ("Consumer Name on Bill", "M. Tariq Khan"),
        ("13-Digit Bill Reference No", "0400012345678"),
        ("Tariff Category", "A-1"),
        ("Sanctioned Load (kW)", "10.0"),
        ("Connected Load (kW)", "8.5"),
        ("Connection Phase", "3-phase"),
        ("Service Address on Bill", "H# 42-C, Ph-6 DHA Khi"),
    ]
    bill_payload = {
        "fields": {
            "bill_name": "M. Tariq Khan",
            "bill_ref": "0400012345678",
            "bill_tariff": "A-1",
            "sanctioned_kw": 10.0,
            "connected_kw": 8.5,
            "phase": "3-phase",
            "bill_address": "H# 42-C, Ph-6 DHA Khi",
        },
        "docs_detected": ["bill"],
    }
    bill_text = "\n".join(f"{k}: {v}" for k, v in bill_lines)
    p2 = clean_dir / "02_KE_Electricity_Bill.pdf"
    p2_png = clean_dir / "02_KE_Electricity_Bill.png"
    _write_pdf(p2, "K-ELECTRIC LIMITED — ELECTRICITY BILL (SYNTHETIC SAMPLE)", "Step 2 — Consumer & Load Particulars", bill_lines, bill_payload)
    _write_png_card(p2_png, "SYNTHETIC K-ELECTRIC BILL — REF 0400012345678", bill_lines, bill_text, bill_payload)
    created.extend([p2, p2_png])

    deed_lines = [
        ("Ownership Document Type", "sale_deed"),
        ("Owner Name on Deed", "Muhammad Tariq Khan"),
        ("Applicant is a Tenant", "false"),
        ("Property Address on Deed", "House 42-C, Phase 6, DHA, Karachi"),
    ]
    deed_payload = {
        "fields": {
            "ownership_type": "sale_deed",
            "owner_name": "Muhammad Tariq Khan",
            "is_tenant": False,
            "property_address": "House 42-C, Phase 6, DHA, Karachi",
        },
        "docs_detected": ["ownership"],
    }
    deed_text = "\n".join(f"{k}: {v}" for k, v in deed_lines)
    p3 = clean_dir / "03_Sale_Deed_Ownership.pdf"
    p3_png = clean_dir / "03_Sale_Deed_Ownership.png"
    _write_pdf(p3, "REGISTERED SALE DEED / PROOF OF OWNERSHIP (SAMPLE)", "Step 3 — Property Title & Premises Details", deed_lines, deed_payload)
    _write_png_card(p3_png, "SYNTHETIC SALE DEED — HOUSE 42-C DHA PHASE 6", deed_lines, deed_text, deed_payload)
    created.extend([p3, p3_png])

    spec_lines = [
        ("Proposed System Size (kW)", "9.9"),
        ("Inverter Rating (kW)", "10.0"),
        ("Panel Count", "18"),
        ("Panel Wattage (W)", "550"),
        ("Attached Documents Included", "Single-line diagram, Affidavit (Schedule-V), Vendor checklist, Inverter data sheet, Inverter settings letter"),
    ]
    spec_payload = {
        "fields": {
            "proposed_kw": 9.9,
            "inverter_kw": 10.0,
            "panel_count": 18,
            "panel_watt": 550,
        },
        "docs_detected": [
            "single_line_diagram",
            "affidavit",
            "vendor_checklist",
            "inverter_datasheet",
            "inverter_settings_letter",
        ],
    }
    spec_text = "\n".join(f"{k}: {v}" for k, v in spec_lines)
    p4 = clean_dir / "04_Solar_System_SLD_Specs.pdf"
    p4_png = clean_dir / "04_Solar_System_SLD_Specs.png"
    _write_pdf(p4, "SOLAR PV SYSTEM SPECIFICATION & SLD PACK (SAMPLE)", "Step 3 & 4 — PV Array, Inverter & Mandatory Technical Annexures", spec_lines, spec_payload)
    _write_png_card(p4_png, "SYNTHETIC SOLAR SYSTEM SPECS — 9.9 KW / 10 KW INVERTER", spec_lines, spec_text, spec_payload)
    created.extend([p4, p4_png])

    # All-in-one bundle PDF (uploading this single file fills the entire form!)
    all_clean_lines = cnic_lines + bill_lines + deed_lines + spec_lines
    all_clean_payload = {
        "fields": {
            **cnic_payload["fields"],
            **bill_payload["fields"],
            **deed_payload["fields"],
            **spec_payload["fields"],
        },
        "docs_detected": [
            "cnic",
            "bill",
            "ownership",
            "single_line_diagram",
            "affidavit",
            "vendor_checklist",
            "inverter_datasheet",
            "inverter_settings_letter",
        ],
    }
    p_bundle_clean = clean_dir / "00_Complete_Application_Bundle_Clean.pdf"
    _write_pdf(
        p_bundle_clean,
        "COMPLETE NET-BILLING APPLICATION DOSSIER (CLEAN SAMPLE)",
        "Contains CNIC + K-Electric Bill + Sale Deed + 9.9 kW Solar System Specs",
        all_clean_lines,
        all_clean_payload,
    )
    created.append(p_bundle_clean)

    # =========================================================================
    # 2. TRAP / VIOLATION PACK (Salman Siddiqui — Expired CNIC + 14.85 kW > 10 kW + Name Mismatch)
    # =========================================================================
    trap_dir = SAMPLES_DIR / "trap_pack"
    trap_lines = [
        ("Case Description", "Trap Test: 14.85 kW system on 10 kW sanctioned load + Bill Name Mismatch"),
        ("Applicant Type", "residential"),
        ("Name on CNIC", "Salman Ahmed Siddiqui"),
        ("Father / Husband Name", "Riaz Ahmed Siddiqui"),
        ("CNIC Number", "42101-9988776-1"),
        ("CNIC Expiry Date", "2024-05-10"),
        ("Address on CNIC", "Bungalow B-19, Block 13-D, Gulshan-e-Iqbal, Karachi"),
        ("Consumer Name on Bill", "Kamran Qureshi"),
        ("13-Digit Bill Reference No", "0400099887766"),
        ("Tariff Category", "A-1"),
        ("Sanctioned Load (kW)", "10.0"),
        ("Connected Load (kW)", "11.5"),
        ("Connection Phase", "1-phase"),
        ("Service Address on Bill", "B-19, Blk 13-D, Gulshan-e-Iqbal, Karachi"),
        ("Ownership Document Type", "sale_deed"),
        ("Owner Name on Deed", "Salman Ahmed Siddiqui"),
        ("Applicant is a Tenant", "false"),
        ("Property Address on Deed", "Bungalow B-19, Block 13-D, Gulshan-e-Iqbal, Karachi"),
        ("Proposed System Size (kW)", "14.85"),
        ("Inverter Rating (kW)", "15.0"),
        ("Panel Count", "27"),
        ("Panel Wattage (W)", "550"),
    ]
    trap_payload = {
        "fields": {
            "description": "Trap Test: 14.85 kW system on 10 kW sanctioned load + Bill Name Mismatch",
            "applicant_type": "residential",
            "cnic_name": "Salman Ahmed Siddiqui",
            "cnic_father": "Riaz Ahmed Siddiqui",
            "cnic_no": "42101-9988776-1",
            "cnic_expiry": "2024-05-10",
            "cnic_address": "Bungalow B-19, Block 13-D, Gulshan-e-Iqbal, Karachi",
            "bill_name": "Kamran Qureshi",
            "bill_ref": "0400099887766",
            "bill_tariff": "A-1",
            "sanctioned_kw": 10.0,
            "connected_kw": 11.5,
            "phase": "1-phase",
            "bill_address": "B-19, Blk 13-D, Gulshan-e-Iqbal, Karachi",
            "ownership_type": "sale_deed",
            "owner_name": "Salman Ahmed Siddiqui",
            "is_tenant": False,
            "property_address": "Bungalow B-19, Block 13-D, Gulshan-e-Iqbal, Karachi",
            "proposed_kw": 14.85,
            "inverter_kw": 15.0,
            "panel_count": 27,
            "panel_watt": 550,
        },
        "docs_detected": ["cnic", "bill", "ownership", "affidavit", "inverter_datasheet"],
    }
    p_bundle_trap = trap_dir / "00_Complete_Application_Bundle_Trap.pdf"
    _write_pdf(
        p_bundle_trap,
        "COMPLETE NET-BILLING APPLICATION DOSSIER (TRAP / VIOLATIONS SAMPLE)",
        "Contains Expired CNIC + Name Mismatch + 1-Phase + 14.85 kW > 10 kW Sanctioned Load",
        trap_lines,
        trap_payload,
    )
    created.append(p_bundle_trap)

    return created


if __name__ == "__main__":
    paths = generate_all_ocr_samples()
    print(f"Generated {len(paths)} synthetic OCR sample files in {SAMPLES_DIR}:")
    for p in paths:
        print(" -", p.relative_to(BASE_DIR))
