"""Bundle the pinned FinBERT model for offline inference in the API image."""

from __future__ import annotations

import sys

from transformers import AutoModelForSequenceClassification, AutoTokenizer

from crypto_lab.infrastructure.sentiment.finbert_analyzer import MODEL_ID, MODEL_REVISION

if __name__ == "__main__":
    destination = sys.argv[1]
    options = {"revision": MODEL_REVISION, "trust_remote_code": False}
    AutoTokenizer.from_pretrained(MODEL_ID, **options).save_pretrained(destination)
    AutoModelForSequenceClassification.from_pretrained(MODEL_ID, **options).save_pretrained(
        destination
    )
