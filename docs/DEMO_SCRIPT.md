# NetBill Assist — Live Demo Script (4–5 Minutes)

**Course:** DATA722 Generative AI & Strategic Forecasting (Mid-Term Project)  
**Target Audience:** Grading Examiners & Technical Assessors  
**Presenter Role:** Lead AI & Systems Architect for the Solar Installer  

---

## Timing Overview

| Act | Timestamp | Scene | Key Feature Demonstrated |
|:---:|:---:|---|---|
| **Act 1** | `0:00 – 0:45` | Problem & Regulatory Context | SRO 251(I)/2026, 5-day review / 3-day rectification bottleneck |
| **Act 2** | `0:45 – 1:45` | Clean Case Happy Path (`C01`) | Deterministic R1–R7, bilingual checklist, ReportLab draft PDF |
| **Act 3** | `1:45 – 3:00` | Trap Auditing (`C09` & `C18`) | Multi-violation detection, C18 shadow disagreement (code supremacy) |
| **Act 4** | `3:00 – 4:00` | Evaluation & Benchmarking (`/evaluate`) | 9 KPIs, 4 Chart.js charts, ground-truth matrix, CSV export |
| **Act 5** | `4:00 – 4:45` | Architectural Boundaries & Sign-Off | The Human Gate, two-layer redaction, staff audit logging |

---

## Act 1: The Regulatory Problem & Architecture (0:00 – 0:45)

### On Screen
- Open browser to `http://127.0.0.1:8000/`.
- Show the top header: *"K-Electric Net-Billing Onboarding Queue · 2026"*.
- Point cursor to the active KPI cards (Total Cases 21, Ready, Needs Review, Not Ready).

### Narration / Spoken Script
> *"Good morning. In Karachi, rooftop solar installations have surged, but in February 2026, NEPRA replaced net-metering with net-billing under SRO 251(I)/2026.*  
> *Under Regulation 3(5), K-Electric inspects application document dossiers within exactly 5 working days. If any document is defective or mismatched, the applicant has only 3 working days to rectify it—otherwise, the filing is rejected, delaying solar exports by weeks.*  
>  
> *Solar installers face high rejection rates due to document name variations, expired CNICs, and capacity overages. To solve this, we built **NetBill Assist**: an internal audit intelligence assistant for onboarding engineers.*  
> *Notice our core architectural boundary up front: **The Human Gate**. There is zero autonomous submission or payment anywhere. Code decides hard rules; the LLM handles semantic matching and bilingual explanations."*

---

## Act 2: Clean Case Happy Path — Case C01 (0:45 – 1:45)

### On Screen
- On the Dashboard, click the row for **C01** (`Muhammad Tariq Khan`).
- The Case Inspection Page loads (`/cases/C01`).

### Actions & Highlights
1. **Section A (Synthetic Documents):**
   - Point out the realistic CNIC card (green Pakistani NADRA design with expiry `2028-11-20`).
   - Scroll through K-Electric Bill, Title Deed, Single Line Diagram, and Schedule-V Affidavit.
   - Point out the masked CNIC (`42101-*******-1`) and masked billing reference (`04000*******`).
2. **Section B (Compliance & Diagnostics):**
   - Highlight the **100% Readiness Gauge** in green (`READY FOR SUBMISSION`).
   - Review the deterministic checks R1–R7: all green `PASS`.
   - Show L1 (Name Match) and L2 (Address Match): explain that the LLM verified the name with 95% confidence without receiving any raw CNIC number.
3. **Section C (Output Dossier):**
   - Click the **Checklist** tab: show the generated customer instructions in English.
   - Toggle the language switch to **اردو**: demonstrate Noto Nastaliq Urdu RTL typography. Mention the **Faithfulness Gate** that ensures zero invented numbers.
   - Click the **Draft Application** tab: display the generated ReportLab Schedule-II PDF.
   - Point out the diagonal watermark: `DRAFT · NOT FOR SUBMISSION`.
   - Highlight that all data in this PDF comes from Python data structures—**zero LLM text** appears in legal filings.

### Narration / Spoken Script
> *"Let's inspect Case C01, an owner in DHA Phase 6. All 7 deterministic rules R1 through R7 pass instantly. In Section B, our readiness gauge shows 100%.*  
> *In Section C, the assistant generates customer instructions in English and native Urdu, fully vetted by a regex faithfulness gate. If we look at the draft Schedule-II PDF, it is generated via ReportLab with a clear watermark and masked credentials. Every single character in this PDF is drawn deterministically from code—eliminating hallucination risk in legal filings."*

---

## Act 3: Trapping Defects & Code Supremacy — C09 & C18 (1:45 – 3:00)

### On Screen
- Navigate back to the Dashboard (`/`).
- Use the search bar: type `C09` or click the `NOT READY` filter card.
- Open **C09** (`Saeed Ahmed Farooqi`).

### Actions & Highlights
1. **Multiple Regulatory Violations:**
   - Point out the red banner: `NOT READY (CRITICAL ISSUES DETECTED)`.
   - Point out **R3 (Capacity Limit)**: Proposed `12.5 kW` exceeds bill sanctioned load of `10.0 kW`.
   - Point out **R4 (3-Phase Requirement)**: Proposed `12.5 kW` on a single-phase connection (exceeds 5 kW threshold).
   - Point out the Urdu customer checklist: clearly instructs the customer to submit an application for sanctioned load enhancement.
