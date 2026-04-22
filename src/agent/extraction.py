from pydantic import ValidationError
from claude_agent_sdk import query, ClaudeAgentOptions
from .schemas import ExtractedInvoice, ExtractionResult, ConfidenceLevel
from .prompts import EXTRACTION_PROMPT, EXTRACTION_RETRY_PROMPT

_MAX_ATTEMPTS = 2


def _score_confidence(invoice: ExtractedInvoice) -> tuple[ConfidenceLevel, list[str]]:
    """
    Score based on financially critical nullable fields.
    Both present → HIGH; one missing → MEDIUM; both missing → LOW.
    """
    reasons: list[str] = []
    if invoice.amount_due is None:
        reasons.append("amount_due is null")
    if invoice.invoice_date is None:
        reasons.append("invoice_date is null")

    if len(reasons) == 0:
        return ConfidenceLevel.HIGH, []
    if len(reasons) == 1:
        return ConfidenceLevel.MEDIUM, reasons
    return ConfidenceLevel.LOW, reasons


async def _call_model(prompt: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=EXTRACTION_PROMPT,
        permission_mode="bypassPermissions",
    )
    chunks: list[str] = []
    async for message in query(prompt=prompt, options=options):
        chunks.append(str(message))
    return "\n".join(chunks)


async def extract_invoice(document_text: str) -> ExtractionResult:
    """
    Extract an invoice from raw document text.

    Retries once when Pydantic validation fails, feeding the error back to
    the model so it can correct its output. Returns ExtractionResult with a
    confidence score; LOW confidence is set on parse failure or when both
    amount_due and invoice_date are absent from the extracted data.
    """
    last_error: str | None = None

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        if attempt == 1:
            prompt = f"Extract this invoice:\n\n{document_text}"
        else:
            prompt = EXTRACTION_RETRY_PROMPT.format(
                error=last_error,
                document=document_text,
            )

        raw = await _call_model(prompt)

        try:
            invoice = ExtractedInvoice.model_validate_json(raw)
        except ValidationError as exc:
            last_error = str(exc)
            continue

        confidence, reasons = _score_confidence(invoice)
        return ExtractionResult(
            invoice=invoice,
            confidence=confidence,
            low_confidence_reasons=reasons,
            attempts=attempt,
        )

    return ExtractionResult(
        invoice=None,
        confidence=ConfidenceLevel.LOW,
        low_confidence_reasons=["Extraction failed after retry"],
        validation_error=last_error,
        attempts=_MAX_ATTEMPTS,
    )
