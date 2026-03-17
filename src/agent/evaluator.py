from dataclasses import dataclass


@dataclass
class EvalCase:
    prompt: str
    expected_tool: str


DEFAULT_CASES = [
    EvalCase(prompt="refund my recent order", expected_tool="search_orders"),
    EvalCase(prompt="look up alice", expected_tool="search_customers"),
    EvalCase(prompt="cancel ORD-00000002", expected_tool="get_order_by_id"),
]


def choose_tool_heuristic(user_text: str) -> str:
    t = user_text.lower()
    if "ord-" in t:
        return "get_order_by_id"
    if "recent" in t or "last" in t:
        return "search_orders"
    if "@" in t:
        return "find_customer_by_email"
    return "search_customers"


def run_eval() -> list[dict[str, str | bool]]:
    results: list[dict[str, str | bool]] = []
    for case in DEFAULT_CASES:
        actual = choose_tool_heuristic(case.prompt)
        results.append(
            {
                "prompt": case.prompt,
                "expected_tool": case.expected_tool,
                "actual_tool": actual,
                "passed": actual == case.expected_tool,
            }
        )
    return results
