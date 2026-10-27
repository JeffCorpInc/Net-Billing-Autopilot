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
async def run_checks(case_id: str, use_llm: bool = False):
    """Run compliance checks (R1-R7 deterministic + L1/L2 if use_llm=true) on a case."""
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

    # In Phase 3, if use_llm=True, llm_checks will be executed here.
    report = build_case_report(
        pack=pack,
        rule_results=rule_results,
        llm_results=llm_results,
        shadow_checks=shadow_checks,
    )
    return report.model_dump()


