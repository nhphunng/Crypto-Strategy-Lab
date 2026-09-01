from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

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
SENTIMENT_REVISION = "20260901_011_news_sentiment"
PREVIOUS_REVISION = "20260831_010_strategy_search"


def run_alembic(command: str, revision: str) -> None:
    environment = os.environ.copy()
    environment["CSL_DATABASE_URL"] = TEST_DATABASE_URL
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(CONFIG), command, revision],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


async def sentiment_schema() -> dict[str, Any]:
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: {
                    "tables": set(inspect(sync_connection).get_table_names()),
                    "columns": inspect(sync_connection).get_columns("news_sentiment_analyses"),
                    "primary_key": inspect(sync_connection).get_pk_constraint(
                        "news_sentiment_analyses"
                    ),
                    "unique_constraints": inspect(sync_connection).get_unique_constraints(
                        "news_sentiment_analyses"
                    ),
                    "foreign_keys": inspect(sync_connection).get_foreign_keys(
                        "news_sentiment_analyses"
                    ),
                    "indexes": inspect(sync_connection).get_indexes("news_sentiment_analyses"),
                }
            )
    finally:
        await engine.dispose()


async def test_sentiment_migration_creates_exact_postgresql_schema() -> None:
    run_alembic("downgrade", PREVIOUS_REVISION)
    try:
        run_alembic("upgrade", SENTIMENT_REVISION)

        schema = await sentiment_schema()
        assert "news_sentiment_analyses" in schema["tables"]
        assert schema["primary_key"]["constrained_columns"] == ["id"]

        columns = {column["name"]: column for column in schema["columns"]}
        assert set(columns) == {
            "id",
            "news_id",
            "model_id",
            "model_version",
            "label",
            "score",
            "analyzed_at",
            "content_fingerprint",
            "status",
            "failure_code",
        }
        required = set(columns) - {"failure_code"}
        assert all(not columns[name]["nullable"] for name in required)
        assert columns["failure_code"]["nullable"] is True
        assert str(columns["id"]["type"]) == "UUID"
        assert str(columns["news_id"]["type"]) == "UUID"
        assert columns["analyzed_at"]["type"].timezone is True

        unique_constraints = {
            tuple(constraint["column_names"]): constraint["name"]
            for constraint in schema["unique_constraints"]
        }
        assert (
            unique_constraints[("news_id", "model_id", "model_version", "content_fingerprint")]
            == "uq_news_sentiment_analyses_identity"
        )

        foreign_keys = schema["foreign_keys"]
        assert any(
            fk["referred_table"] == "news_items" and fk["constrained_columns"] == ["news_id"]
            for fk in foreign_keys
        )

        indexes = {index["name"] for index in schema["indexes"]}
        assert "ix_news_sentiment_analyses_latest" in indexes
        assert "ix_news_sentiment_analyses_pending_lookup" in indexes
    finally:
        run_alembic("upgrade", "head")


async def test_sentiment_migration_downgrades_cleanly() -> None:
    run_alembic("upgrade", SENTIMENT_REVISION)
    try:
        run_alembic("downgrade", PREVIOUS_REVISION)
        engine = create_async_engine(TEST_DATABASE_URL)
        try:
            async with engine.connect() as connection:
                tables = await connection.run_sync(
                    lambda sync_connection: set(inspect(sync_connection).get_table_names())
                )
            assert "news_sentiment_analyses" not in tables
        finally:
            await engine.dispose()
    finally:
        run_alembic("upgrade", "head")


def test_sentiment_row_model_matches_migration_contract() -> None:
    sentiment_models = importlib.import_module(
        "crypto_lab.infrastructure.persistence.sentiment_models"
    )
    table = sentiment_models.NewsSentimentAnalysisRow.__table__

    assert set(table.columns.keys()) == {
        "id",
        "news_id",
        "model_id",
        "model_version",
        "label",
        "score",
        "analyzed_at",
        "content_fingerprint",
        "status",
        "failure_code",
    }
    assert {constraint.name for constraint in table.constraints} >= {
        "uq_news_sentiment_analyses_identity",
    }
    assert {index.name for index in table.indexes} == {
        "ix_news_sentiment_analyses_latest",
        "ix_news_sentiment_analyses_pending_lookup",
    }
