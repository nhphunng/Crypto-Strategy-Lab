from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime
from decimal import DecimalException
from typing import Protocol, cast
from urllib.parse import urlparse

from websockets.asyncio.client import connect

from crypto_lab.application.market_data.ports import (
    Clock,
    RealtimeProviderEvent,
    RealtimeProviderEventType,
)
from crypto_lab.domain.market_data.candle import Candle, exact_decimal
from crypto_lab.domain.market_data.selection import MarketSelection, Provider


class BinanceRealtimePayloadError(ValueError):
    """Raised when an upstream message cannot satisfy the public Candle contract."""


class RealtimeSocket(Protocol):
    async def recv(self) -> str | bytes: ...

    async def close(self, code: int = 1000, reason: str = "") -> None: ...


type ConnectionFactory = Callable[[str, float, float], AbstractAsyncContextManager[RealtimeSocket]]


@asynccontextmanager
async def _websocket_connection(
    url: str,
    heartbeat_interval_seconds: float,
    stale_after_seconds: float,
) -> AsyncIterator[RealtimeSocket]:
    async with connect(
        url,
        ping_interval=heartbeat_interval_seconds,
        ping_timeout=stale_after_seconds,
        close_timeout=5,
        max_queue=32,
    ) as websocket:
        yield cast(RealtimeSocket, websocket)


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BinanceRealtimePayloadError(f"{field} must be an integer")
    return value


