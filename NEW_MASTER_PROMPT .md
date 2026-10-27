# MASTER PROMPT — Net-Billing Application Assistant
### FastAPI + HTML · UI-rich · built phase by phase

> **How to use:** paste this entire file into your AI coding agent as the first message.
> The LLM API key is added later. Until then the app runs in **fallback mode** (code checks + fuzzy matching + a built-in mock LLM), so every phase can be built and tested without a key.

---

## 0. Your role and working rules

You are a senior full-stack Python engineer and product UI designer. You will build the project specified below **one phase at a time** (Section 9).

**Working rules**
1. At the start of each phase, reply with a short plan (files to create or change, key functions, anything you are unsure about). Then build it.
2. Build ONLY the current phase. Do not skip ahead, and do not stub later phases.
3. Write complete, runnable files. No `TODO` or `pass` placeholders inside the current phase's scope.
4. Inside a phase, build the core functionality first and get it working, then add the visual polish for that phase.
5. At the end of each phase, report in exactly this format and then **STOP and wait for me to say "next phase"**:
   ```
   ## Phase N complete
   Files created/changed: ...
   How to run: <exact commands for Windows and macOS/Linux>
   What to test in the browser: <numbered click-by-click steps>
   Tests: <pytest command and result>
   Assumptions I made: ...
   Known issues: ...
   ```
6. If something in this spec is ambiguous, choose the simplest option that respects the hard boundaries, state the assumption in one line, and continue. Ask me only if a choice would break a hard boundary.
7. If I report a bug, fix it inside the current phase before moving on.
8. Code style: readable for a university course. Small functions, type hints, docstrings, comments explaining *why*. Format with standard PEP 8 style.
9. Use git: `git init` in Phase 0, and commit at the end of each phase with the message `Phase N: <summary>`.

---

## 1. Project context

**Course:** DATA722 Generative AI & Strategic Forecasting, mid-term project.

**Organisation:** "the Installer", a private rooftop-solar installation company in Karachi, Pakistan.

**Background:** In early 2026 NEPRA replaced net metering with net billing under the **NEPRA (Prosumer) Regulations 2026 (SRO 251(I)/2026)**. To export solar power, a customer must apply to their electricity distribution company (in Karachi, **K-Electric**). K-Electric's **Net Billing Guidelines (13 April 2026)** list the documents required. A PPIB-pre-qualified vendor (the Installer) processes the application for the customer.

**Problem:** Applications are often returned as incomplete. The DISCO checks completeness within 5 working days, and the applicant then has only 3 working days to supply missing items (Reg. 3(5)). Each return delays the customer's connection by weeks.

**Product:** the *Net-Billing Application Assistant*, an internal tool for the Installer's onboarding staff. Staff open a customer's application pack. The system:
1. checks it against the regulations and K-Electric's checklist,
2. flags missing documents and inconsistencies across documents,
3. writes a plain-language checklist for the customer in **English or Urdu**,
4. produces a pre-filled **DRAFT** application PDF that the customer reviews and signs.

**Design principle:** code decides; the LLM only matches and explains.

### Hard boundaries (never violate, in any phase)
1. **No autonomous action.** The system never submits an application, signs anything, or pays any fee. No submit or pay endpoint, button or function exists anywhere.
2. **Code decides hard rules.** Formats, dates, numbers and document lists are decided by Python code only. LLM output never changes a hard-rule verdict.
3. **LLM scope is limited** to (a) fuzzy name matching, (b) fuzzy address matching, (c) wording the customer checklist.
4. **No CNIC number or bill reference number is ever sent to the LLM.** A redaction function runs before every LLM call and is unit-tested.
5. **Synthetic data only.** No OCR, no images, no real people. JSON files stand in for data entered by staff.
6. **Draft values come from code only.** No LLM output is ever written into the draft PDF.

---

## 2. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11 or 3.12 |
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| Pages | Jinja2 templates (server-rendered) + vanilla JavaScript `fetch()` for interactivity |
| Styling | Tailwind CSS Play CDN `https://cdn.tailwindcss.com/3.4.5`, configured inline in `base.html` with `darkMode: 'class'` and the brand colours |
| Icons | Lucide `https://unpkg.com/lucide@0.460.0/dist/umd/lucide.min.js` |
| Charts | Chart.js `https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js` |
| Fonts | Google Fonts: Inter (UI), JetBrains Mono (IDs, CNICs), Noto Nastaliq Urdu (Urdu text) |
| Fuzzy matching | `rapidfuzz` |
| LLM client | `openai` Python SDK used as a **generic OpenAI-compatible client** (works with OpenAI, Google Gemini, Groq, OpenRouter, Ollama, and others via `base_url`) |
| PDF | `reportlab` (create), `pypdf` (read back during evaluation) |
| Fake data | `faker-pk` with a hard-coded fallback list |
| Config | `python-dotenv` |
| Tests | `pytest`, `httpx` (FastAPI TestClient) |
| Environment | `uv` (preferred) **and** `requirements.txt` kept in sync, so `python -m venv` also works |

No React, no Node build step, no database. Runtime state lives in JSON files under `data/runtime/`.

---

## 3. Folder structure

