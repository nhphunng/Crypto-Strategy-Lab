from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
REPO_ROOT = Path(__file__).parents[3]
ALEMBIC = REPO_ROOT / ".venv" / "Scripts" / "alembic.exe"
CONFIG = REPO_ROOT / "backend" / "alembic.ini"


def run_alembic(revision: str) -> None:
    environment = os.environ.copy()
    environment["CSL_DATABASE_URL"] = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab",
    )
    subprocess.run(
        [
            str(ALEMBIC),
            "-c",
            str(CONFIG),
            "upgrade" if revision == "head" else "downgrade",
            revision,
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_initial_migration_downgrade_upgrade_cycle() -> None:
    run_alembic("base")
    run_alembic("head")
