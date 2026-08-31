from __future__ import annotations

import asyncio

import pytest
from tests.fixtures.news.fakes import stored

from crypto_lab.application.news.collection_loop import NewsCollectionLoop


class _CountingCollector:
    """A collect-news collaborator that counts executions and may raise."""

    def __init__(self, error: Exception | None = None) -> None:
        self.calls = 0
        self._error = error

    async def execute(self) -> object:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return stored(inserted=2)


def _loop(*, interval: float = 60.0, error: Exception | None = None):
    collector = _CountingCollector(error=error)
    return collector, NewsCollectionLoop(collector, interval_seconds=interval)  # type: ignore[arg-type]


async def _sleep_until(predicate: object, seconds: float = 3.0) -> None:
    deadline = asyncio.get_event_loop().time() + seconds
    while not predicate():
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError("timed out waiting for collection cycle")
        await asyncio.sleep(0.02)


@pytest.mark.asyncio
async def test_loop_runs_once_immediately_on_start() -> None:
    collector, loop = _loop(interval=3600.0)
    loop.start()
    await _sleep_until(lambda: collector.calls >= 1)
    assert collector.calls == 1
    await loop.stop()


@pytest.mark.asyncio
async def test_loop_waits_interval_before_next_cycle() -> None:
    collector, loop = _loop(interval=0.05)
    loop.start()
    await _sleep_until(lambda: collector.calls >= 2)
    assert collector.calls >= 2
    await loop.stop()


@pytest.mark.asyncio
async def test_stop_cancels_cleanly_and_prevents_further_cycles() -> None:
    collector, loop = _loop(interval=0.02)
    loop.start()
    await _sleep_until(lambda: collector.calls >= 1)
    await loop.stop()
    assert loop._task is None
    calls_after_stop = collector.calls
    await asyncio.sleep(0.05)
    assert collector.calls == calls_after_stop


@pytest.mark.asyncio
async def test_loop_survives_a_failing_cycle_and_keeps_running() -> None:
    collector, loop = _loop(interval=0.02, error=RuntimeError("provider down"))
    loop.start()
    await _sleep_until(lambda: collector.calls >= 2)
    assert collector.calls >= 2
    await loop.stop()


@pytest.mark.asyncio
async def test_stop_before_start_is_a_noop() -> None:
    _, loop = _loop(interval=3600.0)
    await loop.stop()
    assert loop._task is None
