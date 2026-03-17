from src.agent.errors import ErrorCategory, ToolError


def test_retryable_flag_for_transient_errors() -> None:
    err = ToolError(category=ErrorCategory.TRANSIENT_ERROR, message="timeout", retryable=True)
    assert err.retryable is True
