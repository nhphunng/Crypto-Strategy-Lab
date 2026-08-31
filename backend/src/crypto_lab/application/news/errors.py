"""Standardized news error codes shared by the REST boundary."""

from __future__ import annotations

from typing import Any

from crypto_lab.application.market_data.errors import ErrorDescriptor

NEWS_COIN_INVALID = "NEWS_COIN_INVALID"
NEWS_RANGE_INVALID = "NEWS_RANGE_INVALID"
NEWS_PAGE_INVALID = "NEWS_PAGE_INVALID"
NEWS_DEPENDENCY_UNAVAILABLE = "NEWS_DEPENDENCY_UNAVAILABLE"


class NewsError(Exception):
    def __init__(self, descriptor: ErrorDescriptor) -> None:
        super().__init__(descriptor.message)
        self.descriptor = descriptor


def coin_invalid(message: str, **details: Any) -> NewsError:
    return NewsError(ErrorDescriptor(NEWS_COIN_INVALID, message, details=details or None))


def range_invalid(message: str, **details: Any) -> NewsError:
    return NewsError(ErrorDescriptor(NEWS_RANGE_INVALID, message, details=details or None))


def page_invalid(message: str, **details: Any) -> NewsError:
    return NewsError(ErrorDescriptor(NEWS_PAGE_INVALID, message, details=details or None))


def dependency_unavailable(**details: Any) -> NewsError:
    return NewsError(
        ErrorDescriptor(
            NEWS_DEPENDENCY_UNAVAILABLE,
            "A required news dependency is unavailable.",
            retryable=True,
            details=details or None,
        )
    )