2. **Edge Case C18 (Disagreement & Code Supremacy):**
   - Navigate to **C18** (`Syed Zeeshan Haider`).
   - Open Section B and expand the **Shadow Checks Diagnostic Panel**.
   - Show the headline finding:
     - **Code Rule R3:** `FAIL` (proposed capacity exceeds sanctioned load).
     - **LLM Shadow Check:** `PASS` (the LLM was lenient, reasoning that 10.5 kW is "close enough" to 10 kW).
     - **Outcome:** Code verdict prevailed. The LLM was completely ignored on regulatory limits.

### Narration / Spoken Script
> *"Now let's examine Case C09, a trap pack with multiple regulatory violations. The system catches that the 12.5 kW proposed inverter exceeds the 10 kW sanctioned load, and flags that single-phase meters cannot support more than 5 kW.*  
> *Next, look at Case C18. This is our key architectural demonstration: **Code Supremacy**.*  
> *In our research shadow checks, the LLM thought 10.5 kW was 'close enough' to 10 kW and voted PASS. But our Python rule strictly enforced NEPRA Regulation 3(1) and marked it FAIL. In NetBill Assist, code always decides hard rules. The LLM cannot override compliance."*

---

## Act 4: System Benchmarking & Evaluation Page (3:00 – 4:00)

### On Screen
- Click **"Evaluation & Metrics"** in the sidebar to open `/evaluate`.
- Show the 9 Benchmark KPI Cards.
- Show the 4 Chart.js charts.

### Actions & Highlights
1. **The 9 Metric Cards:**
   - **Wrong Values in Draft:** `0` (target 0, verified via `pypdf` extraction).
   - **Code Rule Accuracy:** `100.0%` against `expected.csv`.
   - **Trap Recall:** `100.0%` (all 11 trap packs caught).
   - **LLM Match Accuracy:** `100.0%` on Karachi names and addresses.
   - **False Alarms:** `0` on clean cases.
   - **Checklist Faithfulness:** `100.0%` pass rate on the regex gate.
2. **The 4 Visualizations:**
   - Chart 1: Accuracy Per Check (horizontal bars).
   - Chart 2: Trap Case Outcomes (doughnut chart).
   - Chart 3: Code vs LLM Shadow Checks Agreement (highlighting the C18 divergence).
   - Chart 4: Latency per Case (~20ms in mock mode).
3. **Execution & Export:**
   - Select **"3 Runs (Consistency)"** and click **"Run Benchmark"**.
   - Watch the animated progress bar evaluate all 21 packs sequentially.
   - Click **"Export CSV"**: show the downloaded `evaluation_results.csv` with 169 rows.

### Narration / Spoken Script
> *"Under the Evaluation & Metrics tab, we benchmark the entire system against ground truth. Across all 21 synthetic packs, we achieve 100% trap recall and 100% code rule accuracy.*  
> *Critically, our `pypdf` read-back test extracted every single name and kilowatt number from generated draft PDFs and verified **zero wrong values**.*  
> *Our Chart.js visualizer displays accuracy per check, trap outcomes, and the shadow check disagreement on C18. We can re-run multi-run consistency benchmarks with one click and export the full verification matrix to CSV."*

---

## Act 5: Privacy, The Human Gate & Audit Trail (4:00 – 4:45)

### On Screen
- Navigate to `/about`.
- Show the **Human Gate** diagram and the **Two-Layer Redaction Architecture** card.
- Go back to `/cases/C01`, click the **Audit Trail** tab, type a reviewer note (*"Checked title deed against K-Electric bill; verified valid"*), and click **"Sign Off Dossier"**.

### Actions & Highlights
1. Point out the newly appended entry in the append-only audit trail (`data/runtime/audit/C01.jsonl`).
2. Show that the entry records timestamp, reviewer name, previous state, and action.
3. Reiterate the zero-autonomous-action guarantee.

### Narration / Spoken Script
> *"To ensure data privacy, we implement a **two-layer redaction layer**: direct field omission in Python, followed by a compiled regex scrubber. Unit tests prove zero raw CNIC or utility account numbers ever touch the LLM API.*  
> *Finally, when the human onboarding engineer finishes reviewing, they record a signed audit note. This creates an append-only JSONL log.*  
> *The installer now has an auditable, compliant, bilingual pre-screening assistant that eliminates the 3-day K-Electric rejection risk while keeping human engineers firmly in command.*  
> *Thank you, and I look forward to your questions."*

---

## Quick Reference / Evaluator Checklist

- [x] SRO 251(I)/2026 & K-Electric 13 Apr 2026 guidelines referenced.
- [x] Zero autonomous action confirmed (no submit or pay buttons).
- [x] Deterministic code rules R1–R7 explained.
- [x] Scoped LLM semantic matching (L1/L2) and RapidFuzz fallback noted.
- [x] Two-layer privacy redaction demonstrated.
- [x] C18 code vs LLM disagreement demonstrated.
- [x] Bilingual checklist (English & Urdu) and Faithfulness Gate tested.
- [x] ReportLab watermarked draft PDF inspected with zero LLM text.
- [x] 9 Evaluation KPIs and 4 Chart.js charts presented.
- [x] Append-only audit trail sign-off shown.

