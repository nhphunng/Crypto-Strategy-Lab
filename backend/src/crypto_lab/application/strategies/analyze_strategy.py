from __future__ import annotations

import logging
from dataclasses import dataclass
from inspect import isawaitable
from uuid import UUID

from crypto_lab.application.strategies.ports import (
    NormalizedDatasetReader,
    StrategyDefinitionRepository,
    StrategyResolver,
)
from crypto_lab.domain.strategy.errors import ErrorCategory, ErrorIssue, StrategyError
from crypto_lab.domain.strategy.signal import StrategyAnalysisResult
from crypto_lab.domain.strategy.version import ContractVersionRange

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AnalyzeStrategyCommand:
    request_id: str
    definition_id: UUID
    dataset_id: str
    supported_contract: ContractVersionRange


class AnalyzeStrategy:
    def __init__(
        self,
        definitions: StrategyDefinitionRepository,
        datasets: NormalizedDatasetReader,
        strategies: StrategyResolver,
    ) -> None:
        self._definitions = definitions
        self._datasets = datasets
        self._strategies = strategies

    async def execute(self, command: AnalyzeStrategyCommand) -> StrategyAnalysisResult:
        definition = await self._definitions.get(command.definition_id)
        if definition is None:
            raise StrategyError(
                ErrorCategory.STRATEGY_VERSION_UNAVAILABLE,
                "exact strategy definition is unavailable",
                (ErrorIssue("definitionId", "NOT_FOUND", str(command.definition_id)),),
            )
        if not command.supported_contract.supports(definition.contract_version):
            raise StrategyError(
                ErrorCategory.INCOMPATIBLE_CONTRACT_VERSION,
                "consumer does not support the exact contract version",
            )
        context = await self._datasets.get_strategy_context(command.dataset_id)
        if context is None:
            raise StrategyError(
                ErrorCategory.INVALID_CONTEXT,
                "normalized dataset is unavailable",
                (ErrorIssue("datasetId", "NOT_FOUND", command.dataset_id),),
            )
        strategy = self._strategies.resolve(definition.strategy_id, definition.strategy_version)
        try:
            pending = strategy.analyze(definition, context)
            result = await pending if isawaitable(pending) else pending
        except StrategyError:
            logger.info(
                "strategy_analysis_failed",
                extra={
                    "request_id": command.request_id,
                    "strategy_id": definition.strategy_id,
                    "strategy_version": str(definition.strategy_version),
                    "definition_id": str(definition.id),
                    "dataset_id": context.dataset_id,
                    "dataset_version": context.dataset_version,
                },
            )
            raise
        logger.info(
            "strategy_analysis_succeeded",
            extra={
                "request_id": command.request_id,
                "strategy_id": definition.strategy_id,
                "strategy_version": str(definition.strategy_version),
                "definition_id": str(definition.id),
                "dataset_id": context.dataset_id,
                "dataset_version": context.dataset_version,
            },
        )
        return result
