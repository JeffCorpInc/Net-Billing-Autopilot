"""Application configuration and regulatory constants."""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Base directories
APP_DIR = Path(__file__).resolve().parent
BASE_DIR = APP_DIR.parent
DATA_DIR = BASE_DIR / "data"
CASES_DIR = DATA_DIR / "cases"

# On Vercel / serverless platforms, root filesystem is read-only.
# Automatically use /tmp/netbill_runtime so all features work 100% without disk errors.
IS_VERCEL = bool(os.getenv("VERCEL") == "1" or os.getenv("NOW_BUILDER") == "1")
if IS_VERCEL:
    RUNTIME_DIR = Path("/tmp") / "netbill_runtime"
else:
    # Test if data/runtime is writable; fall back to /tmp if read-only
    _test_dir = DATA_DIR / "runtime"
    try:
        _test_dir.mkdir(parents=True, exist_ok=True)
        RUNTIME_DIR = _test_dir
    except OSError:
        RUNTIME_DIR = Path("/tmp") / "netbill_runtime"

CUSTOM_CASES_DIR = RUNTIME_DIR / "custom_cases"
UPLOADS_DIR = RUNTIME_DIR / "uploads"
REPORTS_DIR = RUNTIME_DIR / "reports"
AUDIT_DIR = RUNTIME_DIR / "audit"
EVAL_DIR = RUNTIME_DIR / "eval"
EXPECTED_CSV = DATA_DIR / "expected.csv"
LLM_LOG_PATH = RUNTIME_DIR / "llm_log.jsonl"
REVIEWS_PATH = RUNTIME_DIR / "reviews.json"

# Ensure runtime directories exist
for _dir in (DATA_DIR, CASES_DIR, RUNTIME_DIR, CUSTOM_CASES_DIR, UPLOADS_DIR, REPORTS_DIR, AUDIT_DIR, EVAL_DIR):
    try:
        _dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

# Seed pre-bundled runtime reports and evaluations into /tmp if running on serverless
if RUNTIME_DIR != (DATA_DIR / "runtime") and (DATA_DIR / "runtime").exists():
    import shutil
    for _sub in ("reports", "eval", "custom_cases"):
        _src = DATA_DIR / "runtime" / _sub
        _dst = RUNTIME_DIR / _sub
        if _src.exists() and not _dst.exists():
            try:
                shutil.copytree(str(_src), str(_dst), dirs_exist_ok=True)
            except Exception:
                pass
    _rev_src = DATA_DIR / "runtime" / "reviews.json"
    if _rev_src.exists() and not REVIEWS_PATH.exists():
        try:
            shutil.copy(str(_rev_src), str(REVIEWS_PATH))
        except Exception:
            pass

# Regulatory constants
RULES_AS_OF = "2026-04-13"
RULES_SOURCE = (
    "NEPRA (Prosumer) Regulations 2026 (SRO 251(I)/2026) "
    "and K-Electric Net Billing Guidelines (13 Apr 2026)"
)
FEE_PER_KW_RS = 1000
LOAD_FLOW_THRESHOLD_KW = 250

# Human-friendly document labels
DOC_LABELS: dict[str, str] = {
    "cnic": "CNIC copy",
    "bill": "Latest K-Electric bill",
    "ownership": "Proof of ownership",
    "single_line_diagram": "Single-line diagram",
    "affidavit": "Affidavit (Schedule-V)",
    "vendor_checklist": "Vendor checklist",
    "inverter_datasheet": "Inverter data sheet",
    "inverter_settings_letter": "Inverter settings letter",
    "noc": "Owner's NOC",
    "load_flow_study": "Load-flow study",
    "ntn": "NTN certificate",
    "form_29": "Form 29 / incorporation",
}

# Load environment file
load_dotenv(BASE_DIR / ".env")


class Settings(BaseModel):
    """Runtime application settings."""

    llm_provider: str = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER") or "gemini"
    )
    llm_model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL") or "gemini-flash-lite-latest"
    )
    llm_api_key: str = Field(
        default_factory=lambda: os.getenv("LLM_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or ""
    )
    llm_base_url: str = Field(default_factory=lambda: os.getenv("LLM_BASE_URL", ""))
    llm_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "30.0"))
    )
    llm_max_retries: int = Field(
        default_factory=lambda: int(os.getenv("LLM_MAX_RETRIES", "2"))
    )

    @property
    def is_llm_configured(self) -> bool:
        """Whether a live LLM API key or local base_url is configured."""
        if self.llm_provider == "gemini":
            return bool(self.llm_api_key)
        if self.llm_provider == "openai_compatible":
            return bool(self.llm_api_key or self.llm_base_url)
        return False

    @property
    def mode(self) -> str:
        """Active operational mode: live, mock, or fallback."""
        if self.llm_provider in ("gemini", "openai_compatible") and self.is_llm_configured:
            return "live"
        if self.llm_provider == "mock":
            return "mock"
        return "fallback"


def get_settings() -> Settings:
    """Retrieve application settings snapshot."""
    load_dotenv(BASE_DIR / ".env", override=False)
    return Settings()

