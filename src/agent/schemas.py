from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    REPEATED_FAILURE = "repeated_failure"
    POLICY_UNCLEAR = "policy_unclear"
    HUMAN_REQUESTED = "human_requested"


class CoordinatorDecision(BaseModel):
    outcome: Literal["complete", "clarify", "escalate"]
    confidence: ConfidenceLevel
    clarifying_question: str | None = None
    escalation_reason: EscalationReason | None = None
    escalation_detail: str | None = None


class TicketContext(BaseModel):
    session_id: str
    user_id: str
    request_text: str
    facts: list[str] = Field(default_factory=list)
    tool_failure_counts: dict[str, int] = Field(default_factory=dict)


class LineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    total: float | None = None


class ExtractedInvoice(BaseModel):
    invoice_number: str
    vendor_name: str
    invoice_date: str | None = None  # ISO-8601 date or null
    amount_due: float | None = None
    currency: str
    po_number: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    invoice: ExtractedInvoice | None = None
    confidence: ConfidenceLevel
    low_confidence_reasons: list[str] = Field(default_factory=list)
    validation_error: str | None = None
    attempts: int = 1


class FactItem(BaseModel):
    key: str
    value: str
    source: str


class ResearchRequest(BaseModel):
    user_id: str
    request_text: str
    known_facts: list[str] = Field(default_factory=list)


class ResearchResult(BaseModel):
    ok: bool
    facts: list[FactItem] = Field(default_factory=list)
    error: dict | None = None


class Inconsistency(BaseModel):
    field: str
    description: str
    severity: Literal["warning", "error"]


class ValidationRequest(BaseModel):
    request_text: str
    facts: list[FactItem]


class ValidationResult(BaseModel):
    valid: bool
    inconsistencies: list[Inconsistency] = Field(default_factory=list)
    summary: str
