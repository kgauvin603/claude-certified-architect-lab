import json
from pathlib import Path

from anthropic import Anthropic

from .prompts import COORDINATOR_SYSTEM, FEW_SHOTS
from .schemas import TicketContext
from .sessions import load_session, save_session


client = Anthropic()
SCRATCHPAD_DIR = Path("data/scratchpads")
SCRATCHPAD_DIR.mkdir(parents=True, exist_ok=True)


def write_scratchpad(session_id: str, note: str) -> None:
    path = SCRATCHPAD_DIR / f"{session_id}.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(existing + f"\n- {note}", encoding="utf-8")


def process_request(session_id: str, user_id: str, request_text: str, model: str = "claude-sonnet-4-5") -> dict:
    ctx = load_session(session_id) or TicketContext(
        session_id=session_id,
        user_id=user_id,
        request_text=request_text,
    )
    ctx.request_text = request_text

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=COORDINATOR_SYSTEM + "\n\n" + FEW_SHOTS,
        messages=[
            {
                "role": "user",
                "content": f"Session facts: {json.dumps(ctx.facts)}\n\nUser request: {request_text}",
            }
        ],
    )

    assistant_text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )

    ctx.facts.append(f"Last request: {request_text}")
    write_scratchpad(session_id, f"Handled request summary: {assistant_text[:200]}")
    save_session(ctx)

    return {"session_id": session_id, "response": assistant_text, "facts": ctx.facts}
