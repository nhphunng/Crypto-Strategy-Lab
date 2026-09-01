from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from crypto_lab.domain.sentiment.analysis import NewsSentimentAnalysis
from crypto_lab.domain.sentiment.model import ModelRef, SentimentLabel, SentimentStatus

ANALYZED_AT = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _completed(**overrides: object) -> NewsSentimentAnalysis:
    values: dict[str, object] = {
        "news_id": UUID(int=1),
        "model_id": "lexicon-sentiment",
        "model_version": "1.0.0",
        "label": SentimentLabel.POSITIVE,
        "score": Decimal("0.5"),
        "analyzed_at": ANALYZED_AT,
        "content_fingerprint": "f" * 64,
        "status": SentimentStatus.COMPLETED,
    }
    values.update(overrides)
    return NewsSentimentAnalysis(**values)  # type: ignore[arg-type]


def test_model_ref_rejects_blank_identity() -> None:
    with pytest.raises(ValueError):
        ModelRef(model_id="  ", model_version="1.0.0")
    with pytest.raises(ValueError):
        ModelRef(model_id="lexicon-sentiment", model_version="")


def test_deterministic_id_given_the_same_identity_tuple() -> None:
    first = _completed()
    second = _completed()

    assert first.id == second.id


def test_id_changes_when_any_identity_component_changes() -> None:
    base = _completed()
    different_model_version = _completed(model_version="2.0.0")
    different_fingerprint = _completed(content_fingerprint="a" * 64)
    different_news_id = _completed(news_id=uuid4())

    ids = {
        base.id,
        different_model_version.id,
        different_fingerprint.id,
        different_news_id.id,
    }
    assert len(ids) == 4


@pytest.mark.parametrize("score", (Decimal("-0.01"), Decimal("1.01")))
def test_score_must_be_within_zero_and_one(score: Decimal) -> None:
    with pytest.raises(ValueError):
        _completed(score=score)


def test_score_bounds_are_inclusive() -> None:
    _completed(score=Decimal("0"))
    _completed(score=Decimal("1"))


def test_completed_analysis_forbids_a_failure_code() -> None:
    with pytest.raises(ValueError):
        _completed(failure_code="SomeError")


def test_failed_analysis_requires_a_non_blank_failure_code() -> None:
    with pytest.raises(ValueError):
        _completed(
            status=SentimentStatus.FAILED,
            label=SentimentLabel.NEUTRAL,
            score=Decimal("0"),
            failure_code=None,
        )
    with pytest.raises(ValueError):
        _completed(
            status=SentimentStatus.FAILED,
            label=SentimentLabel.NEUTRAL,
            score=Decimal("0"),
            failure_code="   ",
        )


def test_failed_analysis_must_use_the_neutral_zero_placeholder() -> None:
    with pytest.raises(ValueError):
        _completed(
            status=SentimentStatus.FAILED,
            label=SentimentLabel.POSITIVE,
            score=Decimal("0"),
            failure_code="TimeoutError",
        )
    with pytest.raises(ValueError):
        _completed(
            status=SentimentStatus.FAILED,
            label=SentimentLabel.NEUTRAL,
            score=Decimal("0.3"),
            failure_code="TimeoutError",
        )


def test_failed_analysis_with_valid_placeholder_is_accepted() -> None:
    failed = _completed(
        status=SentimentStatus.FAILED,
        label=SentimentLabel.NEUTRAL,
        score=Decimal("0"),
        failure_code="TimeoutError",
    )
    assert failed.status is SentimentStatus.FAILED
    assert failed.signed_score == Decimal("0")


def test_analyzed_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError):
        _completed(analyzed_at=datetime(2026, 9, 1, 12, 0))


@pytest.mark.parametrize(
    ("label", "score", "expected"),
    (
        (SentimentLabel.POSITIVE, Decimal("0.75"), Decimal("0.75")),
        (SentimentLabel.NEGATIVE, Decimal("0.6"), Decimal("-0.6")),
        (SentimentLabel.NEUTRAL, Decimal("0"), Decimal("0")),
    ),
)
def test_signed_score_encodes_label_direction(
    label: SentimentLabel, score: Decimal, expected: Decimal
) -> None:
    analysis = _completed(label=label, score=score)
    assert analysis.signed_score == expected
