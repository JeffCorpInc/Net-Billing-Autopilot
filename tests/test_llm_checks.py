"""Tests for LLM checks, mock provider, fuzzy scoring, and fallback handling."""

import os
from unittest.mock import patch
import pytest

from app.llm_checks import (
    compute_address_fuzzy_score,
    compute_name_fuzzy_score,
    run_l1_name_check,
    run_l2_address_check,
    run_shadow_checks,
)
from app.storage import get_pack


class TestMockProviderChecks:
    """Verify mock LLM provider verdicts match expected ground truth."""

    def test_clean_name_and_address_variants_pass(self):
        # C03: "Muhammad Usman" vs "M. Usman"
        c03 = get_pack("C03")
        r_c03 = run_l1_name_check(c03)
        assert r_c03.status == "PASS"

        # C04: "House 45-A, PECHS Block 2" vs "H# 45-A PECHS Blk-2 Khi"
        c04 = get_pack("C04")
        r_c04 = run_l2_address_check(c04)
        assert r_c04.status == "PASS"

        # C05: "Mohammad Hamza Qureshi" vs "Muhammad Hamza Qureshi"
        c05 = get_pack("C05")
        r_c05 = run_l1_name_check(c05)
        assert r_c05.status == "PASS"

        # C08: "Syed Ali Raza" vs "S. Ali Raza"
        c08 = get_pack("C08")
        r_c08 = run_l1_name_check(c08)
        assert r_c08.status == "PASS"

    def test_trap_mismatches_fail(self):
        # C11: Different person on bill
        c11 = get_pack("C11")
        r_c11 = run_l1_name_check(c11)
        assert r_c11.status == "FAIL"

        # C12: Different property address in Korangi
        c12 = get_pack("C12")
        r_c12 = run_l2_address_check(c12)
        assert r_c12.status == "FAIL"

        # C20: Deed owner different person, not a tenant
        c20 = get_pack("C20")
        r_c20 = run_l1_name_check(c20)
        assert r_c20.status == "FAIL"

    def test_c18_shadow_checks_disagreement(self):
        """Verify C18 deliberately exhibits Code vs LLM capacity disagreement in mock mode."""
        c18 = get_pack("C18")
        shadow = run_shadow_checks(c18)
        assert len(shadow) == 2
        r3_shadow = next(s for s in shadow if "R3" in s["check"])
        assert r3_shadow["agree"] is False
        assert r3_shadow["code_verdict"] is False
        assert r3_shadow["llm_verdict"] is True


class TestFuzzyAndFallback:
    """Verify RapidFuzz scoring and fallback mode handling."""

    def test_fuzzy_name_scores(self):
        score_high = compute_name_fuzzy_score("Muhammad Usman", "M. Usman", "Muhammad Usman", False)
        assert score_high >= 80.0

        score_low = compute_name_fuzzy_score("Zubair Khan", "Farhan Akhtar", "Zubair Khan", False)
        assert score_low < 60.0

    def test_fuzzy_fallback_on_corrupted_llm_json(self):
        """Ensure invalid or corrupted LLM response falls back cleanly to fuzzy score without crash."""
        c03 = get_pack("C03")
        with patch("app.llm_checks.complete_json", return_value=(None, {"provider": "mock"})):
            res = run_l1_name_check(c03)
            assert res.source == "fuzzy-fallback"
            assert res.status in ["PASS", "UNSURE", "FAIL"]
            assert res.llm["fuzzy_score"] >= 80.0

    def test_provider_none_fallback(self):
        """Ensure LLM_PROVIDER=none operates in pure fallback mode."""
        c03 = get_pack("C03")
        with patch.dict(os.environ, {"LLM_PROVIDER": "none"}):
            res = run_l1_name_check(c03)
            assert res.source == "fuzzy-fallback"
            assert res.status == "PASS"
