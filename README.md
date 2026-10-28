# NetBill Assist — Net-Billing Application Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-40%20Passing-brightgreen.svg)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An internal intelligence tool for rooftop-solar installer onboarding staff in Karachi, Pakistan. Built for **DATA722: Generative AI & Strategic Forecasting (Mid-Term Project)**.

NetBill Assist enforces the **NEPRA (Prosumer) Regulations 2026 (SRO 251(I)/2026)** and **K-Electric Net Billing Guidelines (13 April 2026)**. It performs deterministic regulatory validation, semantically aligns inconsistent identity and billing records, generates customer rectification instructions in English and Urdu, and compiles compliant draft Schedule-II filings.

---

## 1. Executive Summary & Regulatory Background

In early 2026, the National Electric Power Regulatory Authority (NEPRA) replaced the historical net-metering regime with net billing under **SRO 251(I)/2026**. Under **Regulation 3(5)**:
- Distribution companies (such as **K-Electric** in Karachi) verify application completeness within **5 working days**.
- If any discrepancy or missing document is identified, the applicant is granted strictly **3 working days** to rectify the dossier before summary rejection.
- Rejected filings delay commercial solar export interconnection by weeks.

**NetBill Assist** is designed for the installer's onboarding team to audit document packs **before** submission to K-Electric.

---

## 2. The 6 Hard Architectural Boundaries

| # | Boundary | Specification | Enforcement Mechanism |
|---|---|---|---|
| **1** | **No Autonomous Action** | Zero automated submit, transmit, or pay buttons anywhere in the system | Human Gate: physical customer sign-off & manual portal filing |
| **2** | **Code Decides Hard Rules** | R1–R7 rules calculated 100% deterministically in Python | Hard rules code-only; LLM output never overrides hard verdicts |
| **3** | **Scoped LLM Scope** | LLM restricted strictly to fuzzy name/address matching & checklist wording | Controlled temperature (0.0) with JSON schema validation |
| **4** | **Zero Sensitive PII on Wire** | Zero CNIC numbers or billing account numbers sent to any LLM | Two-layer redaction (direct field exclusion + regex scrubber) |
| **5** | **Synthetic Data Isolation** | 100% synthetic data generated deterministically (Faker seed 722) | 21 application packs (`C01`–`C21`) evaluated against `expected.csv` |
| **6** | **Draft PDF Code Supremacy** | Zero LLM text in generated Schedule-II draft PDF | ReportLab draws verified pack data only with diagonal watermark |

---

## 3. Regulatory Rule Catalog (R1–R7)

All calculations are evaluated deterministically in `app/rules.py` against reference date `2026-04-13`:

