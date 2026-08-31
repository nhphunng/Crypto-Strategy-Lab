"""Persistence adapters for backtest, evaluation, and news repositories."""

from crypto_lab.infrastructure.persistence.repositories.news_repository import (
    SqlAlchemyNewsRepository,
)

__all__ = ["SqlAlchemyNewsRepository"]
