from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from math import ceil
from typing import Any

import httpx

from crypto_lab.application.market_data.errors import (
    ProviderPayloadInvalid,
    ProviderRateLimited,
    ProviderUnavailable,
)
from crypto_lab.application.market_data.ports import Clock
from crypto_lab.domain.market_data.candle import Candle, MarketSelection
from crypto_lab.domain.market_data.ranges import TimeRange

_DECIMAL_PATTERN = re.compile(r"^(0|[1-9][0-9]*)(\.[0-9]+)?$")
Sleep = Callable[[float], Awaitable[None]]
Jitter = Callable[[], float]


class BinanceMarketDataProvider:
    provider = "BINANCE"

    def __init__(
        self,
        client: httpx.AsyncClient,
        clock: Clock,
        *,
        base_url: str = "https://api.binance.com",
        max_attempts: int = 3,
        max_retry_delay_seconds: int = 30,
        sleep: Sleep = asyncio.sleep,
        jitter: Jitter = lambda: 0.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self._client = client
        self._clock = clock
        self._base_url = base_url.rstrip("/")
        self._max_attempts = max_attempts
        self._max_retry_delay = max_retry_delay_seconds
        self._sleep = sleep
        self._jitter = jitter

    async def iter_historical(
        self,
        selection: MarketSelection,
        time_range: TimeRange,
    ) -> AsyncIterator[tuple[Candle, ...]]:
        if selection.provider != self.provider:
            raise ProviderPayloadInvalid
        time_range.validate_alignment(selection.timeframe)
        cursor = time_range.start_time
        seen: dict[datetime, str] = {}
        while cursor < time_range.end_time:
            remaining = ceil(
                (time_range.end_time - cursor).total_seconds() / selection.timeframe.seconds
            )
            payload = await self._request_page(
                {
                    "symbol": selection.pair,
                    "interval": selection.timeframe.value,
                    "startTime": _to_epoch_ms(cursor),
                    "endTime": _to_epoch_ms(time_range.end_time) - 1,
                    "limit": min(1000, remaining),
                }
            )
            if not payload:
                break
            page_by_open: dict[datetime, Candle] = {}
            for raw in payload:
                candle = self._map_row(raw, selection)
                if not time_range.contains_open(candle.open_time):
                    continue
                existing_hash = seen.get(candle.open_time)
                if existing_hash is not None and existing_hash != candle.content_hash:
                    raise ProviderPayloadInvalid
                page_existing = page_by_open.get(candle.open_time)
                if page_existing is not None and page_existing.content_hash != candle.content_hash:
                    raise ProviderPayloadInvalid
                if existing_hash is None:
                    page_by_open[candle.open_time] = candle
            ordered = tuple(page_by_open[key] for key in sorted(page_by_open))
            if not ordered:
                break
            for candle in ordered:
                seen[candle.open_time] = candle.content_hash
            yield ordered
            next_cursor = ordered[-1].open_time + selection.timeframe.duration
            if next_cursor <= cursor:
                break
            cursor = next_cursor

    async def _request_page(self, params: dict[str, str | int]) -> list[Any]:
        last_retry_after: int | None = None
        for attempt in range(self._max_attempts):
            try:
                response = await self._client.get(
                    f"{self._base_url}/api/v3/klines",
                    params=params,
                )
            except httpx.RequestError as error:
                if attempt + 1 >= self._max_attempts:
                    raise ProviderUnavailable from error
                await self._sleep(self._backoff(attempt))
                continue
            if response.status_code in (418, 429):
                last_retry_after = self._retry_after(response)
                if attempt + 1 >= self._max_attempts:
                    raise ProviderRateLimited(last_retry_after)
                await self._sleep(float(last_retry_after or self._backoff(attempt)))
                continue
            if response.status_code >= 500:
                if attempt + 1 >= self._max_attempts:
                    raise ProviderUnavailable
                await self._sleep(self._backoff(attempt))
                continue
            if response.status_code >= 400:
                raise ProviderUnavailable
            try:
                payload = response.json()
            except ValueError as error:
                raise ProviderPayloadInvalid from error
            if not isinstance(payload, list):
                raise ProviderPayloadInvalid
            return payload
        raise ProviderRateLimited(last_retry_after)

    def _map_row(self, raw: object, selection: MarketSelection) -> Candle:
        if not isinstance(raw, list) or len(raw) < 7:
            raise ProviderPayloadInvalid
        try:
            open_time = _from_epoch_ms(_exact_int(raw[0]))
            close_time = _from_epoch_ms(_exact_int(raw[6]))
            candle = Candle(
                provider=selection.provider,
                pair=selection.pair,
                timeframe=selection.timeframe,
                open_time=open_time,
                close_time=close_time,
                open=_decimal_string(raw[1]),
                high=_decimal_string(raw[2]),
                low=_decimal_string(raw[3]),
                close=_decimal_string(raw[4]),
                volume=_decimal_string(raw[5]),
                closed=True,
                received_at=self._clock.now(),
            )
        except (TypeError, ValueError, InvalidOperation) as error:
            raise ProviderPayloadInvalid from error
        return candle

    def _backoff(self, attempt: int) -> float:
        return min(float(self._max_retry_delay), (2**attempt) + max(0.0, self._jitter()))

    def _retry_after(self, response: httpx.Response) -> int | None:
        raw = response.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            seconds = int(raw)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(raw).astimezone(UTC)
            except (TypeError, ValueError, OverflowError):
                return None
            seconds = max(1, ceil((retry_at - self._clock.now()).total_seconds()))
        return max(1, min(seconds, self._max_retry_delay))


def _exact_int(value: object) -> int:
    if type(value) is not int:
        raise TypeError("epoch milliseconds must be exact integers")
    return value


def _decimal_string(value: object) -> Decimal:
    if not isinstance(value, str) or _DECIMAL_PATTERN.fullmatch(value) is None:
        raise TypeError("provider numeric value must be a fixed-point decimal string")
    return Decimal(value)


def _to_epoch_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _from_epoch_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)
