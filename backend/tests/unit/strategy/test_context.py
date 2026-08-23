from dataclasses import replace
from datetime import timedelta

import pytest
from tests.fixtures.strategy.factories import context

from crypto_lab.domain.strategy.context import ContextCompleteness, StrategyContext
from crypto_lab.domain.strategy.errors import ErrorCategory, StrategyError


def test_complete_empty_context_is_valid_and_deterministic() -> None:
    assert context([]).candles == ()
    assert context([]).context_fingerprint == context([]).context_fingerprint


@pytest.mark.parametrize("mode", ["unsorted", "duplicate", "gap", "open", "future", "selection"])
def test_invalid_context_is_rejected_all_or_nothing(mode: str) -> None:
    valid = context(["1", "2", "3"])
    values = list(valid.candles)
    if mode == "unsorted":
        values[0], values[1] = values[1], values[0]
    elif mode == "duplicate":
        values[1] = values[0]
    elif mode == "gap":
        values.pop(1)
    elif mode == "open":
        values[1] = replace(values[1], closed=False)
    elif mode == "future":
        pass
    else:
        values[1] = replace(values[1], pair="ETHUSDT")
    decision = valid.decision_timestamp
    if mode == "future":
        decision = values[-1].open_time - timedelta(hours=1)
    with pytest.raises(StrategyError) as caught:
        StrategyContext(
            valid.dataset_id,
            valid.dataset_version,
            valid.provider,
            valid.pair,
            valid.timeframe,
            valid.range_start,
            valid.range_end,
            decision,
            ContextCompleteness.COMPLETE,
            tuple(values),
        )
    assert caught.value.category is ErrorCategory.INVALID_CONTEXT


def test_incomplete_context_is_rejected() -> None:
    valid = context([])
    with pytest.raises(StrategyError):
        replace(valid, completeness=ContextCompleteness.INCOMPLETE)
