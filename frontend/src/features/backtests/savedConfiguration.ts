import type { SavedStrategyConfiguration } from '../../services/strategyConfigurations'
import type { BacktestStrategy, StrategyDefinition } from './types'

export function configurationStrategy(
  configuration: SavedStrategyConfiguration,
): BacktestStrategy {
  const single = configuration.kind === 'SINGLE' ? configuration.members[0] : null
  return {
    strategyId: `saved:${configuration.configurationId}`,
    strategyType: configuration.kind,
    displayName: `${configuration.displayName} · config v${configuration.configurationVersion}`,
    strategyVersion: single?.strategyVersion ?? '1.0.0',
    contractVersion: '1.0.0',
    status: 'AVAILABLE',
    origin: 'SAVED_CONFIGURATION',
    parameters: [],
  }
}

export function configurationDefinition(
  configuration: SavedStrategyConfiguration,
): StrategyDefinition {
  const single = configuration.kind === 'SINGLE' ? configuration.members[0] : null
  return {
    definitionId: configuration.rootDefinitionId,
    // cfg-* identifies the saved configuration. Backend provenance identifies
    // a composite root definition by this stable composite-* strategy ID.
    strategyId: single?.strategyId ?? `composite-${configuration.contentFingerprint.slice(0, 54)}`,
    strategyType: configuration.kind,
    strategyVersion: single?.strategyVersion ?? '1.0.0',
    contractVersion: '1.0.0',
    parameters: single?.parameters ?? {},
    parameterSchemaFingerprint: configuration.contentFingerprint,
    contentFingerprint: configuration.contentFingerprint,
    createdAt: configuration.createdAt,
    origin: 'BUILT_IN',
  }
}
