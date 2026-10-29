# FEATURE PROMPT — CNIC Scanner (EasyOCR) for the Net-Billing Application Assistant

> Paste this into your AI coding agent **as a new task in the existing project**.
> This adds ONE feature: read a CNIC (front + back) from photos and pre-fill the CNIC fields.
> Manual entry stays exactly as it is. Where the scanner finally appears in the app will be decided later, so build it as a **self-contained, mountable component**.

---

## ⚠ RULE UPDATE — read this first

This task **replaces hard boundary 5** of the master prompt you were given earlier for this project.

**Old rule (no longer valid):**
> 5. **Synthetic data only.** No OCR, no images, no real people. JSON files stand in for data entered by staff.

**New rule (use from now on, in this task and all future tasks on this project):**
> 5. **Synthetic data only; OCR for the CNIC only, and only locally.** No real people's data. Packs are created by staff (manual entry or the CNIC scanner) or come from the synthetic JSON files. OCR is allowed **only for the CNIC front and back**. It runs **locally** with EasyOCR, uploaded images are processed in memory and **never written to disk, logged, or sent to any LLM or external API**, and OCR results are **suggestions that staff must confirm** before anything is saved. Bills, deeds and other documents are not OCR'd. All test images are synthetic, CNIC-like sample cards.

All other hard boundaries of the master prompt (1–4 and 6: no submit/pay, code decides hard rules, limited LLM scope, redaction before every LLM call, draft values from code only) **remain unchanged and still apply**.

**Make the update permanent in the project before writing any feature code:**
1. If the project has an agent instruction or rules file (for example `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.cursor/rules/*`, `.github/copilot-instructions.md`, or a saved copy of the master prompt), replace rule 5 there with the new wording. If no such file exists, create `docs/PROJECT_RULES.md` listing all six hard boundaries, with rule 5 in its new form.
2. Add a "Rule changes" section to `README.md`: date, old rule, new rule, reason ("CNIC scanner added: local OCR, staff-confirmed").
3. Update the About page's data-handling text and the safety banner if they say "no OCR" or similar.
4. In your Stage A report, list exactly which files you changed for this rule update.

---

## 0. Working rules
1. Work in the existing project. Do not change existing behaviour, routes, rules or the manual entry form, apart from the small integration hook in Section 7.
2. Build the stages in Section 10 one at a time. After each stage, report: files created/changed, how to run, what to test, test results, assumptions. Then **STOP and wait for "next stage"**.
3. Complete, runnable code only, with no placeholders. Type hints, docstrings, small functions.
4. If anything is ambiguous, pick the simplest option that respects Section 1, state the assumption, and continue.

---

## 1. Goal and boundaries

**Goal:** staff can either type CNIC details by hand OR upload photos of the CNIC front and back. The system reads them with EasyOCR, shows what it found with a confidence level per field, and staff choose which values to apply to the form. Staff can always edit any field afterwards.

**Hard boundaries**
1. **OCR runs locally only** (EasyOCR on this machine). CNIC images are never sent to any LLM or external API.
2. **Images are never written to disk.** Process them in memory and discard them after the response. Never log field values; log only timings, confidence numbers and warnings.
3. **OCR results are suggestions.** The scanner never saves a pack and never runs checks. It only returns values; the existing form and save flow persist the data after staff confirm.
4. **Manual entry always works,** including when EasyOCR is not installed or its models are not downloaded. The scanner then shows "Scanner unavailable" and the form works normally.
5. The OCR endpoint never returns the raw OCR text dump to the browser. It returns only the structured fields, their boxes and warnings.

---

## 2. Libraries

Add to `pyproject.toml` / `requirements.txt` as an **optional OCR group**, so the core app still installs without it:

| Package | Purpose |
|---|---|
| `easyocr` | OCR engine (English + Urdu) |
| `torch`, `torchvision` (CPU builds) | Required by EasyOCR |
| `opencv-python-headless` | Card detection, perspective fix, image clean-up |
| `numpy` | Image arrays |
| `Pillow` | Image loading, EXIF rotation, synthetic card generation |
| `python-multipart` | FastAPI file uploads |
| `rapidfuzz` | Fuzzy label matching ("Narne" ≈ "Name") (already in project) |
| `arabic-reshaper`, `python-bidi` | Correct Urdu shaping when **drawing** synthetic test cards with Pillow |
| `pillow-heif` *(optional)* | Accept iPhone HEIC photos |

