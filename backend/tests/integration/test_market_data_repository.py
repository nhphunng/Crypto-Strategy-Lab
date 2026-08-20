from datetime import UTC, datetime, timedelta

import pytest

from crypto_lab.application.market_data.errors import CandleConflictError
from crypto_lab.domain.market_data.candle import MarketSelection, canonical_decimal
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)
from tests.fixtures.market_data import make_candle

pytestmark = pytest.mark.integration
SELECTION = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
RANGE = TimeRange(
    datetime(2024, 1, 1, tzinfo=UTC),
    datetime(2024, 1, 1, 0, 10, tzinfo=UTC),
)


@pytest.mark.asyncio
async def test_exact_duplicate_is_idempotent_and_decimal_utc_round_trip(
    postgres_repository: SqlAlchemyMarketDataRepository,
) -> None:
    candles = (
        make_candle(RANGE.start_time),
        make_candle(RANGE.start_time + timedelta(minutes=5)),
    )
    await postgres_repository.store_closed_candles(candles)
    await postgres_repository.store_closed_candles(tuple(reversed(candles)))

    stored = await postgres_repository.read_candles(SELECTION, RANGE)

    assert stored == candles
    assert stored[0].open_time.tzinfo is not None
    assert stored[0].volume == candles[0].volume
    assert canonical_decimal(stored[0].volume) == canonical_decimal(candles[0].volume)


@pytest.mark.asyncio
async def test_conflicting_closed_duplicate_fails_without_overwrite(
    postgres_repository: SqlAlchemyMarketDataRepository,
) -> None:
    original = make_candle(RANGE.start_time, close="101.25")
    conflict = make_candle(RANGE.start_time, close="101.50")
    await postgres_repository.store_closed_candles((original,))

    with pytest.raises(CandleConflictError):
        await postgres_repository.store_closed_candles((conflict,))

    assert await postgres_repository.read_candles(SELECTION, RANGE) == (original,)
