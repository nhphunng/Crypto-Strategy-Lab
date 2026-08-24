from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from crypto_lab.domain.market_data.selection import MarketSelection
from crypto_lab.infrastructure.market_data.realtime_selection_hub import (
    RealtimeSelectionHub,
)
from tests.integration.fakes.fake_realtime_market_provider import (
    FakeRealtimeMarketProvider,
)


@pytest.mark.asyncio
async def test_equal_selection_fans_out_across_clients_until_last_release() -> None:
    selection = MarketSelection("BINANCE", "BTCUSDT", "5m")
    upstream = FakeRealtimeMarketProvider()
    hub = RealtimeSelectionHub(upstream)
    first = hub.client()
    second = hub.client()
    first_stream = first.stream(selection)
    second_stream = second.stream(selection)

    first_event = asyncio.create_task(anext(first_stream))
    await upstream.wait_until_streaming(selection)
    second_event = asyncio.create_task(anext(second_stream))
    await asyncio.sleep(0)

    heartbeat_at = datetime(2026, 8, 20, 8, 30, tzinfo=UTC)
    heartbeat = upstream.heartbeat(selection, occurred_at=heartbeat_at)
    assert await first_event == heartbeat
    assert await second_event == heartbeat
    assert upstream.stream_calls == [selection]

    await first.release(selection)
    assert upstream.release_calls == []

    next_second = asyncio.create_task(anext(second_stream))
    next_heartbeat = upstream.heartbeat(
        selection,
        occurred_at=datetime(2026, 8, 20, 8, 31, tzinfo=UTC),
    )
    assert await next_second == next_heartbeat

    await second.release(selection)
    assert upstream.release_calls == [selection]
    await first_stream.aclose()
    await second_stream.aclose()
    await hub.close()
