import pytest
from unittest.mock import AsyncMock, patch
from pydantic import ValidationError

from src.agent.schemas import ExtractedInvoice, ExtractionResult, LineItem, ConfidenceLevel
from src.agent.extraction import _score_confidence, extract_invoice


# ---------------------------------------------------------------------------
# Schema: required field enforcement
# ---------------------------------------------------------------------------

def test_missing_required_invoice_number_fails() -> None:
    with pytest.raises(ValidationError):
        ExtractedInvoice.model_validate({"vendor_name": "ACME", "currency": "USD"})


def test_missing_vendor_name_fails() -> None:
    with pytest.raises(ValidationError):
        ExtractedInvoice.model_validate({"invoice_number": "INV-001", "currency": "USD"})


def test_missing_currency_fails() -> None:
    with pytest.raises(ValidationError):
        ExtractedInvoice.model_validate({"invoice_number": "INV-001", "vendor_name": "ACME"})


def test_nullable_fields_accept_none() -> None:
    inv = ExtractedInvoice.model_validate({
        "invoice_number": "INV-001",
        "vendor_name": "ACME",
        "currency": "USD",
    })
    assert inv.invoice_date is None
    assert inv.amount_due is None
    assert inv.po_number is None
    assert inv.line_items == []


def test_line_items_are_typed_as_line_item_models() -> None:
    inv = ExtractedInvoice.model_validate({
        "invoice_number": "INV-001",
        "vendor_name": "ACME",
        "currency": "USD",
        "line_items": [{"description": "Widget", "quantity": 2, "unit_price": 9.99, "total": 19.98}],
    })
    assert isinstance(inv.line_items[0], LineItem)
    assert inv.line_items[0].total == 19.98


def test_line_item_nullable_fields_accept_none() -> None:
    item = LineItem.model_validate({"description": "Service fee"})
    assert item.quantity is None
    assert item.unit_price is None
    assert item.total is None


# ---------------------------------------------------------------------------
# _score_confidence
# ---------------------------------------------------------------------------

def _full_invoice(**overrides) -> ExtractedInvoice:
    base = {
        "invoice_number": "INV-001",
        "vendor_name": "ACME",
        "currency": "USD",
        "invoice_date": "2024-03-15",
        "amount_due": 199.99,
    }
    base.update(overrides)
    return ExtractedInvoice.model_validate(base)


def test_score_high_when_date_and_amount_present() -> None:
    confidence, reasons = _score_confidence(_full_invoice())
    assert confidence == ConfidenceLevel.HIGH
    assert reasons == []


def test_score_medium_when_amount_missing() -> None:
    confidence, reasons = _score_confidence(_full_invoice(amount_due=None))
    assert confidence == ConfidenceLevel.MEDIUM
    assert "amount_due is null" in reasons


def test_score_medium_when_date_missing() -> None:
    confidence, reasons = _score_confidence(_full_invoice(invoice_date=None))
    assert confidence == ConfidenceLevel.MEDIUM
    assert "invoice_date is null" in reasons


def test_score_low_when_both_date_and_amount_missing() -> None:
    confidence, reasons = _score_confidence(_full_invoice(invoice_date=None, amount_due=None))
    assert confidence == ConfidenceLevel.LOW
    assert len(reasons) == 2


# ---------------------------------------------------------------------------
# extract_invoice: success on first attempt
# ---------------------------------------------------------------------------

GOOD_JSON = """{
  "invoice_number": "INV-2024-001",
  "vendor_name": "Widgets Inc",
  "currency": "USD",
  "invoice_date": "2024-03-15",
  "amount_due": 299.50,
  "po_number": "PO-9876",
  "line_items": [{"description": "Widget A", "quantity": 10, "unit_price": 29.95, "total": 299.50}]
}"""

SPARSE_JSON = """{
  "invoice_number": "INV-SPARSE",
  "vendor_name": "Unknown Vendor",
  "currency": "EUR"
}"""


@pytest.mark.anyio
async def test_extract_invoice_success_high_confidence() -> None:
    with patch("src.agent.extraction._call_model", new_callable=AsyncMock, return_value=GOOD_JSON):
        result = await extract_invoice("dummy document")
    assert result.invoice is not None
    assert result.confidence == ConfidenceLevel.HIGH
    assert result.attempts == 1
    assert result.validation_error is None
    assert result.invoice.invoice_number == "INV-2024-001"


@pytest.mark.anyio
async def test_extract_invoice_low_confidence_when_both_nullable_missing() -> None:
    with patch("src.agent.extraction._call_model", new_callable=AsyncMock, return_value=SPARSE_JSON):
        result = await extract_invoice("dummy document")
    assert result.invoice is not None
    assert result.confidence == ConfidenceLevel.LOW
    assert len(result.low_confidence_reasons) == 2


# ---------------------------------------------------------------------------
# extract_invoice: retry on validation failure
# ---------------------------------------------------------------------------

INVALID_JSON = '{"vendor_name": "ACME", "currency": "USD"}'  # missing invoice_number


@pytest.mark.anyio
async def test_extract_invoice_retries_once_on_bad_json() -> None:
    call_count = 0

    async def _side_effect(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        return GOOD_JSON if call_count == 2 else INVALID_JSON

    with patch("src.agent.extraction._call_model", side_effect=_side_effect):
        result = await extract_invoice("dummy document")

    assert result.invoice is not None
    assert result.attempts == 2
    assert result.validation_error is None  # succeeded on retry


@pytest.mark.anyio
async def test_extract_invoice_retry_prompt_includes_error() -> None:
    prompts: list[str] = []

    async def _capture(prompt: str) -> str:
        prompts.append(prompt)
        return INVALID_JSON

    with patch("src.agent.extraction._call_model", side_effect=_capture):
        result = await extract_invoice("dummy document")

    assert len(prompts) == 2
    assert "validation" in prompts[1].lower() or "error" in prompts[1].lower()


@pytest.mark.anyio
async def test_extract_invoice_fails_after_two_attempts() -> None:
    with patch("src.agent.extraction._call_model", new_callable=AsyncMock, return_value=INVALID_JSON):
        result = await extract_invoice("dummy document")

    assert result.invoice is None
    assert result.confidence == ConfidenceLevel.LOW
    assert result.attempts == 2
    assert result.validation_error is not None
    assert "Extraction failed after retry" in result.low_confidence_reasons


@pytest.mark.anyio
async def test_extract_invoice_does_not_retry_more_than_once() -> None:
    call_count = 0

    async def _always_bad(prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        return INVALID_JSON

    with patch("src.agent.extraction._call_model", side_effect=_always_bad):
        await extract_invoice("dummy document")

    assert call_count == 2
