from __future__ import annotations

from datetime import datetime
from typing import Protocol


class SourceRetentionRepository(Protocol):
    async def purge_expired_raw_sources(self, now: datetime, *, batch_size: int) -> int: ...


class PurgeExpiredSourceContent:
    def __init__(self, repository: SourceRetentionRepository, *, batch_size: int = 500) -> None:
        self._repository = repository
        self._batch_size = batch_size

    async def execute(self, now: datetime) -> int:
        return await self._repository.purge_expired_raw_sources(now, batch_size=self._batch_size)
