from crypto_lab.domain.strategy.protocol import Strategy


def downstream_identity(strategy: Strategy) -> tuple[str, str]:
    return strategy.metadata.strategy_id, str(strategy.metadata.strategy_version)


def test_downstream_contract_does_not_branch_on_generated_origin() -> None:
    names = downstream_identity.__code__.co_names
    assert "StrategyOrigin" not in names
    assert "LLM_GENERATED" not in names