**Install notes for the README** (Windows and macOS/Linux):
```bash
# 1) CPU-only PyTorch first (much smaller than the default CUDA build)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
# 2) OCR group
pip install easyocr opencv-python-headless python-multipart arabic-reshaper python-bidi pillow-heif
# with uv:
uv add easyocr opencv-python-headless python-multipart arabic-reshaper python-bidi pillow-heif --optional ocr
```
- EasyOCR downloads its detection and recognition models (about 100–200 MB) on first use. Add `OCR_MODEL_DIR` to `.env` (default `./.easyocr_models`, gitignored) and a script `python -m app.ocr.download_models` that pre-downloads them, so the first scan isn't slow during a demo.
- `.env` additions: `OCR_ENABLED=true`, `OCR_MODEL_DIR=./.easyocr_models`, `OCR_GPU=false`, `OCR_MAX_UPLOAD_MB=8`.

---

## 3. Module layout

```
app/ocr/
├── __init__.py
├── reader.py          # EasyOCR singleton: lazy load, warm-up, availability flag
├── preprocess.py      # load bytes → fix EXIF rotation → detect & straighten card → quality checks
├── extract_front.py   # front-side field extraction
├── extract_back.py    # back-side extraction (CNIC number + Urdu address)
├── normalize.py       # OCR character fixes, CNIC/date/gender normalisation
├── validate.py        # cross-field validation → warnings + confidence adjustments
├── schemas.py         # Pydantic models for the response
├── service.py         # scan_cnic(front_bytes, back_bytes) → CnicScanResult (orchestrates everything)
└── download_models.py
static/cnic_scanner.js          # mountable front-end component
templates/partials/cnic_scanner.html
templates/dev_cnic_scanner.html # standalone test page (until final placement is decided)
tools/make_cnic_images.py       # synthetic CNIC-like test images + ground truth
tools/eval_ocr.py               # accuracy evaluation
tests/ocr/                      # unit tests (no EasyOCR needed) + one slow integration test
```

---

## 4. How the function works

### 4.1 `reader.py`
- One global `easyocr.Reader(['ur', 'en'], gpu=OCR_GPU, model_storage_directory=OCR_MODEL_DIR)` created lazily on the first request and protected by a lock.
- `is_available() -> (bool, reason)`: false if `OCR_ENABLED` is false, `easyocr` isn't importable, or the models are missing and can't be downloaded.
- `readtext(img) -> list[OcrToken]` with `detail=1`, `paragraph=False`. Each token: `{text, conf, box: [x0, y0, x1, y1], script: "latin"|"urdu"|"mixed"}`. Script is detected from Unicode ranges (`؀-ۿ` = Urdu/Arabic).
- If there's a measurable gain, use an English-only reader for the front: create a second lazily-loaded `Reader(['en'])` and compare. Keep whichever is more accurate on the synthetic set, and document the choice.
- OCR is blocking: call it from FastAPI through `run_in_threadpool`.

### 4.2 `preprocess.py`
1. Read the bytes and reject anything that isn't JPG, PNG, WEBP or HEIC, or that exceeds `OCR_MAX_UPLOAD_MB`. Apply EXIF orientation (`ImageOps.exif_transpose`).
2. Downscale so the longest side is ≤ 1600 px.
3. **Card detection:** grayscale → blur → Canny edges → contours → the largest 4-point polygon with an aspect ratio close to an ID card (85.6 × 54 mm ≈ 1.586, tolerance ±0.25) covering ≥ 20% of the image. Perspective-warp it to **1000 × 630**.
   - Fallback: if no card outline is found, assume the photo is already cropped; resize to 1000 × 630 and add a warning `card_not_detected`.
4. **Orientation:** if after warping the OCR finds few tokens, also try a 180° rotation and keep whichever gives higher total confidence.
5. **Quality checks** (warnings, never blocking):
   - blur: variance of the Laplacian below a threshold → `image_blurry` ("Photo looks blurry, consider retaking")
   - too dark or too bright: mean brightness outside 60–200 → `poor_lighting`
   - glare: a large fraction of near-white pixels → `glare_detected`
6. Mild enhancement for OCR: CLAHE contrast on the grayscale copy. Keep a colour copy for the preview.
7. Return the straightened colour image (to show in the UI) plus the version prepared for OCR.

### 4.3 `extract_front.py`, using labels and positions
The front side has English labels with the value printed directly below each label: Name, Father Name (or Husband Name), Gender, Country of Stay, Identity Number, Date of Birth, Date of Issue, Date of Expiry.

