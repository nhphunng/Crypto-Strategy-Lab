from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

_DEFAULT_ALIASES: dict[str, tuple[str, ...]] = {
    "BTC": ("bitcoin", "btc"),
    "ETH": ("ethereum", "ether", "eth"),
    "SOL": ("solana", "sol"),
}


class CoinResolver:
    """Map free-text coin keywords to canonical codes using word boundaries.

    Matching is case-insensitive and never matches a substring inside another
    word (``BTC`` does not match ``BTCUSDT``, ``SOL`` does not match ``solar``).
    """

    def __init__(
        self,
        aliases: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        source = aliases if aliases is not None else _DEFAULT_ALIASES
        self._patterns: dict[str, list[re.Pattern[str]]] = {}
        for coin, words in source.items():
            self._patterns[coin] = [
                re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) for word in words
            ]

    def resolve(self, text: str) -> tuple[str, ...]:
        """Return the sorted canonical coin codes mentioned in ``text``."""
        found: set[str] = set()
        for coin, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.search(text) is not None:
                    found.add(coin)
                    break
        return tuple(sorted(found))
