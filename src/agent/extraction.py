from anthropic import Anthropic
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from .prompts import EXTRACTION_PROMPT
from .schemas import ExtractedInvoice


client = Anthropic()


class RecoverableValidationError(Exception):
    pass


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(RecoverableValidationError),
)
def extract_invoice_text(document_text: str, model: str = "claude-sonnet-4-5") -> ExtractedInvoice:
    response = client.messages.create(
        model=model,
        max_tokens=1200,
        system=EXTRACTION_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Extract this invoice:\n\n{document_text}",
            }
        ],
    )

    text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )

    try:
        return ExtractedInvoice.model_validate_json(text)
    except ValidationError as exc:
        raise RecoverableValidationError(str(exc)) from exc
