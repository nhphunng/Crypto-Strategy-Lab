from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from crypto_lab.api.common import ApiModel
from crypto_lab.domain.backtest.configuration import BacktestRun, ExecutionPolicy
from crypto_lab.domain.backtest.equity import EquityPoint
from crypto_lab.domain.backtest.result import BacktestResult
from crypto_lab.domain.backtest.trade import Trade
from crypto_lab.domain.evaluation.comparison import EvaluationComparison
from crypto_lab.domain.evaluation.policy import EvaluationPolicy, ScoringPolicy
from crypto_lab.domain.evaluation.result import ANALYSIS_TYPE, DISCLAIMER, EvaluationResult
from crypto_lab.domain.market_data.candle import canonical_decimal, format_utc_millis


class CreateBacktestRunRequest(ApiModel):
    job_id: UUID = Field(alias="jobId")
    dataset_id: UUID = Field(alias="datasetId")
    dataset_schema_version: Literal["1"] = Field(alias="datasetSchemaVersion")
    dataset_checksum: str = Field(alias="datasetChecksum", pattern=r"^[0-9a-f]{64}$")
    strategy_definition_id: UUID = Field(alias="strategyDefinitionId")
    strategy_version: str = Field(alias="strategyVersion")
    contract_version: Literal["1.0.0"] = Field(alias="contractVersion")
    execution_policy_id: UUID = Field(alias="executionPolicyId")
    execution_policy_version: str = Field(alias="executionPolicyVersion")
    initial_capital: Decimal = Field(alias="initialCapital", gt=0)
    fee_rate: Decimal = Field(alias="feeRate", ge=0)
    slippage_rate: Decimal = Field(alias="slippageRate", ge=0, lt=1)
    random_seed: int = Field(alias="randomSeed")

    @field_validator("initial_capital", "fee_rate", "slippage_rate", mode="before")
    @classmethod
    def reject_float(cls, value: object) -> object:
        if isinstance(value, float | bool):
            raise ValueError("decimal values must be JSON strings or integers")
        return value


class PolicyIdentityDto(ApiModel):
    id: UUID
    policy_id: str = Field(alias="policyId")
    version: str


class ScoringPolicyIdentityDto(PolicyIdentityDto):
    name: str


class BacktestEvaluationPolicyBundleDto(ApiModel):
    execution_policy: PolicyIdentityDto = Field(alias="executionPolicy")
    evaluation_policy: PolicyIdentityDto = Field(alias="evaluationPolicy")
    scoring_policy: ScoringPolicyIdentityDto = Field(alias="scoringPolicy")


class BacktestRunDto(ApiModel):
    id: UUID
    job_id: UUID = Field(alias="jobId")
    status: str
    dataset_id: UUID = Field(alias="datasetId")
    strategy_definition_id: UUID = Field(alias="strategyDefinitionId")
    strategy_id: str = Field(alias="strategyId")
    pair: str
    timeframe: str
    parent_search_run_id: UUID | None = Field(None, alias="parentSearchRunId")
    candidate_display_name: str | None = Field(None, alias="candidateDisplayName")
    execution_policy_id: UUID = Field(alias="executionPolicyId")
    execution_policy_version: str = Field(alias="executionPolicyVersion")
    initial_capital: str = Field(alias="initialCapital")
    fee_rate: str = Field(alias="feeRate")
    slippage_rate: str = Field(alias="slippageRate")
    random_seed: int = Field(alias="randomSeed")
    requested_at: str = Field(alias="requestedAt")
    completed_at: str | None = Field(alias="completedAt")
    failure_code: str | None = Field(alias="failureCode")