- **R1: CNIC Format** (`Clause 2.1`): Enforces standard 13-digit Pakistani CNIC pattern `^\d{5}-\d{7}-\d{1}$`.
- **R2: CNIC Expiry** (`Clause 2.1`): CNIC expiration date must be on or after `2026-04-13`.
- **R3: Capacity Limit** (`Reg 3(1)`): Proposed inverter capacity must be $\le 100\%$ of sanctioned load (`proposed_kw <= sanctioned_load_kw`).
- **R4: Connection Phase** (`Clause 3.2`): If proposed capacity $> 5\text{ kW}$, a 3-phase meter connection is strictly mandatory.
- **R5: Connected Load** (`Clause 4.1`): Actual connected load must be $\le$ bill sanctioned load to prevent transformer overload.
- **R6: Load-Flow Study** (`Reg 3(7)`): Interconnection capacity $> 250\text{ kW}$ triggers a mandatory distribution network stability study.
- **R7: Document Completeness** (`Clause 2.2`): Enforces mandatory documents (CNIC copy, paid bill, title deed, SLD, Schedule-V affidavit, vendor checklist, inverter datasheet, inverter settings letter, owner's NOC for tenants, NTN/Form-29 for commercial).

---

## 4. LLM Semantic Checks & RapidFuzz Fallback

In Karachi municipal billing records, names and addresses vary widely across documents (e.g., honorifics, abbreviations, and colony toponyms):

- **L1: Name Consistency**: Compares applicant CNIC name, electricity bill consumer name, and title deed owner name. Recognizes lawful tenant applications with owner NOCs.
- **L2: Address Consistency**: Reconciles Karachi municipal variants (e.g., *"DHA Phase 6"* vs *"Defence Phase VI"*, *"Clifton Block 2"* vs *"Block II Clifton"*).
- **RapidFuzz Hybrid Scoring**: Token sort ratio calculation ensures instant fallback when LLM API is unavailable (`LLM_PROVIDER=none`).
- **Shadow Checks (Research)**: Runs experimental LLM prompts on R2 and R3. Demonstrates code supremacy on edge case **C18** (where LLM was lenient on capacity limits, but code rejected the pack).

### Two-Layer Redaction Architecture
Strict defense-in-depth ensures zero sensitive credentials ever reach third-party model APIs:
1. **Layer 1 (Direct Field Exclusion)**: Python dictionary builders explicitly drop `cnic_number` and `account_number`.
2. **Layer 2 (Regex Scrubber)**: Serialized JSON strings are scanned with compiled regexes, converting any raw 13-digit Pakistani CNIC or 13/14-digit K-Electric account reference to `[REDACTED_CNIC]` or `[REDACTED_REF]`.
Tested across all 21 synthetic cases with zero leaks.

---

## 5. Bilingual Customer Checklist & Faithfulness Gate

When an application pack fails checks:
- The system generates clear customer instructions in **English** and **Urdu (اردو)**.
- **The Faithfulness Gate**: A deterministic regex audit runs prior to displaying any LLM-generated checklist.
- The gate validates:
  1. No hallucinated or extraneous check IDs.
  2. All failed check IDs are addressed.
  3. Zero invented numbers, kW quantities, or foreign dates appear in the customer text.
- If the gate fails, the system immediately reverts to safe deterministic templates (`app/checklist.py`).

---

## 6. Official Draft PDF (Schedule-II)

Built using **ReportLab** (`app/draft_pdf.py`):
- Strict A4 dimensions, clean corporate typography, and formal grid layout.
- Diagonal light-gray watermark: `DRAFT · NOT FOR SUBMISSION · FOR APPLICANT REVIEW ONLY`.
- Identity numbers masked for safety (`42101-*******-1` and `04000*******`).
- **Zero LLM text**: All fields drawn strictly from validated Python data models. Verified via `pypdf` extraction tests with 0 discrepancies.

---

## 7. Installation & Quick Start

### Prerequisites
- Python 3.11, 3.12, 3.13, or 3.14
- Virtual environment (`venv`)

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/your-username/project-solar.git
cd project-solar

# Create virtual environment
python -m venv .venv

# Activate environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# (Linux / macOS)
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)
Copy the example file:
```bash
cp .env.example .env
```
Default configuration runs the deterministic **Mock LLM engine** (zero API keys required, ideal for grading and local testing):
```ini
LLM_PROVIDER=mock
LLM_MODEL=mock-engine
APP_PORT=8000
```
To test with Google Gemini or OpenAI:
```ini
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
LLM_API_KEY=your_gemini_api_key_here
```

### 3. Generate Synthetic Packs (Reproducible)
Generate the 21 test packs and `expected.csv` using seed `722`:
```bash
python make_cases.py
```

