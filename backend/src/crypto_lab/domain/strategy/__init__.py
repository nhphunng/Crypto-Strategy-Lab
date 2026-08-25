"""Framework-independent Strategy contract owned by Feature 003."""

from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.errors import ErrorCategory, ErrorIssue, StrategyError
from crypto_lab.domain.strategy.protocol import Strategy, StrategyMetadata
from crypto_lab.domain.strategy.signal import Signal, SignalAction, SignalPhase
from crypto_lab.domain.strategy.version import ContractVersionRange, SemanticVersion

__all__ = [
    "ContractVersionRange",
    "ErrorCategory",
    "ErrorIssue",
    "SemanticVersion",
    "Signal",
    "SignalAction",
    "SignalPhase",
    "Strategy",
    "StrategyDefinition",
    "StrategyError",
    "StrategyMetadata",
    "StrategyOrigin",
]
