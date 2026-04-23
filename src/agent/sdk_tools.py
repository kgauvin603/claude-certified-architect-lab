from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server
from .errors import ToolResult, ToolError, ErrorCategory
from .observability import log_tool_call

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


def sdk_text(result: ToolResult) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": result.model_dump_json()}]}


@tool(
    "find_customer_by_email",
    (
        "Exact lookup: call ONLY when a complete, syntactically valid email address is provided "
        "(must contain '@' and a domain). Do NOT call for display names, partial emails, or vague "
        "identity like 'find Alice'. Use search_customers whenever the full email is not confirmed."
    ),
    {"email": str},
)
async def find_customer_by_email(args: dict[str, Any]) -> dict[str, Any]:
    email = args["email"].strip().lower()
    parts = email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1] or "." not in parts[1]:
        log_tool_call("find_customer_by_email", f"email={email!r}", "error: invalid email format")
        return sdk_text(ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message=f"'{args['email']}' is not a valid email address",
                retryable=False,
                suggested_action="Ask the user for their full email address, or use search_customers with a name",
            ),
        ))

    customer = CUSTOMERS.get(email)
    if not customer:
        log_tool_call("find_customer_by_email", f"email={email!r}", "error: not found")
        return sdk_text(ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No customer found for email '{email}'",
                retryable=False,
                suggested_action="Verify the email with the user, or try search_customers with a partial name",
            ),
        ))

    log_tool_call("find_customer_by_email", f"email={email!r}", f"found customer_id={customer['customer_id']}")
    return sdk_text(ToolResult(ok=True, data=customer))


@tool(
    "search_customers",
    (
        "Fuzzy search: call when identity is ambiguous — partial name, misspelled name, display name "
        "(e.g. 'Alice'), or incomplete email. Use when the user says 'find', 'look up', or 'search' "
        "without supplying a verified full email. Do NOT call when a complete email address is already known."
    ),
    {"query": str},
)
async def search_customers(args: dict[str, Any]) -> dict[str, Any]:
    q = args["query"].strip()
    if not q:
        log_tool_call("search_customers", "query=''", "error: empty query")
        return sdk_text(ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message="query must not be empty",
                retryable=False,
                suggested_action="Ask the user for a name, partial email, or other identifying information",
            ),
        ))

    q_lower = q.lower()
    results = [v for k, v in CUSTOMERS.items() if q_lower in k or q_lower in v["name"].lower()]
    log_tool_call("search_customers", f"query={q!r}", f"{len(results)} results")
    return sdk_text(ToolResult(ok=True, data={"results": results, "count": len(results)}))


@tool(
    "get_order_by_id",
    (
        "Exact lookup: call ONLY when the user provides a complete order ID in the format ORD-######## "
        "(the prefix 'ORD-' followed by exactly 8 digits, 12 characters total). Do NOT call for "
        "'recent order', 'last order', date ranges, status queries, or any partial reference. "
        "Use search_orders for all ambiguous or incomplete order references."
    ),
    {"order_id": str},
)
async def get_order_by_id(args: dict[str, Any]) -> dict[str, Any]:
    order_id = args["order_id"].strip().upper()
    suffix = order_id[4:] if order_id.startswith("ORD-") else ""
    if len(order_id) != 12 or not order_id.startswith("ORD-") or not suffix.isdigit():
        log_tool_call("get_order_by_id", f"order_id={order_id!r}", "error: invalid format")
        return sdk_text(ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message=f"'{args['order_id']}' is not a valid order ID; expected ORD-######## (12 characters)",
                retryable=False,
                suggested_action="Ask the user for a valid order ID, or use search_orders if the ID is uncertain",
            ),
        ))

    order = ORDERS.get(order_id)
    if not order:
        log_tool_call("get_order_by_id", f"order_id={order_id!r}", "error: not found")
        return sdk_text(ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No order found for '{order_id}'",
                retryable=False,
                suggested_action="Confirm the order ID with the user, or use search_orders to locate it",
            ),
        ))

    log_tool_call("get_order_by_id", f"order_id={order_id!r}", f"found status={order['status']} amount={order['amount']}")
    return sdk_text(ToolResult(ok=True, data=order))


@tool(
    "search_orders",
    (
        "Fuzzy/range search: call for any order reference that is not a complete ORD-######## ID — "
        "this includes 'recent order', 'last order', date ranges, delivery status (e.g. 'delivered'), "
        "customer ID (e.g. CUST-1001), or partial identifiers. "
        "Do NOT call when the user has already provided a complete, verified ORD-######## order ID."
    ),
    {"query": str},
)
async def search_orders(args: dict[str, Any]) -> dict[str, Any]:
    q = args["query"].strip()
    if not q:
        log_tool_call("search_orders", "query=''", "error: empty query")
        return sdk_text(ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.VALIDATION_ERROR,
                message="query must not be empty",
                retryable=False,
                suggested_action="Provide a status (e.g. 'delivered'), customer ID, or partial order ID",
            ),
        ))

    q_lower = q.lower()
    results = [
        v for _, v in ORDERS.items()
        if q_lower in v["order_id"].lower()
        or q_lower in v["status"].lower()
        or q_lower in v.get("customer_id", "").lower()
    ]
    log_tool_call("search_orders", f"query={q!r}", f"{len(results)} results")
    return sdk_text(ToolResult(ok=True, data={"results": results, "count": len(results)}))


@tool(
    "check_refund_eligibility",
    "Checks whether an order is eligible for refund under current refund rules.",
    {"order_id": str},
)
async def check_refund_eligibility(args: dict[str, Any]) -> dict[str, Any]:
    order_id = args["order_id"].strip().upper()
    order = ORDERS.get(order_id)
    if not order:
        log_tool_call("check_refund_eligibility", f"order_id={order_id!r}", "error: not found")
        return sdk_text(ToolResult(
            ok=False,
            error=ToolError(
                category=ErrorCategory.NOT_FOUND,
                message=f"No order found for '{order_id}'",
                retryable=False,
                suggested_action="Use get_order_by_id or search_orders to verify the order ID first",
            ),
        ))

    if order["status"] != "delivered":
        log_tool_call("check_refund_eligibility", f"order_id={order_id!r}", "eligible=False (not delivered)")
        return sdk_text(ToolResult(ok=True, data={
            "eligible": False,
            "reason": "Order has not been delivered yet.",
        }))

    if order["days_since_delivery"] is not None and order["days_since_delivery"] <= 30:
        log_tool_call("check_refund_eligibility", f"order_id={order_id!r}", "eligible=True (within 30-day window)")
        return sdk_text(ToolResult(ok=True, data={
            "eligible": True,
            "reason": "Within 30-day refund window.",
        }))

    log_tool_call("check_refund_eligibility", f"order_id={order_id!r}", "eligible=False (outside 30-day window)")
    return sdk_text(ToolResult(ok=True, data={
        "eligible": False,
        "reason": "Outside 30-day refund window.",
    }))


@tool(
    "escalate_case",
    "Escalate to a human when policy is unclear, the user requests a human, or the agent cannot safely make progress.",
    {"summary": str},
)
async def escalate_case(args: dict[str, Any]) -> dict[str, Any]:
    summary = args["summary"]
    log_tool_call("escalate_case", f"summary={summary[:60]!r}", "escalated to billing-support")
    return sdk_text(ToolResult(ok=True, data={
        "escalated": True,
        "queue": "billing-support",
        "summary": summary,
    }))


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
