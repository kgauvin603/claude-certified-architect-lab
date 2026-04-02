from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server
from .errors import ToolResult, ToolError, ErrorCategory

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


def sdk_text(payload: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": str(payload)}]}


@tool(
    "find_customer_by_email",
    "Exact lookup for a customer when the full email address is known. Do not use for partial names or vague identity.",
    {"email": str},
)
async def find_customer_by_email(args: dict[str, Any]) -> dict[str, Any]:
    email = args["email"]
    if "@" not in email:
        result = ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message="email must be a valid email address",
                retryable=False,
                suggested_action="Ask the user for a full email address",
            ),
        )
        return sdk_text(result.model_dump())

    customer = CUSTOMERS.get(email)
    if not customer:
        result = ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No customer found for {email}",
                retryable=False,
                suggested_action="Use search_customers if identity is incomplete",
            ),
        )
        return sdk_text(result.model_dump())

    return sdk_text(ToolResult(ok=True, data=customer).model_dump())


@tool(
    "search_customers",
    "Fuzzy search for customers when you only have a partial name, partial email, or ambiguous identity.",
    {"query": str},
)
async def search_customers(args: dict[str, Any]) -> dict[str, Any]:
    q = args["query"].lower().strip()
    results = [v for k, v in CUSTOMERS.items() if q in k.lower() or q in v["name"].lower()]
    return sdk_text(ToolResult(ok=True, data={"results": results}).model_dump())


@tool(
    "get_order_by_id",
    "Exact lookup for an order using a complete order ID in the form ORD-########.",
    {"order_id": str},
)
async def get_order_by_id(args: dict[str, Any]) -> dict[str, Any]:
    order_id = args["order_id"]
    if not order_id.startswith("ORD-") or len(order_id) != 12:
        result = ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message="order_id must match ORD-########",
                retryable=False,
                suggested_action="Ask the user for a valid order ID",
            ),
        )
        return sdk_text(result.model_dump())

    order = ORDERS.get(order_id)
    if not order:
        result = ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No order found for {order_id}",
                retryable=False,
                suggested_action="Use search_orders for fuzzy requests",
            ),
        )
        return sdk_text(result.model_dump())

    return sdk_text(ToolResult(ok=True, data=order).model_dump())


@tool(
    "search_orders",
    "Fuzzy search for orders when the request is ambiguous, such as recent order, last month, or partial identifiers.",
    {"query": str},
)
async def search_orders(args: dict[str, Any]) -> dict[str, Any]:
    q = args["query"].lower().strip()
    results = [v for _, v in ORDERS.items() if q in v["order_id"].lower() or q in v["status"].lower()]
    return sdk_text(ToolResult(ok=True, data={"results": results}).model_dump())


@tool(
    "check_refund_eligibility",
    "Checks whether an order is eligible for refund under current refund rules.",
    {"order_id": str},
)
async def check_refund_eligibility(args: dict[str, Any]) -> dict[str, Any]:
    order_id = args["order_id"]
    order = ORDERS.get(order_id)
    if not order:
        result = ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No order found for {order_id}",
                retryable=False,
            ),
        )
        return sdk_text(result.model_dump())

    if order["status"] != "delivered":
        return sdk_text(ToolResult(ok=True, data={
            "eligible": False,
            "reason": "Order has not been delivered yet."
        }).model_dump())

    if order["days_since_delivery"] is not None and order["days_since_delivery"] <= 30:
        return sdk_text(ToolResult(ok=True, data={
            "eligible": True,
            "reason": "Within 30-day refund window."
        }).model_dump())

    return sdk_text(ToolResult(ok=True, data={
        "eligible": False,
        "reason": "Outside refund window."
    }).model_dump())


@tool(
    "escalate_case",
    "Escalate to a human when policy is unclear, the user requests a human, or the agent cannot safely make progress.",
    {"summary": str},
)
async def escalate_case(args: dict[str, Any]) -> dict[str, Any]:
    return sdk_text(ToolResult(ok=True, data={
        "escalated": True,
        "queue": "billing-support",
        "summary": args["summary"],
    }).model_dump())


SUPPORT_MCP_SERVER = create_sdk_mcp_server(
    name="support_tools",
    version="1.0.0",
    tools=[
        find_customer_by_email,
        search_customers,
        get_order_by_id,
        search_orders,
        check_refund_eligibility,
        escalate_case,
    ],
)
