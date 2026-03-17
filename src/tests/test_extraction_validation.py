import pytest
from pydantic import ValidationError

from src.agent.schemas import ExtractedInvoice


def test_missing_required_invoice_number_fails() -> None:
    bad = {
        "vendor_name": "ACME",
        "currency": "USD",
    }
    with pytest.raises(ValidationError):
        ExtractedInvoice.model_validate(bad)
