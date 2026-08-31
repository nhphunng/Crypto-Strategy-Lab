"""Seed deterministic normalized news items through NewsRepository.

Usage (from the repository root, with the database reachable and migrated):

    python backend/scripts/seed_news_demo.py

The script builds the normal application container and inserts two well-formed
NewsItem records through the idempotent repository — one published within the
last 24 hours (BTC) and one within the last 7 days (ETH) — so the browser E2E
can verify coin filtering, the 24H -> 7D widening, and the API-backed source of
truth. It never touches SQL directly and never reaches a public feed.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from crypto_lab.api.dependencies import build_container  # noqa: E402
from crypto_lab.domain.news.item import NewsItem  # noqa: E402
from crypto_lab.infrastructure.settings import Settings  # noqa: E402

DEFAULT_URL = os.getenv(
    "CSL_DATABASE_URL",
    "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab",
)

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def _item(
    index: int,
    *,
    coin: str,
    published: datetime,
) -> NewsItem:
    slug = coin.lower()
    url = f"https://example.com/articles/{slug}-{index}"
    return NewsItem(
        id=UUID(int=index),
        provider="demo",
        provider_item_id=f"demo-{slug}-{index}",
        title=f"[Demo] {coin} market update #{index}",
        content=(
            f"Seeded {coin} summary. This is provider-normalized feed content "
            "used only by the deterministic browser journey; it does not come "
            "from a live feed."
        ),
        source="Demo Feed",
        published_at=published,
        crawled_at=published + timedelta(minutes=5),
        related_coins=(coin,),
        url=url,
        canonical_url=url,
    )


async def seed(container) -> int:
    assert container.news_repository is not None
    items = (
        _item(1, coin="BTC", published=NOW - timedelta(hours=3)),
        _item(2, coin="ETH", published=NOW - timedelta(days=3)),
    )
    result = await container.news_repository.upsert_many(items)
    print(
        "news seed: "
        f"inserted={result.inserted} updated={result.updated} "
        f"unchanged={result.unchanged}"
    )
    return 0


async def run_once() -> int:
    container = build_container(Settings(_env_file=None))
    try:
        return await seed(container)
    finally:
        await container.close()


def main() -> None:
    raise SystemExit(asyncio.run(run_once()))


if __name__ == "__main__":  # pragma: no cover
    main()
