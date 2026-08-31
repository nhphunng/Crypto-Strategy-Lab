from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from crypto_lab.domain.backtest.result import BacktestResult
from crypto_lab.domain.evaluation.policy import EvaluationPolicy, ScoringPolicy
from crypto_lab.domain.evaluation.result import EvaluationResult


class BacktestReader(Protocol):
    async def get_result(self, result_id: UUID) -> BacktestResult | None: ...


class EvaluationRepository(Protocol):
    async def save(self, result: EvaluationResult) -> EvaluationResult: ...
    async def get(self, result_id: UUID) -> EvaluationResult | None: ...
    async def get_many(self, result_ids: tuple[UUID, ...]) -> tuple[EvaluationResult, ...]: ...


class PolicyReader(Protocol):
    async def get_evaluation(self, policy_id: UUID, version: str) -> EvaluationPolicy | None: ...
    async def get_scoring(self, policy_id: UUID, version: str) -> ScoringPolicy | None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...
