"""Generate exactly 21 deterministic net-billing cases (C01-C21) and ground truth expected.csv."""

import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

# Seed for reproducibility
random.seed(722)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CASES_DIR = DATA_DIR / "cases"
EXPECTED_CSV = DATA_DIR / "expected.csv"

CASES_DIR.mkdir(parents=True, exist_ok=True)

# Curated Pakistani names and Karachi addresses
PAKISTANI_NAMES = [
    "Muhammad Usman",
    "Mohammad Hamza Qureshi",
    "Syed Ali Raza",
    "Bilal Ahmed",
    "Zubair Khan",
    "Farhan Akhtar",
    "Tariq Mahmood",
    "Adeel Memon",
    "Kashif Siddiqui",
    "Imran Ashraf",
    "Omer Farooq",
    "Saad Rafiq",
    "Waqas Ali",
    "Zeeshan Haider",
    "Kamran Akram",
    "Shahid Afridi",
    "Asif Mehmood",
    "Babar Azam",
    "Shaheen Afridi",
    "Haris Rauf",
    "Naseem Shah",
    "Fakhar Zaman",
    "Shadab Khan",
    "Iftikhar Ahmed",
    "Mohammad Rizwan",
    "Sarfaraz Ahmed",
    "Shoaib Malik",
    "Junaid Khan",
    "Wahab Riaz",
    "Sohail Tanvir",
]

FATHER_NAMES = [
    "Abdul Rehman",
    "Ghulam Nabi",
    "Syed Mehmood Ali",
    "Bashir Ahmed",
    "Muhammad Yaqoob",
    "Akhtar Hussain",
    "Mahmood Ul Hassan",
    "Abdul Sattar",
    "Muhammad Siddique",
    "Muhammad Ashraf",
]

KARACHI_ADDRESSES = [
    "House 45-A, PECHS Block 2, Karachi",
    "Flat 302, Al-Ghafoor Tower, Gulshan-e-Iqbal Block 13-D, Karachi",
    "B-142, Block 5, Clifton, Karachi",
    "Plot 88-C, 11th Commercial Street, DHA Phase 2 Ext, Karachi",
    "House 12, Street 4, Sector 11-A, North Nazimabad, Karachi",
    "Apartment 5-B, Executive Heights, Gulistan-e-Johar Block 7, Karachi",
    "Plot 14/B, Block A, Sindhi Muslim Cooperative Housing Society, Karachi",
    "House 78, Dhoraji Colony, Karachi",
    "Plot 220, Sector 31-D, Korangi Industrial Area, Karachi",
    "House 19-C, Khayaban-e-Shamsheer, DHA Phase 5, Karachi",
    "B-24, Federal B Area Block 14, Karachi",
    "House 55, Malir Cantt Sector F, Karachi",
    "Flat G-1, Palm Residency, Scheme 33, Karachi",
    "Plot 105, Mehran Town, Sector 6-F, Korangi, Karachi",
    "House 8, Street 2, Bahadurabad, Karachi",
]

BASE_DOCS = [
    "cnic",
    "bill",
    "ownership",
    "single_line_diagram",
    "affidavit",
    "vendor_checklist",
    "inverter_datasheet",
    "inverter_settings_letter",
]

