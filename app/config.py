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
RUNTIME_DIR = DATA_DIR / "runtime"
REPORTS_DIR = RUNTIME_DIR / "reports"
AUDIT_DIR = RUNTIME_DIR / "audit"
EVAL_DIR = RUNTIME_DIR / "eval"
LLM_LOG_PATH = RUNTIME_DIR / "llm_log.jsonl"
REVIEWS_PATH = RUNTIME_DIR / "reviews.json"

# Ensure runtime directories exist
for _dir in (DATA_DIR, CASES_DIR, RUNTIME_DIR, REPORTS_DIR, AUDIT_DIR, EVAL_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

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

    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "mock"))
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", ""))
    llm_api_key: str = Field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
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
        if self.llm_provider == "openai_compatible":
            return bool(self.llm_api_key or self.llm_base_url)
        return False

    @property
    def mode(self) -> str:
        """Active operational mode: live, mock, or fallback."""
        if self.llm_provider == "openai_compatible" and self.is_llm_configured:
            return "live"
        if self.llm_provider == "mock":
            return "mock"
        return "fallback"


def get_settings() -> Settings:
    """Retrieve application settings snapshot."""
    load_dotenv(BASE_DIR / ".env", override=False)
    return Settings()