class ProvenanceDto(ApiModel):
    dataset_id: UUID = Field(alias="datasetId")
    dataset_schema_version: str = Field(alias="datasetSchemaVersion")
    dataset_checksum: str = Field(alias="datasetChecksum")
    strategy_definition_id: UUID = Field(alias="strategyDefinitionId")
    strategy_id: str = Field(alias="strategyId")
    strategy_version: str = Field(alias="strategyVersion")
    contract_version: str = Field(alias="contractVersion")
    execution_policy_id: UUID = Field(alias="executionPolicyId")
    execution_policy_version: str = Field(alias="executionPolicyVersion")
    execution_config_fingerprint: str = Field(alias="executionConfigFingerprint")


class BacktestResultDto(ApiModel):
    id: UUID
    run_id: UUID = Field(alias="runId")
    job_id: UUID = Field(alias="jobId")
    result_checksum: str = Field(alias="resultChecksum")
    history_state: str = Field(alias="historyState")
    trade_state: str = Field(alias="tradeState")
    initial_capital: str = Field(alias="initialCapital")
    final_equity: str = Field(alias="finalEquity")
    signal_count: int = Field(alias="signalCount")
    trade_count: int = Field(alias="tradeCount")
    equity_point_count: int = Field(alias="equityPointCount")
    provenance: ProvenanceDto
    analysis_type: Literal["HISTORICAL_SIMULATION"] = Field(alias="analysisType")
    disclaimer: str


class TradeDto(ApiModel):
    id: UUID
    sequence: int
    entry_signal_id: UUID = Field(alias="entrySignalId")
    exit_signal_id: UUID | None = Field(alias="exitSignalId")
    entry_time: str = Field(alias="entryTime")
    exit_time: str = Field(alias="exitTime")
    entry_reference_price: str = Field(alias="entryReferencePrice")
    exit_reference_price: str = Field(alias="exitReferencePrice")
    entry_price: str = Field(alias="entryPrice")
    exit_price: str = Field(alias="exitPrice")
    side: str
    quantity: str
    entry_fee: str = Field(alias="entryFee")
    exit_fee: str = Field(alias="exitFee")
    profit_loss: str = Field(alias="profitLoss")
    return_percent: str = Field(alias="returnPercent")
    close_reason: str = Field(alias="closeReason")


class EquityPointDto(ApiModel):
    position: int
    candle_open_time: str = Field(alias="candleOpenTime")
    valued_at: str = Field(alias="valuedAt")
    close_price: str = Field(alias="closePrice")
    cash: str
    quantity: str
    position_value: str = Field(alias="positionValue")
    equity: str


class PageMetaDto(ApiModel):
    page: int
    page_size: int = Field(alias="pageSize")
    total: int


class TradePageDto(ApiModel):
    items: tuple[TradeDto, ...]
    pagination: PageMetaDto
    next_cursor: str | None = Field(alias="nextCursor")


class EquityPageDto(ApiModel):
    items: tuple[EquityPointDto, ...]
    pagination: PageMetaDto
    next_cursor: str | None = Field(alias="nextCursor")


class CreateEvaluationRequest(ApiModel):
    backtest_result_id: UUID = Field(alias="backtestResultId")
    evaluation_policy_id: UUID = Field(alias="evaluationPolicyId")
    evaluation_policy_version: str = Field(alias="evaluationPolicyVersion")
    scoring_policy_id: UUID = Field(alias="scoringPolicyId")
    scoring_policy_version: str = Field(alias="scoringPolicyVersion")


class MetricSetDto(ApiModel):
    total_return: str = Field(alias="totalReturn")
    win_rate: str = Field(alias="winRate")
    max_drawdown: str = Field(alias="maxDrawdown")
    number_of_trades: int = Field(alias="numberOfTrades")
    profit_factor: str | None = Field(alias="profitFactor")
    sharpe_ratio: str | None = Field(alias="sharpeRatio")


