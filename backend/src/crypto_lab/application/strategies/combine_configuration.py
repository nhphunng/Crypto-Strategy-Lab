from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from crypto_lab.application.strategies.analyze_strategy import (
    AnalyzeStrategy,
    AnalyzeStrategyCommand,
)
from crypto_lab.application.strategies.ports import StrategyDefinitionRepository
from crypto_lab.domain.backtest.configuration import canonical_hash
from crypto_lab.domain.strategy.configuration import (
    CombinationMethod,
    SavedStrategyConfiguration,
)
from crypto_lab.domain.strategy.signal import (
    HistoryState,
    Signal,
    SignalAction,
    SignalPhase,
    StrategyAnalysisResult,
)
from crypto_lab.domain.strategy.version import ContractVersionRange


class ConfigurationReader(Protocol):
    async def get_by_root_definition(
        self, definition_id: UUID
    ) -> SavedStrategyConfiguration | None: ...


class ConfiguredStrategyAnalyzer:
    def __init__(
        self,
        service: AnalyzeStrategy,
        configurations: ConfigurationReader,
        definitions: StrategyDefinitionRepository,
    ) -> None:
        self._service = service
        self._configurations = configurations
        self._definitions = definitions

    async def analyze(
        self, definition_id: UUID, dataset_id: UUID, request_id: str
    ) -> StrategyAnalysisResult:
        configuration = await self._configurations.get_by_root_definition(definition_id)
        if configuration is None or configuration.combination is None:
            return await self._execute(definition_id, dataset_id, request_id)
        results = tuple(
            [
                await self._execute(member.definition_id, dataset_id, request_id)
                for member in configuration.members
            ]
        )
        root = await self._definitions.get(configuration.root_definition_id)
        if root is None:
            raise ValueError("composite root strategy definition is unavailable")
        first = results[0]
        provenance = first.context_provenance
        sentiment = tuple(
            item for result in results for item in result.context_provenance.sentiment
        )
        if sentiment:
            provenance = replace(
                provenance,
                context_fingerprint=canonical_hash(
                    [result.context_provenance.context_fingerprint for result in results]
                ),
                sentiment=sentiment,
            )
        signals: list[Signal] = []
        aligned = zip(*(result.signals for result in results), strict=True)
        for sequence, children in enumerate(aligned):
            timestamp = children[0].timestamp
            if any(child.timestamp != timestamp for child in children):
                raise ValueError("composite child signals are not timestamp-aligned")
            if any(child.phase is SignalPhase.WARMUP for child in children):
                action, strength, phase = SignalAction.HOLD, None, SignalPhase.WARMUP
            else:
                action, strength = combine_actions(
                    configuration.combination.method,
                    tuple(child.action for child in children),
                    tuple(member.weight for member in configuration.members),
                    configuration.combination.tie_action,
                    configuration.combination.buy_threshold,
                    configuration.combination.sell_threshold,
                )
                phase = SignalPhase.EVALUATED
            signals.append(
                Signal.create(
                    context_fingerprint=provenance.context_fingerprint,
                    strategy_definition_id=root.id,
                    strategy_id=root.strategy_id,
                    strategy_type=root.strategy_type,
                    strategy_version=root.strategy_version,
                    contract_version=root.contract_version,
                    dataset_id=children[0].dataset_id,
                    dataset_version=children[0].dataset_version,
                    timestamp=timestamp,
                    sequence=sequence,
                    action=action,
                    phase=phase,
                    strength=strength,
                    reason=(
                        "Composite members: " + ", ".join(child.action.value for child in children)
                    ),
                )
            )
        history = (
            HistoryState.EVALUABLE
            if any(signal.phase is SignalPhase.EVALUATED for signal in signals)
            else HistoryState.EMPTY
            if all(result.history_state is HistoryState.EMPTY for result in results)
            else HistoryState.INSUFFICIENT
        )
        return StrategyAnalysisResult(
            strategy_definition=root,
            validated_parameters=root.parameters,
            context_provenance=provenance,
            contract_version=root.contract_version,
            history_state=history,
            signals=tuple(signals),
        )

    async def _execute(
        self, definition_id: UUID, dataset_id: UUID, request_id: str
    ) -> StrategyAnalysisResult:
        return await self._service.execute(
            AnalyzeStrategyCommand(
                request_id,
                definition_id,
                str(dataset_id),
                ContractVersionRange(1, 0, 0),
            )
        )


def combine_actions(
    method: CombinationMethod,
    actions: tuple[SignalAction, ...],
    weights: tuple[Decimal | None, ...],
    tie_action: SignalAction,
    buy_threshold: Decimal,
    sell_threshold: Decimal,
) -> tuple[SignalAction, Decimal]:
    scores: dict[SignalAction, Decimal] = {
        SignalAction.BUY: Decimal("1"),
        SignalAction.HOLD: Decimal("0"),
        SignalAction.SELL: Decimal("-1"),
    }
    if method is CombinationMethod.WEIGHTED:
        if len(weights) != len(actions) or any(weight is None for weight in weights):
            raise ValueError("weighted actions require one weight per action")
        score = Decimal("0")
        for action, weight in zip(actions, weights, strict=True):
            score = score + (weight or Decimal("0")) * scores[action]
        action = (
            SignalAction.BUY
            if score >= buy_threshold
            else SignalAction.SELL
            if score <= sell_threshold
            else SignalAction.HOLD
        )
        return action, score
    counts = {action: actions.count(action) for action in SignalAction}
    highest = max(counts.values())
    winners = tuple(action for action, count in counts.items() if count == highest)
    action = winners[0] if len(winners) == 1 else tie_action
    margin = Decimal(counts[SignalAction.BUY] - counts[SignalAction.SELL]) / Decimal(len(actions))
    return action, margin
