"""Pydantic data models for packs, documents, checks, and reports."""

from datetime import date
from typing import Any, Literal
from pydantic import BaseModel, Field


class CNICDoc(BaseModel):
    name: str
    father_name: str
    cnic_no: str
    expiry: str  # YYYY-MM-DD
    address: str


class BillDoc(BaseModel):
    consumer_name: str
    reference_no: str
    sanctioned_load_kw: float
    connected_load_kw: float
    tariff: str
    connection_phase: Literal["1-phase", "3-phase", "1-Phase", "3-Phase"]
    address: str


class OwnershipDoc(BaseModel):
    type: Literal["sale_deed", "lease_deed", "allotment_letter", "none"]
    owner_name: str
    property_address: str


class SystemSpec(BaseModel):
    proposed_kw: float
    inverter_kw: float
    panel_count: int
    panel_watt: int


class Pack(BaseModel):
    case_id: str
    category: Literal["clean", "trap"]
    description: str
    applicant_type: Literal["residential", "commercial"]
    cnic: CNICDoc
    bill: BillDoc
    ownership: OwnershipDoc
    system: SystemSpec
    is_tenant: bool = False
    docs_present: list[str] = Field(default_factory=list)


class CheckResult(BaseModel):
    id: str  # e.g. R1, R2, L1, L2
    key: str  # e.g. cnic_format, capacity, name_match
    name: str
    status: Literal["PASS", "FAIL", "UNSURE", "INFO", "PENDING"]
    detail: str
    citation: str
    source: Literal["code", "llm", "mock-llm", "fuzzy-fallback"] = "code"
    data: dict[str, Any] = Field(default_factory=dict)
    llm: dict[str, Any] | None = None


class CaseSummary(BaseModel):
    case_id: str
    category: Literal["clean", "trap"]
    description: str
    applicant_name: str
    proposed_kw: float
    sanctioned_load_kw: float
    docs_present_count: int
    docs_required_count: int
    overall: Literal["READY", "NOT_READY", "NEEDS_REVIEW", "PENDING"] = "PENDING"
    readiness: float = 0.0
    reviewed: bool = False


class CaseReport(BaseModel):
    case_id: str
    timestamp: str
    mode: str
    overall: Literal["READY", "NOT_READY", "NEEDS_REVIEW", "PENDING"]
    readiness_score: float
    results: list[CheckResult] = Field(default_factory=list)
    shadow_checks: list[dict[str, Any]] = Field(default_factory=list)