class EvaluationResultDto(ApiModel):
    id: UUID
    backtest_result_id: UUID = Field(alias="backtestResultId")
    job_id: UUID = Field(alias="jobId")
    run_id: UUID = Field(alias="runId")
    strategy_id: str = Field(alias="strategyId")
    strategy_version: str = Field(alias="strategyVersion")
    dataset_id: UUID = Field(alias="datasetId")
    pair: str
    timeframe: str
    start_time: str = Field(alias="startTime")
    end_time: str = Field(alias="endTime")
    execution_config: dict[str, object] = Field(alias="executionConfig")
    metrics: MetricSetDto
    score: str
    eligible: bool
    exclusion_reasons: tuple[str, ...] = Field(alias="exclusionReasons")
    evaluation_policy_id: UUID = Field(alias="evaluationPolicyId")
    evaluation_policy_version: str = Field(alias="evaluationPolicyVersion")
    scoring_policy_id: UUID = Field(alias="scoringPolicyId")
    scoring_policy_version: str = Field(alias="scoringPolicyVersion")
    evaluated_at: str = Field(alias="evaluatedAt")
    content_fingerprint: str = Field(alias="contentFingerprint")
    analysis_type: Literal["HISTORICAL_SIMULATION"] = Field(alias="analysisType")
    disclaimer: str


class ComparisonRequest(ApiModel):
    evaluation_result_ids: tuple[UUID, ...] = Field(
        alias="evaluationResultIds", min_length=2, max_length=20
    )
    mode: Literal["STRICT", "CONTEXTUAL"] = "CONTEXTUAL"


class ContextDifferenceDto(ApiModel):
    dimension: str
    values: tuple[str, ...]


class ComparisonDto(ApiModel):
    compatible: bool
    differences: tuple[ContextDifferenceDto, ...]
    results: tuple[EvaluationResultDto, ...]


def run_to_dto(run: BacktestRun) -> BacktestRunDto:
    c = run.configuration
    return BacktestRunDto(
        id=c.run_id,
        job_id=c.job_id,
        status=run.status.value,
        dataset_id=c.dataset_id,
        strategy_definition_id=c.strategy_definition_id,
        strategy_id=c.strategy_id,
        pair=c.pair,
        timeframe=c.timeframe.value,
        execution_policy_id=c.execution_policy_id,
        execution_policy_version=c.execution_policy_version,
        initial_capital=canonical_decimal(c.initial_capital),
        fee_rate=canonical_decimal(c.fee_rate),
        slippage_rate=canonical_decimal(c.slippage_rate),
        random_seed=c.random_seed,
        requested_at=format_utc_millis(run.requested_at),
        completed_at=None if run.completed_at is None else format_utc_millis(run.completed_at),
        failure_code=run.failure_code,
    )


def policy_bundle_to_dto(
    execution: ExecutionPolicy, evaluation: EvaluationPolicy, scoring: ScoringPolicy
) -> BacktestEvaluationPolicyBundleDto:
    return BacktestEvaluationPolicyBundleDto(
        execution_policy=PolicyIdentityDto(
            id=execution.id, policy_id=execution.policy_id, version=execution.version
        ),
        evaluation_policy=PolicyIdentityDto(
            id=evaluation.id, policy_id=evaluation.policy_id, version=evaluation.version
        ),
        scoring_policy=ScoringPolicyIdentityDto(
            id=scoring.id,
            policy_id=scoring.policy_id,
            version=scoring.version,
            name=scoring.name,
        ),
    )


def result_to_dto(result: BacktestResult) -> BacktestResultDto:
    c = result.configuration
    provenance = ProvenanceDto(
        dataset_id=c.dataset_id,
        dataset_schema_version=c.dataset_schema_version,
        dataset_checksum=c.dataset_checksum,
        strategy_definition_id=c.strategy_definition_id,
        strategy_id=c.strategy_id,
        strategy_version=c.strategy_version,
        contract_version=c.contract_version,
        execution_policy_id=c.execution_policy_id,
        execution_policy_version=c.execution_policy_version,
        execution_config_fingerprint=c.execution_config_fingerprint,
    )
    return BacktestResultDto(
        id=result.id,
        run_id=c.run_id,
        job_id=c.job_id,
        result_checksum=result.result_checksum,
        history_state=result.history_state.value,
        trade_state=result.trade_state.value,
        initial_capital=canonical_decimal(c.initial_capital),
        final_equity=canonical_decimal(result.final_equity),
        signal_count=len(result.signals),
        trade_count=len(result.trades),
        equity_point_count=len(result.equity_curve.points),
        provenance=provenance,
        analysis_type=ANALYSIS_TYPE,
        disclaimer=DISCLAIMER,
    )


