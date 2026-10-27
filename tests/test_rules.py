"""Unit tests for regulatory rules R1-R7 and verification against ground truth expected.csv."""

import csv
from datetime import date, timedelta
from pathlib import Path
import pytest

from app.models import Pack
from app.rules import (
    check_r1_cnic_format,
    check_r2_cnic_expiry,
    check_r3_capacity,
    check_r4_connection_phase,
    check_r5_required_docs,
    check_r6_fee,
    check_r7_connected_load,
    run_code_rules,
)
from app.storage import get_pack

EXPECTED_CSV = Path(__file__).resolve().parent.parent / "data" / "expected.csv"


def load_expected_csv() -> dict[str, dict[str, str]]:
    """Load ground truth expected.csv into a dictionary keyed by case_id."""
    results = {}
    with open(EXPECTED_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results[row["case_id"]] = row
    return results


class TestGroundTruthCases:
    """Verify all 21 packs match expected.csv for code rules R1-R5 and R7."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.expected = load_expected_csv()

    def test_all_21_cases_match_ground_truth(self):
        today = date.today()
        for case_id, exp in self.expected.items():
            pack = get_pack(case_id)
            assert pack is not None, f"Pack {case_id} could not be loaded"

            # Execute rules
            r1 = check_r1_cnic_format(pack)
            r2 = check_r2_cnic_expiry(pack, today=today)
            r3 = check_r3_capacity(pack)
            r4 = check_r4_connection_phase(pack)
            r5 = check_r5_required_docs(pack)
            r7 = check_r7_connected_load(pack)

            assert r1.status == exp["cnic_format"], f"{case_id} R1 cnic_format failed"
            assert r2.status == exp["cnic_expiry"], f"{case_id} R2 cnic_expiry failed"
            assert r3.status == exp["capacity"], f"{case_id} R3 capacity failed"
            assert r4.status == exp["connection_phase"], f"{case_id} R4 connection_phase failed"
            assert r5.status == exp["required_docs"], f"{case_id} R5 required_docs failed"
            assert r7.status == exp["connected_load"], f"{case_id} R7 connected_load failed"


class TestEdgeCases:
    """Edge cases for boundaries (equal capacity, expiry today, etc.)."""

    @pytest.fixture
    def base_pack(self) -> Pack:
        pack = get_pack("C01")
        assert pack is not None
        return pack

    def test_capacity_exact_limit(self, base_pack: Pack):
        """Proposed kW exactly equal to sanctioned load must PASS."""
        base_pack.system.proposed_kw = 10.0
        base_pack.bill.sanctioned_load_kw = 10.0
        res = check_r3_capacity(base_pack)
        assert res.status == "PASS"

    def test_capacity_fractional_over(self, base_pack: Pack):
        """Proposed kW slightly exceeding sanctioned load must FAIL."""
        base_pack.system.proposed_kw = 10.1
        base_pack.bill.sanctioned_load_kw = 10.0
        res = check_r3_capacity(base_pack)
        assert res.status == "FAIL"

    def test_cnic_expiry_today(self, base_pack: Pack):
        """CNIC expiring today must PASS."""
        today = date.today()
        base_pack.cnic.expiry = today.isoformat()
        res = check_r2_cnic_expiry(base_pack, today=today)
        assert res.status == "PASS"

    def test_cnic_expiry_yesterday(self, base_pack: Pack):
        """CNIC expired yesterday must FAIL."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        base_pack.cnic.expiry = yesterday.isoformat()
        res = check_r2_cnic_expiry(base_pack, today=today)
        assert res.status == "FAIL"

    def test_single_phase_fails(self, base_pack: Pack):
        """1-phase connection must FAIL."""
        base_pack.bill.connection_phase = "1-phase"
        res = check_r4_connection_phase(base_pack)
        assert res.status == "FAIL"

    def test_connected_load_equal(self, base_pack: Pack):
        """Connected load equal to sanctioned load must PASS."""
        base_pack.bill.connected_load_kw = 10.0
        base_pack.bill.sanctioned_load_kw = 10.0
        res = check_r7_connected_load(base_pack)
        assert res.status == "PASS"

    def test_connected_load_over(self, base_pack: Pack):
        """Connected load exceeding sanctioned load must FAIL."""
        base_pack.bill.connected_load_kw = 12.0
        base_pack.bill.sanctioned_load_kw = 10.0
        res = check_r7_connected_load(base_pack)
        assert res.status == "FAIL"

    def test_fee_estimate(self, base_pack: Pack):
        """Fee estimate should be 1000 Rs per kW and INFO status."""
        base_pack.system.proposed_kw = 8.0
        res = check_r6_fee(base_pack)
        assert res.status == "INFO"
        assert res.data["fee_rs"] == 8000
