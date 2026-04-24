from typing import Optional

EXACT_TOOLS = {"find_customer_by_email", "get_order_by_id"}
FUZZY_TOOLS = {"search_customers", "search_orders"}


def generate_explanation(
    trace_events: list[str],
    decision: dict,
    research: dict,
    validation: Optional[dict],
) -> dict:
    tools_called = _extract_tools(trace_events)
    exact_used = [t for t in tools_called if t in EXACT_TOOLS]
    fuzzy_used = [t for t in tools_called if t in FUZZY_TOOLS]
    subagents = _extract_subagents(trace_events)
    outcome = decision.get("outcome", "unknown")
    confidence = decision.get("confidence", "unknown")

    return {
        "orchestrator_role": _describe_orchestrator(trace_events, outcome),
        "subagents_used": subagents,
        "tools_called": tools_called,
        "tool_selection_rationale": _describe_tool_selection(tools_called, exact_used, fuzzy_used),
        "exact_vs_fuzzy": _describe_exact_vs_fuzzy(exact_used, fuzzy_used),
        "outcome": outcome,
        "outcome_explanation": _describe_outcome(outcome, confidence, decision),
        "exam_concepts": _exam_concepts(
            tools_called, exact_used, fuzzy_used, subagents,
            outcome, confidence, research, validation, trace_events,
        ),
    }


def _extract_tools(events: list[str]) -> list[str]:
    seen: list[str] = []
    for e in events:
        if e.startswith("Tool: "):
            name = e[6:].split("→")[0].strip()
            if name and name not in seen:
                seen.append(name)
    return seen


def _extract_subagents(events: list[str]) -> list[str]:
    agents: list[str] = []
    if any("Researcher" in e for e in events):
        agents.append("Researcher")
    if any("Validator" in e for e in events):
        agents.append("Validator")
    return agents


def _describe_orchestrator(events: list[str], outcome: str) -> str:
    steps = []
    if any("Researcher" in e for e in events):
        steps.append("dispatched the Researcher subagent to gather facts using MCP tools")
    if any("Validator" in e for e in events):
        steps.append("dispatched the Validator subagent to check consistency")
    steps.append(f"made a final decision: {outcome}")
    return "The Orchestrator " + ", then ".join(steps) + "."


def _describe_tool_selection(tools: list[str], exact: list[str], fuzzy: list[str]) -> str:
    if not tools:
        return "No tools were called during this request."
    parts = []
    for t in tools:
        if t in EXACT_TOOLS:
            parts.append(f"{t} (exact lookup — requires precise identifier)")
        elif t in FUZZY_TOOLS:
            parts.append(f"{t} (fuzzy search — used for partial or descriptive queries)")
        else:
            parts.append(t)
    return "Tools selected: " + "; ".join(parts) + "."


def _describe_exact_vs_fuzzy(exact: list[str], fuzzy: list[str]) -> str:
    if not exact and not fuzzy:
        return "No lookup tools were called."
    if exact and not fuzzy:
        return (
            f"Only exact-lookup tools were used ({', '.join(exact)}). "
            "The request contained a precise identifier (email or order ID), "
            "so the agent correctly avoided fuzzy search."
        )
    if fuzzy and not exact:
        return (
            f"Only fuzzy-search tools were used ({', '.join(fuzzy)}). "
            "The request lacked a precise identifier, "
            "so the agent searched by description or partial match."
        )
    return (
        f"Both exact-lookup ({', '.join(exact)}) and fuzzy-search ({', '.join(fuzzy)}) tools were used. "
        "Exact lookup was used for precise identifiers; fuzzy search for broader queries."
    )


def _describe_outcome(outcome: str, confidence: str, decision: dict) -> str:
    if outcome == "complete":
        return (
            f"The agent completed with {confidence} confidence. "
            "All facts were gathered and validated successfully."
        )
    if outcome == "clarify":
        q = decision.get("clarifying_question", "")
        return f"The agent requested clarification (confidence={confidence}): {q}"
    if outcome == "escalate":
        reason = decision.get("escalation_reason") or ""
        detail = decision.get("escalation_detail") or ""
        return f"The agent escalated (confidence={confidence}, reason={reason}): {detail}"
    return f"Outcome: {outcome} (confidence={confidence})"


def _exam_concepts(
    tools: list[str],
    exact: list[str],
    fuzzy: list[str],
    subagents: list[str],
    outcome: str,
    confidence: str,
    research: dict,
    validation: Optional[dict],
    events: list[str],
) -> dict:
    validation_note = (
        "was skipped (no facts to validate)" if validation is None
        else ("ran and found no issues" if validation.get("valid") else "ran and found inconsistencies")
    )
    return {
        "tool_selection": (
            "Tool selection is a core exam topic. "
            + (
                f"This request used exact-lookup tools ({', '.join(exact)}) when a precise identifier was present, "
                "demonstrating correct disambiguation over fuzzy search."
                if exact else
                "This request used fuzzy search, appropriate when no exact identifier was available."
            )
        ),
        "mcp_design": (
            "MCP tools are exposed in-process via create_sdk_mcp_server(). "
            "Each tool has a precise description that guides the model's selection. "
            "The exam tests whether you separate exact-lookup tools from fuzzy-search tools in your MCP server design."
        ),
        "subagent_context_isolation": (
            f"This request used {len(subagents)} subagent(s): {', '.join(subagents) or 'none'}. "
            "Each subagent received only the facts it needed (last 5 known facts). "
            "Context isolation prevents information leakage and keeps prompts focused — a key exam principle."
        ),
        "structured_outputs": (
            "All subagent outputs are validated against Pydantic schemas (ResearchResult, ValidationResult). "
            "JSON parse failures trigger retries. The schema enforces required vs nullable fields. "
            "The exam tests whether you design structured output contracts that can be validated."
        ),
        "validation": (
            f"Validation {validation_note}. "
            "The Validator subagent checks for internal inconsistencies in gathered facts "
            "before a decision is made, adding a confidence layer above raw research."
        ),
        "confidence_and_escalation": (
            f"Final confidence: {confidence}, outcome: {outcome}. "
            "The exam tests whether your agent escalates on low confidence or repeated failures "
            "rather than returning incorrect answers with false high confidence."
        ),
        "observability": (
            f"This request generated {len(events)} trace events including ORCHESTRATOR_START, "
            "RESEARCHER events, TOOL_CALL entries, VALIDATOR events, DECISION, and RESPONSE_SENT. "
            "Each event carries the same request_id for correlation — a required exam design pattern."
        ),
    }
