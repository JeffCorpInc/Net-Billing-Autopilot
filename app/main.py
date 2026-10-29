import urllib.parse
"""FastAPI application entrypoint: page routes, API endpoints, error handling."""

from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import (
    BASE_DIR,
    DOC_LABELS,
    RULES_AS_OF,
    RULES_SOURCE,
    get_settings,
)

app = FastAPI(
    title="Net-Billing Application Assistant",
    description="Assistant for K-Electric net-billing solar onboarding under NEPRA 2026 regulations.",
    version="0.1.0",
)

# CORS middleware for development safety
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



class VercelPathFixMiddleware:
    """ASGI middleware to resolve original request paths when deployed behind Vercel rewrites."""

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            # 1. First check explicit query parameter from Vercel rewrite
            raw_qs = scope.get("query_string", b"").decode("utf-8", errors="ignore")
            params = urllib.parse.parse_qs(raw_qs)
            orig_path = params.get("__orig_path", [""])[0]

            if orig_path:
                clean_path = "/" + orig_path.lstrip("/")
                scope["path"] = clean_path
                scope["raw_path"] = clean_path.encode("utf-8")
                # Clean up __orig_path from downstream query string
                filtered = {k: v for k, v in params.items() if k != "__orig_path"}
                scope["query_string"] = urllib.parse.urlencode(filtered, doseq=True).encode("utf-8")
            else:
                # 2. Check proxy matched path headers
                headers_dict = dict(scope.get("headers", []))
                matched_path = None
                for hname in (
                    b"x-matched-path",
                    b"x-original-uri",
                    b"x-real-path",
                    b"x-forwarded-uri",
                    b"x-vercel-matched-path",
                ):
                    raw_val = headers_dict.get(hname)
                    if raw_val:
                        val = raw_val.decode("utf-8", errors="ignore").split("?")[0]
                        if val and val not in ("/api/index", "/api/index.py", "/api"):
                            matched_path = val
                            break

                path = scope.get("path", "")
                if matched_path:
                    scope["path"] = matched_path
                    scope["raw_path"] = matched_path.encode("utf-8")
                elif path.startswith("/api/index/"):
                    sub = path[len("/api/index"):]
                    scope["path"] = sub
                    scope["raw_path"] = sub.encode("utf-8")
                elif path.startswith("/api/index.py/"):
                    sub = path[len("/api/index.py"):]
                    scope["path"] = sub
                    scope["raw_path"] = sub.encode("utf-8")
                elif path in ("/api/index", "/api/index.py"):
                    scope["path"] = "/"
                    scope["raw_path"] = b"/"

        await self.asgi_app(scope, receive, send)


