from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.infrastructure.persistence.search_models import (
    StrategySearchCandidateRow,
    StrategySearchRunRow,
)


class SqlAlchemySearchRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create(self, values: Mapping[str, object]) -> StrategySearchRunRow:
        async with self._sessions() as session, session.begin():
            row = StrategySearchRunRow(**values)
            session.add(row)
        return row

    async def get(self, run_id: UUID) -> StrategySearchRunRow | None:
        async with self._sessions() as session:
            return await session.get(StrategySearchRunRow, run_id)

    async def list(self, limit: int = 100) -> tuple[StrategySearchRunRow, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(StrategySearchRunRow)
                    .order_by(StrategySearchRunRow.created_at.desc())
                    .limit(limit)
                )
            ).all()
        return tuple(rows)

    async def patch(self, run_id: UUID, **values: object) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(
                update(StrategySearchRunRow)
                .where(StrategySearchRunRow.id == run_id)
                .values(**values)
            )

    async def add_candidate(self, values: Mapping[str, object]) -> StrategySearchCandidateRow:
        async with self._sessions() as session, session.begin():
            row = StrategySearchCandidateRow(**values)
            session.add(row)
        return row

    async def patch_candidate(self, candidate_id: UUID, **values: object) -> None:
        async with self._sessions() as session, session.begin():
            await session.execute(
                update(StrategySearchCandidateRow)
                .where(StrategySearchCandidateRow.id == candidate_id)
                .values(**values)
            )

    async def candidates(
        self, run_id: UUID, limit: int = 50
    ) -> tuple[StrategySearchCandidateRow, ...]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(StrategySearchCandidateRow)
                    .where(StrategySearchCandidateRow.search_run_id == run_id)
                    .order_by(StrategySearchCandidateRow.sequence.desc())
                    .limit(limit)
                )
            ).all()
        return tuple(rows)

    async def cancel(self, run_id: UUID, now: object) -> bool:
        async with self._sessions() as session, session.begin():
            result = await session.execute(
                update(StrategySearchRunRow)
                .where(
                    StrategySearchRunRow.id == run_id,
                    StrategySearchRunRow.status.in_(("QUEUED", "RUNNING")),
                )
                .values(
                    status="CANCELLED",
                    stop_reason="USER_CANCELLED",
                    completed_at=now,
                    current_candidate=None,
                )
            )
        return bool(result.rowcount)
