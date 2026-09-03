"""Analyze one batch of stored news with the configured FinBERT model."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from crypto_lab.api.dependencies import build_container


async def main() -> int:
    container = build_container()
    try:
        assert container.analyze_pending_news is not None
        report = await container.analyze_pending_news.execute(
            limit=container.settings.sentiment_analysis_batch_size
        )
        print(
            f"sentiment: attempted={report.attempted} "
            f"succeeded={report.succeeded} failed={report.failed}"
        )
        return int(report.failed > 0)
    finally:
        await container.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
