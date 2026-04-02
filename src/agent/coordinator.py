import json
from pathlib import Path
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from .schemas import TicketContext
from .sessions import load_session, save_session
from .prompts import COORDINATOR_SYSTEM, FEW_SHOTS
from .sdk_tools import SUPPORT_MCP_SERVER

SCRATCHPAD_DIR = Path("data/scratchpads")
SCRATCHPAD_DIR.mkdir(parents=True, exist_ok=True)


def write_scratchpad(session_id: str, note: str) -> None:
    path = SCRATCHPAD_DIR / f"{session_id}.md"
    existing = path.read_text() if path.exists() else ""
    path.write_text(existing + f"\n- {note}")


def build_options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=COORDINATOR_SYSTEM + "\n\n" + FEW_SHOTS,
        mcp_servers={"support": SUPPORT_MCP_SERVER},
        allowed_tools=[
            "mcp__support__find_customer_by_email",
            "mcp__support__search_customers",
            "mcp__support__get_order_by_id",
            "mcp__support__search_orders",
            "mcp__support__check_refund_eligibility",
            "mcp__support__escalate_case",
        ],
        permission_mode="bypassPermissions",
    )


async def process_request(session_id: str, user_id: str, request_text: str) -> dict:
    ctx = load_session(session_id) or TicketContext(
        session_id=session_id,
        user_id=user_id,
        request_text=request_text,
    )
    ctx.request_text = request_text

    prompt = (
        f"Session facts: {json.dumps(ctx.facts)}\n\n"
        f"User ID: {user_id}\n"
        f"User request: {request_text}\n\n"
        "Handle the request using the available tools. "
        "Prefer fuzzy search tools for vague requests. "
        "Escalate if policy is unclear or the user explicitly asks for a human."
    )

    final_messages = []

    async with ClaudeSDKClient(options=build_options()) as client:
        await client.query(prompt, session_id=session_id)
        async for message in client.receive_response():
            final_messages.append(message)

    rendered = "\n".join(str(m) for m in final_messages)
    ctx.facts.append(f"Last request: {request_text}")
    write_scratchpad(session_id, f"Handled request summary: {rendered[:300]}")
    save_session(ctx)

    return {
        "session_id": session_id,
        "response": rendered,
        "facts": ctx.facts,
    }
