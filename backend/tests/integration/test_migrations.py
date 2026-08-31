from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration
REPO_ROOT = Path(__file__).parents[3]
CONFIG = REPO_ROOT / "backend" / "alembic.ini"
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab",
)


def run_alembic(command: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["CSL_DATABASE_URL"] = TEST_DATABASE_URL
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(CONFIG),
            command,
            revision,
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


async def table_names() -> set[str]:
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.connect() as connection:
            names = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_table_names()
            )
        return set(names)
    finally:
        await engine.dispose()


async def test_migrations_upgrade_in_dependency_order_and_round_trip() -> None:
    run_alembic("downgrade", "base")

    run_alembic("upgrade", "0001_historical_market_data")
    assert await table_names() == {
        "alembic_version",
        "candles",
        "candle_dataset_members",
        "candle_datasets",
    }

    run_alembic("upgrade", "20260813_003_strategy")
    assert "strategy_definitions" in await table_names()

    run_alembic("upgrade", "20260813_004_backtest")
    assert {
        "execution_policies",
        "backtest_runs",
        "backtest_results",
        "backtest_signal_snapshots",
        "backtest_trades",
        "backtest_equity_points",
        "evaluation_policies",
        "scoring_policies",
        "evaluation_results",
    } <= await table_names()

    run_alembic("upgrade", "head")
    assert {
        "leaderboards",
        "leaderboard_entries",
        "leaderboard_update_records",
        "strategy_generation_requests",
        "strategy_source_snapshots",
        "generated_strategy_drafts",
        "generated_strategy_artifacts",
        "strategy_validation_reports",
        "strategy_generation_provenance",
        "news_items",
    } <= await table_names()

    run_alembic("downgrade", "base")
    assert await table_names() == {"alembic_version"}
    run_alembic("upgrade", "head")


def test_alembic_has_one_head() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(CONFIG), "heads"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    heads = [line for line in result.stdout.splitlines() if line.strip().endswith("(head)")]
    assert heads == ["20260830_010_news (head)"]
