from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from crypto_lab.application.news.provider_errors import (
    NewsFeedParseError,
    NewsTransportError,
)
from crypto_lab.domain.news.coin_resolution import CoinResolver
from crypto_lab.infrastructure.news.rss_provider import (
    RssFeedDefinition,
    RssNewsProvider,
)
from tests.fixtures.market_data import FixedClock

CRAWLED = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)

RSS = RssFeedDefinition("Example Crypto RSS", "https://feeds.example.com/rss.xml")
ATOM = RssFeedDefinition("Example Crypto Atom", "https://feeds.example.com/atom.xml")


def _bytes(name: str) -> bytes:
    return (Path(__file__).parent.parent / "fixtures" / "news" / name).read_bytes()


def _provider(handler: object, feeds: tuple[RssFeedDefinition, ...]) -> RssNewsProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return RssNewsProvider(
        client=client,
        feeds=feeds,
        clock=FixedClock(CRAWLED),
        coin_resolver=CoinResolver(),
    )


def _by_id(items: tuple[object, ...]) -> dict[str, object]:
    by_id: dict[str, object] = {}
    for item in items:
        by_id[getattr(item, "provider_item_id")] = item  # noqa: B009
    return by_id


@pytest.mark.asyncio
async def test_rss_feed_maps_to_normalized_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_bytes("rss_feed.xml"))

    provider = _provider(handler, (RSS,))
    items = await provider.collect()

    assert provider.provider == "RSS"
    assert len(items) == 3
    by_id = _by_id(items)
    btc = by_id["https://feeds.example.com/articles/btc-high"]
    assert btc.title == "Bitcoin reaches a new high"
    assert btc.content == "Bitcoin climbed above $100k."
    assert btc.related_coins == ("BTC",)
    assert btc.published_at == datetime(2026, 8, 30, 10, 0, tzinfo=UTC)
    assert btc.url == "https://feeds.example.com/articles/btc-high"
    assert btc.canonical_url == btc.url
    assert btc.source == "Example Crypto RSS"
    eth = by_id["https://feeds.example.com/articles/eth-upgrade"]
    assert eth.related_coins == ("ETH",)
    assert eth.published_at == datetime(2026, 8, 30, 11, 30, tzinfo=UTC)
    sol = by_id["https://feeds.example.com/articles/sol-rally"]
    assert sol.content == "SOL gains & network activity."
    assert sol.related_coins == ("SOL",)
    assert sol.published_at == datetime(2026, 8, 30, 10, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_atom_feed_maps_to_normalized_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_bytes("atom_feed.xml"))

    provider = _provider(handler, (ATOM,))
    items = await provider.collect()

    assert len(items) == 2
    by_id = _by_id(items)
    first = by_id["urn:uuid:entry-1"]
    assert first.title == "Bitcoin ETF inflows rise"
    assert first.content == "Bitcoin ETF inflows continue to grow."
    assert first.related_coins == ("BTC",)
    assert first.published_at == datetime(2026, 8, 30, 9, 30, tzinfo=UTC)
    assert first.url == "https://feeds.example.com/articles/btc-etf"
    second = by_id["urn:uuid:entry-2"]
    assert second.content == "SOL upgrade ships."
    assert second.related_coins == ("SOL",)
    assert second.published_at == datetime(2026, 8, 30, 7, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_rss_and_atom_feed_merge_without_conflict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/atom.xml"):
            return httpx.Response(200, content=_bytes("atom_feed.xml"))
        return httpx.Response(200, content=_bytes("rss_feed.xml"))

    provider = _provider(handler, (RSS, ATOM))
    items = await provider.collect()
    sources = sorted(item.source for item in items)
    assert sources == [
        "Example Crypto Atom",
        "Example Crypto Atom",
        "Example Crypto RSS",
        "Example Crypto RSS",
        "Example Crypto RSS",
    ]


@pytest.mark.asyncio
async def test_malformed_entries_are_skipped_and_logged(caplog: pytest.LogCaptureFixture) -> None:
    payload = b"""<rss version="2.0"><channel>
  <item>
    <title>No link</title><guid>g1</guid>
    <pubDate>Sat, 30 Aug 2026 10:00:00 +0000</pubDate>
  </item>
  <item>
    <title>Bad date</title><link>https://feeds.example.com/x</link>
    <guid>g2</guid><pubDate>not-a-date</pubDate>
  </item>
  <item>
    <link>https://feeds.example.com/y</link><guid>g3</guid>
    <pubDate>Sat, 30 Aug 2026 10:00:00 +0000</pubDate>
  </item>
</channel></rss>"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    with caplog.at_level(logging.WARNING, logger="crypto_lab.infrastructure.news.rss_provider"):
        provider = _provider(handler, (RSS,))
        items = await provider.collect()

    assert items == ()
    assert len(caplog.records) == 3


@pytest.mark.asyncio
async def test_malformed_document_raises_typed_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="this is definitely not xml")

    provider = _provider(handler, (RSS,))
    with pytest.raises(NewsFeedParseError):
        await provider.collect()


@pytest.mark.asyncio
async def test_transport_error_raises_typed_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = _provider(handler, (RSS,))
    with pytest.raises(NewsTransportError):
        await provider.collect()
