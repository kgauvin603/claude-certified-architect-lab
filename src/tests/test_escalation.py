import pytest
from src.agent.schemas import (
    TicketContext,
    ConfidenceLevel,
    EscalationReason,
    ResearchResult,
    ValidationResult,
    FactItem,
    Inconsistency,
)
from src.agent.coordinator import score_confidence, decide


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(**kwargs) -> TicketContext:
    return TicketContext(
        session_id="s1",
        user_id="u1",
        request_text="test",
        **kwargs,
    )


def _ok_research(*facts: tuple[str, str]) -> ResearchResult:
    return ResearchResult(
        ok=True,
        facts=[FactItem(key=k, value=v, source="tool") for k, v in facts],
    )


def _failed_research(retryable: bool = True) -> ResearchResult:
    return ResearchResult(
        ok=False,
        error={"category": "transient_error", "message": "lookup failed", "retryable": retryable},
    )


def _clean_validation() -> ValidationResult:
    return ValidationResult(valid=True, inconsistencies=[], summary="all good")


def _warning_validation() -> ValidationResult:
    return ValidationResult(
        valid=False,
        inconsistencies=[
            Inconsistency(field="delivery_date", description="date slightly off", severity="warning")
        ],
        summary="minor warning",
    )


def _error_validation() -> ValidationResult:
    return ValidationResult(
        valid=False,
        inconsistencies=[
            Inconsistency(field="customer_id", description="order belongs to different customer", severity="error")
        ],
        summary="critical mismatch",
    )


# ---------------------------------------------------------------------------
# score_confidence
# ---------------------------------------------------------------------------

def test_score_high_when_research_ok_and_validation_passes() -> None:
    assert score_confidence(_ok_research(), _clean_validation()) == ConfidenceLevel.HIGH


def test_score_medium_when_research_ok_no_validation() -> None:
    assert score_confidence(_ok_research(), None) == ConfidenceLevel.MEDIUM


def test_score_medium_when_validation_has_warnings_only() -> None:
    assert score_confidence(_ok_research(), _warning_validation()) == ConfidenceLevel.MEDIUM


def test_score_low_when_research_fails() -> None:
    assert score_confidence(_failed_research(), None) == ConfidenceLevel.LOW


def test_score_low_when_validation_has_errors() -> None:
    assert score_confidence(_ok_research(), _error_validation()) == ConfidenceLevel.LOW


# ---------------------------------------------------------------------------
# decide — high confidence → complete
# ---------------------------------------------------------------------------

def test_decide_complete_on_high_confidence() -> None:
    ctx = _ctx()
    decision = decide(ctx, _ok_research(("order_id", "ORD-00000001")), _clean_validation())
    assert decision.outcome == "complete"
    assert decision.confidence == ConfidenceLevel.HIGH
    assert decision.escalation_reason is None
    assert decision.clarifying_question is None


# ---------------------------------------------------------------------------
# decide — medium confidence → clarify
# ---------------------------------------------------------------------------

def test_decide_clarify_on_medium_confidence_no_validation() -> None:
    ctx = _ctx()
    decision = decide(ctx, _ok_research(("name", "Alice")), None)
    assert decision.outcome == "clarify"
    assert decision.confidence == ConfidenceLevel.MEDIUM
    assert decision.clarifying_question is not None
    assert len(decision.clarifying_question) > 0


def test_decide_clarify_includes_warning_field() -> None:
    ctx = _ctx()
    decision = decide(ctx, _ok_research(), _warning_validation())
    assert decision.outcome == "clarify"
    assert "delivery_date" in (decision.clarifying_question or "")


# ---------------------------------------------------------------------------
# decide — low confidence → escalate
# ---------------------------------------------------------------------------

def test_decide_escalate_on_low_confidence_research_failure() -> None:
    ctx = _ctx()
    decision = decide(ctx, _failed_research(retryable=False), None)
    assert decision.outcome == "escalate"
    assert decision.confidence == ConfidenceLevel.LOW
    assert decision.escalation_reason == EscalationReason.LOW_CONFIDENCE
    assert decision.escalation_detail is not None


def test_decide_escalate_on_validation_error() -> None:
    ctx = _ctx()
    decision = decide(ctx, _ok_research(), _error_validation())
    assert decision.outcome == "escalate"
    assert decision.escalation_reason == EscalationReason.LOW_CONFIDENCE
    assert "customer_id" in (decision.escalation_detail or "")


# ---------------------------------------------------------------------------
# decide — repeated failure → escalate
# ---------------------------------------------------------------------------

def test_decide_escalate_on_repeated_failure() -> None:
    ctx = _ctx(tool_failure_counts={"transient_error": 2})
    decision = decide(ctx, _ok_research(), _clean_validation())
    assert decision.outcome == "escalate"
    assert decision.escalation_reason == EscalationReason.REPEATED_FAILURE
    assert "transient_error" in (decision.escalation_detail or "")


def test_decide_repeated_failure_overrides_high_confidence() -> None:
    # Even with good research + validation, repeated failure must escalate
    ctx = _ctx(tool_failure_counts={"validation_error": 2})
    decision = decide(ctx, _ok_research(), _clean_validation())
    assert decision.outcome == "escalate"
    assert decision.escalation_reason == EscalationReason.REPEATED_FAILURE


def test_decide_one_failure_does_not_escalate() -> None:
    # Exactly 1 failure is below the threshold; should still reach normal path
    ctx = _ctx(tool_failure_counts={"transient_error": 1})
    decision = decide(ctx, _ok_research(), _clean_validation())
    assert decision.outcome == "complete"


# ---------------------------------------------------------------------------
# Retryable vs non-retryable error distinction
# ---------------------------------------------------------------------------

def test_retryable_error_still_scores_low() -> None:
    result = score_confidence(_failed_research(retryable=True), None)
    assert result == ConfidenceLevel.LOW


def test_non_retryable_error_scores_low() -> None:
    result = score_confidence(_failed_research(retryable=False), None)
    assert result == ConfidenceLevel.LOW