```
netbilling-assistant/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app: page routes + API routes
│   ├── config.py          # settings from .env, rule constants, RULES_AS_OF, sources
│   ├── models.py          # Pydantic models: Pack, CheckResult, LLMVerdict, CaseReport, ChecklistResult
│   ├── storage.py         # read packs, read/write runtime JSON (reports, reviews, audit, eval)
│   ├── rules.py           # R1–R7 deterministic checks
│   ├── redact.py          # strips CNIC/reference numbers before any LLM call
│   ├── llm_client.py      # provider-agnostic client: none | mock | openai_compatible
│   ├── prompts.py         # all LLM system prompts in one place
│   ├── llm_checks.py      # L1 name match, L2 address match, shadow checks, fuzzy fallback
│   ├── merge.py           # combine results, overall status, readiness score
│   ├── checklist.py       # L3 checklist + faithfulness gate + template fallback
│   ├── draft_pdf.py       # draft application PDF
│   ├── audit.py           # append-only audit trail per case
│   └── evaluate.py        # per-case evaluation + summary metrics
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── case.html
│   ├── evaluate.html
│   ├── about.html
│   └── partials/          # Jinja macros: status_chip, doc_cards, check_row, metric_card
├── static/
│   ├── app.js             # fetch helpers, toasts, theme, modal, animations
│   ├── case.js            # case page logic
│   ├── evaluate.js        # evaluation page logic + charts
│   └── styles.css         # custom CSS beyond Tailwind (RTL, document textures, gauge, print)
├── data/
│   ├── cases/C01.json … C21.json
│   ├── expected.csv
│   └── runtime/           # reports/, reviews.json, audit/, eval/, llm_log.jsonl  (gitignored)
├── tests/
│   ├── test_rules.py
│   ├── test_redact.py
│   ├── test_llm_checks.py
│   ├── test_checklist_gate.py
│   └── test_api.py
├── docs/
│   ├── DEMO_SCRIPT.md
│   └── screenshots/
├── make_cases.py
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 4. Configuration and the LLM provider (key added later)

`.env.example`:
```
# none = no LLM (fuzzy fallback only) · mock = deterministic fake LLM for testing · openai_compatible = real API
LLM_PROVIDER=mock
LLM_MODEL=
LLM_API_KEY=
LLM_BASE_URL=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

Example values to document in the README (do not hard-code them):
| Provider | LLM_BASE_URL | LLM_MODEL (example) |
|---|---|---|
| OpenAI | *(leave empty)* | gpt-4o-mini |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | gemini-2.0-flash |
| Groq | `https://api.groq.com/openai/v1` | llama-3.3-70b-versatile |
| Ollama (local) | `http://localhost:11434/v1` | qwen2.5:7b |

**`llm_client.py` requirements**
- One function: `complete_json(system: str, user: str, temperature: float) -> tuple[dict | None, dict]`, returning the parsed JSON (or `None`) and metadata `{provider, model, latency_ms, ok, error, attempts}`.
- `none`: returns `None` immediately, so callers use the fuzzy fallback.
- `mock`: a deterministic fake LLM so the whole UI works before a key exists. For L1/L2 it uses rapidfuzz plus the variant rules in Section 6.2 to return realistic JSON. For L3 it builds the checklist from templates. For shadow checks it returns the correct answer, except it deliberately gets **C18's capacity wrong**, so the "Code vs LLM disagreement" UI has something to show. Every mock response is labelled `provider: "mock"`.
- `openai_compatible`: uses `openai.OpenAI(api_key, base_url)`. Ask for JSON in the prompt. Try `response_format={"type": "json_object"}` first; if the provider rejects it, retry without. Parse robustly: strip code fences and extract the first `{...}` block. Retry with backoff (1s, 3s) on timeouts, 429 and 5xx. Never raise to the caller: always return `(None, meta)` on failure.
- Every call is appended to `data/runtime/llm_log.jsonl`: timestamp, case_id, task (L1/L2/L3/shadow), provider, model, SHA-256 of the prompt, the **redacted** input, raw output, latency, ok/error.
- `GET /api/health` returns `{status, llm_provider, llm_model, llm_configured: bool, mode: "live"|"mock"|"fallback"}`.

**Switching to the real API later must need only `.env` changes and a server restart, with no code changes.**

---

## 5. Data

### 5.1 Pack schema (`models.Pack`)
```json
{
  "case_id": "C07",
  "category": "clean",
  "description": "Clean commercial pack, 10 kW on a 15 kW sanctioned load",
  "applicant_type": "residential",
  "cnic": {"name": "", "father_name": "", "cnic_no": "42101-1234567-1", "expiry": "YYYY-MM-DD", "address": ""},
  "bill": {"consumer_name": "", "reference_no": "", "sanctioned_load_kw": 10, "connected_load_kw": 10,
           "tariff": "A-1", "connection_phase": "3-phase", "address": ""},
  "ownership": {"type": "sale_deed", "owner_name": "", "property_address": ""},
  "system": {"proposed_kw": 8, "inverter_kw": 8, "panel_count": 15, "panel_watt": 550},
  "is_tenant": false,
  "docs_present": ["cnic", "bill", "ownership", "single_line_diagram", "affidavit",
                   "vendor_checklist", "inverter_datasheet", "inverter_settings_letter"]
}
```
- `category`: `"clean"` or `"trap"` (used by dashboard filters and evaluation).
- `applicant_type`: `"residential"` or `"commercial"`.
- `ownership.type`: `"sale_deed"`, `"lease_deed"`, `"allotment_letter"` or `"none"`.
- `tariff`: residential `A-1`, commercial `A-2`, industrial `B-1` to `B-3`.
- `panel_count` = ceil(proposed_kw × 1000 / panel_watt).

