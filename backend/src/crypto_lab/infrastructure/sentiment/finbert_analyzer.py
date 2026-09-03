"""CPU inference with the pinned, pretrained ProsusAI financial sentiment model.

Loading and inference run off the API event loop. The deployment image bundles
the model; local development downloads the same revision on first use.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from threading import Lock
from typing import Any

from crypto_lab.application.sentiment.errors import SentimentModelUnavailable
from crypto_lab.domain.news.item import NewsItem
from crypto_lab.domain.sentiment.model import SentimentLabel

MODEL_ID = "ProsusAI/finbert"
MODEL_REVISION = "4556d13015211d73dccd3fdd39d39232506f3e43"
# A release identity within the storage contract's 32-character version field.
# The complete immutable upstream revision is always used for model loading.
MODEL_VERSION = "1.0.0+4556d1301521"


class FinBertSentimentAnalyzer:
    model_id = MODEL_ID
    model_version = MODEL_VERSION

    def __init__(self, model_path: str | None = None) -> None:
        self._model_path = model_path
        self._pipeline: Any = None
        self._lock = Lock()

    async def analyze(self, item: NewsItem) -> tuple[SentimentLabel, Decimal]:
        return await asyncio.to_thread(self._analyze, f"{item.title}\n{item.content}")

    def _analyze(self, text: str) -> tuple[SentimentLabel, Decimal]:
        # Serialize CPU work and initialization, including after async cancellation.
        with self._lock:
            if self._pipeline is None:
                try:
                    from transformers import (
                        AutoModelForSequenceClassification,
                        AutoTokenizer,
                        pipeline,
                    )

                    source = self._model_path or MODEL_ID
                    options: dict[str, Any] = {"trust_remote_code": False}
                    if self._model_path:
                        options["local_files_only"] = True
                    else:
                        options["revision"] = MODEL_REVISION
                    tokenizer = AutoTokenizer.from_pretrained(source, **options)
                    model = AutoModelForSequenceClassification.from_pretrained(source, **options)
                    self._pipeline = pipeline(
                        "text-classification", model=model, tokenizer=tokenizer, device=-1
                    )
                except Exception as error:
                    raise SentimentModelUnavailable("FinBERT could not be loaded") from error
            prediction = self._pipeline(text, truncation=True, max_length=512)[0]
            label = SentimentLabel(prediction["label"].upper())
            score = Decimal(str(prediction["score"]))
            if not score.is_finite() or not Decimal(0) <= score <= Decimal(1):
                raise ValueError("Model confidence must be between zero and one")
            return label, score.quantize(Decimal("0.000001"))
