from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from claude_agent_sdk import query, ClaudeAgentOptions
from .schemas import ExtractedInvoice
from .prompts import EXTRACTION_PROMPT


class RecoverableValidationError(Exception):
    pass


async def _run_extraction(document_text: str) -> str:
    options = ClaudeAgentOptions(
        system_prompt=EXTRACTION_PROMPT,
        permission_mode="bypassPermissions",
    )

    chunks = []
    async for message in query(
        prompt=f"Extract this invoice as JSON only:\n\n{document_text}",
        options=options,
    ):
        chunks.append(str(message))
    return "\n".join(chunks)


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(RecoverableValidationError),
)
async def extract_invoice_text(document_text: str) -> ExtractedInvoice:
    raw = await _run_extraction(document_text)

    try:
        return ExtractedInvoice.model_validate_json(raw)
    except ValidationError as e:
        raise RecoverableValidationError(str(e)) from e
