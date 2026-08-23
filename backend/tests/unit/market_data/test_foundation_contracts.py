from __future__ import annotations

import pytest

from crypto_lab.domain.market_data.timeframe import Timeframe


def test_selection_contract_coerces_accepted_wire_values() -> None:
    from crypto_lab.domain.market_data.selection import (
        ConnectionState,
        MarketSelection,
        Provider,
    )

    selection = MarketSelection("BINANCE", "BTCUSDT", "5m")

    assert selection.provider is Provider.BINANCE
    assert selection.timeframe is Timeframe.FIVE_MINUTES
    assert selection.key == (Provider.BINANCE, "BTCUSDT", Timeframe.FIVE_MINUTES)
    assert {state.value for state in ConnectionState} == {
        "LOADING",
        "LIVE",
        "STALE",
        "RECONNECTING",
        "ERROR",
    }


@pytest.mark.parametrize(
    ("provider", "pair", "timeframe"),
    [
        ("binance", "BTCUSDT", "5m"),
        ("BINANCE", "btcusdt", "5m"),
        ("BINANCE", "BTC/USDT", "5m"),
        ("BINANCE", "BTCUSDT", "3m"),
    ],
)
def test_selection_contract_rejects_noncanonical_values(
    provider: str, pair: str, timeframe: str
) -> None:
    from crypto_lab.domain.market_data.selection import MarketSelection

    with pytest.raises(ValueError):
        MarketSelection(provider, pair, timeframe)


def test_candle_module_keeps_the_accepted_market_selection_import() -> None:
    from crypto_lab.domain.market_data.candle import MarketSelection as LegacyImport
    from crypto_lab.domain.market_data.selection import MarketSelection

    assert LegacyImport is MarketSelection


def test_registry_reference_counts_equal_selections_and_is_idempotent() -> None:
    from crypto_lab.application.chart_delivery.subscription_registry import (
        SubscriptionRegistry,
    )
    from crypto_lab.domain.market_data.selection import MarketSelection

    registry = SubscriptionRegistry(max_slots=4)
    selection = MarketSelection("BINANCE", "BTCUSDT", "5m")

    first = registry.bind("slot-1", selection)
    second = registry.bind("slot-2", selection)
    duplicate = registry.bind("slot-2", selection)

    assert first.acquired_selection == selection
    assert second.acquired_selection is None
    assert duplicate.changed is False
    assert registry.reference_count(selection) == 2
    assert registry.slots_for(selection) == ("slot-1", "slot-2")


def test_registry_replacement_releases_only_the_zero_reference_selection() -> None:
    from crypto_lab.application.chart_delivery.subscription_registry import (
        SubscriptionRegistry,
    )
    from crypto_lab.domain.market_data.selection import MarketSelection

    registry = SubscriptionRegistry(max_slots=4)
    shared = MarketSelection("BINANCE", "BTCUSDT", "5m")
    replacement = MarketSelection("BINANCE", "BTCUSDT", "1h")
    registry.bind("slot-1", shared)
    registry.bind("slot-2", shared)

    first_replace = registry.bind("slot-1", replacement)
    final_release = registry.unbind("slot-2")

    assert first_replace.released_selection is None
    assert first_replace.acquired_selection == replacement
    assert final_release.released_selection == shared
    assert registry.reference_count(shared) == 0
    assert registry.reference_count(replacement) == 1


def test_registry_enforces_four_slot_cap_without_mutation() -> None:
    from crypto_lab.application.chart_delivery.subscription_registry import (
        SubscriptionLimitExceeded,
        SubscriptionRegistry,
    )
    from crypto_lab.domain.market_data.selection import MarketSelection

    registry = SubscriptionRegistry(max_slots=4)
    timeframes = ("1m", "5m", "15m", "1h")
    for index, timeframe in enumerate(timeframes, start=1):
        registry.bind(
            f"slot-{index}",
            MarketSelection("BINANCE", "BTCUSDT", timeframe),
        )

    with pytest.raises(SubscriptionLimitExceeded):
        registry.bind("slot-5", MarketSelection("BINANCE", "BTCUSDT", "4h"))

    assert registry.slot_count == 4
    assert registry.binding_for("slot-5") is None
