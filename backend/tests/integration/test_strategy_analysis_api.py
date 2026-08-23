from crypto_lab.application.strategies.analyze_strategy import (
    AnalyzeStrategy,
    AnalyzeStrategyCommand,
)
from crypto_lab.bootstrap.strategies import build_strategy_registry
from crypto_lab.domain.strategy.version import ContractVersionRange
from tests.fixtures.strategy.factories import context, definition


class Definitions:
    def __init__(self, value):
        self.value = value

    async def get(self, _identity):
        return self.value


class Datasets:
    async def get_strategy_context(self, _identity):
        return context(["1", "2", "1", "3"])


async def test_bounded_analysis_uses_exact_definition_and_dataset() -> None:
    registry = build_strategy_registry()
    strategy = registry.resolve("ma", registry.discover()[0].strategy_version)
    selected = definition(strategy, {"period": 2})
    use_case = AnalyzeStrategy(Definitions(selected), Datasets(), registry)  # type: ignore[arg-type]
    result = await use_case.execute(
        AnalyzeStrategyCommand("request", selected.id, "dataset", ContractVersionRange(1, 0, 0))
    )
    assert result.strategy_definition.id == selected.id