CASE_SPECS = [
    {
        "id": "C01",
        "category": "clean",
        "desc": "Clean residential pack, 8 kW on 10 kW sanctioned load, all documents consistent",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "expected_fails": [],
    },
    {
        "id": "C02",
        "category": "clean",
        "desc": "Clean residential pack, proposed load exactly equals sanctioned load (5 kW = 5 kW)",
        "app_type": "residential",
        "proposed_kw": 5.0,
        "sanctioned_kw": 5.0,
        "connected_kw": 5.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "expected_fails": [],
    },
    {
        "id": "C03",
        "category": "clean",
        "desc": "Clean pack with standard Pakistani name abbreviation variant (Muhammad Usman vs M. Usman)",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "name_variant": ("Muhammad Usman", "M. Usman", "Muhammad Usman"),
        "expected_fails": [],
    },
    {
        "id": "C04",
        "category": "clean",
        "desc": "Clean pack with standard Karachi address abbreviation (House 45-A, PECHS Block 2 vs H# 45-A PECHS Blk-2 Khi)",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "addr_variant": (
            "House 45-A, PECHS Block 2, Karachi",
            "H# 45-A PECHS Blk-2 Khi",
            "House 45-A, PECHS Block 2, Karachi",
        ),
        "expected_fails": [],
    },
    {
        "id": "C05",
        "category": "clean",
        "desc": "Clean pack with spelling variant on deed (Mohammad Hamza Qureshi vs Muhammad Hamza Qureshi)",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "name_variant": (
            "Mohammad Hamza Qureshi",
            "Mohammad Hamza Qureshi",
            "Muhammad Hamza Qureshi",
        ),
        "expected_fails": [],
    },
    {
        "id": "C06",
        "category": "clean",
        "desc": "Clean tenant pack, landlord on lease_deed, NOC on file, CNIC matches bill",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": True,
        "owner_type": "lease_deed",
        "landlord_name": "Tariq Mahmood",
        "add_docs": ["noc"],
        "expected_fails": [],
    },
    {
        "id": "C07",
        "category": "clean",
        "desc": "Clean commercial pack, 10 kW proposed on 15 kW sanctioned load, tariff A-2",
        "app_type": "commercial",
        "proposed_kw": 10.0,
        "sanctioned_kw": 15.0,
        "connected_kw": 15.0,
        "tariff": "A-2",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "expected_fails": [],
    },
    {
        "id": "C08",
        "category": "clean",
        "desc": "Clean pack with honorific abbreviation (Syed Ali Raza vs S. Ali Raza)",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "name_variant": ("Syed Ali Raza", "S. Ali Raza", "Syed Ali Raza"),
        "expected_fails": [],
    },
    {
        "id": "C09",
        "category": "trap",
        "desc": "System capacity trap: proposed 12 kW exceeds sanctioned load of 10 kW",
        "app_type": "residential",
        "proposed_kw": 12.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "expected_fails": ["capacity"],
    },
    {
        "id": "C10",
        "category": "trap",
        "desc": "Expired CNIC trap: applicant CNIC expired 75 days ago",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "cnic_expired_days": 75,
        "expected_fails": ["cnic_expiry"],
    },
    {
        "id": "C11",
        "category": "trap",
        "desc": "Name mismatch trap: bill consumer is an entirely different person",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "name_variant": ("Zubair Khan", "Farhan Akhtar", "Zubair Khan"),
        "expected_fails": ["name_match"],
    },
    {
        "id": "C12",
        "category": "trap",
        "desc": "Address mismatch trap: bill address is a different property in Korangi",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "addr_variant": (
            "House 24, Block 3, Gulshan-e-Iqbal, Karachi",
            "Plot 12, Sector 15, Korangi Industrial Area, Karachi",
            "House 24, Block 3, Gulshan-e-Iqbal, Karachi",
        ),
        "expected_fails": ["address_match"],
    },
    {
        "id": "C13",
        "category": "trap",
        "desc": "Missing tenant NOC trap: tenant applicant without landlord NOC",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": True,
        "owner_type": "lease_deed",
        "landlord_name": "Adeel Memon",
        "expected_fails": ["required_docs"],
    },
    {
        "id": "C14",
        "category": "trap",
        "desc": "Missing document trap: single-line diagram missing from pack",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "remove_docs": ["single_line_diagram"],
        "expected_fails": ["required_docs"],
    },
    {
        "id": "C15",
        "category": "trap",
        "desc": "Phase trap: single phase connection is ineligible under NEPRA Reg 2(1)(v)",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "1-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "expected_fails": ["connection_phase"],
    },
    {
        "id": "C16",
        "category": "trap",
        "desc": "Commercial large-system trap (300 kW): missing mandatory load-flow study",
        "app_type": "commercial",
        "proposed_kw": 300.0,
        "sanctioned_kw": 400.0,
        "connected_kw": 400.0,
        "tariff": "B-3",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "add_docs": ["ntn", "form_29"],  # missing load_flow_study for >= 250 kW
        "expected_fails": ["required_docs"],
    },
    {
        "id": "C17",
        "category": "trap",
        "desc": "CNIC format trap: 13-digit number missing standard hyphens",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "cnic_no_override": "4210112345671",
        "expected_fails": ["cnic_format"],
    },
    {
        "id": "C18",
        "category": "trap",
        "desc": "Dual trap: proposed 14 kW on 10 kW load AND expired CNIC",
        "app_type": "residential",
        "proposed_kw": 14.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "cnic_expired_days": 45,
        "expected_fails": ["capacity", "cnic_expiry"],
    },
    {
        "id": "C19",
        "category": "trap",
        "desc": "Missing document trap: Schedule-V applicant affidavit omitted",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "remove_docs": ["affidavit"],
        "expected_fails": ["required_docs"],
    },
    {
        "id": "C20",
        "category": "trap",
        "desc": "Ownership mismatch trap: deed owner is a different person and applicant is not a tenant",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 10.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "name_variant": ("Adeel Memon", "Adeel Memon", "Kashif Siddiqui"),
        "expected_fails": ["name_match"],
    },
    {
        "id": "C21",
        "category": "trap",
        "desc": "Connected load trap: connected load 12 kW exceeds sanctioned load of 10 kW",
        "app_type": "residential",
        "proposed_kw": 8.0,
        "sanctioned_kw": 10.0,
        "connected_kw": 12.0,
        "tariff": "A-1",
        "phase": "3-phase",
        "is_tenant": False,
        "owner_type": "sale_deed",
        "expected_fails": ["connected_load"],
    },
]