1. **Find the labels:** fuzzy-match tokens (and pairs of adjacent tokens) against the label list using `rapidfuzz.fuzz.ratio ≥ 80`. Match two-word labels first so that "Father Name" is not mistaken for "Name".
2. **Pick the value for each label:** the Latin-script tokens whose top edge is within 0–70 px below the label's bottom edge and whose left edge is within ±40 px of the label's left edge. Join tokens on the same line left to right. Stop at the next label.
3. **Pattern fallback across all tokens** (when a label isn't found):
   - identity number: `\d{5}[-\s]?\d{7}[-\s]?\d` after normalisation
   - dates: `\d{2}[.\-/]\d{2}[.\-/]\d{4}`. If labels are missing but three dates exist, sort them: **earliest = date of birth, middle = issue, latest = expiry**
   - gender: a standalone `M` or `F` near the Gender label, or anywhere as a last resort
4. Output fields: `name`, `father_name` (with `relation: "father"|"husband"`), `gender`, `cnic_no`, `date_of_birth`, `date_of_issue`, `date_of_expiry`.

### 4.4 `extract_back.py`
1. **CNIC number:** the same number pattern, anywhere on the card (it is printed in English digits).
2. **Address (Urdu):** take the Urdu-script tokens in the main text area. Ignore tokens in the barcode/QR region and tiny tokens. Group them into lines (tokens whose vertical centres are within 12 px), sort lines top to bottom and tokens **right to left** within each line, then join.
   - If two address blocks are detected (present and permanent), return both as `address_urdu_lines` grouped by block, and set `address_urdu` to the first block.
3. Confidence for the Urdu address is capped at **0.7**, so it always shows amber and staff always look at it.
4. Output fields: `cnic_no_back`, `address_urdu`, `address_urdu_blocks`.

### 4.5 `normalize.py`
- **Character fixes in digit fields only:** O/o/D/Q → 0, I/l/|/! → 1, Z → 2, S/s → 5, G → 6, B → 8. Remove spaces. Never apply this to names.
- **CNIC:** strip everything except digits. If exactly 13 digits, format as `12345-1234567-1`; otherwise keep the raw value and add a warning.
- **Dates:** parse DD.MM.YYYY (also `-` and `/`) into ISO `YYYY-MM-DD`. Reject impossible dates.
- **Names:** collapse whitespace, Title Case, remove stray symbols, keep letters, spaces, dots and hyphens.
- **Gender:** map to `M` / `F`.

### 4.6 `validate.py`
Each rule adds a warning and adjusts the confidence of the fields involved:

| Rule | If it passes | If it fails |
|---|---|---|
| Front number = back number | both +0.10 | both capped at 0.5, warning `cnic_mismatch_front_back` |
| Last digit parity matches gender (odd = M, even = F, by convention) | +0.05 | warning `gender_digit_mismatch` (do not change the values) |
| DOB < issue < expiry | +0.05 each | dates involved capped at 0.5, warning `date_order_invalid` |
| Age at issue ≥ 18 | — | warning `age_unusual` |
| Expiry in the past | — | warning `cnic_expired` (information only; rule R2 in the main app decides) |
| Number starts with `42` | — | warning `non_karachi_cnic` (information only) |

**Final confidence per field** = OCR token confidence (mean of the tokens used) × pattern factor (1.0 if it matches the expected pattern, 0.6 if not) + validation adjustments, clamped to 0–1.
**Levels:** ≥ 0.80 `high` (green) · 0.50–0.79 `medium` (amber) · < 0.50 `low` (red) · not found `missing`.

### 4.7 `schemas.py`: the response

```json
{
  "ok": true,
  "available": true,
  "elapsed_ms": 4210,
  "fields": {
    "name":           {"value": "Ayesha Siddiqui", "confidence": 0.91, "level": "high",   "side": "front", "box": [120, 180, 430, 215]},
    "father_name":    {"value": "Imran Siddiqui",  "confidence": 0.86, "level": "high",   "side": "front", "box": [...], "relation": "father"},
    "gender":         {"value": "F",               "confidence": 0.78, "level": "medium", "side": "front", "box": [...]},
    "cnic_no":        {"value": "42101-1234567-2", "confidence": 0.97, "level": "high",   "side": "front", "box": [...]},
    "date_of_birth":  {"value": "1990-04-12", ...},
    "date_of_issue":  {"value": "2022-01-05", ...},
    "date_of_expiry": {"value": "2032-01-05", ...},
    "cnic_no_back":   {"value": "42101-1234567-2", ...,  "side": "back"},
    "address_urdu":   {"value": "مکان نمبر ۱۲، بلاک ۵، گلشن اقبال، کراچی", "confidence": 0.62, "level": "medium", "side": "back", "box": [...]}
  },
  "warnings": [{"code": "image_blurry", "side": "back", "message": "Back photo looks blurry, consider retaking."}],
  "preview": {
    "front": "data:image/jpeg;base64,...",
    "back":  "data:image/jpeg;base64,..."
  }
}
```
- `box` coordinates refer to the straightened 1000 × 630 preview image, so the UI can draw them directly.
- Previews are JPEG quality 70, generated in memory, and only included in this response.
- Either side is optional: front only, back only, or both. Missing sides give `missing` fields and no error.

### 4.8 `service.py`
`scan_cnic(front: bytes | None, back: bytes | None) -> CnicScanResult` runs preprocess → OCR → extract → normalise → validate → build the response. Each side runs in a try/except so one bad photo doesn't fail the other. Log `elapsed_ms`, token counts, confidence levels and warning codes only.

---

## 5. API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/ocr/status` | `{available, reason, models_ready, languages: ["ur","en"]}` |
| POST | `/api/ocr/cnic` | multipart form: `front` (file, optional), `back` (file, optional) → `CnicScanResult` |
| POST | `/api/ocr/warmup` | Loads the reader and runs a tiny dummy image (call it in the background when the modal opens) |

Errors return JSON `{detail, code}`: `ocr_unavailable` (503), `file_too_large` (413), `unsupported_type` (415), `no_file` (400). No stack traces.

---

## 6. Front-end component (mountable)

`static/cnic_scanner.js` exposes:
```js
CnicScanner.mount(containerElement, {
  fieldMap: {                       // scanner field → CSS selector of the existing manual input
    name: '#cnic_name',
    father_name: '#cnic_father_name',
    cnic_no: '#cnic_no',
    date_of_expiry: '#cnic_expiry',
    gender: '#cnic_gender',          // optional if the form has it
    date_of_birth: '#cnic_dob',      // optional
    address_urdu: '#cnic_address_urdu' // optional; if absent, show the value read-only with a copy button
  },
  onApply: (appliedFields) => {},   // called after values are written into the form
  compact: false                    // true = smaller layout for narrow modals
});
```
- The selectors in `fieldMap` are placeholders. **Do not guess the final form IDs;** read them from the existing manual CNIC form and list them in the stage report. I will confirm the final placement later.
- `templates/partials/cnic_scanner.html` provides the markup; the JS can also render it if the partial isn't included.

**UI behaviour (Tailwind, matching the app's design system, dark mode supported):**
1. **Collapsed header** inside the modal: a `scan-line` icon, "Scan CNIC to auto-fill", the subtitle "Photos are processed on this computer and not stored", and an Expand button. The manual fields underneath stay visible and usable at all times.
2. **Two drop zones** side by side (stacked on mobile): "Front side" and "Back side". Each supports drag-and-drop, click-to-browse and the phone camera (`accept="image/*" capture="environment"`), shows a thumbnail, and has a Remove button.
3. **Read CNIC** button: disabled until at least one side is added. While running, a progress state: "Loading OCR models…" on the first run (if `/api/ocr/status` says not warmed up), then "Reading front…" → "Reading back…".
4. **Results panel:**
   - left: the straightened preview with the field boxes drawn on a `<canvas>` overlay, coloured by level; hovering a field row highlights its box
   - right: one row per field with its label, value (editable inline), a confidence chip (High / Check / Low / Not found) and an **Apply** checkbox. Checked by default for high and medium; unchecked for low and missing.
   - the Urdu address renders with `dir="rtl"` `lang="ur"` in Noto Nastaliq Urdu
   - warnings appear as amber callouts with a "Retake photo" link that reopens that side's drop zone
5. **Apply to form:** writes the checked values into the mapped inputs.
   - If an input already has a different value typed by staff, show a small inline prompt: "Replace 'X' with 'Y'?", Replace / Keep.
   - Filled inputs get an amber "From scan" tag and a light amber ring until staff edit or focus them. Then the tag changes to "Checked".
   - Fire `input` and `change` events, so the existing form validation runs.
6. **States:** "Scanner unavailable — enter details manually" when `/api/ocr/status` is false (manual form unaffected) · error toasts for upload errors · a "Clear scan" action that removes images and results from memory.
7. Accessibility: keyboard-operable drop zones, `aria-live` for progress, labels on all controls.

---

## 7. Integration hook (minimal)
- Add one empty container `<div id="cnic-scanner-slot"></div>` **inside the existing CNIC details modal**, above the manual CNIC fields, plus a single `CnicScanner.mount(...)` call when the modal opens. Change nothing else in the modal.
- Also create `/dev/cnic-scanner` (served only when `APP_ENV=dev`): a standalone page with a copy of the CNIC fields, so the feature can be tested independently of where it finally lives.

---

## 8. Synthetic test images (`tools/make_cnic_images.py`)
- Generate CNIC-**like** cards from the existing synthetic packs (plus 10 extra random identities), at 1000 × 630 then saved at varied sizes.
- **Generic design only:** plain coloured card, the same English labels and field positions as a real CNIC, a grey silhouette instead of a photo, a placeholder QR square on the back. **No government emblem, hologram, flag, NADRA logo or real watermark.** Add a small "SAMPLE — NOT A REAL CARD" text.
- Back side: the address in Urdu (generate Urdu versions of the synthetic addresses with a small transliteration table for common words: مکان، بلاک، گلی، فیز، سیکٹر، کراچی), rendered with **Noto Nastaliq Urdu** (download the TTF into `tools/fonts/`) after shaping with `arabic_reshaper` + `python-bidi` so Pillow draws it correctly.
- **Variants per card:** `clean`, `rotated` (±3–10°), `perspective` (card on a textured background photographed at an angle), `blurred`, `dark`, `glare` (white ellipse overlay), `jpeg_low` (quality 30).
- Write `tools/out/ground_truth.csv`: file, side, variant and every expected field value.
- Output goes to `tools/out/` (gitignored).

---

## 9. Evaluation (`tools/eval_ocr.py`)
- Run `scan_cnic` on every generated image and compare with the ground truth after normalisation.
- **Metrics per field and per variant:**
  - exact-match accuracy for the number, dates, gender and names (names compared case-insensitively)
  - character similarity (`rapidfuzz.fuzz.ratio`) for the Urdu address
  - **calibration:** accuracy within each confidence level (high, medium, low). High should be ≥ 95% correct; if not, report it and suggest new thresholds.
  - average time per side
- Output `tools/out/ocr_results.csv` and a console summary table. Optionally add an "OCR accuracy" card to the existing evaluation page.

---

## 10. Build stages (stop after each)

**Stage A — Core OCR module (no UI)**
`reader.py`, `preprocess.py`, `normalize.py`, `extract_front.py`, `extract_back.py`, `validate.py`, `schemas.py`, `service.py`, `download_models.py`, plus a CLI: `python -m app.ocr.service front.jpg back.jpg` that prints the JSON (without previews).
Tests in `tests/ocr/` that **do not need EasyOCR**: feed hand-made `OcrToken` lists into the extractors and test label matching ("Narne" → Name, "Father Name" vs "Name"), the date-sorting fallback, digit character fixes, CNIC formatting, date parsing, every validation rule and the confidence levels. Add one `@pytest.mark.slow` test that runs real EasyOCR on a generated image.
*Accept when:* the unit tests pass, and the CLI reads a clean synthetic card correctly.

**Stage B — Synthetic images and evaluation**
`make_cnic_images.py`, `eval_ocr.py`. Tune the thresholds (label distances, blur threshold, confidence levels) using the results. Report the accuracy table per variant.
*Accept when:* clean images have ≥ 95% exact match on the number and dates, and the report shows where the messy variants fail.

**Stage C — API**
The three endpoints, upload limits, in-memory handling, threadpool execution, warm-up, `/api/ocr/status`. Tests with `TestClient` and a mocked `scan_cnic`.
*Accept when:* the endpoint returns the schema for front-only, back-only and both; errors return the right codes; no image files appear on disk.

**Stage D — Front-end component + dev page**
`cnic_scanner.js`, the partial, the `/dev/cnic-scanner` page and the minimal modal hook from Section 7. Tell me the actual input IDs you found in the existing CNIC form.
*Accept when:* on the dev page, uploading a generated card fills the fields with correct colours and boxes; the replace prompt appears for fields already typed; the scanner-unavailable state works with `OCR_ENABLED=false`; manual entry works unchanged in the real modal.

**Stage E — Polish**
Dark mode, mobile layout and camera capture test, reduced motion, README section (install, model download, privacy notes, limitations: Urdu address accuracy, glare, older CNIC designs, the generic test cards).

**Begin with Stage A. Start by replying with your plan for Stage A.**
