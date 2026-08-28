from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from crypto_lab.domain.market_data.candle import canonical_decimal, format_utc_millis
from crypto_lab.domain.strategy.context import StrategyContext
from crypto_lab.domain.strategy.definition import StrategyDefinition, StrategyOrigin
from crypto_lab.domain.strategy.errors import ErrorCategory, ErrorIssue, StrategyError
from crypto_lab.domain.strategy.generation import GeneratedStrategyArtifact
from crypto_lab.domain.strategy.parameters import ParameterSchema, ValidatedParameterSet
from crypto_lab.domain.strategy.protocol import StrategyCapability, StrategyMetadata
from crypto_lab.domain.strategy.signal import (
    ContextProvenance,
    HistoryState,
    Signal,
    SignalAction,
    SignalPhase,
    StrategyAnalysisResult,
)
from crypto_lab.domain.strategy.version import SemanticVersion
from crypto_lab.infrastructure.sandbox.generated_strategy_runtime import (
    DockerGeneratedStrategyRuntime,
)


class IsolatedGeneratedStrategy:
    def __init__(
        self,
        *,
        strategy_id: str,
        display_name: str,
        strategy_version: SemanticVersion,
        parameter_schema: ParameterSchema,
        artifact: GeneratedStrategyArtifact,
        runtime: DockerGeneratedStrategyRuntime,
        generation_provenance_id: UUID,
    ) -> None:
        self.metadata = StrategyMetadata(
            strategy_id,
            "GENERATED",
            display_name,
            strategy_version,
            artifact.contract_version,
            parameter_schema,
            frozenset({StrategyCapability.REASON}),
            StrategyOrigin.LLM_GENERATED,
            generation_provenance_id,
            artifact.content_fingerprint,
        )
        self._artifact = artifact
        self._runtime = runtime

    def validate_parameters(self, raw: Mapping[str, object]) -> ValidatedParameterSet:
        return self.metadata.parameter_schema.validate(raw)

    async def analyze(
        self, definition: StrategyDefinition, context: StrategyContext
    ) -> StrategyAnalysisResult:
        self._validate_definition(definition)
        payload: dict[str, object] = {
            "contractVersion": str(definition.contract_version),
            "parameters": {
                key: value if isinstance(value, int) else canonical_decimal(value)
                for key, value in definition.parameters.values.items()
            },
            "context": {
                "datasetId": context.dataset_id,
                "datasetVersion": context.dataset_version,
                "provider": context.provider,
                "pair": context.pair,
                "timeframe": context.timeframe.value,
                "rangeStart": format_utc_millis(context.range_start),
                "rangeEnd": format_utc_millis(context.range_end),
                "decisionTimestamp": format_utc_millis(context.decision_timestamp),
                "candles": [
                    {
                        "timestamp": format_utc_millis(candle.open_time),
                        "open": canonical_decimal(candle.open),
                        "high": canonical_decimal(candle.high),
                        "low": canonical_decimal(candle.low),
                        "close": canonical_decimal(candle.close),
                        "volume": canonical_decimal(candle.volume),
                    }
                    for candle in context.candles
                ],
            },
        }
        raw = await self._runtime.execute(self._artifact.source_code, payload)
        raw_signals = raw.get("signals")
        if not isinstance(raw_signals, list) or len(raw_signals) != len(context.candles):
            raise ValueError("generated strategy returned an invalid signal count")
        signals = []
        for index, (item, candle) in enumerate(zip(raw_signals, context.candles, strict=True)):
            if not isinstance(item, dict):
                raise ValueError("generated strategy returned an invalid signal")
            signals.append(
                Signal.create(
                    strategy_definition_id=definition.id,
                    strategy_id=definition.strategy_id,
                    strategy_type=definition.strategy_type,
                    strategy_version=definition.strategy_version,
                    contract_version=definition.contract_version,
                    dataset_id=context.dataset_id,
                    dataset_version=context.dataset_version,
                    context_fingerprint=context.context_fingerprint,
                    timestamp=candle.open_time,
                    sequence=index,
                    action=SignalAction(str(item.get("action"))),
                    phase=SignalPhase(str(item.get("phase"))),
                    reason=str(item["reason"]) if item.get("reason") is not None else None,
                )
            )
        state = (
            HistoryState.EMPTY
            if not signals
            else HistoryState.INSUFFICIENT
            if signals[-1].phase is SignalPhase.WARMUP
            else HistoryState.EVALUABLE
        )
        provenance = ContextProvenance(
            context.dataset_id,
            context.dataset_version,
            context.context_fingerprint,
            context.provider,
            context.pair,
            context.timeframe,
            context.range_start,
            context.range_end,
            context.decision_timestamp,
        )
        return StrategyAnalysisResult(
            definition,
            definition.parameters,
            provenance,
            definition.contract_version,
            state,
            tuple(signals),
        )

    def _validate_definition(self, definition: StrategyDefinition) -> None:
        expected = self.metadata
        mismatches = (
            ("strategyId", definition.strategy_id, expected.strategy_id),
            ("strategyType", definition.strategy_type, expected.strategy_type),
            ("strategyVersion", definition.strategy_version, expected.strategy_version),
            ("contractVersion", definition.contract_version, expected.contract_version),
            ("origin", definition.origin, StrategyOrigin.LLM_GENERATED),
            (
                "generationProvenanceId",
                definition.generation_provenance_id,
                expected.generation_provenance_id,
            ),
            ("generatedArtifactId", definition.generated_artifact_id, self._artifact.id),
            (
                "parameterSchemaFingerprint",
                definition.parameters.schema_fingerprint,
                expected.parameter_schema.fingerprint,
            ),
        )
        issues = tuple(
            ErrorIssue(field, "MISMATCH", f"expected {wanted}, received {actual}")
            for field, actual, wanted in mismatches
            if actual != wanted
        )
        if issues:
            raise StrategyError(
                ErrorCategory.INVALID_STRATEGY_METADATA,
                "generated strategy definition does not match the activated artifact",
                issues,
            )
