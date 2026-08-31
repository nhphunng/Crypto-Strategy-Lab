from crypto_lab.bootstrap.strategies import build_strategy_registry
from crypto_lab.domain.search import RandomSearchGenerator


def test_random_search_is_seeded_unique_and_registry_driven() -> None:
    generator = RandomSearchGenerator(build_strategy_registry())
    strategy_ids = ("ma", "rsi", "bollinger", "support_resistance")

    first = tuple(generator.generate(strategy_ids, 2, 4, 20, 424242))
    repeated = tuple(generator.generate(strategy_ids, 2, 4, 20, 424242))

    assert first == repeated
    assert len(first) == 20
    assert len({candidate.fingerprint for candidate in first}) == len(first)
    assert all(2 <= len(candidate.members) <= 4 for candidate in first)
    assert all(
        member.strategy_id in strategy_ids for candidate in first for member in candidate.members
    )


def test_random_search_respects_relationships_exclusive_bounds_and_dataset_size() -> None:
    generator = RandomSearchGenerator(build_strategy_registry())
    candidates = tuple(
        generator.generate(
            ("ma", "rsi", "bollinger", "support_resistance"),
            2,
            4,
            100,
            424242,
            candle_count=96,
        )
    )

    assert len(candidates) == 100
    for member in (member for candidate in candidates for member in candidate.members):
        if "period" in member.parameters:
            assert int(member.parameters["period"]) <= 48
        if "lookback" in member.parameters:
            assert int(member.parameters["lookback"]) <= 48
        if member.strategy_id == "rsi":
            assert float(member.parameters["lowerThreshold"]) < float(
                member.parameters["upperThreshold"]
            )
        if member.strategy_id == "bollinger":
            assert float(member.parameters["standardDeviations"]) > 0