### 4. Run Development Server
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser to:
- **Dashboard Queue**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Case Audit & Inspection**: [http://127.0.0.1:8000/cases/C01](http://127.0.0.1:8000/cases/C01)
- **Model Evaluation Benchmark**: [http://127.0.0.1:8000/evaluate](http://127.0.0.1:8000/evaluate)
- **Regulatory Architecture**: [http://127.0.0.1:8000/about](http://127.0.0.1:8000/about)

---

## 8. Test Suite

Run the full pytest suite (40 tests):
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Test Coverage Highlights:
- `tests/test_rules.py`: Validates all 21 synthetic cases against `data/expected.csv` and tests regulatory boundary edge cases.
- `tests/test_redact.py`: Exhaustive search verifying zero raw CNIC or account numbers reach any LLM payload across all 21 packs.
- `tests/test_checklist_gate.py`: Faithfulness gate verification, invented number rejection, and Urdu template rendering.
- `tests/test_evaluate.py`: Benchmark metrics calculation, `pypdf` draft PDF read-back fidelity, and CSV export.
- `tests/test_llm_checks.py`: RapidFuzz fallback, shadow check disagreement on C18, and `LLM_PROVIDER=none` safety.

---

## 9. Evaluation Benchmark Summary

| Metric | Target | Result | Status |
|---|---|---|---|
| **Wrong Values in Draft PDF** | 0 discrepancies | **0** | **PASS** |
| **Code Rule Accuracy (R1–R5, R7)** | 100.0% | **100.0%** | **PASS** |
| **Trap Recall (11 Trap Packs)** | 100.0% | **100.0%** | **PASS** |
| **LLM Semantic Match Accuracy** | $\ge 90.0\%$ | **100.0%** | **PASS** |
| **False Alarms on Clean Packs** | 0 false rejections | **0** | **PASS** |
| **Deferred to Staff Rate** | $< 15.0\%$ | **9.5%** | **PASS** |
| **Checklist Faithfulness Gate** | 100.0% pass rate | **100.0%** | **PASS** |
| **LLM Consistency (Multi-run)** | $\ge 90.0\%$ | **100.0%** | **PASS** |
| **Average Latency (Mock Engine)** | $< 500\text{ ms}$ | **~20 ms** | **PASS** |

---

## 10. Repository Structure

```
project-solar/
├── app/
│   ├── __init__.py
│   ├── audit.py            # Append-only audit trail logging
│   ├── checklist.py        # Bilingual customer checklist & faithfulness gate
│   ├── config.py           # Regulatory constants & environment config
│   ├── draft_pdf.py        # ReportLab draft Schedule-II PDF generator
│   ├── evaluate.py         # Ground-truth evaluation benchmark engine
│   ├── llm_checks.py       # L1/L2 semantic checks & shadow checks
│   ├── llm_client.py       # Multi-provider client (Gemini, OpenAI, Mock, None)
│   ├── main.py             # FastAPI web application & REST routes
│   ├── merge.py            # Readiness score & overall status aggregator
│   ├── models.py           # Pydantic schemas (Pack, Report, Checks)
│   ├── prompts.py          # System prompts for L1, L2, shadow checks
│   ├── redact.py           # Two-layer PII & credential redaction engine
│   ├── rules.py            # Deterministic regulatory rules (R1-R7)
│   └── storage.py          # Case pack persistence & runtime storage
├── data/
│   ├── cases/              # 21 synthetic application packs (C01.json - C21.json)
│   ├── expected.csv        # Ground truth validation matrix
│   └── runtime/            # Audit logs, evaluations, and staff reviews
├── static/
│   ├── app.js              # Theme manager & navigation
│   ├── case.js             # Interactive case inspection, tabs, & modals
│   ├── dashboard.js        # KPI filtering, search, & batch execution
│   ├── evaluate.js         # Evaluation charts, matrix table, & benchmark runner
│   └── styles.css          # Tailwind custom styling & print rules
├── templates/
│   ├── about.html          # Regulatory compliance & architecture guide
│   ├── base.html           # Base layout, sidebar, & responsive header
│   ├── case.html           # 3-section case detail workspace
│   ├── dashboard.html      # Application onboarding queue
│   └── evaluate.html       # Benchmark dashboard with Chart.js
├── tests/
│   ├── test_api.py
│   ├── test_checklist_gate.py
│   ├── test_evaluate.py
│   ├── test_llm_checks.py
│   ├── test_phase0.py
│   ├── test_redact.py
│   └── test_rules.py
├── make_cases.py           # Reproducible synthetic dataset generator
├── pyproject.toml          # Project metadata & pytest configuration
└── requirements.txt        # Pinned Python package dependencies
```

---

## 11. Regulatory & Statutory References

1. **NEPRA (Alternative & Renewable Energy) Distributed Generation and Net Billing Regulations, 2026** — SRO 251(I)/2026 dated 09 February 2026.
2. **K-Electric Net Billing Operational Guidelines** — Version 1.0 dated 13 April 2026.

---

## 12. License

This project is submitted for academic assessment under the MIT License.
