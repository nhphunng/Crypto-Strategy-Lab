from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from crypto_lab.domain.strategy.errors import ErrorCategory, ErrorIssue, StrategyError
from crypto_lab.domain.strategy.protocol import Strategy, StrategyMetadata
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion

_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")


class RegistryStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    DEPRECATED = "DEPRECATED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class StrategyRegistryEntry:
    metadata: StrategyMetadata
    status: RegistryStatus
    strategy: Strategy

    @property
    def strategy_id(self) -> str:
        return self.metadata.strategy_id

    @property
    def strategy_version(self) -> SemanticVersion:
        return self.metadata.strategy_version


class StrategyRegistry:
    def __init__(self, supported_contract: ContractVersionRange) -> None:
        self._supported_contract = supported_contract
        self._entries: dict[tuple[str, SemanticVersion], StrategyRegistryEntry] = {}

    def register(
        self, strategy: Strategy, status: RegistryStatus = RegistryStatus.AVAILABLE
    ) -> None:
        self.register_many((strategy,), status=status)

    def register_many(
        self, strategies: tuple[Strategy, ...], status: RegistryStatus = RegistryStatus.AVAILABLE
    ) -> None:
        candidates: list[StrategyRegistryEntry] = []
        seen: set[tuple[str, SemanticVersion]] = set()
        for strategy in strategies:
            metadata = strategy.metadata
            issues = self._metadata_issues(metadata)
            if issues:
                raise StrategyError(
                    ErrorCategory.INVALID_STRATEGY_METADATA,
                    "strategy metadata is invalid",
                    tuple(issues),
                )
            key = (metadata.strategy_id, metadata.strategy_version)
            if key in self._entries or key in seen:
                raise StrategyError(
                    ErrorCategory.DUPLICATE_STRATEGY_ENTRY,
                    "strategy identity is already registered",
                    (ErrorIssue("strategyVersion", "DUPLICATE", f"{key[0]}@{key[1]}"),),
                )
            seen.add(key)
            candidates.append(StrategyRegistryEntry(metadata, status, strategy))
        for entry in candidates:
            self._entries[(entry.strategy_id, entry.strategy_version)] = entry

    def resolve(self, strategy_id: str, strategy_version: SemanticVersion) -> Strategy:
        entry = self._entries.get((strategy_id, strategy_version))
        if entry is None:
            same_id = any(key[0] == strategy_id for key in self._entries)
            category = (
                ErrorCategory.STRATEGY_VERSION_UNAVAILABLE
                if same_id
                else ErrorCategory.UNKNOWN_STRATEGY
            )
            raise StrategyError(category, "exact strategy version is not available")
        if entry.status is RegistryStatus.DEPRECATED:
            raise StrategyError(
                ErrorCategory.STRATEGY_VERSION_DEPRECATED,
                "exact strategy version is deprecated",
            )
        if entry.status is RegistryStatus.UNAVAILABLE:
            raise StrategyError(
                ErrorCategory.STRATEGY_VERSION_UNAVAILABLE,
                "exact strategy version is unavailable",
            )
        return entry.strategy

    def discover(self, status: RegistryStatus | None = None) -> tuple[StrategyRegistryEntry, ...]:
        entries = (
            entry for entry in self._entries.values() if status is None or entry.status is status
        )
        return tuple(sorted(entries, key=lambda item: (item.strategy_id, item.strategy_version)))

    def metadata(
        self, strategy_id: str, strategy_version: SemanticVersion
    ) -> StrategyRegistryEntry:
        entry = self._entries.get((strategy_id, strategy_version))
        if entry is None:
            raise StrategyError(
                ErrorCategory.STRATEGY_VERSION_UNAVAILABLE, "exact metadata is unavailable"
            )
        return entry

    def _metadata_issues(self, metadata: StrategyMetadata) -> list[ErrorIssue]:
        issues = []
        if _ID.fullmatch(metadata.strategy_id) is None:
            issues.append(ErrorIssue("strategyId", "INVALID", "must be a stable lowercase ID"))
        if not metadata.strategy_type or not metadata.display_name:
            issues.append(ErrorIssue("metadata", "REQUIRED", "type and display name are required"))
        if not self._supported_contract.supports(metadata.contract_version):
            raise StrategyError(
                ErrorCategory.INCOMPATIBLE_CONTRACT_VERSION,
                "strategy contract version is unsupported",
            )
        return issues
