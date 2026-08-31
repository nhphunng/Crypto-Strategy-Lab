from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

import httpx

from crypto_lab.application.market_data.ports import Clock
from crypto_lab.application.news.ports import CollectedNewsItem
from crypto_lab.application.news.provider_errors import (
    NewsFeedParseError,
    NewsTransportError,
)
from crypto_lab.domain.news.coin_resolution import CoinResolver

_logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([.,;:!?])")


class _Skipped(Exception):
    """An individual feed entry could not be normalized; skip and log it."""


@dataclass(frozen=True, slots=True)
class RssFeedDefinition:
    """A configured HTTPS RSS/Atom feed. ``source`` is the human attribution."""

    source: str
    url: str


class RssNewsProvider:
    """Collect and normalize entries from HTTPS RSS/Atom feeds.

    The adapter never calls the public Internet on its own; it reads through the
    injected ``httpx.AsyncClient`` (a ``MockTransport`` in tests). Malformed
    entries are skipped and logged; a malformed document or a transport failure
    raises a typed :class:`NewsProviderError` subclass.
    """

    provider = "RSS"

    def __init__(
        self,
        client: httpx.AsyncClient,
        feeds: tuple[RssFeedDefinition, ...],
        clock: Clock,
        coin_resolver: CoinResolver,
    ) -> None:
        self._client = client
        self._feeds = feeds
        self._clock = clock
        self._coins = coin_resolver

    async def collect(self) -> tuple[CollectedNewsItem, ...]:
        collected: list[CollectedNewsItem] = []
        for feed in self._feeds:
            collected.extend(await self._collect_feed(feed))
        return tuple(collected)

    async def _collect_feed(
        self, feed: RssFeedDefinition
    ) -> tuple[CollectedNewsItem, ...]:
        try:
            response = await self._client.get(feed.url)
        except httpx.RequestError as error:
            raise NewsTransportError(feed.source, str(error)) from error
        if response.status_code >= 400:
            raise NewsTransportError(
                feed.source, f"feed returned HTTP {response.status_code}"
            )
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as error:
            raise NewsFeedParseError(feed.source) from error
        root_kind = _local_tag(root.tag)
        if root_kind not in ("rss", "feed"):
            raise NewsFeedParseError(feed.source)

        seen: set[str] = set()
        items: list[CollectedNewsItem] = []
        for element in root.iter():
            if not isinstance(element.tag, str):
                continue
            if _local_tag(element.tag) not in ("item", "entry"):
                continue
            try:
                item = self._parse_entry(element, root_kind, feed)
            except _Skipped as skipped:
                _logger.warning(
                    "Skipping malformed %s entry in %s: %s", root_kind, feed.url, skipped
                )
                continue
            if item.provider_item_id in seen:
                continue
            seen.add(item.provider_item_id)
            items.append(item)
        return tuple(items)

    def _parse_entry(
        self, element: ET.Element, root_kind: str, feed: RssFeedDefinition
    ) -> CollectedNewsItem:
        if root_kind == "rss":
            return self._parse_rss_item(element, feed)
        return self._parse_atom_entry(element, feed)

    def _parse_rss_item(
        self, element: ET.Element, feed: RssFeedDefinition
    ) -> CollectedNewsItem:
        title = _child_text(element, "title")
        if not title:
            raise _Skipped("title is missing")
        raw_link = _child_text(element, "link")
        if not raw_link:
            raise _Skipped("link is missing")
        url = _require_https(raw_link)
        item_id = _child_text(element, "guid") or url
        raw_content = _child_text(element, "encoded") or _child_text(element, "description")
        return self._build_item(element, title, url, item_id, raw_content, feed)

    def _parse_atom_entry(
        self, element: ET.Element, feed: RssFeedDefinition
    ) -> CollectedNewsItem:
        title = _child_text(element, "title")
        if not title:
            raise _Skipped("title is missing")
        url = _require_https(_atom_link(element))
        item_id = _child_text(element, "id") or url
        raw_content = _child_text(element, "content") or _child_text(element, "summary")
        return self._build_item(element, title, url, item_id, raw_content, feed)

    def _build_item(
        self,
        element: ET.Element,
        title: str,
        url: str,
        item_id: str,
        raw_content: str | None,
        feed: RssFeedDefinition,
    ) -> CollectedNewsItem:
        content = _to_plain_text(raw_content or "")
        if not content:
            raise _Skipped("content/summary is missing")
        raw_date = (
            _child_text(element, "pubDate")
            or _child_text(element, "published")
            or _child_text(element, "updated")
            or ""
        )
        published_at = _parse_datetime(raw_date)
        coins = self._coins.resolve(f"{title} {content}")
        return CollectedNewsItem(
            provider_item_id=item_id,
            title=_to_plain_text(title),
            content=content,
            source=feed.source,
            published_at=published_at,
            related_coins=coins,
            url=url,
            canonical_url=url,
        )


def _local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if _local_tag(child.tag) == name and child.text is not None:
            return child.text
    return None


def _atom_link(element: ET.Element) -> str:
    for child in element:
        if _local_tag(child.tag) == "link":
            rel = child.get("rel", "alternate")
            href = child.get("href")
            if rel == "alternate" and href:
                return href
    raise _Skipped("alternate link is missing")


def _require_https(url: str) -> str:
    value = url.strip()
    parsed = urlsplit(value)
    if not value or parsed.scheme.lower() != "https" or not parsed.netloc:
        raise _Skipped(f"link must be an absolute HTTPS URL, got {value!r}")
    return value


def _parse_datetime(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise _Skipped("publication date is missing")
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as error:
            raise _Skipped(f"unparseable date {value!r}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _to_plain_text(markup: str) -> str:
    text = _TAG_RE.sub(" ", markup)
    text = unescape(text)
    text = " ".join(text.split())
    text = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text)
    return text.strip()
