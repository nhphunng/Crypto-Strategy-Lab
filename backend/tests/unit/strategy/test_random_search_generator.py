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
