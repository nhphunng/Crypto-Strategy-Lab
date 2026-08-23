import pytest
from pydantic import ValidationError

from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError
from crypto_lab.infrastructure.llm.strategy_generation_adapter import _GenerationOutput


def test_malformed_provider_output_is_rejected_by_strict_schema() -> None:
    with pytest.raises(ValidationError):
        _GenerationOutput.model_validate({"candidates": [{"displayName": "Missing fields"}]})


def test_generation_failure_is_safe_and_categorized() -> None:
    error = StrategyError(ErrorCategory.GENERATION_FAILED, "provider failed")
    assert error.category is ErrorCategory.GENERATION_FAILED
    assert "secret" not in str(error)
