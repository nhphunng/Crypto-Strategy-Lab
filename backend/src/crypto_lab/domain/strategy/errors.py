from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCategory(StrEnum):
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    INVALID_CONTEXT = "INVALID_CONTEXT"
    UNKNOWN_STRATEGY = "UNKNOWN_STRATEGY"
    DUPLICATE_STRATEGY_ENTRY = "DUPLICATE_STRATEGY_ENTRY"
    INVALID_STRATEGY_METADATA = "INVALID_STRATEGY_METADATA"
    INCOMPATIBLE_CONTRACT_VERSION = "INCOMPATIBLE_CONTRACT_VERSION"
    STRATEGY_VERSION_UNAVAILABLE = "STRATEGY_VERSION_UNAVAILABLE"
    STRATEGY_VERSION_DEPRECATED = "STRATEGY_VERSION_DEPRECATED"
    STRATEGY_INTENT_UNRESOLVED = "STRATEGY_INTENT_UNRESOLVED"
    SOURCE_ACCESS_DENIED = "SOURCE_ACCESS_DENIED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    GENERATION_FAILED = "GENERATION_FAILED"
    STRATEGY_RULES_INCOMPLETE = "STRATEGY_RULES_INCOMPLETE"
    GENERATED_ARTIFACT_INVALID = "GENERATED_ARTIFACT_INVALID"
    ACTIVATION_NOT_ALLOWED = "ACTIVATION_NOT_ALLOWED"


@dataclass(frozen=True, slots=True)
class ErrorIssue:
    field: str | None
    code: str
    message: str


class StrategyError(Exception):
    __slots__ = ("_category", "_issues")

    def __init__(
        self, category: ErrorCategory, message: str, issues: tuple[ErrorIssue, ...] = ()
    ) -> None:
        super().__init__(message)
        self._category = category
        self._issues = tuple(issues)

    @property
    def category(self) -> ErrorCategory:
        return self._category

    @property
    def issues(self) -> tuple[ErrorIssue, ...]:
        return self._issues
