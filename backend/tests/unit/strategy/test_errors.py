import pytest

from crypto_lab.domain.strategy.errors import ErrorCategory, ErrorIssue, StrategyError


def test_error_is_categorized_structured_and_immutable() -> None:
    error = StrategyError(
        ErrorCategory.INVALID_CONTEXT,
        "context rejected",
        (ErrorIssue("candles", "UNSORTED", "must be ascending"),),
    )
    assert str(error) == "context rejected"
    assert error.category is ErrorCategory.INVALID_CONTEXT
    with pytest.raises(AttributeError):
        error.issues = ()  # type: ignore[misc]
