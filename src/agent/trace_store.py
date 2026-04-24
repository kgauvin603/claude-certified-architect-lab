from collections import deque
from datetime import datetime, timezone
import asyncio
from typing import Optional

_store: deque = deque(maxlen=25)
_in_progress: dict[str, dict] = {}
_subscribers: list[asyncio.Queue] = []


def start_trace(request_id: str, user_id: str, session_id: str, request_text: str) -> None:
    _in_progress[request_id] = {
        "request_id": request_id,
        "user_id": user_id,
        "session_id": session_id,
        "request_text": request_text,
        "events": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "duration_ms": None,
        "response_summary": None,
    }


def add_event(request_id: str, event: str) -> None:
    if request_id in _in_progress:
        _in_progress[request_id]["events"].append(event)
    for q in list(_subscribers):
        try:
            q.put_nowait({"request_id": request_id, "event": event})
        except Exception:
            pass


def complete_trace(request_id: str, response_summary: str) -> None:
    if request_id not in _in_progress:
        return
    trace = _in_progress.pop(request_id)
    completed_at = datetime.now(timezone.utc)
    started_dt = datetime.fromisoformat(trace["started_at"])
    duration_ms = int((completed_at - started_dt).total_seconds() * 1000)
    trace["completed_at"] = completed_at.isoformat()
    trace["duration_ms"] = duration_ms
    trace["response_summary"] = response_summary
    _store.append(trace)


def get_traces() -> list[dict]:
    return list(reversed(_store))


def get_trace_by_id(request_id: str) -> Optional[dict]:
    for t in _store:
        if t["request_id"] == request_id:
            return t
    return _in_progress.get(request_id)


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass
