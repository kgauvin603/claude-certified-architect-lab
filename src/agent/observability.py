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


# --- Named event loggers ---

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
