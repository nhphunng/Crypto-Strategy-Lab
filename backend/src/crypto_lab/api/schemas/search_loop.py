"""Search-loop status DTO.

JSON is camelCase, mirroring the convention used by ``api/schemas/news.py``.
"""

from __future__ import annotations

from pydantic import Field

from crypto_lab.api.common import ApiModel
from crypto_lab.application.evaluations.auto_evaluate import SearchLoopStats


class SearchLoopStatusDto(ApiModel):
    status: str
    cycles_completed: int = Field(alias="cyclesCompleted")
    candidates_generated: int = Field(alias="candidatesGenerated")
    candidates_succeeded: int = Field(alias="candidatesSucceeded")
    candidates_failed: int = Field(alias="candidatesFailed")
    last_cycle_at: str | None = Field(alias="lastCycleAt")
    last_error: str | None = Field(alias="lastError")


def stats_to_dto(stats: SearchLoopStats) -> SearchLoopStatusDto:
    return SearchLoopStatusDto.model_validate(stats.to_payload())
