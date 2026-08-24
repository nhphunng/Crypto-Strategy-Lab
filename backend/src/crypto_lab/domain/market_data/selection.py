from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from crypto_lab.domain.market_data.timeframe import Timeframe

PAIR_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")


class Provider(StrEnum):
    BINANCE = "BINANCE"


class ConnectionState(StrEnum):
    LOADING = "LOADING"
    LIVE = "LIVE"
    STALE = "STALE"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


type SelectionKey = tuple[Provider, str, Timeframe]


@dataclass(frozen=True, slots=True, init=False)
class MarketSelection:
    provider: Provider
    pair: str
    timeframe: Timeframe

    def __init__(
        self,
        provider: Provider | str,
        pair: str,
        timeframe: Timeframe | str,
    ) -> None:
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "pair", pair)
        object.__setattr__(self, "timeframe", timeframe)
        self.__post_init__()

    def __post_init__(self) -> None:
        provider_value = self.provider
        if not isinstance(provider_value, str) or provider_value != provider_value.upper():
            raise ValueError("provider must be a canonical uppercase value")
        try:
            provider = Provider(provider_value)
        except ValueError as error:
            raise ValueError("provider is not supported") from error

        if not isinstance(self.pair, str) or PAIR_PATTERN.fullmatch(self.pair) is None:
            raise ValueError("pair must be a canonical uppercase market pair")

        try:
            timeframe = (
                self.timeframe
                if isinstance(self.timeframe, Timeframe)
                else Timeframe(self.timeframe)
            )
        except (TypeError, ValueError) as error:
            raise ValueError("timeframe is not supported") from error

        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "timeframe", timeframe)

    @property
    def key(self) -> SelectionKey:
        return self.provider, self.pair, self.timeframe
