from datetime import UTC, datetime

from tests.fixtures.market_data import make_candle

from crypto_lab.api.schemas.market_data import candle_to_dto
from crypto_lab.domain.market_data.timeframe import Timeframe


def test_tv1_candle_open_time_is_tv2_identity_and_tv3_signal_timestamp() -> None:
    candle = make_candle(datetime(2024, 1, 1, tzinfo=UTC))
    payload = candle_to_dto(candle).model_dump(by_alias=True)

    assert payload["openTime"] == "2024-01-01T00:00:00.000Z"
    assert set(payload) == {
        "provider",
        "pair",
        "timeframe",
        "openTime",
        "closeTime",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "closed",
        "receivedAt",
    }
    assert [value.value for value in Timeframe] == [
        "1m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "1d",
    ]
