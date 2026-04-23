import json
from pydantic import ValidationError
from claude_agent_sdk import query, ClaudeAgentOptions
from .errors import ToolError, ErrorCategory
from .schemas import (
    ResearchRequest,
    ResearchResult,
    ValidationRequest,
    ValidationResult,
)
from .prompts import RESEARCHER_SYSTEM, VALIDATOR_SYSTEM
from .sdk_tools import SUPPORT_MCP_SERVER

_RESEARCHER_TOOLS = [
    "mcp__support__find_customer_by_email",
    "mcp__support__search_customers",
    "mcp__support__get_order_by_id",
    "mcp__support__search_orders",
    "mcp__support__check_refund_eligibility",
]


async def run_researcher(request: ResearchRequest) -> ResearchResult:
    options = ClaudeAgentOptions(
        system_prompt=RESEARCHER_SYSTEM,
        mcp_servers={"support": SUPPORT_MCP_SERVER},
        allowed_tools=_RESEARCHER_TOOLS,
        permission_mode="bypassPermissions",
    )
    prompt = (
        f"User ID: {request.user_id}\n"
        f"Request: {request.request_text}\n"
        f"Known facts: {json.dumps(request.known_facts)}\n\n"
        "Retrieve all relevant facts. Return only structured JSON."
    )
    chunks: list[str] = []
    async for message in query(prompt=prompt, options=options):
        chunks.append(str(message))
    raw = "\n".join(chunks)
    try:
        return ResearchResult.model_validate_json(raw)
    except ValidationError:
        return ResearchResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message=f"Researcher returned unparseable output: {raw[:200]}",
                retryable=True,
            ).model_dump(),
        )


async def run_validator(request: ValidationRequest) -> ValidationResult:
    options = ClaudeAgentOptions(
        system_prompt=VALIDATOR_SYSTEM,
        permission_mode="bypassPermissions",
    )
    facts_payload = [f.model_dump() for f in request.facts]
    prompt = (
        f"Request: {request.request_text}\n"
        f"Facts: {json.dumps(facts_payload)}\n\n"
        "Detect any inconsistencies. Return only structured JSON."
    )
    chunks: list[str] = []
    async for message in query(prompt=prompt, options=options):
        chunks.append(str(message))
    raw = "\n".join(chunks)
    try:
        return ValidationResult.model_validate_json(raw)
    except ValidationError:
        return ValidationResult(
            valid=False,
            inconsistencies=[],
            summary=f"Validator returned unparseable output: {raw[:200]}",
        )
