from __future__ import annotations

import threading
from decimal import Decimal

import pytest
from tests.unit.sentiment.test_analyze_pending_news import _item

from crypto_lab.infrastructure.sentiment.finbert_analyzer import FinBertSentimentAnalyzer


async def test_inference_maps_confidence_and_runs_off_the_event_loop() -> None:
    analyzer = FinBertSentimentAnalyzer()
    main_thread = threading.get_ident()
    calls = []

    def predict(text, **options):
        assert threading.get_ident() != main_thread
        calls.append((text, options))
        return [{"label": "negative", "score": 0.9234567}]

    analyzer._pipeline = predict
    label, score = await analyzer.analyze(_item(1))
    assert label.value == "NEGATIVE"
    assert score == Decimal("0.923457")
    assert calls == [("Headline 1\nContent 1", {"truncation": True, "max_length": 512})]


@pytest.mark.parametrize("confidence", [float("nan"), -0.1, 1.1])
async def test_invalid_model_confidence_is_rejected(confidence: float) -> None:
    analyzer = FinBertSentimentAnalyzer()
    analyzer._pipeline = lambda *args, **kwargs: [{"label": "positive", "score": confidence}]
    with pytest.raises(ValueError, match="confidence"):
        await analyzer.analyze(_item(1))
