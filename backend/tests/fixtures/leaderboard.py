"""Deterministic TV5 fixture: 13 evaluations, a tie, a no-trade, and markers.

The fixture writes only immutable upstream records (dataset, strategy, run,
result, signals, trades, policies, evaluations). The leaderboard projection is
always derived by the feature under test, never seeded directly.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_lab.infrastructure.persistence.backtest_models import (
    BacktestEquityPointRow,
    BacktestResultRow,
    BacktestRunRow,
    BacktestSignalSnapshotRow,
    BacktestTradeRow,
    ExecutionPolicyRow,
)
from crypto_lab.infrastructure.persistence.evaluation_models import (
    EvaluationPolicyRow,
    EvaluationResultRow,
    ScoringPolicyRow,
)
from crypto_lab.infrastructure.persistence.models import (
    CandleDatasetMemberRow,
    CandleDatasetRow,
    CandleRow,
)
from crypto_lab.infrastructure.persistence.strategy_models import StrategyDefinitionRow

NAMESPACE = UUID("11111111-2222-3333-4444-555555555555")
PROVIDER = "BINANCE"
PAIR = "BTCUSDT"
TIMEFRAME = "15m"
INTERVAL = timedelta(minutes=15)
CANDLE_COUNT = 192
START = datetime(2026, 7, 1, 0, 0, tzinfo=UTC)
SCORING_POLICY_ID = "balanced"
SCORING_POLICY_VERSION = "2"
EVALUATION_POLICY_VERSION = "1"

TRUNCATE = text(
    "TRUNCATE leaderboard_update_records, leaderboard_entries, leaderboards, "
    "evaluation_results, evaluation_policies, scoring_policies, "
    "backtest_equity_points, backtest_trades, backtest_signal_snapshots, "
    "backtest_results, backtest_runs, execution_policies, strategy_definitions, "
    "candle_dataset_members, candle_datasets, candles CASCADE"
)


def _uuid(label: str) -> UUID:
    return uuid5(NAMESPACE, label)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    """One deterministic evaluated candidate."""

    index: int
    strategy_id: str
    score: Decimal
    total_return: Decimal
    win_rate: Decimal
    max_drawdown: Decimal
    trade_count: int
    sharpe_ratio: Decimal | None
    eligible: bool = True
    exclusion_reasons: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"candidate-{self.index:02d}"

    @property
    def evaluation_id(self) -> UUID:
        return _uuid(f"evaluation-{self.index:02d}")


CANDIDATES: tuple[CandidateSpec, ...] = (
    CandidateSpec(
        0,
        "ma-rsi-sr",
        Decimal("92.5"),
        Decimal("38.4"),
        Decimal("62.5"),
        Decimal("11.2"),
        4,
        Decimal("2.10"),
    ),
    CandidateSpec(
        1,
        "ma-cross",
        Decimal("88.0"),
        Decimal("31.7"),
        Decimal("59.0"),
        Decimal("13.4"),
        3,
        Decimal("1.84"),
    ),
    CandidateSpec(
        2,
        "rsi-reversal",
        Decimal("85.25"),
        Decimal("28.9"),
        Decimal("57.5"),
        Decimal("14.8"),
        3,
        Decimal("1.62"),
    ),
    # Deterministic tie on OVERALL_SCORE resolved by the policy tie-breakers.
    CandidateSpec(
        3,
        "sr-breakout",
        Decimal("80.0"),
        Decimal("26.5"),
        Decimal("55.0"),
        Decimal("16.0"),
        3,
        Decimal("1.40"),
    ),
    CandidateSpec(
        4,
        "ma-rsi",
        Decimal("80.0"),
        Decimal("24.1"),
        Decimal("54.0"),
        Decimal("15.5"),
        3,
        Decimal("1.38"),
    ),
    CandidateSpec(
        5,
        "rsi-trend",
        Decimal("76.5"),
        Decimal("21.8"),
        Decimal("52.5"),
        Decimal("17.9"),
        2,
        Decimal("1.21"),
    ),
    # Sharpe Ratio is undefined for this candidate and must never rank as superior.
    CandidateSpec(
        6, "sr-range", Decimal("72.0"), Decimal("19.4"), Decimal("51.0"), Decimal("18.6"), 2, None
    ),
    CandidateSpec(
        7,
        "ma-slow",
        Decimal("68.75"),
        Decimal("16.2"),
        Decimal("49.5"),
        Decimal("19.3"),
        2,
        Decimal("0.94"),
    ),
    # No-trade result: metrics are zero and the state must stay explicit.
    CandidateSpec(
        8, "rsi-strict", Decimal("64.0"), Decimal("0"), Decimal("0"), Decimal("0"), 0, None
    ),
    CandidateSpec(
        9,
        "ma-fast",
        Decimal("60.5"),
        Decimal("11.7"),
        Decimal("46.0"),
        Decimal("21.4"),
        2,
        Decimal("0.71"),
    ),
    CandidateSpec(
        10,
        "sr-tight",
        Decimal("55.25"),
        Decimal("8.3"),
        Decimal("44.5"),
        Decimal("23.7"),
        1,
        Decimal("0.55"),
    ),
    CandidateSpec(
        11,
        "rsi-loose",
        Decimal("50.0"),
        Decimal("5.1"),
        Decimal("42.0"),
        Decimal("25.9"),
        1,
        Decimal("0.32"),
    ),
    # Upstream-ineligible: the highest score must still never enter Top-K.
    CandidateSpec(
        12,
        "ma-unstable",
        Decimal("99.0"),
        Decimal("61.2"),
        Decimal("70.0"),
        Decimal("9.1"),
        2,
        Decimal("3.10"),
        eligible=False,
        exclusion_reasons=("INSUFFICIENT_HISTORY",),
    ),
)


@dataclass(slots=True)
class LeaderboardFixture:
    """Identifiers the acceptance tests assert against."""

    scoring_policy_id: str = SCORING_POLICY_ID
    scoring_policy_version: str = SCORING_POLICY_VERSION
    pair: str = PAIR
    timeframe: str = TIMEFRAME
    dataset_id: UUID = field(default_factory=lambda: _uuid("dataset"))
    start_time: datetime = START
    end_time: datetime = START + INTERVAL * CANDLE_COUNT
    candidates: tuple[CandidateSpec, ...] = CANDIDATES

    @property
    def top_one_evaluation_id(self) -> UUID:
        return CANDIDATES[0].evaluation_id

    @property
    def tie_evaluation_ids(self) -> tuple[UUID, UUID]:
        return CANDIDATES[3].evaluation_id, CANDIDATES[4].evaluation_id

    @property
    def no_trade_evaluation_id(self) -> UUID:
        return CANDIDATES[8].evaluation_id

    @property
    def ineligible_evaluation_id(self) -> UUID:
        return CANDIDATES[12].evaluation_id

    @property
    def expected_top_ten(self) -> tuple[UUID, ...]:
        return tuple(spec.evaluation_id for spec in CANDIDATES[:10])

    def run_id(self, index: int) -> UUID:
        return _uuid(f"run-{index:02d}")

    def candle_open_time(self, index: int) -> datetime:
        return START + INTERVAL * index


async def seed_leaderboard_fixture(session: AsyncSession) -> LeaderboardFixture:
    """Insert the complete deterministic upstream fixture."""

    fixture = LeaderboardFixture()
    await _seed_candles(session)
    await _seed_dataset(session)
    execution_policy_id = await _seed_policies(session)
    for spec in CANDIDATES:
        await _seed_candidate(session, spec, execution_policy_id)
    await session.flush()
    return fixture


async def reset_leaderboard_fixture(session: AsyncSession) -> None:
    await session.execute(TRUNCATE)


async def _seed_candles(session: AsyncSession) -> None:
    created = datetime(2026, 7, 3, tzinfo=UTC)
    for index in range(CANDLE_COUNT):
        open_time = START + INTERVAL * index
        base = Decimal(100_000) + Decimal(index) * Decimal("25.5")
        session.add(
            CandleRow(
                id=_uuid(f"candle-{index:04d}"),
                provider=PROVIDER,
                pair=PAIR,
                timeframe=TIMEFRAME,
                open_time=open_time,
                close_time=open_time + INTERVAL - timedelta(milliseconds=1),
                open=base,
                high=base + Decimal("120"),
                low=base - Decimal("120"),
                close=base + Decimal("40"),
                volume=Decimal("12.5") + Decimal(index % 7),
                closed=True,
                received_at=created,
                content_hash=_hash(f"candle-{index:04d}"),
                created_at=created,
            )
        )
    await session.flush()


async def _seed_dataset(session: AsyncSession) -> None:
    created = datetime(2026, 7, 3, tzinfo=UTC)
    dataset_id = _uuid("dataset")
    session.add(
        CandleDatasetRow(
            id=dataset_id,
            request_key=_hash("dataset-request"),
            schema_version="1",
            provider=PROVIDER,
            pair=PAIR,
            timeframe=TIMEFRAME,
            start_time=START,
            end_time=START + INTERVAL * CANDLE_COUNT,
            status="COMPLETE",
            candle_count=CANDLE_COUNT,
            checksum=_hash("dataset-checksum"),
            build_token=None,
            lease_expires_at=None,
            failure_code=None,
            created_at=created,
            updated_at=created,
            completed_at=created,
        )
    )
    await session.flush()
    for index in range(CANDLE_COUNT):
        session.add(
            CandleDatasetMemberRow(
                dataset_id=dataset_id,
                position=index,
                candle_id=_uuid(f"candle-{index:04d}"),
            )
        )
    await session.flush()


async def _seed_policies(session: AsyncSession) -> UUID:
    created = datetime(2026, 7, 3, tzinfo=UTC)
    execution_policy_id = _uuid("execution-policy")
    session.add(
        ExecutionPolicyRow(
            id=execution_policy_id,
            policy_id="spot-long-only",
            version="1",
            fingerprint=_hash("execution-policy"),
            rules={"feeRate": "0.0004", "slippageRate": "0.0002"},
            created_at=created,
        )
    )
    session.add(
        EvaluationPolicyRow(
            id=_uuid("evaluation-policy"),
            policy_id="standard",
            version=EVALUATION_POLICY_VERSION,
            fingerprint=_hash("evaluation-policy"),
            rules={"requireClosedTrades": True},
            created_at=created,
        )
    )
    session.add(
        ScoringPolicyRow(
            id=_uuid("scoring-policy"),
            policy_id=SCORING_POLICY_ID,
            version=SCORING_POLICY_VERSION,
            name="Balanced v2",
            default_rank_metric="OVERALL_SCORE",
            fingerprint=_hash("scoring-policy"),
            rules={
                "metricDirections": {
                    "OVERALL_SCORE": "DESC",
                    "TOTAL_RETURN": "DESC",
                    "WIN_RATE": "DESC",
                    "MAX_DRAWDOWN": "ASC",
                    "SHARPE_RATIO": "DESC",
                },
                "tieBreakers": [
                    "OVERALL_SCORE",
                    "TOTAL_RETURN",
                    "MAX_DRAWDOWN",
                    "NUMBER_OF_TRADES",
                ],
                "eligibilityRules": {"excludeNoTrade": False},
                "weights": {
                    "totalReturn": "0.4",
                    "winRate": "0.2",
                    "maxDrawdown": "0.2",
                    "sharpeRatio": "0.2",
                },
            },
            created_at=created,
        )
    )
    await session.flush()
    return execution_policy_id


async def _seed_candidate(
    session: AsyncSession,
    spec: CandidateSpec,
    execution_policy_id: UUID,
) -> None:
    created = datetime(2026, 7, 3, tzinfo=UTC) + timedelta(minutes=spec.index)
    definition_id = _uuid(f"strategy-{spec.index:02d}")
    run_id = _uuid(f"run-{spec.index:02d}")
    result_id = _uuid(f"result-{spec.index:02d}")
    job_id = _uuid(f"job-{spec.index:02d}")
    end_time = START + INTERVAL * CANDLE_COUNT
    execution_config = {
        "initialCapital": "10000",
        "feeRate": "0.0004",
        "slippageRate": "0.0002",
        "positionSizing": "FULL_EQUITY",
    }

    session.add(
        StrategyDefinitionRow(
            id=definition_id,
            strategy_id=spec.strategy_id,
            strategy_type="COMPOSITE" if "-" in spec.strategy_id else "SINGLE",
            strategy_version="3",
            contract_version="1",
            parameters={
                "displayName": spec.strategy_id.replace("-", " ").upper(),
                "members": [
                    {"strategyId": part, "strategyVersion": "3", "displayName": part.upper()}
                    for part in spec.strategy_id.split("-")
                ],
                "decision": {
                    "method": "WEIGHTED",
                    "buyThreshold": "0.30",
                    "sellThreshold": "-0.30",
                },
            },
            parameter_schema_fingerprint=_hash(f"schema-{spec.index:02d}"),
            content_fingerprint=_hash(f"definition-{spec.index:02d}"),
            created_at=created,
        )
    )
    await session.flush()
    session.add(
        BacktestRunRow(
            id=run_id,
            job_id=job_id,
            status="COMPLETED",
            dataset_id=_uuid("dataset"),
            dataset_schema_version="1",
            dataset_checksum=_hash("dataset-checksum"),
            provider=PROVIDER,
            pair=PAIR,
            timeframe=TIMEFRAME,
            start_time=START,
            end_time=end_time,
            strategy_definition_id=definition_id,
            strategy_id=spec.strategy_id,
            strategy_version="3",
            contract_version="1",
            parameter_fingerprint=_hash(f"parameters-{spec.index:02d}"),
            context_fingerprint=_hash(f"context-{spec.index:02d}"),
            execution_policy_id=execution_policy_id,
            execution_policy_version="1",
            initial_capital=Decimal("10000"),
            fee_rate=Decimal("0.0004"),
            slippage_rate=Decimal("0.0002"),
            random_seed=424242,
            requested_at=created,
            started_at=created,
            completed_at=created + timedelta(seconds=30),
            failure_code=None,
        )
    )
    await session.flush()
    signal_count = spec.trade_count * 2 + (2 if spec.trade_count == 0 else 1)
    session.add(
        BacktestResultRow(
            id=result_id,
            run_id=run_id,
            job_id=job_id,
            input_fingerprint=_hash(f"input-{spec.index:02d}"),
            result_checksum=_hash(f"checksum-{spec.index:02d}"),
            history_state="EVALUABLE",
            trade_state="NO_TRADES" if spec.trade_count == 0 else "HAS_TRADES",
            initial_capital=Decimal("10000"),
            final_equity=Decimal("10000") + spec.total_return * Decimal("100"),
            signal_count=signal_count,
            trade_count=spec.trade_count,
            equity_point_count=2,
            execution_duration_ms=1200 + spec.index,
            dataset_id=_uuid("dataset"),
            dataset_checksum=_hash("dataset-checksum"),
            strategy_definition_id=definition_id,
            execution_policy_id=execution_policy_id,
            execution_policy_version="1",
            execution_config_fingerprint=_hash("execution-config"),
            created_at=created,
        )
    )
    await session.flush()

    signal_ids = await _seed_signals(session, spec, result_id, definition_id)
    await _seed_trades(session, spec, result_id, signal_ids)
    await _seed_equity(session, spec, result_id)

    session.add(
        EvaluationResultRow(
            id=spec.evaluation_id,
            backtest_result_id=result_id,
            job_id=job_id,
            run_id=run_id,
            strategy_definition_id=definition_id,
            strategy_id=spec.strategy_id,
            strategy_version="3",
            dataset_id=_uuid("dataset"),
            dataset_checksum=_hash("dataset-checksum"),
            pair=PAIR,
            timeframe=TIMEFRAME,
            start_time=START,
            end_time=end_time,
            execution_policy_id=execution_policy_id,
            execution_policy_version="1",
            execution_config_fingerprint=_hash("execution-config"),
            execution_config=execution_config,
            evaluation_policy_id=_uuid("evaluation-policy"),
            evaluation_policy_version=EVALUATION_POLICY_VERSION,
            scoring_policy_id=_uuid("scoring-policy"),
            scoring_policy_version=SCORING_POLICY_VERSION,
            total_return=spec.total_return,
            win_rate=spec.win_rate,
            max_drawdown=spec.max_drawdown,
            number_of_trades=spec.trade_count,
            profit_factor=None if spec.trade_count == 0 else Decimal("1.6"),
            sharpe_ratio=spec.sharpe_ratio,
            score=spec.score,
            eligible=spec.eligible,
            exclusion_reasons=list(spec.exclusion_reasons),
            content_fingerprint=_hash(f"evaluation-{spec.index:02d}"),
            evaluated_at=created + timedelta(seconds=45),
        )
    )
    await session.flush()


async def _seed_signals(
    session: AsyncSession,
    spec: CandidateSpec,
    result_id: UUID,
    definition_id: UUID,
) -> list[UUID]:
    """Buy/Sell pairs per Trade, one Hold, and one deliberately unaligned Signal."""

    identifiers: list[UUID] = []
    sequence = 0

    def add(action: str, offset_index: int, unaligned: bool = False) -> UUID:
        nonlocal sequence
        signal_id = _uuid(f"signal-{spec.index:02d}-{sequence:02d}")
        timestamp = START + INTERVAL * offset_index
        if unaligned:
            timestamp += timedelta(minutes=7)
        session.add(
            BacktestSignalSnapshotRow(
                id=signal_id,
                backtest_result_id=result_id,
                source_signal_id=f"{spec.strategy_id}-{sequence:02d}",
                sequence=sequence,
                timestamp=timestamp,
                action=action,
                phase="EVALUATED",
                strength=Decimal("0.55"),
                reason="threshold crossed",
                strategy_definition_id=definition_id,
                strategy_id=spec.strategy_id,
                strategy_version="3",
                contract_version="1",
                dataset_id=_uuid("dataset"),
                dataset_schema_version="1",
                dataset_checksum=_hash("dataset-checksum"),
                analysis_result_fingerprint=_hash(f"analysis-{spec.index:02d}-{sequence:02d}"),
            )
        )
        sequence += 1
        return signal_id

    for trade_index in range(spec.trade_count):
        entry_index = 10 + trade_index * 12 + spec.index
        identifiers.append(add("BUY", entry_index))
        identifiers.append(add("SELL", entry_index + 6))
    add("HOLD", 5 + spec.index)
    if spec.trade_count == 0:
        add("HOLD", 9 + spec.index)
    if spec.index == 0:
        # Partial-marker case: this Signal has no Candle at its timestamp.
        add("BUY", 30, unaligned=True)
    await session.flush()
    return identifiers


async def _seed_trades(
    session: AsyncSession,
    spec: CandidateSpec,
    result_id: UUID,
    signal_ids: list[UUID],
) -> None:
    for trade_index in range(spec.trade_count):
        entry_index = 10 + trade_index * 12 + spec.index
        exit_index = entry_index + 6
        entry_price = Decimal(100_000) + Decimal(entry_index) * Decimal("25.5") + Decimal("40")
        exit_price = Decimal(100_000) + Decimal(exit_index) * Decimal("25.5") + Decimal("40")
        quantity = Decimal("0.05")
        profit_loss = (exit_price - entry_price) * quantity
        session.add(
            BacktestTradeRow(
                id=_uuid(f"trade-{spec.index:02d}-{trade_index:02d}"),
                backtest_result_id=result_id,
                sequence=trade_index,
                entry_signal_snapshot_id=signal_ids[trade_index * 2],
                exit_signal_snapshot_id=signal_ids[trade_index * 2 + 1],
                entry_time=START + INTERVAL * entry_index,
                exit_time=START + INTERVAL * exit_index,
                entry_reference_price=entry_price,
                exit_reference_price=exit_price,
                entry_price=entry_price,
                exit_price=exit_price,
                side="LONG",
                quantity=quantity,
                entry_fee=Decimal("2"),
                exit_fee=Decimal("2"),
                profit_loss=profit_loss,
                return_percent=(exit_price - entry_price) / entry_price * Decimal(100),
                close_reason="SELL_SIGNAL",
            )
        )
    await session.flush()


async def _seed_equity(session: AsyncSession, spec: CandidateSpec, result_id: UUID) -> None:
    for position, index in enumerate((0, CANDLE_COUNT - 1)):
        close_price = Decimal(100_000) + Decimal(index) * Decimal("25.5") + Decimal("40")
        session.add(
            BacktestEquityPointRow(
                id=_uuid(f"equity-{spec.index:02d}-{position}"),
                backtest_result_id=result_id,
                position=position,
                candle_open_time=START + INTERVAL * index,
                valued_at=START + INTERVAL * index,
                cash=Decimal("10000"),
                quantity=Decimal("0"),
                close_price=close_price,
                position_value=Decimal("0"),
                total_equity=Decimal("10000")
                + spec.total_return * Decimal("100") * Decimal(position),
                event_signal_snapshot_id=None,
            )
        )
    await session.flush()


NEWCOMER = CandidateSpec(
    20,
    "ma-rsi-momentum",
    Decimal("95.0"),
    Decimal("44.6"),
    Decimal("64.0"),
    Decimal("10.5"),
    3,
    Decimal("2.35"),
)


async def add_qualifying_candidate(
    session: AsyncSession,
    *,
    index: int = NEWCOMER.index,
    score: Decimal | None = None,
) -> UUID:
    """Complete one more evaluation that must enter the current Top-K."""

    spec = NEWCOMER
    if index != NEWCOMER.index or score is not None:
        spec = replace(
            NEWCOMER,
            index=index,
            score=score if score is not None else NEWCOMER.score,
            strategy_id=f"{NEWCOMER.strategy_id}-{index}",
        )
    await _seed_candidate(session, spec, _uuid("execution-policy"))
    return spec.evaluation_id
