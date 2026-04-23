from pathlib import Path
from .errors import ErrorCategory
from .schemas import (
    TicketContext,
    ResearchRequest,
    ValidationRequest,
    ResearchResult,
    ValidationResult,
    ConfidenceLevel,
    EscalationReason,
    CoordinatorDecision,
)
from .sessions import load_session, save_session
from .subagents import run_researcher, run_validator
from .observability import (
    log_researcher_start,
    log_researcher_result,
    log_validator_start,
    log_validator_result,
    log_decision,
)

SCRATCHPAD_DIR = Path(__file__).parent.parent.parent / "data" / "scratchpads"
SCRATCHPAD_DIR.mkdir(parents=True, exist_ok=True)

_MAX_CARRIED_FACTS = 5
_MAX_TOOL_FAILURES = 2


def write_scratchpad(session_id: str, note: str) -> None:
    path = SCRATCHPAD_DIR / f"{session_id}.md"
    existing = path.read_text() if path.exists() else ""
    path.write_text(existing + f"\n- {note}")


def score_confidence(
    research_result: ResearchResult,
    validation_result: ValidationResult | None,
) -> ConfidenceLevel:
    if not research_result.ok:
        return ConfidenceLevel.LOW
    if validation_result is None:
        return ConfidenceLevel.MEDIUM
    if not validation_result.valid:
        has_errors = any(i.severity == "error" for i in validation_result.inconsistencies)
        return ConfidenceLevel.LOW if has_errors else ConfidenceLevel.MEDIUM
    return ConfidenceLevel.HIGH


def _clarifying_question(
    research_result: ResearchResult,
    validation_result: ValidationResult | None,
) -> str:
    if validation_result and not validation_result.valid and validation_result.inconsistencies:
        first = validation_result.inconsistencies[0]
        return (
            f"I found a potential issue with {first.field}: {first.description}. "
            "Could you confirm this detail so I can proceed?"
        )
    return "Could you provide more details so I can complete your request?"


def _escalation_detail(
    research_result: ResearchResult,
    validation_result: ValidationResult | None,
) -> str:
    if not research_result.ok and research_result.error:
        return research_result.error.get("message", "Research failed")
    if validation_result and not validation_result.valid:
        error_items = [
            i for i in validation_result.inconsistencies if i.severity == "error"
        ]
        if error_items:
            return "; ".join(f"{i.field}: {i.description}" for i in error_items)
    return "Unable to reach sufficient confidence to complete the request"


def decide(
    ctx: TicketContext,
    research_result: ResearchResult,
    validation_result: ValidationResult | None,
) -> CoordinatorDecision:
    if any(count >= _MAX_TOOL_FAILURES for count in ctx.tool_failure_counts.values()):
        return CoordinatorDecision(
            outcome="escalate",
            confidence=ConfidenceLevel.LOW,
            escalation_reason=EscalationReason.REPEATED_FAILURE,
            escalation_detail=f"Tool failure threshold reached: {dict(ctx.tool_failure_counts)}",
        )

    confidence = score_confidence(research_result, validation_result)

    if confidence == ConfidenceLevel.HIGH:
        return CoordinatorDecision(outcome="complete", confidence=confidence)

    if confidence == ConfidenceLevel.MEDIUM:
        return CoordinatorDecision(
            outcome="clarify",
            confidence=confidence,
            clarifying_question=_clarifying_question(research_result, validation_result),
        )

    return CoordinatorDecision(
        outcome="escalate",
        confidence=confidence,
        escalation_reason=EscalationReason.LOW_CONFIDENCE,
        escalation_detail=_escalation_detail(research_result, validation_result),
    )


async def process_request(session_id: str, user_id: str, request_text: str) -> dict:
    ctx = load_session(session_id) or TicketContext(
        session_id=session_id,
        user_id=user_id,
        request_text=request_text,
    )
    ctx.request_text = request_text

    log_researcher_start()
    research_result = await run_researcher(ResearchRequest(
        user_id=user_id,
        request_text=request_text,
        known_facts=ctx.facts[-_MAX_CARRIED_FACTS:],
    ))

    # Retry once on retryable research failure; track each failure
    if not research_result.ok:
        error = research_result.error or {}
        tool_key = error.get("category", "researcher")
        ctx.tool_failure_counts[tool_key] = ctx.tool_failure_counts.get(tool_key, 0) + 1

        if error.get("retryable") and ctx.tool_failure_counts[tool_key] < _MAX_TOOL_FAILURES:
            log_researcher_start()
            research_result = await run_researcher(ResearchRequest(
                user_id=user_id,
                request_text=request_text,
                known_facts=ctx.facts[-_MAX_CARRIED_FACTS:],
            ))
            if not research_result.ok:
                ctx.tool_failure_counts[tool_key] += 1

    log_researcher_result(
        ok=research_result.ok,
        fact_count=len(research_result.facts),
        error_msg=(research_result.error or {}).get("message", "") if not research_result.ok else "",
    )

    validation_result = None
    if research_result.ok and research_result.facts:
        log_validator_start(len(research_result.facts))
        validation_result = await run_validator(ValidationRequest(
            request_text=request_text,
            facts=research_result.facts,
        ))
        log_validator_result(
            valid=validation_result.valid,
            inconsistency_count=len(validation_result.inconsistencies),
        )

    if research_result.ok:
        ctx.facts.extend(f"{f.key}={f.value}" for f in research_result.facts)
    ctx.facts.append(f"Last request: {request_text}")

    decision = decide(ctx, research_result, validation_result)
    log_decision(
        outcome=decision.outcome,
        confidence=decision.confidence,
        escalation_reason=decision.escalation_reason,
    )

    write_scratchpad(
        session_id,
        f"research ok={research_result.ok} "
        f"valid={validation_result.valid if validation_result else 'skipped'} "
        f"outcome={decision.outcome} confidence={decision.confidence}",
    )
    save_session(ctx)

    return {
        "session_id": session_id,
        "research": research_result.model_dump(),
        "validation": validation_result.model_dump() if validation_result else None,
        "facts": ctx.facts,
        "decision": decision.model_dump(),
    }
