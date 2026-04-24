"""Tests for trace store, explanation engine, and lab API endpoints."""
import os
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

_MOCK_RESULT = {
    "session_id": "s1",
    "research": {
        "ok": True,
        "facts": [{"key": "customer_name", "value": "Alice", "source": "find_customer_by_email"}],
        "error": None,
    },
    "validation": {"valid": True, "inconsistencies": [], "summary": "All consistent"},
    "facts": ["customer_name=Alice"],
    "decision": {
        "outcome": "complete",
        "confidence": "high",
        "clarifying_question": None,
        "escalation_reason": None,
        "escalation_detail": None,
    },
}


def _client():
    from src.main import app
    return TestClient(app)


# --- /healthz ---

def test_healthz():
    resp = _client().get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- /chat response shape ---

@patch("src.main.process_request", new_callable=AsyncMock)
def test_chat_includes_request_id(mock_pr):
    mock_pr.return_value = dict(_MOCK_RESULT)
    resp = _client().post("/chat", json={"session_id": "s1", "user_id": "u1", "request_text": "test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "request_id" in data
    assert len(data["request_id"]) == 8


@patch("src.main.process_request", new_callable=AsyncMock)
def test_chat_includes_trace(mock_pr):
    mock_pr.return_value = dict(_MOCK_RESULT)
    resp = _client().post("/chat", json={"session_id": "s1", "user_id": "u1", "request_text": "test"})
    data = resp.json()
    assert isinstance(data["trace"], list)
    assert len(data["trace"]) > 0


@patch("src.main.process_request", new_callable=AsyncMock)
def test_chat_includes_exam_explanation(mock_pr):
    mock_pr.return_value = dict(_MOCK_RESULT)
    resp = _client().post("/chat", json={"session_id": "s1", "user_id": "u1", "request_text": "test"})
    data = resp.json()
    assert "exam_explanation" in data
    exp = data["exam_explanation"]
    assert "exam_concepts" in exp
    concepts = exp["exam_concepts"]
    for key in ("tool_selection", "mcp_design", "subagent_context_isolation",
                "structured_outputs", "validation", "confidence_and_escalation", "observability"):
        assert key in concepts, f"Missing exam concept: {key}"


@patch("src.main.process_request", new_callable=AsyncMock)
def test_chat_trace_contains_orchestrator_events(mock_pr):
    mock_pr.return_value = dict(_MOCK_RESULT)
    resp = _client().post("/chat", json={"session_id": "s1", "user_id": "u1", "request_text": "test"})
    trace = resp.json()["trace"]
    combined = " ".join(trace)
    assert "Orchestrator" in combined, "Trace must include ORCHESTRATOR events"


# --- Trace store ---

def test_trace_store_records_start_and_complete():
    from src.agent import trace_store
    rid = "TSTORE01"
    trace_store.start_trace(rid, "u1", "s1", "trace store test")
    trace_store.add_event(rid, "step-a")
    trace_store.add_event(rid, "step-b")
    trace_store.complete_trace(rid, "outcome=complete")

    t = trace_store.get_trace_by_id(rid)
    assert t is not None
    assert t["events"] == ["step-a", "step-b"]
    assert t["response_summary"] == "outcome=complete"
    assert t["duration_ms"] >= 0
    assert t["completed_at"] is not None


def test_trace_store_in_get_traces():
    from src.agent import trace_store
    rid = "TSTORE02"
    trace_store.start_trace(rid, "u2", "s2", "list test")
    trace_store.complete_trace(rid, "ok")

    ids = [t["request_id"] for t in trace_store.get_traces()]
    assert rid in ids


def test_trace_store_returns_none_for_unknown():
    from src.agent import trace_store
    assert trace_store.get_trace_by_id("DOESNOTEXIST") is None


# --- /traces endpoints ---

@patch("src.main.process_request", new_callable=AsyncMock)
def test_traces_endpoint_returns_list(mock_pr):
    mock_pr.return_value = dict(_MOCK_RESULT)
    client = _client()
    client.post("/chat", json={"session_id": "s1", "user_id": "u1", "request_text": "test"})
    resp = client.get("/traces")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_traces_by_id_not_found():
    resp = _client().get("/traces/DOESNOTEXIST00")
    assert resp.status_code == 404


@patch("src.main.process_request", new_callable=AsyncMock)
def test_traces_by_id_returns_trace(mock_pr):
    mock_pr.return_value = dict(_MOCK_RESULT)
    client = _client()
    chat_resp = client.post("/chat", json={"session_id": "s1", "user_id": "u1", "request_text": "test"})
    rid = chat_resp.json()["request_id"]
    resp = client.get(f"/traces/{rid}")
    assert resp.status_code == 200
    assert resp.json()["request_id"] == rid


# --- Explanation engine ---

def test_explanation_maps_all_exam_concepts():
    from src.agent.explanation import generate_explanation
    exp = generate_explanation(
        trace_events=[
            "Orchestrator: started (user=u1, session=s1)",
            "Orchestrator: plan → Researcher → Validator → decide",
            'Input: "test"',
            "Researcher: started",
            "Tool: find_customer_by_email → ok",
            "Researcher: ok (1 facts)",
            "Validator: started",
            "Validator: valid",
            "Decision: complete (confidence=high)",
            "Response sent",
        ],
        decision={"outcome": "complete", "confidence": "high"},
        research={"ok": True, "facts": [{"key": "name", "value": "Alice", "source": "db"}]},
        validation={"valid": True, "inconsistencies": [], "summary": "OK"},
    )
    assert exp["outcome"] == "complete"
    assert "Researcher" in exp["subagents_used"]
    assert "Validator" in exp["subagents_used"]
    assert "find_customer_by_email" in exp["tools_called"]
    concepts = exp["exam_concepts"]
    for key in ("tool_selection", "mcp_design", "subagent_context_isolation",
                "structured_outputs", "validation", "confidence_and_escalation", "observability"):
        assert key in concepts


def test_explanation_exact_tool_detection():
    from src.agent.explanation import generate_explanation
    exp = generate_explanation(
        trace_events=["Tool: get_order_by_id → ok"],
        decision={"outcome": "complete", "confidence": "high"},
        research={"ok": True, "facts": []},
        validation=None,
    )
    assert "get_order_by_id" in exp["tools_called"]
    assert "exact" in exp["exact_vs_fuzzy"].lower()


def test_explanation_fuzzy_tool_detection():
    from src.agent.explanation import generate_explanation
    exp = generate_explanation(
        trace_events=["Tool: search_customers → ok"],
        decision={"outcome": "complete", "confidence": "medium"},
        research={"ok": True, "facts": []},
        validation=None,
    )
    assert "search_customers" in exp["tools_called"]
    assert "fuzzy" in exp["exact_vs_fuzzy"].lower()


def test_explanation_escalate_outcome():
    from src.agent.explanation import generate_explanation
    exp = generate_explanation(
        trace_events=["Researcher: failed (timeout)", "Decision: escalate (confidence=low)"],
        decision={"outcome": "escalate", "confidence": "low", "escalation_reason": "low_confidence", "escalation_detail": "Research failed"},
        research={"ok": False, "facts": []},
        validation=None,
    )
    assert exp["outcome"] == "escalate"
    assert "escalate" in exp["outcome_explanation"].lower()