def _string(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise BinanceRealtimePayloadError(f"{field} must be a non-empty string")
    return value


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise BinanceRealtimePayloadError(f"{field} must be a boolean")
    return value


def map_binance_kline(
    payload: object,
    selection: MarketSelection,
    *,
    received_at: datetime,
) -> Candle:
    """Validate and map one Binance kline without exposing provider fields upstream."""

    try:
        if not isinstance(payload, dict):
            raise BinanceRealtimePayloadError("payload must be an object")
        if "data" in payload:
            payload = payload["data"]
            if not isinstance(payload, dict):
                raise BinanceRealtimePayloadError("combined stream data must be an object")
        if payload.get("e") != "kline":
            raise BinanceRealtimePayloadError("payload is not a kline event")
        raw_kline = payload.get("k")
        if not isinstance(raw_kline, dict):
            raise BinanceRealtimePayloadError("kline must be an object")

        symbol = _string(raw_kline.get("s"), field="k.s")
        timeframe = _string(raw_kline.get("i"), field="k.i")
        if symbol != selection.pair or timeframe != selection.timeframe.value:
            raise BinanceRealtimePayloadError("kline selection does not match subscription")

        open_time_ms = _integer(raw_kline.get("t"), field="k.t")
        close_time_ms = _integer(raw_kline.get("T"), field="k.T")
        open_time = datetime.fromtimestamp(open_time_ms / 1000, tz=UTC)
        close_time = datetime.fromtimestamp(close_time_ms / 1000, tz=UTC)
        expected_close = selection.timeframe.close_time(open_time)
        if close_time != expected_close:
            raise BinanceRealtimePayloadError("kline close time does not match interval")

        return Candle(
            provider=selection.provider.value,
            pair=symbol,
            timeframe=selection.timeframe,
            open_time=open_time,
            close_time=close_time,
            open=exact_decimal(_string(raw_kline.get("o"), field="k.o"), field="open"),
            high=exact_decimal(_string(raw_kline.get("h"), field="k.h"), field="high"),
            low=exact_decimal(_string(raw_kline.get("l"), field="k.l"), field="low"),
            close=exact_decimal(_string(raw_kline.get("c"), field="k.c"), field="close"),
            volume=exact_decimal(_string(raw_kline.get("v"), field="k.v"), field="volume"),
            closed=_boolean(raw_kline.get("x"), field="k.x"),
            received_at=received_at,
        )
    except BinanceRealtimePayloadError:
        raise
    except (KeyError, TypeError, ValueError, OverflowError, DecimalException) as error:
        raise BinanceRealtimePayloadError("invalid Binance kline payload") from error


class BinanceRealtimeMarketProvider:
    provider = Provider.BINANCE.value

    def __init__(
        self,
        clock: Clock,
        *,
        websocket_url: str = "wss://stream.binance.com:9443/ws",
        heartbeat_interval_seconds: float = 15,
        stale_after_seconds: float = 30,
        connection_factory: ConnectionFactory = _websocket_connection,
    ) -> None:
        parsed = urlparse(websocket_url)
        if parsed.scheme != "wss" or not parsed.hostname:
            raise ValueError("Binance WebSocket URL must be a server-controlled WSS URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError(
                "Binance WebSocket URL must not contain credentials, query, or fragment"
            )
        if heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat interval must be positive")
        if stale_after_seconds <= heartbeat_interval_seconds:
            raise ValueError("stale timeout must exceed heartbeat interval")
        self._clock = clock
        self._websocket_url = websocket_url.rstrip("/")
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._stale_after_seconds = stale_after_seconds
        self._connection_factory = connection_factory
        self._active: dict[MarketSelection, RealtimeSocket] = {}
        self._last_closed: dict[MarketSelection, datetime] = {}

    def last_closed_checkpoint(self, selection: MarketSelection) -> datetime | None:
        return self._last_closed.get(selection)

    def stream(
        self,
        selection: MarketSelection,
    ) -> AsyncGenerator[RealtimeProviderEvent, None]:
        return self._stream(selection)

    async def _stream(
        self,
        selection: MarketSelection,
    ) -> AsyncGenerator[RealtimeProviderEvent, None]:
        if selection.provider is not Provider.BINANCE:
            raise ValueError("selection provider does not match Binance")
        if selection in self._active:
            raise RuntimeError("selection already has an active provider stream")

        url = f"{self._websocket_url}/{selection.pair.lower()}@kline_{selection.timeframe.value}"
        socket: RealtimeSocket | None = None
        try:
            async with self._connection_factory(
                url,
                self._heartbeat_interval_seconds,
                self._stale_after_seconds,
            ) as connected:
                socket = connected
                self._active[selection] = connected
                while True:
                    try:
                        async with asyncio.timeout(self._stale_after_seconds):
                            message = await connected.recv()
                    except TimeoutError:
                        yield RealtimeProviderEvent(
                            RealtimeProviderEventType.DISCONNECTED,
                            selection,
                            self._clock.now(),
                            reason_code="PROVIDER_HEARTBEAT_TIMEOUT",
                        )
                        return

                    occurred_at = self._clock.now()
                    try:
                        decoded = json.loads(message)
                        candle = map_binance_kline(
                            decoded,
                            selection,
                            received_at=occurred_at,
                        )
                    except (json.JSONDecodeError, UnicodeDecodeError, BinanceRealtimePayloadError):
                        yield RealtimeProviderEvent(
                            RealtimeProviderEventType.DISCONNECTED,
                            selection,
                            occurred_at,
                            reason_code="MARKET_PROVIDER_PAYLOAD_INVALID",
                        )
                        return
                    if candle.closed:
                        self._last_closed[selection] = candle.open_time
                    yield RealtimeProviderEvent(
                        RealtimeProviderEventType.CANDLE,
                        selection,
                        occurred_at,
                        candle=candle,
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            yield RealtimeProviderEvent(
                RealtimeProviderEventType.DISCONNECTED,
                selection,
                self._clock.now(),
                reason_code="PROVIDER_DISCONNECTED",
            )
        finally:
            if self._active.get(selection) is socket:
                self._active.pop(selection, None)

    async def release(self, selection: MarketSelection) -> None:
        socket = self._active.pop(selection, None)
        if socket is not None:
            await socket.close(code=1000, reason="selection released")
        self._last_closed.pop(selection, None)
