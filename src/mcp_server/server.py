from mcp.server.fastmcp import FastMCP

from src.agent.errors import ErrorCategory, ToolError, ToolResult


mcp = FastMCP("architect-lab")

CUSTOMERS = {
    "alice@example.com": {"customer_id": "CUST-1001", "name": "Alice Example"},
    "bob@example.com": {"customer_id": "CUST-1002", "name": "Bob Example"},
}

ORDERS = {
    "ORD-00000001": {"order_id": "ORD-00000001", "customer_id": "CUST-1001", "status": "shipped"},
    "ORD-00000002": {"order_id": "ORD-00000002", "customer_id": "CUST-1002", "status": "processing"},
}


@mcp.tool(
    description="Exact lookup for a customer when the full email address is known. Do not use for partial names or fuzzy identity guesses."
)
def find_customer_by_email(email: str) -> dict:
    if "@" not in email:
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message="email must be a valid email address",
                retryable=False,
                suggested_action="Ask the user for a full email address",
            ),
        ).model_dump()

    customer = CUSTOMERS.get(email)
    if not customer:
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No customer found for {email}",
                retryable=False,
                suggested_action="Use search_customers if identity is incomplete",
            ),
        ).model_dump()

    return ToolResult(ok=True, data=customer).model_dump()


@mcp.tool(
    description="Fuzzy search for customers when you only have a partial name, partial email, or ambiguous identity. Prefer this over exact lookup when information is incomplete."
)
def search_customers(query: str) -> dict:
    q = query.lower().strip()
    results = [v for k, v in CUSTOMERS.items() if q in k.lower() or q in v["name"].lower()]
    return ToolResult(ok=True, data={"results": results}).model_dump()


@mcp.tool(
    description="Exact lookup for an order using a complete order ID in the form ORD-########. Do not use for date ranges or vague references such as recent order."
)
def get_order_by_id(order_id: str) -> dict:
    if not order_id.startswith("ORD-") or len(order_id) != 12:
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message="order_id must match ORD-########",
                retryable=False,
                suggested_action="Ask the user for a valid order ID",
            ),
        ).model_dump()

    order = ORDERS.get(order_id)
    if not order:
        return ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No order found for {order_id}",
                retryable=False,
                suggested_action="Use search_orders for fuzzy requests",
            ),
        ).model_dump()

    return ToolResult(ok=True, data=order).model_dump()


@mcp.tool(
    description="Fuzzy search for orders when the request is ambiguous, such as recent order, last month, or partial identifiers."
)
def search_orders(query: str) -> dict:
    q = query.lower().strip()
    results = [v for _, v in ORDERS.items() if q in v["order_id"].lower() or q in v["status"].lower()]
    return ToolResult(ok=True, data={"results": results}).model_dump()


if __name__ == "__main__":
    mcp.run()
