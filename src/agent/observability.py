import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Optional

_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_trace_var: ContextVar[Optional[list]] = ContextVar("trace", default=None)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_var.get() or "--------"  # type: ignore[attr-defined]
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(request_id)s] %(levelname)-5s  %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.INFO)
        root.addHandler(handler)


logger = logging.getLogger("agent")


def new_request_id() -> str:
    return uuid.uuid4().hex[:8].upper()


def get_request_id() -> str:
    return _request_id_var.get() or ""


def set_request_context(request_id: str) -> tuple:
    trace: list[str] = []
    t1 = _request_id_var.set(request_id)
    t2 = _trace_var.set(trace)
    return t1, t2


def reset_request_context(t1: object, t2: object) -> None:
    _request_id_var.reset(t1)  # type: ignore[arg-type]
    _trace_var.reset(t2)  # type: ignore[arg-type]


def get_trace() -> list[str]:
    t = _trace_var.get()
    return list(t) if t is not None else []


def _record(event: str) -> None:
    t = _trace_var.get()
    if t is not None:
        t.append(event)
    rid = _request_id_var.get()
    if rid:
        try:
            from .trace_store import add_event
            add_event(rid, event)
        except Exception:
            pass


# --- Named event loggers ---

def log_orchestrator_start(user_id: str, session_id: str) -> None:
    logger.info("ORCHESTRATOR_START user=%s session=%s", user_id, session_id)
    _record(f"Orchestrator: started (user={user_id}, session={session_id})")


def log_orchestrator_plan(plan: str) -> None:
    logger.info("ORCHESTRATOR_PLAN %s", plan)
    _record(f"Orchestrator: plan → {plan}")


def log_request_received(user_id: str, session_id: str, request_text: str) -> None:
    logger.info('REQUEST_RECEIVED user=%s session=%s input="%s"', user_id, session_id, request_text)
    _record(f'Input: "{request_text}"')


def log_researcher_start() -> None:
    logger.info("RESEARCHER_START")
    _record("Researcher: started")


def log_researcher_result(ok: bool, fact_count: int = 0, error_msg: str = "") -> None:
    if ok:
        logger.info("RESEARCHER_RESULT ok=True facts=%d", fact_count)
        _record(f"Researcher: ok ({fact_count} facts)")
    else:
        logger.info("RESEARCHER_RESULT ok=False error=%r", error_msg)
        _record(f"Researcher: failed ({error_msg})")


def log_tool_call(tool_name: str, args_summary: str, result_summary: str) -> None:
    logger.info("TOOL_CALL %s(%s) → %s", tool_name, args_summary, result_summary)
    _record(f"Tool: {tool_name} → {result_summary}")


def log_validator_start(fact_count: int) -> None:
    logger.info("VALIDATOR_START facts=%d", fact_count)
    _record("Validator: started")


def log_validator_result(valid: bool, inconsistency_count: int = 0) -> None:
    if valid:
        logger.info("VALIDATOR_RESULT valid=True")
        _record("Validator: valid")
    else:
        logger.info("VALIDATOR_RESULT valid=False inconsistencies=%d", inconsistency_count)
        _record(f"Validator: invalid ({inconsistency_count} inconsistencies)")


def log_decision(outcome: str, confidence: str, escalation_reason: Optional[str] = None) -> None:
    if escalation_reason:
        logger.info(
            "DECISION outcome=%s confidence=%s escalation=%s",
            outcome, confidence, escalation_reason,
        )
    else:
        logger.info("DECISION outcome=%s confidence=%s", outcome, confidence)
    _record(f"Decision: {outcome} (confidence={confidence})")


def log_response_sent(session_id: str) -> None:
    logger.info("RESPONSE_SENT session=%s", session_id)
    _record("Response sent")


def log_session_loaded(session_id: str, existing_fact_count: int) -> None:
    logger.info("SESSION_LOADED session=%s existing_facts=%d", session_id, existing_fact_count)
    _record(f"Session: loaded (session={session_id}, existing_facts={existing_fact_count})")


def log_session_facts_summary(carried_facts: list[str]) -> None:
    summary = "; ".join(f[:50] for f in carried_facts)
    logger.info("SESSION_FACTS_SUMMARY %s", summary)
    _record(f"Session: carried facts → {summary}")


def log_current_request_failures(failures: dict) -> None:
    logger.info("CURRENT_REQUEST_FAILURES %s", failures)
    _record(f"Failures this request: {failures or 'none'}")


def log_decision_reason(
    outcome: str,
    confidence: str,
    reason: Optional[str],
    failures: dict,
) -> None:
    detail = f"failures={failures}" if failures else "no failures this request"
    logger.info("DECISION_REASON outcome=%s confidence=%s reason=%s %s", outcome, confidence, reason, detail)
    _record(f"Decision reason: {outcome} (confidence={confidence}, {detail})")