def trade_to_dto(value: Trade) -> TradeDto:
    return TradeDto(
        id=value.id,
        sequence=value.sequence,
        entry_signal_id=value.entry_signal_snapshot_id,
        exit_signal_id=value.exit_signal_snapshot_id,
        entry_time=format_utc_millis(value.entry_time),
        exit_time=format_utc_millis(value.exit_time),
        entry_reference_price=canonical_decimal(value.entry_reference_price),
        exit_reference_price=canonical_decimal(value.exit_reference_price),
        entry_price=canonical_decimal(value.entry_price),
        exit_price=canonical_decimal(value.exit_price),
        side=value.side.value,
        quantity=canonical_decimal(value.quantity),
        entry_fee=canonical_decimal(value.entry_fee),
        exit_fee=canonical_decimal(value.exit_fee),
        profit_loss=canonical_decimal(value.profit_loss),
        return_percent=canonical_decimal(value.return_percent),
        close_reason=value.close_reason.value,
    )


def equity_to_dto(value: EquityPoint) -> EquityPointDto:
    return EquityPointDto(
        position=value.position,
        candle_open_time=format_utc_millis(value.candle_open_time),
        valued_at=format_utc_millis(value.valued_at),
        close_price=canonical_decimal(value.close_price),
        cash=canonical_decimal(value.cash),
        quantity=canonical_decimal(value.quantity),
        position_value=canonical_decimal(value.position_value),
        equity=canonical_decimal(value.total_equity),
    )


def evaluation_to_dto(value: EvaluationResult) -> EvaluationResultDto:
    c, m = value.backtest_result.configuration, value.metrics
    metrics = MetricSetDto(
        total_return=canonical_decimal(m.total_return),
        win_rate=canonical_decimal(m.win_rate),
        max_drawdown=canonical_decimal(m.max_drawdown),
        number_of_trades=m.number_of_trades,
        profit_factor=None if m.profit_factor is None else canonical_decimal(m.profit_factor),
        sharpe_ratio=None if m.sharpe_ratio is None else canonical_decimal(m.sharpe_ratio),
    )
    return EvaluationResultDto(
        id=value.id,
        backtest_result_id=value.backtest_result.id,
        job_id=c.job_id,
        run_id=c.run_id,
        strategy_id=c.strategy_id,
        strategy_version=c.strategy_version,
        dataset_id=c.dataset_id,
        pair=c.pair,
        timeframe=c.timeframe.value,
        start_time=format_utc_millis(c.start_time),
        end_time=format_utc_millis(c.end_time),
        execution_config=c.execution_config,
        metrics=metrics,
        score=canonical_decimal(value.score),
        eligible=value.eligible,
        exclusion_reasons=value.exclusion_reasons,
        evaluation_policy_id=value.evaluation_policy_id,
        evaluation_policy_version=value.evaluation_policy_version,
        scoring_policy_id=value.scoring_policy_id,
        scoring_policy_version=value.scoring_policy_version,
        evaluated_at=format_utc_millis(value.evaluated_at),
        content_fingerprint=value.content_fingerprint,
        analysis_type=ANALYSIS_TYPE,
        disclaimer=DISCLAIMER,
    )


def comparison_to_dto(value: EvaluationComparison) -> ComparisonDto:
    return ComparisonDto(
        compatible=value.compatible,
        differences=tuple(
            ContextDifferenceDto(dimension=item.dimension, values=item.values)
            for item in value.differences
        ),
        results=tuple(evaluation_to_dto(item) for item in value.results),
    )
