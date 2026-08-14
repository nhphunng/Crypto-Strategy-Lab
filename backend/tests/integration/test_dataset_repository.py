import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from tests.fixtures.market_data import make_candle

from crypto_lab.domain.market_data.candle import MarketSelection
from crypto_lab.domain.market_data.dataset import DatasetStatus
from crypto_lab.domain.market_data.ranges import TimeRange
from crypto_lab.domain.market_data.timeframe import Timeframe
from crypto_lab.infrastructure.persistence.market_data_repository import (
    SqlAlchemyMarketDataRepository,
)

pytestmark = pytest.mark.integration
NOW = datetime(2026, 8, 13, 12, tzinfo=UTC)
SELECTION = MarketSelection("BINANCE", "BTCUSDT", Timeframe.FIVE_MINUTES)
RANGE = TimeRange(
    datetime(2024, 1, 1, tzinfo=UTC),
    datetime(2024, 1, 1, 0, 10, tzinfo=UTC),
)


@pytest.mark.asyncio
async def test_concurrent_claim_has_one_owner_and_complete_dataset_is_reused(
    postgres_repository: SqlAlchemyMarketDataRepository,
) -> None:
    first, second = await asyncio.gather(
        postgres_repository.claim_dataset(SELECTION, RANGE, NOW, timedelta(seconds=60)),
        postgres_repository.claim_dataset(SELECTION, RANGE, NOW, timedelta(seconds=60)),
    )
    owner = first if first.acquired else second
    observer = second if first.acquired else first
    assert owner.acquired and owner.build_token is not None
    assert not observer.acquired
    assert owner.dataset.id == observer.dataset.id

    candles = (
        make_candle(RANGE.start_time),
        make_candle(RANGE.start_time + timedelta(minutes=5)),
    )
    await postgres_repository.store_closed_candles(candles)
    completed = await postgres_repository.finalize_dataset(
        owner.dataset.id, owner.build_token, candles, NOW
    )
    reused = await postgres_repository.claim_dataset(
        SELECTION, RANGE, NOW + timedelta(minutes=5), timedelta(seconds=60)
    )

    assert completed.status is DatasetStatus.COMPLETE
    assert completed.candle_count == 2 and len(completed.checksum or "") == 64
    assert not reused.acquired and reused.dataset.checksum == completed.checksum


@pytest.mark.asyncio
async def test_dataset_membership_uses_stable_cursor_pages(
    postgres_repository: SqlAlchemyMarketDataRepository,
) -> None:
    candles = (
        make_candle(RANGE.start_time),
        make_candle(RANGE.start_time + timedelta(minutes=5)),
    )
    await postgres_repository.store_closed_candles(candles)
    claim = await postgres_repository.claim_dataset(SELECTION, RANGE, NOW, timedelta(seconds=60))
    assert claim.build_token is not None
    await postgres_repository.finalize_dataset(claim.dataset.id, claim.build_token, candles, NOW)

    first = await postgres_repository.list_dataset_candles(claim.dataset.id, None, 1)
    second = await postgres_repository.list_dataset_candles(claim.dataset.id, first.next_cursor, 1)

    assert first.candles == (candles[0],) and first.has_more
    assert second.candles == (candles[1],) and not second.has_more