### 5.2 `make_cases.py`
- Generate exactly **21 packs** into `data/cases/`. Use `faker-pk` seeded with `random.seed(722)`. If `faker-pk` is unavailable, fall back to a hard-coded list of 30 Pakistani names and 15 Karachi addresses (Gulshan-e-Iqbal, PECHS, DHA, North Nazimabad, Clifton, Korangi, Malir, etc.). The script must be reproducible: same output for the same date.
- Karachi CNICs start with `42`. Expiry dates are relative to `date.today()`.
- **Defaults** for every pack unless the table says otherwise: CNIC valid for 4 more years; `connection_phase` "3-phase"; `connected_load_kw` = `sanctioned_load_kw`; `proposed_kw` below the sanctioned load; `applicant_type` "residential"; `is_tenant` false; `docs_present` contains all base documents from R5; the same person and the same address on all three documents (identical spelling unless the table says otherwise).
- **Tenant rule:** when `is_tenant` is true, the deed owner (landlord) is expected to differ, and the `noc` document covers it.
- Write `data/expected.csv` from the table below. **The expected values come from this table, never from running `rules.py`**, because the file is the independent ground truth.
- Columns: `case_id, category, cnic_format, cnic_expiry, capacity, connection_phase, connected_load, required_docs, name_match, address_match, overall`. Check values are `PASS`/`FAIL`; overall is `READY`/`NOT_READY`.

| Case | Category | What to set | Expected FAIL (all others PASS) |
|---|---|---|---|
| C01 | clean | all consistent | — |
| C02 | clean | proposed_kw = sanctioned_load_kw = 5 | — |
| C03 | clean | CNIC "Muhammad Usman", bill "M. Usman" | — |
| C04 | clean | CNIC/deed "House 45-A, PECHS Block 2, Karachi", bill "H# 45-A PECHS Blk-2 Khi" | — |
| C05 | clean | CNIC "Mohammad Hamza Qureshi", deed "Muhammad Hamza Qureshi" | — |
| C06 | clean | tenant, landlord on lease_deed, `noc` present, CNIC name = bill name | — |
| C07 | clean | commercial, tariff A-2, 10 kW on 15 kW load | — |
| C08 | clean | CNIC "Syed Ali Raza", bill "S. Ali Raza" | — |
| C09 | trap | proposed 12 kW, sanctioned 10 kW | capacity |
| C10 | trap | CNIC expired 75 days ago | cnic_expiry |
| C11 | trap | bill consumer is a different person (different first and family name) | name_match |
| C12 | trap | bill address is a different property in Korangi | address_match |
| C13 | trap | tenant, landlord on deed, CNIC name = bill name, `noc` missing | required_docs |
| C14 | trap | `single_line_diagram` missing | required_docs |
| C15 | trap | `connection_phase` "1-phase" | connection_phase |
| C16 | trap | commercial, tariff B-3, 300 kW on 400 kW load; CNIC, bill and deed all in the factory owner's name; has `ntn` and `form_29`; `load_flow_study` missing | required_docs |
| C17 | trap | CNIC number "4210112345671" (no dashes) | cnic_format |
| C18 | trap | proposed 14 kW on 10 kW load AND CNIC expired | capacity, cnic_expiry |
| C19 | trap | `affidavit` missing | required_docs |
| C20 | trap | deed owner is a different person, `is_tenant` false | name_match |
| C21 | trap | connected load 12 kW, sanctioned 10 kW, proposed 8 kW | connected_load |

---

## 6. Business logic

`config.py` holds all constants, plus:
```
RULES_AS_OF = "2026-04-13"
RULES_SOURCE = "NEPRA (Prosumer) Regulations 2026 (SRO 251(I)/2026) and K-Electric Net Billing Guidelines (13 Apr 2026)"
FEE_PER_KW_RS = 1000
LOAD_FLOW_THRESHOLD_KW = 250
```

### 6.1 Code checks (`rules.py`), final and never overridden

| ID | Key | Check | Logic | Citation |
|---|---|---|---|---|
| R1 | cnic_format | CNIC format | regex `^\d{5}-\d{7}-\d$` | NADRA CNIC format |
| R2 | cnic_expiry | CNIC validity | `expiry >= today` | Installer policy |
| R3 | capacity | System size | `proposed_kw <= sanctioned_load_kw` | Reg. 3(2) |
| R4 | connection_phase | Connection type | `connection_phase == "3-phase"` | Reg. 2(1)(v) |
| R5 | required_docs | Required documents | base: cnic, bill, ownership, single_line_diagram, affidavit, vendor_checklist, inverter_datasheet, inverter_settings_letter; + `noc` if tenant; + `load_flow_study` if proposed_kw ≥ 250; + `ntn` and `form_29` if commercial and proposed_kw ≥ 250. Output includes `missing: [...]` and `required: [...]` | Reg. 3(3), 3(4), Sch. II & V; KE Guidelines |
| R6 | fee | Fee estimate (INFO) | `proposed_kw × FEE_PER_KW_RS` | Schedule-IV |
| R7 | connected_load | Connected load | `connected_load_kw <= sanctioned_load_kw`; on fail: "Regularise the connected load with K-Electric before applying" | KE Guidelines |

