from __future__ import annotations

from crypto_lab.api.dependencies import BALANCED_SCORING_POLICY, EVALUATION_POLICY
from crypto_lab.api.schemas.backtest_evaluation import evaluation_to_dto
from crypto_lab.domain.backtest.engine import execute_backtest
from crypto_lab.domain.evaluation.metrics import calculate_metrics
from crypto_lab.domain.evaluation.result import create_evaluation_result
from crypto_lab.domain.evaluation.scoring import score_metrics
from tests.fixtures.backtest_evaluation.cross_feature import NOW
from tests.fixtures.backtest_evaluation.scenarios import no_trade


def test_tv5_record_exposes_score_eligibility_nulls_and_provenance() -> None:
    configuration, candles, analysis, execution = no_trade()
    backtest = execute_backtest(configuration, candles, analysis, execution, created_at=NOW)
    metrics = calculate_metrics(backtest)
    outcome = score_metrics(metrics, BALANCED_SCORING_POLICY)
    result = create_evaluation_result(
        backtest,
        EVALUATION_POLICY,
        BALANCED_SCORING_POLICY,
        metrics,
        outcome,
        NOW,
    )
    payload = evaluation_to_dto(result).model_dump(by_alias=True)
    assert payload["analysisType"] == "HISTORICAL_SIMULATION"
    assert payload["metrics"]["profitFactor"] is None
    assert payload["metrics"]["sharpeRatio"] is None
    assert payload["score"] == "0"
    assert payload["eligible"] is False
    assert payload["scoringPolicyVersion"] == BALANCED_SCORING_POLICY.version
    assert payload["executionConfig"]["signalTiming"] == "NEXT_CANDLE_OPEN"
