from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from crypto_lab.domain.backtest.configuration import BacktestRun, ExecutionPolicy
from crypto_lab.domain.backtest.equity import EquityPoint
from crypto_lab.domain.backtest.result import BacktestResult
from crypto_lab.domain.backtest.trade import Trade
from crypto_lab.domain.market_data.candle import Candle
from crypto_lab.domain.market_data.dataset import CandleDataset
from crypto_lab.domain.strategy.signal import StrategyAnalysisResult


@dataclass(frozen=True, slots=True)
class BacktestDataset:
    metadata: CandleDataset
    candles: tuple[Candle, ...]


@dataclass(frozen=True, slots=True)
class Page:
    items: tuple[object, ...]
    next_cursor: str | None


class DatasetReader(Protocol):
    async def get_complete(self, dataset_id: UUID) -> BacktestDataset | None: ...


class StrategyAnalyzer(Protocol):
    async def analyze(
        self, definition_id: UUID, dataset_id: UUID, request_id: str
    ) -> StrategyAnalysisResult: ...


class BacktestRepository(Protocol):
    async def create_or_resolve_run(self, run: BacktestRun) -> BacktestRun: ...
    async def get_run(self, run_id: UUID) -> BacktestRun | None: ...
    async def update_run(self, run: BacktestRun) -> None: ...
    async def save_result(self, result: BacktestResult) -> BacktestResult: ...
    async def get_result(self, result_id: UUID) -> BacktestResult | None: ...
    async def get_result_for_run(self, run_id: UUID) -> BacktestResult | None: ...
    async def result_counts(self, result_id: UUID) -> tuple[int, int] | None: ...
    async def list_trades(
        self, result_id: UUID, cursor: str | None, limit: int
    ) -> tuple[tuple[Trade, ...], str | None]: ...
    async def list_equity(
        self, result_id: UUID, cursor: str | None, limit: int
    ) -> tuple[tuple[EquityPoint, ...], str | None]: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class ExecutionPolicyReader(Protocol):
    async def get(self, policy_id: UUID, version: str) -> ExecutionPolicy | None: ...
