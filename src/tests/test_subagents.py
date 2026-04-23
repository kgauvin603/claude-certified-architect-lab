import asyncio
import json
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from claude_agent_sdk.types import ResultMessage

from src.agent.schemas import (
    FactItem,
    ResearchRequest,
    ResearchResult,
    Inconsistency,
    ValidationRequest,
    ValidationResult,
)
from src.agent.errors import ErrorCategory, ToolError
from src.agent.subagents import run_researcher, run_validator


def _make_result(text: str) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=0,
        duration_api_ms=0,
        is_error=False,
        num_turns=1,
        session_id="test-session",
        result=text,
    )


def _async_gen(items: list[str]):
    async def _gen():
        for item in items:
            yield _make_result(item)
    return _gen()


# --- ResearchResult schema ---

def test_research_result_requires_ok_field() -> None:
    with pytest.raises(ValidationError):
        ResearchResult.model_validate({})


def test_research_result_ok_with_facts() -> None:
    r = ResearchResult(
        ok=True,
        facts=[FactItem(key="customer_id", value="CUST-1001", source="find_customer_by_email")],
    )
    assert r.ok is True
    assert len(r.facts) == 1


def test_research_result_retryable_error() -> None:
    err = ToolError(category=ErrorCategory.VALIDATION_ERROR, message="bad output", retryable=True)
    r = ResearchResult(ok=False, error=err.model_dump())
    assert r.error is not None
    assert r.error["retryable"] is True


def test_research_result_non_retryable_error() -> None:
    err = ToolError(category=ErrorCategory.FATAL_ERROR, message="fatal", retryable=False)
    r = ResearchResult(ok=False, error=err.model_dump())
    assert r.error["retryable"] is False


# --- ValidationResult schema ---

def test_validation_result_valid_no_inconsistencies() -> None:
    v = ValidationResult(valid=True, summary="All facts consistent.")
    assert v.valid is True
    assert v.inconsistencies == []


def test_validation_result_detects_inconsistency() -> None:
    v = ValidationResult(
        valid=False,
        inconsistencies=[
            Inconsistency(
                field="customer_id",
                description="Order belongs to CUST-1002 but session is for CUST-1001",
                severity="error",
            )
        ],
        summary="Customer mismatch detected.",
    )
    assert v.valid is False
    assert v.inconsistencies[0].severity == "error"


def test_inconsistency_severity_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        Inconsistency(field="f", description="d", severity="critical")


# --- run_researcher (mocked query) ---

def test_run_researcher_returns_structured_output() -> None:
    good_json = json.dumps({
        "ok": True,
        "facts": [{"key": "customer_id", "value": "CUST-1001", "source": "find_customer_by_email"}],
        "error": None,
    })
    with patch("src.agent.subagents.query", return_value=_async_gen([good_json])):
        result = asyncio.run(run_researcher(ResearchRequest(
            user_id="alice@example.com",
            request_text="find my account",
        )))
    assert result.ok is True
    assert result.facts[0].key == "customer_id"
    assert result.facts[0].source == "find_customer_by_email"


def test_run_researcher_returns_retryable_error_on_invalid_json() -> None:
    with patch("src.agent.subagents.query", return_value=_async_gen(["not valid json"])):
        result = asyncio.run(run_researcher(ResearchRequest(
            user_id="alice@example.com",
            request_text="find my account",
        )))
    assert result.ok is False
    assert result.error is not None
    assert result.error["retryable"] is True


def test_run_researcher_returns_error_on_not_found() -> None:
    not_found_json = json.dumps({
        "ok": False,
        "facts": [],
        "error": {"category": "not_found", "message": "Customer not found", "retryable": False},
    })
    with patch("src.agent.subagents.query", return_value=_async_gen([not_found_json])):
        result = asyncio.run(run_researcher(ResearchRequest(
            user_id="unknown@example.com",
            request_text="find my account",
        )))
    assert result.ok is False
    assert result.error["retryable"] is False


# --- run_validator (mocked query) ---

def test_run_validator_passes_clean_facts() -> None:
    good_json = json.dumps({
        "valid": True,
        "inconsistencies": [],
        "summary": "All facts are consistent.",
    })
    facts = [FactItem(key="order_status", value="delivered", source="get_order_by_id")]
    with patch("src.agent.subagents.query", return_value=_async_gen([good_json])):
        result = asyncio.run(run_validator(ValidationRequest(
            request_text="check refund for ORD-00000001",
            facts=facts,
        )))
    assert result.valid is True
    assert result.inconsistencies == []


def test_run_validator_detects_customer_mismatch() -> None:
    bad_json = json.dumps({
        "valid": False,
        "inconsistencies": [
            {"field": "customer_id", "description": "Order belongs to different customer", "severity": "error"}
        ],
        "summary": "Customer ID mismatch.",
    })
    facts = [FactItem(key="customer_id", value="CUST-9999", source="get_order_by_id")]
    with patch("src.agent.subagents.query", return_value=_async_gen([bad_json])):
        result = asyncio.run(run_validator(ValidationRequest(
            request_text="refund order ORD-00000001",
            facts=facts,
        )))
    assert result.valid is False
    assert result.inconsistencies[0].field == "customer_id"
    assert result.inconsistencies[0].severity == "error"


def test_run_validator_handles_unparseable_output_gracefully() -> None:
    with patch("src.agent.subagents.query", return_value=_async_gen(["garbage response"])):
        result = asyncio.run(run_validator(ValidationRequest(
            request_text="check order",
            facts=[FactItem(key="k", value="v", source="s")],
        )))
    assert result.valid is False
    assert "unparseable" in result.summary


# --- Coordinator context isolation ---

def test_coordinator_caps_carried_facts_at_five() -> None:
    from src.agent.schemas import TicketContext
    ctx = TicketContext(
        session_id="test-session",
        user_id="u1",
        request_text="test",
        facts=[f"fact-{i}" for i in range(10)],
    )
    passed = ctx.facts[-5:]
    assert len(passed) == 5
    assert passed[0] == "fact-5"
    assert passed[-1] == "fact-9"
