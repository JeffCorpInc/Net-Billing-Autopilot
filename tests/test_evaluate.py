"""Tests for Phase 5 Evaluation Benchmark Engine, Metrics, and Export."""

import pytest
from starlette.testclient import TestClient

from app.evaluate import (
    compute_summary_metrics,
    evaluate_single_case,
    generate_evaluation_csv,
    load_all_eval_results,
    load_expected_ground_truth,
    verify_draft_pdf_values,
)
from app.main import app
from app.merge import build_case_report
from app.rules import run_code_rules
from app.storage import get_pack

client = TestClient(app)


def test_load_expected_ground_truth():
    gt = load_expected_ground_truth()
    assert len(gt) == 21
    assert "C01" in gt
    assert "C18" in gt
    assert "C21" in gt
    assert gt["C01"]["overall"] == "READY"
    assert gt["C09"]["overall"] == "NOT_READY"


def test_evaluate_single_clean_case_c01():
    res = evaluate_single_case("C01", runs=1)
    assert res["case_id"] == "C01"
    assert res["category"] == "clean"
    assert res["overall_got"] == "READY"
    assert res["overall_match"] is True
    assert res["wrong_pdf_values"] == 0
    assert res["gate_passed"] is True
    assert res["checks"]["cnic_format"]["got"] == "PASS"
    assert res["checks"]["capacity"]["got"] == "PASS"
    assert res["checks"]["name_match"]["got"] == "PASS"
    assert res["checks"]["address_match"]["got"] == "PASS"


def test_evaluate_single_trap_case_c09():
    res = evaluate_single_case("C09", runs=1)
    assert res["case_id"] == "C09"
    assert res["category"] == "trap"
    assert res["overall_got"] == "NOT_READY"
    assert res["overall_match"] is True
    assert res["checks"]["capacity"]["got"] == "FAIL"


def test_evaluate_shadow_disagreement_c18():
    res = evaluate_single_case("C18", runs=1)
    assert res["case_id"] == "C18"
    shadow = res["shadow_checks"]
    assert len(shadow) == 2
    # Check that capacity check demonstrated LLM disagreement (code was strict, LLM was lenient)
    cap_shadow = next((s for s in shadow if "capacity" in s["check"].lower()), None)
    assert cap_shadow is not None
    assert cap_shadow["agree"] is False
    assert cap_shadow["code_verdict"] is False
    assert cap_shadow["llm_verdict"] is True


def test_verify_draft_pdf_values_fidelity():
    pack = get_pack("C01")
    assert pack is not None
    rules = run_code_rules(pack)
    report = build_case_report(pack=pack, rule_results=rules)
    discrepancies = verify_draft_pdf_values(pack, report)
    assert discrepancies == []


def test_compute_summary_metrics_structure():
    # Evaluate a subset or use existing results
    c01 = evaluate_single_case("C01", runs=1)
    c09 = evaluate_single_case("C09", runs=1)
    c18 = evaluate_single_case("C18", runs=1)

    summary = compute_summary_metrics([c01, c09, c18])
    assert summary["total_cases"] == 3
    metrics = summary["metrics"]

    assert "wrong_values_in_draft" in metrics
    assert metrics["wrong_values_in_draft"]["value"] == 0

    assert "code_rule_accuracy" in metrics
    assert metrics["code_rule_accuracy"]["value"] == 100.0

    assert "trap_recall" in metrics
    assert metrics["trap_recall"]["value"] == 100.0

    assert "checklist_faithfulness" in metrics
    assert metrics["checklist_faithfulness"]["value"] == 100.0

    assert "accuracy_per_check" in summary
    assert "trap_outcomes" in summary
    assert len(summary["findings"]) > 0


def test_generate_evaluation_csv_format():
    evaluate_single_case("C01", runs=1)
    csv_str = generate_evaluation_csv()
    lines = csv_str.strip().split("\r\n" if "\r\n" in csv_str else "\n")
    assert len(lines) >= 9  # Header + 8 check rows for C01
    assert "case_id,category,check_key,expected,got,match,detail,avg_latency_ms" in lines[0]


def test_api_evaluation_routes():
    # 1. Single case eval endpoint
    r_case = client.post("/api/evaluate/case/C01?runs=1")
    assert r_case.status_code == 200
    data = r_case.json()
    assert data["case_id"] == "C01"
    assert data["overall_got"] == "READY"

    # 2. Summary endpoint
    r_sum = client.get("/api/evaluate/summary")
    assert r_sum.status_code == 200
    sum_data = r_sum.json()
    assert "metrics" in sum_data
    assert "findings" in sum_data

    # 3. CSV export endpoint
    r_csv = client.get("/api/evaluate/export.csv")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]
    assert "attachment; filename=\"evaluation_results.csv\"" in r_csv.headers["content-disposition"]

    # 4. Evaluation page HTML
    r_page = client.get("/evaluate")
    assert r_page.status_code == 200
    assert "Benchmark Against Ground Truth" in r_page.text
    assert "Wrong Values in Draft" in r_page.text
    assert "chart-accuracy-per-check" in r_page.text