app.add_middleware(VercelPathFixMiddleware)
# Directories
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Global template context helper
def get_base_context(request: Request) -> dict:
    settings = get_settings()
    return {
        "request": request,
        "rules_as_of": RULES_AS_OF,
        "rules_source": RULES_SOURCE,
        "doc_labels": DOC_LABELS,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_mode": settings.mode,
    }


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with clean JSON responses for API or page error."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return HTMLResponse(
        content=f"<h1>{exc.status_code} Error</h1><p>{exc.detail}</p>",
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Prevent raw stack traces from reaching user."""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please try again."},
        )
    return HTMLResponse(
        content="<h1>500 Internal Error</h1><p>An unexpected error occurred.</p>",
        status_code=500,
    )


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
@app.get("/admin", response_class=HTMLResponse)

@app.get("/api/index", include_in_schema=False)
@app.get("/api/index.py", include_in_schema=False)
async def vercel_index_alias(request: Request):
    """Fallback alias for Vercel default function invocation without rewrites."""
    return await dashboard_page(request)

async def dashboard_page(request: Request):
    """Render Admin Dashboard page."""
    context = get_base_context(request)
    context.update({"active_page": "dashboard", "portal_mode": False})
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)


@app.get("/apply", response_class=HTMLResponse)
@app.get("/new", response_class=HTMLResponse)
async def new_case_page(request: Request):
    """Render standalone User Application Portal for creating a new application pack."""
    from app.storage import next_custom_case_id
    context = get_base_context(request)
    context.update({
        "active_page": "new_case",
        "portal_mode": True,
        "next_case_id": next_custom_case_id(),
        "edit_mode": False,
        "pack_json": "null",
        "existing_files": [],
    })
    return templates.TemplateResponse(request=request, name="new_case.html", context=context)


@app.get("/case/{case_id}/edit", response_class=HTMLResponse)
@app.get("/cases/{case_id}/edit", response_class=HTMLResponse)
async def edit_case_page(request: Request, case_id: str):
    """Render standalone User Application Portal in Edit Mode for an existing custom case."""
    import json
    from app.storage import get_pack, list_uploaded_files
    if not case_id.upper().startswith("U"):
        raise HTTPException(
            status_code=400,
            detail="Built-in benchmark cases (C01-C21) are read-only. Create a custom case to edit.",
        )
    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    context = get_base_context(request)
    context.update({
        "active_page": "new_case",
        "portal_mode": True,
        "next_case_id": pack.case_id,
        "edit_mode": True,
        "pack": pack,
        "pack_json": json.dumps(pack.model_dump()),
        "existing_files": list_uploaded_files(case_id),
    })
    return templates.TemplateResponse(request=request, name="new_case.html", context=context)


@app.get("/case/{case_id}", response_class=HTMLResponse)
@app.get("/cases/{case_id}", response_class=HTMLResponse)
async def case_page(request: Request, case_id: str):
    """Render individual application case page."""
    import json
    from app.storage import get_latest_report, get_pack, list_uploaded_files, load_reviews
    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    report = get_latest_report(case_id)
    if not report:
        from app.merge import build_case_report
        from app.rules import run_code_rules
        rule_results = run_code_rules(pack)
        report = build_case_report(pack=pack, rule_results=rule_results)

    reviews = load_reviews()
    review = reviews.get(case_id)
    uploaded_files = list_uploaded_files(case_id)

    context = get_base_context(request)
    context.update({
        "active_page": "case",
        "case_id": case_id,
        "pack": pack,
        "pack_json": json.dumps(pack.model_dump()),
        "report": report,
        "review": review,
        "uploaded_files": uploaded_files,
        "is_custom_case": case_id.upper().startswith("U"),
    })
    return templates.TemplateResponse(request=request, name="case.html", context=context)


@app.get("/evaluate", response_class=HTMLResponse)
async def evaluate_page(request: Request):
    """Render evaluation and benchmark page."""
    context = get_base_context(request)
    context.update({"active_page": "evaluate"})
    return templates.TemplateResponse(request=request, name="evaluate.html", context=context)


@app.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """Render about and regulatory background page."""
    context = get_base_context(request)
    context.update({"active_page": "about"})
    return templates.TemplateResponse(request=request, name="about.html", context=context)



# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.get("/api/health")
async def health_check():
    """Health check endpoint indicating LLM configuration and runtime mode."""
    settings = get_settings()
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model or ("mock-engine" if settings.llm_provider == "mock" else "none"),
        "llm_configured": settings.is_llm_configured,
        "mode": settings.mode,
    }


@app.get("/api/cases")
async def get_all_cases():
    """Return summary list of all application cases (custom + 21 benchmark) for the dashboard."""
    from app.storage import list_case_summaries
    summaries = list_case_summaries()
    return [s.model_dump() for s in summaries]


@app.post("/api/cases")
async def create_new_case(request: Request):
    """Create a new custom user application pack, run compliance checks, and persist it."""
    from app.audit import log_audit_event
    from app.llm_checks import run_l1_name_check, run_l2_address_check, run_shadow_checks
    from app.merge import build_case_report
    from app.models import Pack
    from app.rules import run_code_rules
    from app.storage import next_custom_case_id, save_custom_pack

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Auto-assign next U01, U02... case_id
    case_id = next_custom_case_id()
    payload["case_id"] = case_id

    if not payload.get("category"):
        payload["category"] = "clean"
    if not payload.get("description"):
        payload["description"] = "Custom staff-entered net-billing application pack"

    try:
        pack = Pack.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Validation error: {exc}")

    # Run deterministic rules first so we can auto-classify category ("clean" vs "trap")
    from fastapi.concurrency import run_in_threadpool
    rule_results = run_code_rules(pack)
    l1_res = await run_in_threadpool(run_l1_name_check, pack)
    l2_res = await run_in_threadpool(run_l2_address_check, pack)
    llm_results = [l1_res, l2_res]
    shadow_checks = await run_in_threadpool(run_shadow_checks, pack)

    any_fail = any(r.status == "FAIL" for r in (rule_results + llm_results))
    pack.category = "trap" if any_fail else "clean"

    save_custom_pack(pack)

    log_audit_event(
        case_id=case_id,
        event_type="case_created",
        details={
            "applicant_name": pack.cnic.name,
            "proposed_kw": pack.system.proposed_kw,
            "docs_count": len(pack.docs_present),
        },
    )

    report = build_case_report(
        pack=pack,
        rule_results=rule_results,
        llm_results=llm_results,
        shadow_checks=shadow_checks,
    )

    return {
        "status": "ok",
        "case_id": case_id,
        "pack": pack.model_dump(),
        "report": report.model_dump(),
    }


@app.put("/api/cases/{case_id}")
async def update_existing_case(case_id: str, request: Request):
    """Update an existing custom user application pack, re-run compliance checks, and persist."""
    from app.audit import log_audit_event
    from app.llm_checks import run_l1_name_check, run_l2_address_check, run_shadow_checks
    from app.merge import build_case_report
    from app.models import Pack
    from app.rules import run_code_rules
    from app.storage import get_pack, save_custom_pack

    if not case_id.upper().startswith("U"):
        raise HTTPException(
            status_code=400,
            detail="Built-in benchmark cases (C01-C21) cannot be modified.",
        )

    existing_pack = get_pack(case_id)
    if not existing_pack:
        raise HTTPException(status_code=404, detail=f"Custom case {case_id} not found")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    payload["case_id"] = existing_pack.case_id
    if not payload.get("category"):
        payload["category"] = existing_pack.category
    if not payload.get("description"):
        payload["description"] = existing_pack.description

    try:
        pack = Pack.model_validate(payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Validation error: {exc}")

    from fastapi.concurrency import run_in_threadpool
    rule_results = run_code_rules(pack)
    l1_res = await run_in_threadpool(run_l1_name_check, pack)
    l2_res = await run_in_threadpool(run_l2_address_check, pack)
    llm_results = [l1_res, l2_res]
    shadow_checks = await run_in_threadpool(run_shadow_checks, pack)

    any_fail = any(r.status == "FAIL" for r in (rule_results + llm_results))
    pack.category = "trap" if any_fail else "clean"

    save_custom_pack(pack)

    log_audit_event(
        case_id=pack.case_id,
        event_type="case_updated",
        details={
            "applicant_name": pack.cnic.name,
            "proposed_kw": pack.system.proposed_kw,
            "docs_count": len(pack.docs_present),
        },
    )

    report = build_case_report(
        pack=pack,
        rule_results=rule_results,
        llm_results=llm_results,
        shadow_checks=shadow_checks,
    )

    return {
        "status": "ok",
        "case_id": pack.case_id,
        "pack": pack.model_dump(),
        "report": report.model_dump(),
    }


@app.post("/api/cases/{case_id}/upload")
async def upload_case_files(case_id: str, request: Request):
    """Save uploaded document files (base64 or metadata) for a case."""
    import base64
    from app.audit import log_audit_event
    from app.storage import get_pack, list_uploaded_files, save_uploaded_file

    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    uploaded_names = []
    try:
        data = await request.json()
        files_meta = data.get("files", [])
        for fmeta in files_meta:
            safe_name = Path(str(fmeta.get("name", "document.pdf"))).name
            b64_data = fmeta.get("content_base64")
            if b64_data:
                # Strip data URI prefix if present
                if "," in b64_data:
                    b64_data = b64_data.split(",", 1)[1]
                raw_bytes = base64.b64decode(b64_data)
            else:
                raw_bytes = f"Uploaded file placeholder: {safe_name} ({fmeta.get('size', 0)} bytes)".encode("utf-8")
            save_uploaded_file(case_id, safe_name, raw_bytes)
            uploaded_names.append(safe_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Upload failed: {exc}")

    saved = list_uploaded_files(case_id)
    if uploaded_names:
        log_audit_event(
            case_id=case_id,
            event_type="files_uploaded",
            details={"count": len(uploaded_names), "files": uploaded_names},
        )

    return {"status": "ok", "files": saved}


@app.get("/api/cases/{case_id}/files/{filename}")
async def view_uploaded_file(case_id: str, filename: str):
    """Serve an uploaded document scan for viewing or downloading."""
    import mimetypes
    from fastapi.responses import FileResponse
    from app.storage import get_uploaded_file_path

    fpath = get_uploaded_file_path(case_id, filename)
    if not fpath:
        raise HTTPException(status_code=404, detail="Uploaded file not found")

    media_type, _ = mimetypes.guess_type(str(fpath))
    return FileResponse(path=str(fpath), media_type=media_type or "application/octet-stream", filename=fpath.name)


@app.delete("/api/cases/{case_id}/files/{filename}")
async def delete_uploaded_file_endpoint(case_id: str, filename: str):
    """Delete a specific uploaded document scan from a case."""
    from app.audit import log_audit_event
    from app.storage import delete_uploaded_file, list_uploaded_files

    removed = delete_uploaded_file(case_id, filename)
    if not removed:
        raise HTTPException(status_code=404, detail=f"File {filename} not found")

    log_audit_event(
        case_id=case_id,
        event_type="file_deleted",
        details={"filename": filename},
    )
    return {"status": "ok", "deleted": filename, "files": list_uploaded_files(case_id)}


@app.delete("/api/cases/{case_id}")
async def delete_case_endpoint(case_id: str):
    """Delete a custom user-created case (U* only)."""
    from app.storage import delete_custom_pack
    if not case_id.upper().startswith("U"):
        raise HTTPException(
            status_code=400,
            detail="Built-in benchmark cases (C01-C21) cannot be deleted.",
        )
    deleted = delete_custom_pack(case_id.upper())
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Custom case {case_id} not found")
    return {"status": "ok", "deleted": case_id.upper()}


@app.post("/api/assistant/chat")
async def assistant_chat_endpoint(request: Request):
    """AI Onboarding Copilot endpoint for live form validation & custom user case Q&A."""
    from fastapi.concurrency import run_in_threadpool
    from app.assistant import run_assistant_chat
    from app.storage import get_pack

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    case_id = str(body.get("case_id") or "DRAFT").strip()
    user_message = str(body.get("message") or "").strip()
    draft_state = body.get("draft_state")
    inspect_only = bool(body.get("inspect_only", False))

    # Block benchmark cases C01..C21 from using the custom user assistant
    if case_id.upper().startswith("C") and case_id[1:].isdigit():
        raise HTTPException(
            status_code=400,
            detail="AI Assistant is available only for New Applications and Custom User Cases (U01, U02...).",
        )

    # If draft_state is not passed directly, load from saved custom case pack if available
    if not isinstance(draft_state, dict):
        pack = get_pack(case_id) if case_id != "DRAFT" else None
        draft_state = pack.model_dump() if pack else {}

    result = await run_in_threadpool(
        run_assistant_chat,
        case_id=case_id,
        draft_state=draft_state,
        user_message=user_message,
        inspect_only=inspect_only,
    )
    return result


@app.get("/api/ocr/status")
def ocr_status_endpoint():
    """Return readiness and supported documents for the backend OCR extractor."""
    from app.ocr import get_ocr_status
    return get_ocr_status()


@app.post("/api/ocr/extract")
async def ocr_extract_endpoint(request: Request):
    """Run backend OCR & document field extraction on uploaded files (CNIC, Bill, Deed, System Specs)."""
    from fastapi.concurrency import run_in_threadpool
    from app.ocr import extract_documents_from_uploads

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload for OCR extraction")

    files = body.get("files")
    if not isinstance(files, list) or len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided for OCR extraction")

    result = await run_in_threadpool(extract_documents_from_uploads, files)
    return result


@app.get("/api/cases/{case_id}")
async def get_case_detail(case_id: str):
    """Retrieve full pack, latest report, and staff review for a case."""
    from app.storage import get_latest_report, get_pack, load_reviews
    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    report = get_latest_report(case_id)
    if not report:
        from app.merge import build_case_report
        from app.rules import run_code_rules
        rule_results = run_code_rules(pack)
        report = build_case_report(pack=pack, rule_results=rule_results)

    reviews = load_reviews()
    review = reviews.get(case_id)

    return {
        "pack": pack.model_dump(),
        "report": report.model_dump() if report else None,
        "review": review,
    }


@app.post("/api/check/{case_id}")
def run_checks(case_id: str, use_llm: bool = True):
    """Run compliance checks (R1-R7 deterministic + L1/L2 and shadow if use_llm=true) on a case."""
    from app.llm_checks import run_l1_name_check, run_l2_address_check, run_shadow_checks
    from app.merge import build_case_report
    from app.rules import run_code_rules
    from app.storage import get_pack

    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    # Run deterministic rules R1-R7
    rule_results = run_code_rules(pack)
    llm_results = []
    shadow_checks = []

    if use_llm:
        l1_res = run_l1_name_check(pack)
        l2_res = run_l2_address_check(pack)
        llm_results = [l1_res, l2_res]
        shadow_checks = run_shadow_checks(pack)

    report = build_case_report(
        pack=pack,
        rule_results=rule_results,
        llm_results=llm_results,
        shadow_checks=shadow_checks,
    )
    return report.model_dump()


@app.post("/api/checklist/{case_id}")
def get_checklist(case_id: str, lang: str = "en"):
    """Generate bilingual customer checklist with faithfulness gate protection."""
    from app.audit import log_audit_event
    from app.checklist import generate_customer_checklist
    from app.storage import get_latest_report, get_pack

    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    report = get_latest_report(case_id)
    if not report:
        # Run checks automatically if not yet run
        from app.llm_checks import run_l1_name_check, run_l2_address_check, run_shadow_checks
        from app.merge import build_case_report
        from app.rules import run_code_rules

        rule_results = run_code_rules(pack)
        l1_res = run_l1_name_check(pack)
        l2_res = run_l2_address_check(pack)
        report = build_case_report(
            pack=pack,
            rule_results=rule_results,
            llm_results=[l1_res, l2_res],
            shadow_checks=run_shadow_checks(pack),
        )

    checklist_res = generate_customer_checklist(case_id=case_id, report=report, lang=lang)

    # Log to audit trail
    log_audit_event(
        case_id=case_id,
        event_type="checklist_generated",
        details={
            "lang": lang,
            "gate": checklist_res.gate,
            "gate_reason": checklist_res.gate_reason,
            "item_count": len(checklist_res.items),
            "source": checklist_res.source,
        },
    )

    return checklist_res.model_dump()


@app.get("/api/draft/{case_id}")
async def get_draft_pdf(case_id: str, download: int = 0):
    """Generate and serve draft application PDF (inline or attachment)."""
    from fastapi.responses import Response
    from app.audit import log_audit_event
    from app.draft_pdf import generate_draft_pdf_bytes
    from app.storage import get_latest_report, get_pack

    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    report = get_latest_report(case_id)
    pdf_bytes = generate_draft_pdf_bytes(pack=pack, report=report)

    disposition = "attachment" if download == 1 else "inline"
    filename = f"draft_{case_id}.pdf"

    log_audit_event(
        case_id=case_id,
        event_type="draft_generated",
        details={"disposition": disposition, "size_bytes": len(pdf_bytes)},
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


@app.post("/api/review/{case_id}")
async def submit_review(case_id: str, request: Request):
    """Mark case reviewed by onboarding staff member."""
    from app.audit import record_staff_review
    from app.storage import get_latest_report, get_pack

    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    report = get_latest_report(case_id)
    if not report:
        raise HTTPException(
            status_code=400,
            detail="Staff review is permitted only after compliance checks have been executed.",
        )

    try:
        data = await request.json()
    except Exception:
        data = {}

    staff_name = str(data.get("staff_name", "")).strip()
    note = str(data.get("note", "")).strip()

    if not staff_name:
        raise HTTPException(status_code=400, detail="Staff name is required.")

    record = record_staff_review(case_id=case_id, staff_name=staff_name, note=note)
    return {"status": "ok", "review": record}


@app.get("/api/audit/{case_id}")
async def get_audit_trail_endpoint(case_id: str):
    """Retrieve full audit log trail for a case."""
    from app.audit import get_case_audit_trail
    from app.storage import get_pack

    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    trail = get_case_audit_trail(case_id)
    return {"case_id": case_id, "entries": trail}


@app.post("/api/evaluate/case/{case_id}")
def evaluate_case_endpoint(case_id: str, runs: int = 1):
    """Evaluate one case against ground truth and store result in data/runtime/eval/."""
    from app.evaluate import evaluate_single_case
    try:
        res = evaluate_single_case(case_id=case_id, runs=runs)
        return res
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}")


@app.get("/api/evaluate/summary")
def evaluate_summary_endpoint():
    """Retrieve aggregated metrics from stored evaluation results."""
    from app.evaluate import compute_summary_metrics, load_all_eval_results
    evals = load_all_eval_results()
    if not evals:
        # If no evals yet, run batch automatically for initial summary
        from app.evaluate import evaluate_single_case
        from app.storage import list_case_summaries
        cases = list_case_summaries()
        for c in cases:
            try:
                evaluate_single_case(c.case_id, runs=1)
            except Exception:
                pass
        evals = load_all_eval_results()

    return compute_summary_metrics(evals)


@app.get("/api/evaluate/export.csv")
async def evaluate_export_csv():
    """Export per-case, per-check ground truth evaluation matrix as CSV."""
    from fastapi.responses import Response
    from app.evaluate import generate_evaluation_csv
    csv_text = generate_evaluation_csv()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="evaluation_results.csv"'},
    )





