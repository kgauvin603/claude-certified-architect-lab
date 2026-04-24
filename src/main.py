import asyncio
import json
import logging
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from src.agent.coordinator import process_request
from src.agent.explanation import generate_explanation
from src.agent import trace_store
from src.agent.observability import (
    configure_logging,
    new_request_id,
    set_request_context,
    reset_request_context,
    log_orchestrator_start,
    log_request_received,
    log_response_sent,
    get_trace,
)
from src.lab_html import LAB_HTML

if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")

configure_logging()

logger = logging.getLogger("agent")

app = FastAPI(title="Claude Certified Architect Lab")


class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    request_text: str


def _response_summary(result: dict) -> str:
    decision = result.get("decision") or {}
    outcome = decision.get("outcome", "unknown")
    confidence = decision.get("confidence", "unknown")
    facts = len((result.get("research") or {}).get("facts") or [])
    return f"outcome={outcome} confidence={confidence} facts={facts}"


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/lab", response_class=HTMLResponse)
async def lab():
    return HTMLResponse(content=LAB_HTML)


@app.get("/traces")
async def list_traces():
    return trace_store.get_traces()


@app.get("/traces/{request_id}")
async def get_trace_by_id(request_id: str):
    t = trace_store.get_trace_by_id(request_id)
    if t is None:
        return JSONResponse({"error": "trace not found"}, status_code=404)
    return t


@app.get("/events")
async def events():
    async def generate():
        q = trace_store.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            trace_store.unsubscribe(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat")
async def chat(req: ChatRequest):
    request_id = new_request_id()
    t1, t2 = set_request_context(request_id)
    trace_store.start_trace(request_id, req.user_id, req.session_id, req.request_text)
    try:
        log_orchestrator_start(req.user_id, req.session_id)
        log_request_received(req.user_id, req.session_id, req.request_text)
        raw = await process_request(req.session_id, req.user_id, req.request_text)
        result = raw if isinstance(raw, dict) else {"result": str(raw)}
        log_response_sent(req.session_id)
        trace = get_trace()
        result["trace"] = trace
        result["request_id"] = request_id
        result["exam_explanation"] = generate_explanation(
            trace_events=trace,
            decision=result.get("decision") or {},
            research=result.get("research") or {},
            validation=result.get("validation"),
        )
        trace_store.complete_trace(request_id, _response_summary(result))
        return result
    except Exception as exc:
        logger.exception("Unhandled error in /chat request_id=%s", request_id)
        trace_store.complete_trace(request_id, f"error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": {"category": "FATAL_ERROR", "message": str(exc), "retryable": False}},
        )
    finally:
        reset_request_context(t1, t2)
