"""A deterministic, dependency-free lexicon-based sentiment scorer.

This project has no ML/NLP dependencies today (see ``backend/pyproject.toml``);
adding a heavyweight model (transformers/torch/nltk/...) would be a
disproportionate footprint change made unilaterally by this task. Instead this
is a small, transparent keyword-scoring model, versioned like any other model
via ``model_id``/``model_version`` -- it is deliberately simple, not a claim
to state-of-the-art NLP.
"""

from __future__ import annotations

import re
from decimal import Decimal

from crypto_lab.domain.news.item import NewsItem
from crypto_lab.domain.sentiment.model import SentimentLabel

_TOKEN = re.compile(r"[a-z0-9']+")

_POSITIVE_WORDS: frozenset[str] = frozenset(
    {
        "surge",
        "surges",
        "surged",
        "rally",
        "rallies",
        "rallied",
        "bullish",
        "soar",
        "soars",
        "soared",
        "breakout",
        "adopt",
        "adopts",
        "adoption",
        "approve",
        "approves",
        "approved",
        "approval",
        "partnership",
        "partnerships",
        "upgrade",
        "upgrades",
        "upgraded",
        "outperform",
        "outperforms",
        "outperformed",
        "gain",
        "gains",
        "gained",
        "inflow",
        "inflows",
        "milestone",
        "recovery",
        "recovers",
        "optimism",
        "optimistic",
    }
)

_NEGATIVE_WORDS: frozenset[str] = frozenset(
    {
        "crash",
        "crashes",
        "crashed",
        "plunge",
        "plunges",
        "plunged",
        "bearish",
        "selloff",
        "hack",
        "hacks",
        "hacked",
        "exploit",
        "exploits",
        "exploited",
        "lawsuit",
        "lawsuits",
        "ban",
        "bans",
        "banned",
        "collapse",
        "collapses",
        "collapsed",
        "downgrade",
        "downgrades",
        "downgraded",
        "fraud",
        "delist",
        "delists",
        "delisted",
        "outflow",
        "outflows",
        "liquidation",
        "liquidations",
        "liquidated",
        "scam",
        "scams",
        "investigation",
    }
)

# Multi-word phrases are matched as lowercase substrings rather than tokens.
_POSITIVE_PHRASES: tuple[str, ...] = ("record high", "all-time high")
_NEGATIVE_PHRASES: tuple[str, ...] = ("sell-off", "sell off")

_THRESHOLD = Decimal("0.15")
_QUANTUM = Decimal("0.000001")


class LexiconSentimentAnalyzer:
    """Scores a News item by counting positive vs. negative lexicon hits.

    Deterministic: identical input always yields an identical, byte-equal
    output. Never raises for ordinary input -- an item with no lexicon hits
    scores NEUTRAL/0, which is expected and not itself a failure.
    """

    def __init__(self) -> None:
        self.model_id = "lexicon-sentiment"
        self.model_version = "1.0.0"

    async def analyze(self, item: NewsItem) -> tuple[SentimentLabel, Decimal]:
        text = f"{item.title} {item.content}".lower()
        tokens = _TOKEN.findall(text)
        positive_hits = sum(1 for token in tokens if token in _POSITIVE_WORDS)
        positive_hits += sum(1 for phrase in _POSITIVE_PHRASES if phrase in text)
        negative_hits = sum(1 for token in tokens if token in _NEGATIVE_WORDS)
        negative_hits += sum(1 for phrase in _NEGATIVE_PHRASES if phrase in text)

        total_hits = positive_hits + negative_hits
        raw = Decimal(positive_hits - negative_hits) / Decimal(max(1, total_hits))

        if raw > _THRESHOLD:
            label = SentimentLabel.POSITIVE
        elif raw < -_THRESHOLD:
            label = SentimentLabel.NEGATIVE
        else:
            label = SentimentLabel.NEUTRAL

        score = abs(raw).quantize(_QUANTUM)
        return label, score


__all__ = ["LexiconSentimentAnalyzer"]
