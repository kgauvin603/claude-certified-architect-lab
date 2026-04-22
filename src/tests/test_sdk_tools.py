import asyncio
import pytest
from src.agent.errors import ErrorCategory
from src.agent.sdk_tools import (
    find_customer_by_email,
    search_customers,
    get_order_by_id,
    search_orders,
)


def _run(tool, args: dict) -> dict:
    import json
    # @tool wraps functions in SdkMcpTool; .handler is the underlying coroutine
    raw = asyncio.run(tool.handler(args))
    return json.loads(raw["content"][0]["text"])


# --- find_customer_by_email ---

def test_find_customer_exact_hit() -> None:
    r = _run(find_customer_by_email, {"email": "alice@example.com"})
    assert r["ok"] is True
    assert r["data"]["customer_id"] == "CUST-1001"


def test_find_customer_normalizes_case() -> None:
    r = _run(find_customer_by_email, {"email": "ALICE@EXAMPLE.COM"})
    assert r["ok"] is True


def test_find_customer_invalid_email_not_retryable() -> None:
    r = _run(find_customer_by_email, {"email": "notanemail"})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.VALIDATION_ERROR
    assert r["error"]["retryable"] is False
    assert r["error"]["suggested_action"] is not None


def test_find_customer_missing_domain_is_invalid() -> None:
    r = _run(find_customer_by_email, {"email": "user@"})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.VALIDATION_ERROR


def test_find_customer_not_found() -> None:
    r = _run(find_customer_by_email, {"email": "nobody@example.com"})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.NOT_FOUND
    assert r["error"]["retryable"] is False
    assert "search_customers" in r["error"]["suggested_action"]


# --- search_customers ---

def test_search_customers_partial_name() -> None:
    r = _run(search_customers, {"query": "alice"})
    assert r["ok"] is True
    assert r["data"]["count"] == 1
    assert r["data"]["results"][0]["name"] == "Alice Example"


def test_search_customers_partial_email() -> None:
    r = _run(search_customers, {"query": "bob@"})
    assert r["ok"] is True
    assert r["data"]["count"] == 1


def test_search_customers_no_match_returns_empty() -> None:
    r = _run(search_customers, {"query": "zzznomatch"})
    assert r["ok"] is True
    assert r["data"]["count"] == 0
    assert r["data"]["results"] == []


def test_search_customers_empty_query_not_retryable() -> None:
    r = _run(search_customers, {"query": ""})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.VALIDATION_ERROR
    assert r["error"]["retryable"] is False
    assert r["error"]["suggested_action"] is not None


# --- Disambiguation: find vs search ---

def test_ambiguity_partial_name_must_use_search_not_exact() -> None:
    # 'alice' alone is not a valid email — exact lookup must reject it
    r = _run(find_customer_by_email, {"email": "alice"})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.VALIDATION_ERROR


# --- get_order_by_id ---

def test_get_order_exact_hit() -> None:
    r = _run(get_order_by_id, {"order_id": "ORD-00000001"})
    assert r["ok"] is True
    assert r["data"]["order_id"] == "ORD-00000001"
    assert r["data"]["status"] == "delivered"
    assert r["data"]["amount"] == 129.99


def test_get_order_normalizes_case() -> None:
    r = _run(get_order_by_id, {"order_id": "ord-00000001"})
    assert r["ok"] is True


def test_get_order_invalid_format_not_retryable() -> None:
    r = _run(get_order_by_id, {"order_id": "12345"})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.VALIDATION_ERROR
    assert r["error"]["retryable"] is False
    assert r["error"]["suggested_action"] is not None


def test_get_order_non_digit_suffix_is_invalid() -> None:
    r = _run(get_order_by_id, {"order_id": "ORD-ABCDEFGH"})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.VALIDATION_ERROR


def test_get_order_not_found() -> None:
    r = _run(get_order_by_id, {"order_id": "ORD-99999999"})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.NOT_FOUND
    assert r["error"]["retryable"] is False
    assert "search_orders" in r["error"]["suggested_action"]


# --- search_orders ---

def test_search_orders_by_status() -> None:
    r = _run(search_orders, {"query": "delivered"})
    assert r["ok"] is True
    assert r["data"]["count"] == 1
    assert r["data"]["results"][0]["order_id"] == "ORD-00000001"


def test_search_orders_by_customer_id() -> None:
    r = _run(search_orders, {"query": "CUST-1002"})
    assert r["ok"] is True
    assert r["data"]["count"] == 1
    assert r["data"]["results"][0]["order_id"] == "ORD-00000002"


def test_search_orders_by_partial_order_id() -> None:
    r = _run(search_orders, {"query": "00000002"})
    assert r["ok"] is True
    assert r["data"]["count"] == 1


def test_search_orders_no_match_returns_empty() -> None:
    r = _run(search_orders, {"query": "zzznomatch"})
    assert r["ok"] is True
    assert r["data"]["count"] == 0


def test_search_orders_empty_query_not_retryable() -> None:
    r = _run(search_orders, {"query": ""})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.VALIDATION_ERROR
    assert r["error"]["retryable"] is False
    assert r["error"]["suggested_action"] is not None


# --- Disambiguation: get_order vs search_orders ---

def test_ambiguity_vague_reference_must_not_use_exact_lookup() -> None:
    # "recent" is not an ORD-######## ID — exact lookup must reject it
    r = _run(get_order_by_id, {"order_id": "recent"})
    assert r["ok"] is False
    assert r["error"]["category"] == ErrorCategory.VALIDATION_ERROR
