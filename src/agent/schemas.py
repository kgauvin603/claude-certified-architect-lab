from pydantic import BaseModel, Field


class TicketContext(BaseModel):
    session_id: str
    user_id: str
    request_text: str
    facts: list[str] = Field(default_factory=list)


class ExtractedInvoice(BaseModel):
    invoice_number: str
    vendor_name: str
    invoice_date: str | None = None
    amount_due: float | None = None
    currency: str
    po_number: str | None = None
    line_items: list[dict] = Field(default_factory=list)
