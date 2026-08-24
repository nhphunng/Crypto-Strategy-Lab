"""Load the deterministic TV5 demo data into a running PostgreSQL database.

Usage (from the repository root, with the database reachable):

    python backend/scripts/seed_leaderboard_demo.py            # reset and seed
    python backend/scripts/seed_leaderboard_demo.py --complete # publish one more
                                                               # qualifying evaluation

The script writes only immutable upstream records. The leaderboard projection
is always derived by the feature itself.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from sqlalchemy import func, select  # noqa: E402
from tests.fixtures.leaderboard import (  # noqa: E402
    add_qualifying_candidate,
    reset_leaderboard_fixture,
    seed_leaderboard_fixture,
)

from crypto_lab.api.dependencies import build_container  # noqa: E402
from crypto_lab.infrastructure.database import Database  # noqa: E402
from crypto_lab.infrastructure.persistence.evaluation_models import (  # noqa: E402
    EvaluationResultRow,
)
from crypto_lab.infrastructure.settings import Settings  # noqa: E402

DEFAULT_URL = os.getenv(
    "CSL_DATABASE_URL",
    "postgresql+asyncpg://crypto_lab:crypto_lab@localhost:55432/crypto_lab",
)


async def seed(database_url: str, *, complete_one_more: bool) -> None:
    database = Database.create(database_url)
    try:
        if not await database.ping():
            raise SystemExit(f"database unavailable at {database_url}")
        if complete_one_more:
            async with database.sessions() as session:
                existing = await session.scalar(
                    select(func.count()).select_from(EvaluationResultRow)
                )
            index = 20 + int(existing or 0)
            async with database.sessions() as session, session.begin():
                evaluation_id = await add_qualifying_candidate(session, index=index)
            container = build_container(Settings(database_url=database_url))
            try:
                leaderboard = container.leaderboard
                assert leaderboard is not None
                # Only the projection change is committed here. Publication is
                # left to the running API process, which claims the durable
                # update record and pushes it to connected clients.
                outcomes = await leaderboard.updater.for_evaluation(evaluation_id)
            finally:
                await container.close()
            changed = [outcome for outcome in outcomes if outcome.changed]
            print(f"completed evaluation {evaluation_id}")
            print(f"projections updated: {len(changed)} of {len(outcomes)}")
            for outcome in changed:
                print(f"  leaderboard {outcome.leaderboard_id} -> v{outcome.projection_version}")
            return

        async with database.sessions() as session, session.begin():
            await reset_leaderboard_fixture(session)
            fixture = await seed_leaderboard_fixture(session)
        print("seeded the deterministic TV5 fixture")
        print(f"  scoring policy : {fixture.scoring_policy_id} v{fixture.scoring_policy_version}")
        print(f"  market         : {fixture.pair} {fixture.timeframe}")
        print(f"  candidates     : {len(fixture.candidates)} (10 qualify for K=10)")
        print(f"  top one        : {fixture.top_one_evaluation_id}")
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=DEFAULT_URL)
    parser.add_argument(
        "--complete",
        action="store_true",
        help="append one qualifying evaluation and publish its leaderboard update",
    )
    arguments = parser.parse_args()
    asyncio.run(seed(arguments.database_url, complete_one_more=arguments.complete))


if __name__ == "__main__":
    main()
