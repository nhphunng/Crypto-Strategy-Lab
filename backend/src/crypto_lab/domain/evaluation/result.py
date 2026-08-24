from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid5

from crypto_lab.domain.backtest.configuration import canonical_hash
from crypto_lab.domain.backtest.result import BacktestResult
from crypto_lab.domain.evaluation.metrics import EvaluationMetrics
from crypto_lab.domain.evaluation.policy import EvaluationPolicy, ScoringPolicy
from crypto_lab.domain.evaluation.scoring import ScoreOutcome
from crypto_lab.domain.market_data.candle import canonical_decimal

ANALYSIS_TYPE = "HISTORICAL_SIMULATION"
DISCLAIMER = "Historical simulation for analysis only; not investment advice or guaranteed profit."


@dataclass(frozen=True, slots=True)
class ComparisonContext:
    dataset_id: UUID
    dataset_checksum: str
    pair: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    execution_config_fingerprint: str
    evaluation_policy_version: str
    scoring_policy_version: str


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    id: UUID
    backtest_result: BacktestResult
    evaluation_policy_id: UUID
    evaluation_policy_version: str
    scoring_policy_id: UUID
    scoring_policy_version: str
    metrics: EvaluationMetrics
    score: Decimal
    eligible: bool
    exclusion_reasons: tuple[str, ...]
    content_fingerprint: str
    evaluated_at: datetime

    @property
    def comparison_context(self) -> ComparisonContext:
        config = self.backtest_result.configuration
        return ComparisonContext(
            config.dataset_id,
            config.dataset_checksum,
            config.pair,
            config.timeframe.value,
            config.start_time,
            config.end_time,
            config.execution_config_fingerprint,
            self.evaluation_policy_version,
            self.scoring_policy_version,
        )


def create_evaluation_result(
    backtest: BacktestResult,
    evaluation_policy: EvaluationPolicy,
    scoring_policy: ScoringPolicy,
    metrics: EvaluationMetrics,
    outcome: ScoreOutcome,
    evaluated_at: datetime,
) -> EvaluationResult:
    identity = "|".join(
        (
            str(backtest.id),
            str(evaluation_policy.id),
            evaluation_policy.version,
            str(scoring_policy.id),
            scoring_policy.version,
        )
    )
    result_id = uuid5(backtest.id, identity)
    fingerprint = canonical_hash(
        {
            "backtestResultId": str(backtest.id),
            "evaluationPolicyFingerprint": evaluation_policy.fingerprint,
            "metrics": {
                key: None
                if value is None
                else str(value)
                if isinstance(value, int)
                else canonical_decimal(value)
                for key, value in metrics.values().items()
            },
            "score": canonical_decimal(outcome.score),
            "eligible": outcome.eligible,
            "exclusionReasons": list(outcome.exclusion_reasons),
            "scoringPolicyFingerprint": scoring_policy.fingerprint,
        }
    )
    return EvaluationResult(
        result_id,
        backtest,
        evaluation_policy.id,
        evaluation_policy.version,
        scoring_policy.id,
        scoring_policy.version,
        metrics,
        outcome.score,
        outcome.eligible,
        outcome.exclusion_reasons,
        fingerprint,
        evaluated_at,
    )
