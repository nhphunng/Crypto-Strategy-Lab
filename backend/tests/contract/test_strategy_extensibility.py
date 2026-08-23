from crypto_lab.domain.strategy.protocol import Strategy


def consume_strategy(strategy: Strategy) -> tuple[str, str]:
    return strategy.metadata.strategy_id, str(strategy.metadata.strategy_version)


def test_downstream_contract_has_no_concrete_strategy_branch() -> None:
    assert "MovingAverage" not in consume_strategy.__code__.co_names
    assert "Rsi" not in consume_strategy.__code__.co_names
