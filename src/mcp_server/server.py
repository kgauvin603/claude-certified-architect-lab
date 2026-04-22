from mcp.server.fastmcp import FastMCP

from src.agent.errors import ErrorCategory, ToolError, ToolResult


mcp = FastMCP("architect-lab")

CUSTOMERS = {
    "alice@example.com": {"customer_id": "CUST-1001", "name": "Alice Example"},
    "bob@example.com": {"customer_id": "CUST-1002", "name": "Bob Example"},
}

ORDERS = {
    "ORD-00000001": {
        "order_id": "ORD-00000001",
        "customer_id": "CUST-1001",
        "status": "delivered",
        "amount": 129.99,
        "days_since_delivery": 12,
        "refundable": True,
    },
    "ORD-00000002": {
        "order_id": "ORD-00000002",
        "customer_id": "CUST-1002",
        "status": "processing",
        "amount": 49.99,
        "days_since_delivery": None,
        "refundable": False,
    },
}


@mcp.tool(
    description=(
        "Exact lookup: call ONLY when a complete, syntactically valid email address is provided "
        "(must contain '@' and a domain). Do NOT call for display names, partial emails, or vague "
        "identity like 'find Alice'. Use search_customers whenever the full email is not confirmed."
    )
)
def find_customer_by_email(email: str) -> dict:
    parts = email.strip().lower().split("@")
    if len(parts) != 2 or not parts[0] or not parts[1] or "." not in parts[1]:
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message=f"'{email}' is not a valid email address",
                retryable=False,
                suggested_action="Ask the user for their full email address, or use search_customers with a name",
            ),
        ).model_dump()

    customer = CUSTOMERS.get(email.strip().lower())
    if not customer:
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No customer found for email '{email}'",
                retryable=False,
                suggested_action="Verify the email with the user, or try search_customers with a partial name",
            ),
        ).model_dump()

    return ToolResult(ok=True, data=customer).model_dump()


@mcp.tool(
    description=(
        "Fuzzy search: call when identity is ambiguous — partial name, misspelled name, display name "
        "(e.g. 'Alice'), or incomplete email. Use when the user says 'find', 'look up', or 'search' "
        "without supplying a verified full email. Do NOT call when a complete email address is already known."
    )
)
def search_customers(query: str) -> dict:
    q = query.strip()
    if not q:
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message="query must not be empty",
                retryable=False,
                suggested_action="Ask the user for a name, partial email, or other identifying information",
            ),
        ).model_dump()

    q_lower = q.lower()
    results = [v for k, v in CUSTOMERS.items() if q_lower in k or q_lower in v["name"].lower()]
    return ToolResult(ok=True, data={"results": results, "count": len(results)}).model_dump()


@mcp.tool(
    description=(
        "Exact lookup: call ONLY when the user provides a complete order ID in the format ORD-######## "
        "(the prefix 'ORD-' followed by exactly 8 digits, 12 characters total). Do NOT call for "
        "'recent order', 'last order', date ranges, status queries, or any partial reference. "
        "Use search_orders for all ambiguous or incomplete order references."
    )
)
def get_order_by_id(order_id: str) -> dict:
    oid = order_id.strip().upper()
    suffix = oid[4:] if oid.startswith("ORD-") else ""
    if len(oid) != 12 or not oid.startswith("ORD-") or not suffix.isdigit():
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message=f"'{order_id}' is not a valid order ID; expected ORD-######## (12 characters)",
                retryable=False,
                suggested_action="Ask the user for a valid order ID, or use search_orders if the ID is uncertain",
            ),
        ).model_dump()

    order = ORDERS.get(oid)
    if not order:
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No order found for '{oid}'",
                retryable=False,
                suggested_action="Confirm the order ID with the user, or use search_orders to locate it",
            ),
        ).model_dump()

    return ToolResult(ok=True, data=order).model_dump()


@mcp.tool(
    description=(
        "Fuzzy/range search: call for any order reference that is not a complete ORD-######## ID — "
        "this includes 'recent order', 'last order', date ranges, delivery status (e.g. 'delivered'), "
        "customer ID (e.g. CUST-1001), or partial identifiers. "
        "Do NOT call when the user has already provided a complete, verified ORD-######## order ID."
    )
)
def search_orders(query: str) -> dict:
    q = query.strip()
    if not q:
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message="query must not be empty",
                retryable=False,
                suggested_action="Provide a status (e.g. 'delivered'), customer ID, or partial order ID",
            ),
        ).model_dump()

    q_lower = q.lower()
    results = [
        v for _, v in ORDERS.items()
        if q_lower in v["order_id"].lower()
        or q_lower in v["status"].lower()
        or q_lower in v.get("customer_id", "").lower()
    ]
    return ToolResult(ok=True, data={"results": results, "count": len(results)}).model_dump()


if __name__ == "__main__":
    mcp.run()
