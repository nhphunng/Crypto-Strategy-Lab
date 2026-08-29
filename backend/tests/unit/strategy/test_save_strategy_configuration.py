from __future__ import annotations

from datetime import UTC, datetime
from importlib import import_module
from uuid import UUID

from crypto_lab.bootstrap.strategies import build_strategy_registry


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 8, 28, 12, tzinfo=UTC)


class _Definitions:
    def __init__(self) -> None:
        self.values = []

    async def create_or_resolve(self, definition):
        self.values.append(definition)
        return definition


class _Configurations:
    def __init__(self) -> None:
        self.values = []

    async def save(self, configuration):
        self.values.append(configuration)
        return configuration


async def test_single_configuration_validates_and_persists_exact_parameters() -> None:
    module = import_module("crypto_lab.application.strategies.save_configuration")
    definitions = _Definitions()
    configurations = _Configurations()
    service = module.SaveStrategyConfiguration(
        build_strategy_registry(), definitions, configurations, _Clock()
    )

    saved = await service.execute(
        module.SaveStrategyConfigurationCommand(
            display_name="MA 34",
            provider="BINANCE",
            pair="SOLUSDT",
            timeframe="1h",
            members=(
                module.StrategyConfigurationMemberInput(
                    strategy_id="ma",
                    strategy_version="1.0.0",
                    parameters={"period": 34},
                    weight=None,
                ),
            ),
            combination=None,
        )
    )

    assert saved.kind.value == "SINGLE"
    assert saved.selection.pair == "SOLUSDT"
    assert saved.selection.timeframe.value == "1h"
    assert saved.members[0].parameters == {"period": 34}
    assert saved.root_definition_id == saved.members[0].definition_id
    assert definitions.values[0].parameters.values == {"period": 34}
    assert configurations.values == [saved]
    assert isinstance(saved.id, UUID)
    assert len(saved.content_fingerprint) == 64
