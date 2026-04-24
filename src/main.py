import os

from fastapi import FastAPI
from pydantic import BaseModel
from src.agent.coordinator import process_request
from src.agent.observability import (
    configure_logging,
    new_request_id,
    set_request_context,
    reset_request_context,
    log_request_received,
    log_response_sent,
    get_trace,
)

if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")

configure_logging()

app = FastAPI()


class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    request_text: str


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest):
    request_id = new_request_id()
    t1, t2 = set_request_context(request_id)
    try:
        log_request_received(req.user_id, req.session_id, req.request_text)
        result = await process_request(req.session_id, req.user_id, req.request_text)
        result = result if isinstance(result, dict) else {"result": str(result)}
        log_response_sent(req.session_id)
        try:
            result["trace"] = get_trace()
        except Exception:
            pass
        return result
    finally:
        reset_request_context(t1, t2)