def generate_all_cases() -> None:
    """Generate all 21 deterministic packs and write expected.csv."""
    today = date.today()
    expected_rows = []

    for i, spec in enumerate(CASE_SPECS):
        case_id = spec["id"]
        category = spec["category"]
        desc = spec["desc"]
        app_type = spec["app_type"]
        proposed_kw = float(spec["proposed_kw"])
        sanctioned_kw = float(spec["sanctioned_kw"])
        connected_kw = float(spec["connected_kw"])
        tariff = spec["tariff"]
        phase = spec["phase"]
        is_tenant = spec["is_tenant"]
        owner_type = spec["owner_type"]

        # Default names
        name_seed = PAKISTANI_NAMES[i % len(PAKISTANI_NAMES)]
        father_seed = FATHER_NAMES[i % len(FATHER_NAMES)]
        addr_seed = KARACHI_ADDRESSES[i % len(KARACHI_ADDRESSES)]

        # Specific variants
        if "name_variant" in spec:
            cnic_name, bill_name, deed_name = spec["name_variant"]
        else:
            cnic_name = name_seed
            bill_name = name_seed
            deed_name = spec.get("landlord_name", name_seed if not is_tenant else "Landlord Owner")

        if "addr_variant" in spec:
            cnic_addr, bill_addr, deed_addr = spec["addr_variant"]
        else:
            cnic_addr = addr_seed
            bill_addr = addr_seed
            deed_addr = addr_seed

        # CNIC Number & Expiry
        cnic_no = spec.get("cnic_no_override", f"42101-{1000000 + i * 37:07d}-1")
        if "cnic_expired_days" in spec:
            expiry_date = today - timedelta(days=spec["cnic_expired_days"])
        else:
            expiry_date = today + timedelta(days=365 * 4)

        # Reference number
        ref_no = f"01{1000000000 + i * 49:010d}12"

        # System specifications
        panel_watt = 550
        panel_count = math.ceil((proposed_kw * 1000) / panel_watt)
        inverter_kw = proposed_kw

        # Documents present
        docs = list(BASE_DOCS)
        if "add_docs" in spec:
            docs.extend(spec["add_docs"])
        if "remove_docs" in spec:
            for r in spec["remove_docs"]:
                if r in docs:
                    docs.remove(r)

        pack_data = {
            "case_id": case_id,
            "category": category,
            "description": desc,
            "applicant_type": app_type,
            "cnic": {
                "name": cnic_name,
                "father_name": father_seed,
                "cnic_no": cnic_no,
                "expiry": expiry_date.isoformat(),
                "address": cnic_addr,
            },
            "bill": {
                "consumer_name": bill_name,
                "reference_no": ref_no,
                "sanctioned_load_kw": sanctioned_kw,
                "connected_load_kw": connected_kw,
                "tariff": tariff,
                "connection_phase": phase,
                "address": bill_addr,
            },
            "ownership": {
                "type": owner_type,
                "owner_name": deed_name,
                "property_address": deed_addr,
            },
            "system": {
                "proposed_kw": proposed_kw,
                "inverter_kw": inverter_kw,
                "panel_count": panel_count,
                "panel_watt": panel_watt,
            },
            "is_tenant": is_tenant,
            "docs_present": docs,
        }

        # Save pack JSON
        pack_file = CASES_DIR / f"{case_id}.json"
        with open(pack_file, "w", encoding="utf-8") as f:
            json.dump(pack_data, f, indent=2, ensure_ascii=False)

        # Expected row logic from spec ground truth
        fails = set(spec.get("expected_fails", []))
        cnic_format_val = "FAIL" if "cnic_format" in fails else "PASS"
        cnic_expiry_val = "FAIL" if "cnic_expiry" in fails else "PASS"
        capacity_val = "FAIL" if "capacity" in fails else "PASS"
        connection_phase_val = "FAIL" if "connection_phase" in fails else "PASS"
        connected_load_val = "FAIL" if "connected_load" in fails else "PASS"
        required_docs_val = "FAIL" if "required_docs" in fails else "PASS"
        name_match_val = "FAIL" if "name_match" in fails else "PASS"
        address_match_val = "FAIL" if "address_match" in fails else "PASS"

        overall_val = "NOT_READY" if len(fails) > 0 else "READY"

        expected_rows.append({
            "case_id": case_id,
            "category": category,
            "cnic_format": cnic_format_val,
            "cnic_expiry": cnic_expiry_val,
            "capacity": capacity_val,
            "connection_phase": connection_phase_val,
            "connected_load": connected_load_val,
            "required_docs": required_docs_val,
            "name_match": name_match_val,
            "address_match": address_match_val,
            "overall": overall_val,
        })

    # Write expected.csv
    fieldnames = [
        "case_id",
        "category",
        "cnic_format",
        "cnic_expiry",
        "capacity",
        "connection_phase",
        "connected_load",
        "required_docs",
        "name_match",
        "address_match",
        "overall",
    ]
    with open(EXPECTED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(expected_rows)

    print(f"Generated 21 cases in {CASES_DIR} and ground truth in {EXPECTED_CSV}")


if __name__ == "__main__":
    generate_all_cases()
