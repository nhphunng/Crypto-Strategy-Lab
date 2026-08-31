"""Run one news collection cycle against the configured feeds.

Usage (from the repository root, with the database reachable):

    python backend/scripts/collect_news_once.py

Builds the normal application container, runs `CollectNews.execute()` once, and
prints a summary. Exits non-zero only when every configured provider failed;
otherwise exits zero. It does not duplicate crawler logic and it does not start
the background loop.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from crypto_lab.api.dependencies import build_container  # noqa: E402
from crypto_lab.application.news.collect_news import NewsCollectionFailure  # noqa: E402
from crypto_lab.infrastructure.settings import Settings  # noqa: E402

DEFAULT_URL = os.getenv(
    "CSL_DATABASE_URL",
    "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab",
)


async def run_once() -> int:
    settings = Settings(news_collection_enabled=True)
    container = build_container(settings)
    collect_news = container.collect_news
    if collect_news is None:
        print("news collection is not configured (CSL_NEWS_FEEDS empty?)", file=sys.stderr)
        await container.close()
        return 2

    try:
        summary = await collect_news.execute()
    except NewsCollectionFailure as error:
        print(f"news collection failed: {error}", file=sys.stderr)
        await container.close()
        return 1

    await container.close()
    print(
        "news collection: "
        f"inserted={summary.inserted} updated={summary.updated} "
        f"unchanged={summary.unchanged}"
    )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(run_once()))


if __name__ == "__main__":  # pragma: no cover
    main()
