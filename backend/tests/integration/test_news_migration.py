from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

pytestmark = pytest.mark.integration
REPO_ROOT = Path(__file__).parents[3]
CONFIG = REPO_ROOT / "backend" / "alembic.ini"
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab",
)
NEWS_REVISION = "20260830_010_news"
PREVIOUS_REVISION = "20260828_009_strategy_configs"


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


async def news_schema() -> dict[str, Any]:
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: {
                    "tables": set(inspect(sync_connection).get_table_names()),
                    "columns": inspect(sync_connection).get_columns("news_items"),
                    "primary_key": inspect(sync_connection).get_pk_constraint("news_items"),
                    "unique_constraints": inspect(sync_connection).get_unique_constraints(
                        "news_items"
                    ),
                    "indexes": inspect(sync_connection).get_indexes("news_items"),
                }
            )
    finally:
        await engine.dispose()


async def news_index_definitions() -> dict[str, str]:
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.connect() as connection:
            rows = await connection.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE schemaname = current_schema() AND tablename = 'news_items'"
                )
            )
            return {row.indexname: row.indexdef for row in rows}
    finally:
        await engine.dispose()


async def test_news_migration_creates_exact_postgresql_schema_and_indexes() -> None:
    run_alembic("downgrade", PREVIOUS_REVISION)
    try:
        run_alembic("upgrade", NEWS_REVISION)

        schema = await news_schema()
        assert "news_items" in schema["tables"]
        assert schema["primary_key"]["constrained_columns"] == ["id"]

        columns = {column["name"]: column for column in schema["columns"]}
        assert set(columns) == {
            "id",
            "provider",
            "provider_item_id",
            "title",
            "content",
            "source",
            "published_at",
            "crawled_at",
            "related_coins",
            "url",
            "canonical_url",
            "content_fingerprint",
        }
        assert all(not column["nullable"] for column in columns.values())
        assert str(columns["id"]["type"]) == "UUID"
        assert str(columns["provider"]["type"]) == "VARCHAR(32)"
        assert str(columns["provider_item_id"]["type"]) == "VARCHAR(256)"
        assert str(columns["title"]["type"]) == "VARCHAR(500)"
        assert str(columns["content"]["type"]) == "TEXT"
        assert str(columns["source"]["type"]) == "VARCHAR(160)"
        assert columns["published_at"]["type"].timezone is True
        assert columns["crawled_at"]["type"].timezone is True
        assert str(columns["related_coins"]["type"]) == "ARRAY"
        assert str(columns["related_coins"]["type"].item_type) == "VARCHAR(16)"
        assert str(columns["url"]["type"]) == "TEXT"
        assert str(columns["canonical_url"]["type"]) == "TEXT"
        assert str(columns["content_fingerprint"]["type"]) == "CHAR(64)"

        unique_constraints = {
            tuple(constraint["column_names"]): constraint["name"]
            for constraint in schema["unique_constraints"]
        }
        assert unique_constraints[("provider", "provider_item_id")] == (
            "uq_news_items_provider_item"
        )
        assert unique_constraints[("canonical_url",)] == "uq_news_items_canonical_url"

        indexes = {index["name"]: index for index in schema["indexes"]}
        assert indexes["ix_news_items_related_coins"]["column_names"] == ["related_coins"]
        assert indexes["ix_news_items_published"]["column_names"] == ["published_at", "id"]

        definitions = await news_index_definitions()
        assert "using gin (related_coins)" in definitions[
            "ix_news_items_related_coins"
        ].lower()
        assert "using btree (published_at desc, id)" in definitions[
            "ix_news_items_published"
        ].lower()
    finally:
        run_alembic("upgrade", "head")


async def test_news_migration_downgrades_cleanly() -> None:
    run_alembic("upgrade", NEWS_REVISION)
    try:
        run_alembic("downgrade", PREVIOUS_REVISION)
        engine = create_async_engine(TEST_DATABASE_URL)
        try:
            async with engine.connect() as connection:
                tables = await connection.run_sync(
                    lambda sync_connection: set(inspect(sync_connection).get_table_names())
                )
            assert "news_items" not in tables
        finally:
            await engine.dispose()
    finally:
        run_alembic("upgrade", "head")


def test_news_row_model_matches_migration_contract() -> None:
    news_models = importlib.import_module(
        "crypto_lab.infrastructure.persistence.news_models"
    )
    table = news_models.NewsItemRow.__table__

    assert set(table.columns.keys()) == {
        "id",
        "provider",
        "provider_item_id",
        "title",
        "content",
        "source",
        "published_at",
        "crawled_at",
        "related_coins",
        "url",
        "canonical_url",
        "content_fingerprint",
    }
    assert {constraint.name for constraint in table.constraints} >= {
        "uq_news_items_provider_item",
        "uq_news_items_canonical_url",
    }
    assert {index.name for index in table.indexes} == {
        "ix_news_items_related_coins",
        "ix_news_items_published",
    }
