def choose_tool(user_text: str) -> str:
    t = user_text.lower()
    if "ord-" in t:
        return "get_order_by_id"
    if "recent" in t or "last" in t:
        return "search_orders"
    if "@" in t:
        return "find_customer_by_email"
    return "search_customers"


def test_recent_order_prefers_search() -> None:
    assert choose_tool("refund my recent order") == "search_orders"


def test_partial_identity_prefers_fuzzy_search() -> None:
    assert choose_tool("look up alice") == "search_customers"
