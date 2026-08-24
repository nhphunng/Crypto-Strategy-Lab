"""Standardized leaderboard error codes shared by REST and WebSocket boundaries."""

from __future__ import annotations

from typing import Any

from crypto_lab.application.market_data.errors import ErrorDescriptor

LEADERBOARD_NOT_FOUND = "LEADERBOARD_NOT_FOUND"
LEADERBOARD_ENTRY_NOT_FOUND = "LEADERBOARD_ENTRY_NOT_FOUND"
LEADERBOARD_QUERY_INVALID = "LEADERBOARD_QUERY_INVALID"
LEADERBOARD_RANGE_INVALID = "LEADERBOARD_RANGE_INVALID"
LEADERBOARD_DEPENDENCY_UNAVAILABLE = "LEADERBOARD_DEPENDENCY_UNAVAILABLE"
LEADERBOARD_SUBSCRIPTION_INVALID = "LEADERBOARD_SUBSCRIPTION_INVALID"
LEADERBOARD_SUBSCRIPTION_LIMITED = "LEADERBOARD_SUBSCRIPTION_LIMITED"
LEADERBOARD_EVENT_VERSION_UNSUPPORTED = "LEADERBOARD_EVENT_VERSION_UNSUPPORTED"


class LeaderboardError(Exception):
    def __init__(self, descriptor: ErrorDescriptor) -> None:
        super().__init__(descriptor.message)
        self.descriptor = descriptor


def leaderboard_not_found(**details: Any) -> LeaderboardError:
    return LeaderboardError(
        ErrorDescriptor(
            LEADERBOARD_NOT_FOUND,
            "The requested leaderboard projection does not exist.",
            details=details or None,
        )
    )


def entry_not_found(**details: Any) -> LeaderboardError:
    return LeaderboardError(
        ErrorDescriptor(
            LEADERBOARD_ENTRY_NOT_FOUND,
            "The requested leaderboard entry does not exist.",
            details=details or None,
        )
    )


def query_invalid(message: str, **details: Any) -> LeaderboardError:
    return LeaderboardError(
        ErrorDescriptor(LEADERBOARD_QUERY_INVALID, message, details=details or None)
    )


def range_invalid(message: str, **details: Any) -> LeaderboardError:
    return LeaderboardError(
        ErrorDescriptor(LEADERBOARD_RANGE_INVALID, message, details=details or None)
    )


def dependency_unavailable(**details: Any) -> LeaderboardError:
    return LeaderboardError(
        ErrorDescriptor(
            LEADERBOARD_DEPENDENCY_UNAVAILABLE,
            "A required leaderboard dependency is unavailable.",
            retryable=True,
            details=details or None,
        )
    )
