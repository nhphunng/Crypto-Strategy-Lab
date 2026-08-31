from __future__ import annotations

import pytest
from pydantic import ValidationError

from crypto_lab.infrastructure.settings import NewsFeedConfig, Settings


def test_news_collection_disabled_by_default_in_tests() -> None:
    settings = Settings(_env_file=None)

    assert settings.news_collection_enabled is False
    assert settings.news_collection_interval_seconds == 900
    assert settings.news_feeds == (
        NewsFeedConfig(source="Cointelegraph", url="https://cointelegraph.com/rss"),
    )


def test_news_collection_can_be_enabled_with_custom_interval() -> None:
    settings = Settings(
        _env_file=None,
        news_collection_enabled=True,
        news_collection_interval_seconds=120,
    )

    assert settings.news_collection_enabled is True
    assert settings.news_collection_interval_seconds == 120


def test_news_feeds_are_parsed_from_json_and_validated() -> None:
    settings = Settings(
        _env_file=None,
        news_feeds=(
            NewsFeedConfig(source="Cointelegraph", url="https://cointelegraph.com/rss"),
        ),
    )

    assert settings.news_feeds[0].source == "Cointelegraph"
    assert settings.news_feeds[0].url == "https://cointelegraph.com/rss"


@pytest.mark.parametrize(
    "url",
    (
        "http://cointelegraph.com/rss",  # non-HTTPS
        "https:///missing-host",  # missing host
        "https://user:pass@cointelegraph.com/rss",  # credentials
        "https://cointelegraph.com/rss?token=secret",  # query
        "https://cointelegraph.com/rss#frag",  # fragment
    ),
)
def test_news_feed_rejects_non_server_controlled_url(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, news_feeds=(NewsFeedConfig(source="X", url=url),))


def test_news_feed_rejects_blank_source() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, news_feeds=(NewsFeedConfig(source="   ", url="https://example.com/rss"),))


def test_news_interval_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, news_collection_interval_seconds=10)
