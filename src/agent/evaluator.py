import re
from dataclasses import dataclass

# Exact-identifier patterns
_EXACT_ORDER_ID = re.compile(r"\bord-\d{8}\b")
_EXACT_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b")

# Fuzzy signals: temporal or vague order language
_ORDER_FUZZY = frozenset([
    "recent", "last month", "last week", "last order",
    "last purchase", "yesterday", "latest", "bought last",
])

# Fuzzy signals: identity lookup verbs
_CUSTOMER_FUZZY = frozenset(["look up", "find", "search for", "search"])

# Order intent words that alone don't identify the order
_ORDER_INTENT = frozenset([
    "order", "refund", "cancel", "purchase", "delivery", "shipment", "return",
])

# Common contractions that look like possessives but are not names
_CONTRACTIONS = frozenset([
    "it's", "that's", "what's", "who's", "there's", "here's", "he's", "she's",
])


def _has_possessive_name(text: str) -> bool:
    """True when text contains a possessive like "John's" that is not a contraction."""
    return bool(re.search(r"\b\w+'s\b", text)) and not any(c in text for c in _CONTRACTIONS)


@dataclass
class EvalCase:
    prompt: str
    expected_tool: str


DEFAULT_CASES = [
    # Exact-identifier cases
    EvalCase(prompt="cancel ORD-00000002", expected_tool="get_order_by_id"),
    EvalCase(prompt="look up alice@example.com", expected_tool="find_customer_by_email"),
    # Fuzzy order cases
    EvalCase(prompt="refund my recent order", expected_tool="search_orders"),
    EvalCase(prompt="cancel what I bought last month", expected_tool="search_orders"),
    # Fuzzy customer cases
    EvalCase(prompt="look up alice", expected_tool="search_customers"),
    EvalCase(prompt="look up John's account", expected_tool="search_customers"),
    # Clarification required
    EvalCase(prompt="cancel my order", expected_tool="clarify"),
    EvalCase(prompt="I need a refund", expected_tool="clarify"),
]


def choose_tool_heuristic(user_text: str) -> str:
    """
    Returns the correct tool name, or "clarify" when no actionable
    identifier is present and guessing would be wrong.
    """
    t = user_text.lower()

    # 1. Exact identifiers always win
    if _EXACT_ORDER_ID.search(t):
        return "get_order_by_id"
    if _EXACT_EMAIL.search(t):
        return "find_customer_by_email"

    # 2. Temporal / recency language → fuzzy order search
    if any(sig in t for sig in _ORDER_FUZZY):
        return "search_orders"

    # 3. Identity lookup verb or possessive name → fuzzy customer search
    if any(sig in t for sig in _CUSTOMER_FUZZY) or _has_possessive_name(t):
        return "search_customers"

    # 4. Order-intent words without an identifier → must clarify
    if any(word in t for word in _ORDER_INTENT):
        return "clarify"

    # 5. No signal at all → must clarify
    return "clarify"


def run_eval() -> list[dict[str, str | bool]]:
    results: list[dict[str, str | bool]] = []
    for case in DEFAULT_CASES:
        actual = choose_tool_heuristic(case.prompt)
        results.append({
            "prompt": case.prompt,
            "expected_tool": case.expected_tool,
            "actual_tool": actual,
            "passed": actual == case.expected_tool,
        })
    return results