Each check returns `CheckResult {id, key, name, status: PASS|FAIL|INFO, detail, citation, source: "code", data: {...}}`, where `data` carries the numbers used (for gauges). The `detail` text is human-readable, e.g. "Proposed 12 kW exceeds the sanctioned load of 10 kW".

Human-friendly document labels (used everywhere in the UI): cnic "CNIC copy", bill "Latest K-Electric bill", ownership "Proof of ownership", single_line_diagram "Single-line diagram", affidavit "Affidavit (Schedule-V)", vendor_checklist "Vendor checklist", inverter_datasheet "Inverter data sheet", inverter_settings_letter "Inverter settings letter", noc "Owner's NOC", load_flow_study "Load-flow study", ntn "NTN certificate", form_29 "Form 29 / incorporation".

### 6.2 LLM checks (`llm_checks.py` + `prompts.py`)

**Redaction (`redact.py`):** build LLM inputs from an allow-list of fields only (names, addresses, `is_tenant`, and for shadow checks the expiry date, today's date and the kW values). As a second layer, scrub any string matching `\d{5}-?\d{7}-?\d` or 10+ consecutive digits, replacing it with `[REDACTED]`. `tests/test_redact.py` runs every pack through every LLM input builder and asserts that no CNIC or reference number appears.

**L1 name match.** Input: `{cnic_name, bill_consumer_name, deed_owner_name, is_tenant}`. System prompt:
```
You check whether names on Pakistani documents refer to the same person.
Rules:
- Spelling variants and abbreviations of the same name mean the same person:
  Muhammad/Mohammad/Mohd/M., Syed/Sayed/S., Abdul/Abd., a missing middle name.
- Ignore titles and honorifics (Mr, Mrs, Dr, Haji, Engr).
- A different first name or a different family name means a different person.
- If is_tenant is true, ignore deed_owner_name; compare only cnic_name and bill_consumer_name.
- If you cannot decide, answer UNSURE. Never guess.
Return ONLY this JSON:
{"verdict":"PASS|FAIL|UNSURE","confidence":0.0,"reason":"one short sentence","evidence":["cnic_name vs bill_consumer_name: ..."]}
```

**L2 address match.** Input: `{cnic_address, bill_address, deed_address}`. System prompt:
```
You check whether addresses on Pakistani documents refer to the same property in Karachi.
Rules:
- These are equal: House/H#/H-/H.No, Block/Blk/B-, Street/St, Phase/Ph, Sector/Sec, Road/Rd,
  Gulshan-e-Iqbal/Gulshan Iqbal, Karachi/Khi. Ignore punctuation, case and word order.
- A different house or plot number, block, sector, phase or area means a different property.
- If you cannot decide, answer UNSURE.
Return ONLY this JSON:
{"verdict":"PASS|FAIL|UNSURE","confidence":0.0,"reason":"one short sentence","evidence":["cnic_address vs bill_address: ..."]}
```

**Settings:** temperature 0. Validate the output with the `LLMVerdict` Pydantic model. Invalid output is treated as a failed call.

**Fuzzy score (always computed):** normalise both strings (lowercase, expand the abbreviations listed above, remove punctuation), then `rapidfuzz.fuzz.token_set_ratio` for each pair; report the minimum. Shown beside the LLM verdict.

**Fallback** (provider `none`, or the LLM failed after retries): verdict from the fuzzy score, ≥ 85 PASS, 60–84 UNSURE, < 60 FAIL, with `source: "fuzzy-fallback"`. The UI shows a "Fallback mode" badge on those rows.

**Shadow checks (research only, never used for verdicts):** ask the LLM to judge R2 and R3 from raw values:
```
Answer two questions from the data. Return ONLY JSON:
{"cnic_valid": true|false, "capacity_ok": true|false, "reasoning": "one sentence"}
Data: {"cnic_expiry": "...", "today": "...", "proposed_kw": ..., "sanctioned_load_kw": ...}
```
Store the answers and whether they agree with code. Shown in the "Code vs LLM" panel and on the evaluation page. These checks are skipped in `none` mode.

Each LLM-based result is a `CheckResult` with `source` set to `"llm"`, `"mock-llm"` or `"fuzzy-fallback"`, plus `llm: {verdict, confidence, reason, evidence, fuzzy_score, latency_ms, model}`.

### 6.3 Merge (`merge.py`)
- **Overall status:** `NOT_READY` if any of R1–R5, R7, L1, L2 is FAIL; otherwise `NEEDS_REVIEW` if any is UNSURE; otherwise `READY`. R6 is informational.
- **Readiness score** = PASS count ÷ 8 (R1–R5, R7, L1, L2) × 100.
- Save the latest `CaseReport` to `data/runtime/reports/{id}.json`, including the timestamp, mode and every result. The dashboard reads these.
- Before any check runs, a case's status is `PENDING`.

### 6.4 Customer checklist (`checklist.py`)
- Input to the LLM: only the failed or unsure checks as `[{check_id, detail, citation}]` (redacted) and the language `en` or `ur`.
- If nothing failed: skip the LLM and return a single item, "All checks passed. The draft is ready for your review and signature." (with an Urdu equivalent).
- System prompt (temperature 0.2):
```
You write a short, polite checklist for a solar customer in Karachi whose net-billing application needs fixing.
Use ONLY the issues given. Write exactly one item per issue, in the order given.
Each item tells the customer what to do, in plain words, in 1–2 sentences, and ends with the citation in brackets.
No greeting, no sign-off, no extra advice, no new requirements, no numbers that are not in the issue.
Language: {LANG}. For Urdu use natural Urdu script (not Roman Urdu); keep citations and numbers in English digits.
Return ONLY JSON: {"items":[{"check_id":"R3","text":"..."}]}
```
- **Faithfulness gate:** reject the output if (a) any `check_id` is not in the input set, (b) any input check is missing, (c) the item count differs, or (d) any number in the text does not appear in that issue's detail or citation. On rejection, use a code-built template checklist (with hand-written English and Urdu templates for every check key) and report `gate: "rejected", reason`. On success, report `gate: "passed"`.
- Return `ChecklistResult {lang, items, gate, gate_reason, source}`.

### 6.5 Draft PDF (`draft_pdf.py`)
- A4, clean layout. Title: "DRAFT — Net-Billing Application (Schedule-II fields)". Subtitle with the case ID and generation timestamp.
- A diagonal light-grey watermark on every page: "DRAFT — customer must review and sign".
- Sections: Applicant (name, father name, masked CNIC `42101-*******-1`, CNIC expiry) · Premises (address, ownership type, tenant yes/no) · Electricity connection (masked reference `01********12`, tariff, phase, sanctioned and connected load) · Proposed system (kW, inverter kW, panels × watt) · Documents (a table of required documents, each marked present or missing) · Fee estimate · Check summary (overall status + failed checks) · Declaration text and an **empty** signature and date box for the customer.
- Footer: "Rules as of 13 Apr 2026 · Synthetic data · Generated by NetBill Assist — not submitted".
- All values come from the pack JSON via code. No LLM output.
- `GET /api/draft/{id}` serves it with `Content-Disposition: inline`; `?download=1` switches to `attachment; filename="draft_{id}.pdf"`.

### 6.6 Review and audit (`audit.py`)
- `POST /api/review/{id}` with body `{staff_name, note}`. Allowed only after checks have run. Stores the record in `reviews.json` and does not change the overall status.
- Append-only audit trail at `data/runtime/audit/{id}.jsonl`: checks run (mode, overall), each LLM call (task, latency, ok), checklist generated (lang, gate), draft generated, reviewed (by whom).

---

## 7. API

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Dashboard page |
| GET | `/case/{id}` | Case page |
| GET | `/evaluate` | Evaluation page |
| GET | `/about` | About page |
| GET | `/api/health` | Health + LLM mode |
| GET | `/api/cases` | `[{case_id, category, description, applicant_name, proposed_kw, sanctioned_load_kw, docs_present_count, docs_required_count, overall, readiness, reviewed}]` |
| GET | `/api/cases/{id}` | Pack + latest report (if any) + review (if any) |
| POST | `/api/check/{id}?use_llm=true` | Runs R1–R7 (+ L1, L2, shadow) → CaseReport |
| POST | `/api/checklist/{id}?lang=en\|ur` | ChecklistResult |
| GET | `/api/draft/{id}` | Draft PDF |
| POST | `/api/review/{id}` | Mark reviewed |
| GET | `/api/audit/{id}` | Audit trail entries |
| POST | `/api/evaluate/case/{id}?runs=3` | Evaluates one case and stores the result in `data/runtime/eval/` |
| GET | `/api/evaluate/summary` | Aggregated metrics from the stored per-case results |
| GET | `/api/evaluate/export.csv` | Per-case, per-check results as CSV |

The "Run all checks" and "Run evaluation" buttons loop over cases **client-side**, calling the per-case endpoint one case at a time and updating a progress bar. This keeps the backend simple, with no background jobs. Unknown case IDs return 404 with JSON `{detail}`. All errors show as toasts in the UI.

---

## 8. UI / UX specification — rich, polished, professional

### 8.1 Design language
- Modern SaaS dashboard: background `slate-50` (dark: `slate-950`), white cards (dark: `slate-900`) with `rounded-2xl`, soft shadow and a 1px `slate-200` border (dark: `slate-800`). Generous whitespace, 8px spacing grid.
- **Brand colours:** solar amber `#F59E0B` (primary buttons, active nav, highlights), deep navy `#0F172A` (sidebar, headings), grid teal `#0D9488` (secondary accents), LLM purple `#7C3AED` (anything produced by the LLM).
- **Status system (identical everywhere):** PASS emerald + `check-circle` · FAIL rose + `x-circle` · UNSURE / NEEDS_REVIEW amber + `alert-triangle` · INFO sky + `info` · PENDING slate + `clock` · READY emerald + `badge-check` · NOT_READY rose + `octagon-x`. Status chips are rounded pills, icon + label, and never colour alone.
- **Source badges:** `CODE` (navy), `LLM` (purple), `MOCK LLM` (purple outline), `FALLBACK` (amber outline).
- **Typography:** Inter. Page titles 24–28px semibold, section titles 18px, body 14–15px. Numbers use tabular figures. IDs and CNICs in JetBrains Mono.
- **Dark mode:** a toggle in the top bar, saved in `localStorage` (wrap reads and writes in try/catch), applied before first paint to avoid a flash.
- **Motion:** 150–300ms ease-out. Cards fade and slide up on load, check rows appear staggered, the readiness ring and gauge animate their fill, skeleton shimmer while loading. Everything is disabled under `prefers-reduced-motion`.
- **Accessibility:** visible focus rings (amber), `aria-label`s on icon-only buttons, tab panels with proper ARIA roles and arrow-key navigation, contrast ≥ 4.5:1, Urdu blocks with `lang="ur" dir="rtl"`.
- **Responsive:** the sidebar becomes a hamburger drawer under 1024px; cards stack under 768px; the cases table becomes a card list under 640px; no horizontal page scroll at 375px.

### 8.2 Layout (`base.html`)
- **Sidebar (navy):** logo (Lucide `sun` in an amber rounded square + "NetBill Assist" + small "Net-billing application assistant"), nav items Dashboard / Evaluation / About with icons and the active item highlighted amber. At the bottom: a "Rules as of 13 Apr 2026" pill and an **LLM mode indicator** from `/api/health` (green dot "Live · model-name", purple dot "Mock LLM", amber dot "Fallback · no LLM").
- **Top bar:** page title + breadcrumb, a global search (on the dashboard it filters cases), the default checklist-language toggle EN | اردو (sets the default language for checklists only; the UI itself stays in English), and the dark-mode toggle.
- **Safety banner** (thin, below the top bar, dismissible per session): "Synthetic data only · This tool never submits applications or pays fees".
- **Toasts:** bottom-right, auto-dismiss after 4s, success/error/info variants with icons.
- **Modal component:** reused for "Mark reviewed" and for confirmations.
- **Footer** on every page: the rules source and as-of date, plus "Estimates based on synthetic data".

### 8.3 Dashboard (`/`)
- **Hero strip:** greeting "Onboarding queue", a subtitle with the date, and a primary "Run all checks" button. A progress bar appears under it while running ("Checking C07… 7/21").
- **KPI cards (4):** Total cases · Ready · Needs review · Not ready, each with an icon in a tinted circle, a large number, the percentage of the total and a thin progress bar in the status colour. Clicking a card applies that filter.
- **Insight card:** "Most common issue" (the most frequently failed check across reports, with its count) and "Documents most often missing" (top 3 chips).
- **Filter bar:** chips All / Ready / Needs review / Not ready / Pending / Clean / Traps, a search box, and a sort dropdown.
- **Cases table:** case ID (mono) · applicant name + a small description underneath · type icon (home / building) · **capacity mini-bar** (proposed vs sanctioned, turning rose when over, label "12 / 10 kW") · documents "7/8" with a tiny progress ring · readiness % · overall status chip · reviewed badge (teal `user-check` + initials) · "Open" button. Sortable headers, row hover, the whole row clickable.
- States: skeleton rows while loading; an empty state with an illustration-style icon when filters match nothing.

### 8.4 Case page (`/case/{id}`), the main screen
**Header card:** back link, case ID (mono), applicant name (large), description, category badge (Clean / Trap), overall status badge (large), **readiness ring** (animated SVG circle with % in the centre), "Last checked 2 min ago · Mock LLM" meta line. Actions: **Run checks** (amber primary, spinner while running), **Generate checklist**, **Download draft**, **Mark reviewed** (disabled until checks run; opens a modal asking for staff name and an optional note). There is no submit or pay button.

**Stepper** under the header: ① Documents → ② Checks → ③ Checklist & draft → ④ Staff review. Steps light up as they are completed.

**Section A — Documents** (three cards side by side, designed to look like the real documents):
- *CNIC card:* rounded ID-card shape with a green gradient header ("Islamic Republic of Pakistan · National Identity Card", styled text only, no emblem or real logo), a silhouette avatar, name, father name, masked CNIC in mono, expiry date. A rose "EXPIRED" ribbon on the corner if expired; a rose outline on the CNIC number if R1 fails.
- *Electricity bill card:* a white card with a navy header strip reading "Electricity Bill (K-Electric)" as plain text (no logo), masked reference number, consumer name, address, and a small grid: sanctioned load · connected load · tariff · phase. Fields involved in failed checks are outlined rose.
- *Ownership card:* a cream "paper" background with a subtle texture, a serif heading ("Sale Deed" / "Lease Deed"), owner name, property address, and a "Tenant · NOC on file" or "Tenant · NOC missing" badge when relevant.
- **Cross-document highlighting:** after L1/L2 run, the compared name and address fields get a coloured left border and tint (emerald match, amber unsure, rose mismatch). Hovering a name or address highlights the corresponding fields on the other two cards and shows a tooltip with the LLM's reason.
- **Documents strip:** every required document as a chip with an icon (emerald check if present, rose cross if missing). Missing chips show a tooltip "Required by …" with the citation. A header shows "7 of 8 documents".

**Section B — Checks:**
- A two-column layout on desktop. **Left:** the list of check rows. **Right:** visual panels.
- **Check row:** status icon · name · status chip · one-line detail · citation pill · source badge. LLM rows expand (chevron) to show the verdict, a confidence bar, the reason, evidence pairs, the fuzzy score with a mini bar, the latency and the model.
- When checks run, rows show a loader and then resolve one by one (staggered by about 120ms) for a satisfying "checking" feel.
- **Right panels:**
  1. **Capacity gauge:** an SVG semicircle from 0 to 1.5 × sanctioned load, with a teal zone up to the sanctioned load and a rose zone beyond. The needle shows proposed kW and animates on load. Labels: "Proposed 12 kW · Limit 10 kW".
  2. **Load panel:** two small horizontal bars, connected vs sanctioned.
  3. **Fee card:** "Estimated NEPRA fee: Rs 8,000 (8 kW × Rs 1,000)".
  4. **Code vs LLM panel** (purple-accented): for each shadow check, the code answer vs the LLM answer with ✓ agree or ⚠ disagree. On disagreement: "LLM said capacity OK, code found 14 kW > 10 kW → code decides". If skipped: "Shadow checks need an LLM".

**Section C — Checklist & draft** (tabs, keyboard-accessible):
- *Customer checklist:* an EN | اردو segmented control, numbered items in a card styled like a message preview, citation pills. Urdu renders RTL in Noto Nastaliq Urdu at 18px with line-height 2.2. A gate badge: "Verified against checks" (emerald, `shield-check`) or "Template fallback: LLM output rejected" (amber, with the reason on hover). Buttons: "Copy text" (plain text with numbering) and "Regenerate".
- *Draft application:* a PDF preview in an `<iframe>` (about 700px tall), a Download button, and an info callout: "The customer must review and sign this draft. Staff then submit it through the K-Electric portal. This tool never submits."
- *Audit trail:* a vertical timeline with icons, timestamps (relative and absolute on hover), and the event details.

**Section D — Review status:** if reviewed, a teal card shows "Reviewed by {name} on {date}" and the note.

### 8.5 Evaluation page (`/evaluate`)
- **Header:** an explanation line, the current LLM mode badge, a runs selector (1 or 3), and a **Run evaluation** button with a progress bar per case. A warning chip appears if the mode is mock or fallback ("Results reflect mock LLM; add an API key for real results").
- **Metric cards (grid):** Wrong values in draft (target 0) · Code rule accuracy (target 100%) · Trap recall (target 100%) · LLM match accuracy (target ≥ 90%) · False alarms on clean cases · Deferred to staff (UNSURE rate) · Checklist faithfulness (gate pass rate) · LLM consistency across runs · Average LLM latency. Each card shows the value, target, and a tick or cross.
- **Charts (Chart.js, themed for light and dark):**
  1. Horizontal bar: accuracy per check (R1–R5, R7, L1, L2).
  2. Doughnut: outcomes across trap cases (caught / deferred / missed).
  3. **Headline chart:** grouped bar of code vs LLM agreement on the shadow checks per case, with disagreements highlighted rose.
  4. Bar: LLM latency per case.
- **Results grid:** rows = cases, columns = checks; cells show the got/expected status with an emerald (match) or rose (mismatch) tint; hovering shows the detail; clicking a row opens the case.
- **Findings box:** auto-generated bullet points from the metrics (code-written, not LLM), e.g. "Code rules matched ground truth on 147/147 checks", "LLM disagreed with code on 1 of 42 hard-rule shadow checks (C18 capacity)".
- **Export CSV** button.

### 8.6 About page (`/about`)
Polished copy covering: what the tool does · the human gate (diagram: Staff review → Customer signs → Staff submits) · "code decides, LLM explains" · data handling (synthetic data, redaction, production would need in-country hosting for CNIC data under PECA 2016 §16 and §19) · limitations (no OCR, K-Electric checklist only, synthetic data) · sources as links:
- NEPRA Prosumer Regulations 2026: https://ke.com.pk/wp-content/uploads/2026/04/8.-NEPRA-Prosumer-Regulations-SRO-251I2026-09-02-26.pdf
- K-Electric Net Billing Guidelines (13 Apr 2026): https://ke.com.pk/wp-content/uploads/2026/04/Net-Billing-Guidelines-13th-Apr26.pdf

---

## 9. Build phases (stop and wait after each)

### Phase 0 — Setup and shell
- Project skeleton, `pyproject.toml` + `requirements.txt`, `.env.example`, `.gitignore` (`.env`, `.venv/`, `data/runtime/`, `__pycache__/`, `.pytest_cache/`), `git init`.
- `config.py` with settings and constants; `llm_client.py` with the `none` and `mock` providers and the `openai_compatible` skeleton fully implemented (it simply won't be used until a key exists).
- `base.html` with the complete layout: sidebar, top bar, safety banner, footer, dark-mode toggle, toast system, modal component, LLM mode indicator.
- Placeholder dashboard, evaluate and about pages that use the layout. `/api/health`.
- **Test:** open `http://127.0.0.1:8000`, switch dark mode and reload (it persists), trigger a demo toast, check the sidebar mode shows "Mock LLM", resize to a phone width.
- **Accept when:** one command starts the server; no console errors except the Tailwind Play CDN's production warning.

### Phase 1 — Data and dashboard
- `make_cases.py`, 21 packs, `expected.csv`, `models.py`, `storage.py`, `/api/cases`, `/api/cases/{id}`.
- Full dashboard UI: KPI cards, filters, search, sort, cases table with capacity mini-bars and document counts (statuses PENDING for now), skeleton and empty states.
- `tests/test_api.py`: the cases endpoint returns 21 items; a pack validates against the schema.
- **Test:** the dashboard lists 21 cases; the filters, search and sort work; C09's capacity bar is rose.
- **Accept when:** running `make_cases.py` twice on the same day gives identical files.

### Phase 2 — Rules and case page
- `rules.py` (R1–R7), `merge.py` (with L1/L2 temporarily PENDING), `/api/check/{id}?use_llm=false`, report storage.
- Case page: header, readiness ring, stepper, document cards with failure outlines, documents strip, check rows with animation, capacity gauge, load panel, fee card.
- Dashboard "Run all checks" with a progress bar and live status updates.
- `tests/test_rules.py`: R1–R5 and R7 match `expected.csv` for all 21 cases, plus edge cases (kW equal to the load, expiry today).
- **Test:** C09 capacity gauge in the rose zone; C10 shows the EXPIRED ribbon; C14 has a missing chip; C21 fails connected load; C02 passes at exactly the limit.
- **Accept when:** all rule tests pass.

### Phase 3 — LLM checks (mock / fallback now, real API later)
- `redact.py`, `prompts.py`, `llm_checks.py` (L1, L2, fuzzy score, fallback, shadow checks), merge with real L1/L2, `use_llm=true`.
- UI: LLM check rows with expandable details, source badges, cross-document highlighting and hover linking, the Code vs LLM panel, fallback badges.
- Tests: `test_redact.py` (no CNIC or reference numbers in any LLM input for all 21 packs); `test_llm_checks.py` (with the mock provider: C03, C04, C05 and C08 pass; C11, C12 and C20 fail; invalid JSON from a stubbed client falls back without crashing).
- **Test:** with `LLM_PROVIDER=mock`, C03 name passes with an LLM reason; C11 fails with rose highlights across the cards; C18 shows a Code vs LLM disagreement. With `LLM_PROVIDER=none`, fallback badges appear and the app still works.
- **Accept when:** all tests pass in both `mock` and `none` modes.

### Phase 4 — Checklist, draft PDF, review and audit
- `checklist.py` with the faithfulness gate and the English and Urdu templates; `draft_pdf.py`; `audit.py`; the review endpoint; the audit endpoint.
- UI: the checklist tab (EN/Urdu, RTL, gate badge, copy, regenerate), draft tab with iframe preview, audit timeline, review modal and review card, stepper progression.
- `tests/test_checklist_gate.py`: the gate rejects an extra check_id, a missing check, and an invented number; accepts a valid output.
- **Test:** C18 checklist in Urdu renders RTL with 2 items; the C09 draft shows the watermark, masked CNIC and an empty signature box; mark C09 reviewed and see it on the dashboard.
- **Accept when:** gate tests pass, and the PDF opens in the iframe and downloads.

### Phase 5 — Evaluation
- `evaluate.py` (per-case evaluation, runs 1 or 3, PDF read-back with `pypdf` for "wrong values in draft"), the summary and export endpoints.
- Evaluation page: run controls with progress, metric cards, 4 charts, results grid, findings box, CSV export.
- **Scoring rules:** code checks compared with `expected.csv`. LLM checks: PASS/FAIL compared with `expected.csv`; **UNSURE is never correct**; on trap cases UNSURE counts as caught (deferred to staff); on clean cases UNSURE counts as a false alarm. Consistency = % of (case, check) pairs with an identical verdict across runs. Wrong values in draft = PDF fields that differ from the pack.
- **Test:** run the evaluation in mock mode; all metric cards and charts fill in; the C18 disagreement shows in the headline chart; export opens in Excel.
- **Accept when:** metrics match a manual spot-check of C03, C09 and C18.

### Phase 6 — Polish, accessibility and docs
- Responsive pass (375px, 768px, 1280px), dark-mode pass on every component and chart, keyboard pass, reduced-motion pass, error states (server down, LLM timeout), loading states everywhere.
- About page with full copy.
- `README.md`: overview, screenshots, architecture diagram (Mermaid), setup with uv and with venv on Windows and macOS/Linux, how to add the LLM API key (the provider table from Section 4), how to run tests, the phase summary, limitations.
- **Accept when:** no layout breaks at 375px; every page works in dark mode; `pytest` is all green.

### Phase 7 — Demo pack
- `docs/DEMO_SCRIPT.md`: a 4–5 minute walkthrough: dashboard overview → Run all checks → C03 (name variant passes) → C09 (over capacity, gauge, draft) → C11 (name mismatch, Urdu checklist) → C18 (Code vs LLM disagreement) → evaluation page and findings. Include what to say at each step.
- Capture screenshots into `docs/screenshots/` (use Playwright if available, otherwise list exactly which screens to capture manually).
- **Accept when:** following the script live works start to finish.

### Phase 8 — Switch to the real LLM (when I provide the key)
- I will give you the provider, model and key. Update only `.env` (and README notes if needed).
- Run the tests, then run the evaluation with runs = 3 and report the metric changes compared with mock mode, any prompt adjustments needed (making changes only in `prompts.py`), and any provider quirks handled in `llm_client.py`.
- **Accept when:** the app shows "Live · model-name", the evaluation completes, and the hard boundaries still hold.

---

## 10. Quality checklist (applies to every phase)
- No secrets in code; `.env` is gitignored.
- No network calls except the configured LLM endpoint and the listed CDNs and Google Fonts.
- Every check result shows its citation; every result page shows the rules as-of date and "Synthetic data".
- No submit or pay function exists anywhere in the codebase.
- Every LLM input passes through `redact.py`.
- Server-side errors never show a raw stack trace to the user: return JSON `{detail}` and show a toast.
- All pages work with JavaScript loading slowly: show skeletons, not blank screens.

**Begin with Phase 0. Start by replying with your plan for Phase 0.**
