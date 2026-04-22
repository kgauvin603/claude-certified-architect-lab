import re
import pytest
from src.agent.evaluator import choose_tool_heuristic, run_eval


# ---------------------------------------------------------------------------
# Local simple heuristic used in the original tests (kept for compatibility)
# Uses the same ORD-######## regex the tool descriptions require, so partial
# IDs like "ORD-123" are not mistaken for exact identifiers.
# ---------------------------------------------------------------------------

_FULL_ORDER_ID = re.compile(r"\bord-\d{8}\b")

def choose_tool(user_text: str) -> str:
    t = user_text.lower()
    if _FULL_ORDER_ID.search(t):
        return "get_order_by_id"
    if "recent" in t or "last" in t:
        return "search_orders"
    if "@" in t:
        return "find_customer_by_email"
    return "search_customers"


# ---------------------------------------------------------------------------
# Original tests (unchanged)
# ---------------------------------------------------------------------------

def test_recent_order_prefers_search() -> None:
    assert choose_tool("refund my recent order") == "search_orders"


def test_partial_identity_prefers_fuzzy_search() -> None:
    assert choose_tool("look up alice") == "search_customers"


# ---------------------------------------------------------------------------
# Required new cases: exact prompts from the task
# ---------------------------------------------------------------------------

def test_refund_recent_order_uses_search_orders() -> None:
    assert choose_tool("refund my recent order") == "search_orders"


def test_possessive_name_uses_search_customers() -> None:
    # "John's" is a possessive first name — no email present
    assert choose_tool("look up John's account") == "search_customers"


def test_temporal_last_month_uses_search_orders() -> None:
    # "last month" is a temporal reference — no order ID present
    assert choose_tool("cancel what I bought last month") == "search_orders"


# ---------------------------------------------------------------------------
# Disambiguation: exact-lookup tools must reject non-exact input
# ---------------------------------------------------------------------------

def test_exact_order_id_uses_get_order_by_id() -> None:
    assert choose_tool("cancel ORD-00000002") == "get_order_by_id"


def test_exact_email_uses_find_customer_by_email() -> None:
    assert choose_tool("look up alice@example.com") == "find_customer_by_email"


def test_partial_order_id_does_not_use_exact_lookup() -> None:
    # "ORD-" without the full 8-digit suffix should not trigger exact lookup
    result = choose_tool("I think my order starts with ORD-123")
    assert result != "get_order_by_id"


# ---------------------------------------------------------------------------
# Clarification: improved heuristic must ask instead of guessing
# ---------------------------------------------------------------------------

def test_vague_cancel_requires_clarification() -> None:
    # No order ID, no email, no name, no temporal reference
    assert choose_tool_heuristic("cancel my order") == "clarify"


def test_bare_refund_request_requires_clarification() -> None:
    assert choose_tool_heuristic("I need a refund") == "clarify"


def test_possessive_name_heuristic_uses_search_customers() -> None:
    assert choose_tool_heuristic("look up John's account") == "search_customers"


def test_last_month_heuristic_uses_search_orders() -> None:
    assert choose_tool_heuristic("cancel what I bought last month") == "search_orders"


def test_recent_heuristic_uses_search_orders() -> None:
    assert choose_tool_heuristic("refund my recent order") == "search_orders"


# ---------------------------------------------------------------------------
# run_eval: all DEFAULT_CASES must pass
# ---------------------------------------------------------------------------

def test_run_eval_all_cases_pass() -> None:
    results = run_eval()
    failures = [r for r in results if not r["passed"]]
    assert failures == [], f"Eval failures: {failures}"
