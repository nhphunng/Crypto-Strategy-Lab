from __future__ import annotations

from crypto_lab.domain.news.coin_resolution import CoinResolver

RESOLVER = CoinResolver()


def test_resolves_canonical_symbols() -> None:
    assert RESOLVER.resolve("BTC breaks out") == ("BTC",)
    assert RESOLVER.resolve("ETH rallies") == ("ETH",)
    assert RESOLVER.resolve("SOL pumps") == ("SOL",)


def test_resolves_alias_names_case_insensitively() -> None:
    assert RESOLVER.resolve("bitcoin") == ("BTC",)
    assert RESOLVER.resolve("BITCOIN") == ("BTC",)
    assert RESOLVER.resolve("Ethereum") == ("ETH",)
    assert RESOLVER.resolve("ether") == ("ETH",)
    assert RESOLVER.resolve("Solana") == ("SOL",)
    assert RESOLVER.resolve("sol") == ("SOL",)


def test_detects_multiple_coins_sorted_and_deduplicated() -> None:
    assert RESOLVER.resolve("Bitcoin, Ethereum and Solana all rally") == (
        "BTC",
        "ETH",
        "SOL",
    )
    assert RESOLVER.resolve("BTC and bitcoin both surge") == ("BTC",)


def test_word_boundaries_never_match_containing_words() -> None:
    assert RESOLVER.resolve("Bitcoiners discuss") == ()
    assert RESOLVER.resolve("solar energy and solutions") == ()
    assert RESOLVER.resolve("the ethanol market") == ()
    assert RESOLVER.resolve("BTCUSDT") == ()


def test_no_match_returns_empty_tuple() -> None:
    assert RESOLVER.resolve("Federal Reserve policy") == ()
