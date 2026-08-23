import json
import logging

import httpx
import pytest
from pydantic import ValidationError

from crypto_lab.infrastructure.logging import JsonFormatter, configure_logging, sanitize_fields
from crypto_lab.infrastructure.settings import Settings
from crypto_lab.main import create_app
from tests.contract.test_market_data_api import build_test_container


def test_provider_url_requires_server_controlled_https_shape() -> None:
    with pytest.raises(ValidationError):
        Settings(binance_base_url="http://127.0.0.1/internal", _env_file=None)
    with pytest.raises(ValidationError):
        Settings(binance_base_url="https://user:password@example.com", _env_file=None)


def test_structured_logging_redacts_sensitive_keys() -> None:
    assert sanitize_fields({"token": "secret", "pair": "BTCUSDT"}) == {
        "token": "[REDACTED]",
        "pair": "BTCUSDT",
    }
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "message", (), None)
    record.fields = {"api_key": "secret"}
    payload = json.loads(JsonFormatter().format(record))
    assert payload["api_key"] == "[REDACTED]"


def test_dependency_http_urls_are_not_logged_at_info() -> None:
    configure_logging("INFO")

    assert logging.getLogger("httpx").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.WARNING


@pytest.mark.asyncio
async def test_health_and_oversized_range_are_bounded() -> None:
    container, provider = build_test_container()
    app = create_app(container)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        live = await client.get("/health/live")
        ready = await client.get("/health/ready")
        oversized = await client.get(
            "/api/v1/market-data/candles",
            params={
                "provider": "BINANCE",
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "startTime": "2024-01-01T00:00:00.000Z",
                "endTime": "2024-01-05T00:00:00.000Z",
                "limit": 1001,
            },
        )
    assert live.status_code == ready.status_code == 200
    assert oversized.status_code == 422
    assert oversized.json()["error"]["code"] == "MARKET_RANGE_TOO_LARGE"
    assert provider.calls == []
