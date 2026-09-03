"""Read-only sentiment series for a trading pair, for the NewsSentimentStrategy.

Maps a market pair symbol (e.g. "BTCUSDT") to the coin code stored on News
items (e.g. "BTC") by stripping a known quote-currency suffix -- this is a
plain pair-symbol split, unrelated to ``domain.news.coin_resolution``'s
free-text keyword matching over article bodies.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from crypto_lab.application.sentiment.context_reader import SentimentDataPoint
from crypto_lab.domain.sentiment.model import ModelRef, SentimentLabel, SentimentStatus
from crypto_lab.infrastructure.persistence.news_models import NewsItemRow
from crypto_lab.infrastructure.persistence.sentiment_models import NewsSentimentAnalysisRow

_QUOTE_SUFFIXES: tuple[str, ...] = ("USDT", "BUSD", "USDC", "USD")


def _coin_from_pair(pair: str) -> str:
    for suffix in _QUOTE_SUFFIXES:
        if pair.endswith(suffix) and len(pair) > len(suffix):
            return pair[: -len(suffix)]
    return pair


class SqlAlchemySentimentContextReader:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def series(
        self,
        pair: str,
        start_time: datetime,
        end_time: datetime,
        model: ModelRef,
    ) -> tuple[SentimentDataPoint, ...]:
        coin = _coin_from_pair(pair)
        analysis = NewsSentimentAnalysisRow
        news = NewsItemRow
        # Return version history through the decision boundary. The strategy
        # chooses the latest version available at EACH candle, not today's latest.
        statement = (
            select(
                news.published_at,
                analysis.analyzed_at,
                analysis.label,
                analysis.score,
                news.id,
                analysis.id,
                analysis.content_fingerprint,
            )
            .select_from(news)
            .join(analysis, analysis.news_id == news.id)
            .where(
                analysis.model_id == model.model_id,
                analysis.model_version == model.model_version,
                analysis.status == SentimentStatus.COMPLETED.value,
                analysis.analyzed_at <= end_time,
                news.related_coins.any(coin),  # type: ignore[arg-type]
                news.published_at >= start_time,
                news.published_at <= end_time,
            )
            .order_by(news.published_at.asc(), news.id, analysis.analyzed_at, analysis.id)
        )
        async with self._sessions() as session:
            rows = (await session.execute(statement)).all()
        return tuple(
            SentimentDataPoint(
                published_at=published_at,
                analyzed_at=analyzed_at,
                signed_score=_signed_score(SentimentLabel(label), score),
                news_id=str(news_id),
                analysis_id=str(analysis_id),
                content_fingerprint=fingerprint,
            )
            for published_at, analyzed_at, label, score, news_id, analysis_id, fingerprint in rows
        )


def _signed_score(label: SentimentLabel, score: Decimal) -> Decimal:
    if label is SentimentLabel.POSITIVE:
        return score
    if label is SentimentLabel.NEGATIVE:
        return -score
    return Decimal("0")


__all__ = ["SqlAlchemySentimentContextReader"]
