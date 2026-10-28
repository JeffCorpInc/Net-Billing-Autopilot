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
async def dashboard_page(request: Request):
    """Render dashboard page."""
    context = get_base_context(request)
    context.update({"active_page": "dashboard"})
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)


@app.get("/case/{case_id}", response_class=HTMLResponse)
@app.get("/cases/{case_id}", response_class=HTMLResponse)
async def case_page(request: Request, case_id: str):
    """Render individual application case page."""
    from app.storage import get_latest_report, get_pack, load_reviews
    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    report = get_latest_report(case_id)
    reviews = load_reviews()
    review = reviews.get(case_id)

    context = get_base_context(request)
    context.update({
        "active_page": "case",
        "case_id": case_id,
        "pack": pack,
        "report": report,
        "review": review,
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
    """Return summary list of all 21 application cases for the dashboard."""
    from app.storage import list_case_summaries
    summaries = list_case_summaries()
    return [s.model_dump() for s in summaries]


@app.get("/api/cases/{case_id}")
async def get_case_detail(case_id: str):
    """Retrieve full pack, latest report, and staff review for a case."""
    from app.storage import get_latest_report, get_pack, load_reviews
    pack = get_pack(case_id)
    if not pack:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    report = get_latest_report(case_id)
    reviews = load_reviews()
    review = reviews.get(case_id)

    return {
        "pack": pack.model_dump(),
        "report": report.model_dump() if report else None,
        "review": review,
    }


@app.post("/api/check/{case_id}")
async def run_checks(case_id: str, use_llm: bool = True):
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
async def get_checklist(case_id: str, lang: str = "en"):
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
async def evaluate_case_endpoint(case_id: str, runs: int = 1):
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
async def evaluate_summary_endpoint():
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





