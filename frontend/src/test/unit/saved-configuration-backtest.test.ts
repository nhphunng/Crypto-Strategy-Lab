import { describe, expect, it } from 'vitest'
import {
  configurationDefinition,
  configurationStrategy,
} from '../../features/backtests/savedConfiguration'
import type { SavedStrategyConfiguration } from '../../services/strategyConfigurations'

const fingerprint = '70f4f6454d91ce9013e24baa2438037d928103fe85ee95006940181234567890'

function configuration(
  overrides: Partial<SavedStrategyConfiguration> = {},
): SavedStrategyConfiguration {
  return {
    configurationId: 'a54e12cf-9968-5e23-aad2-4b1f7a0d2c09',
    configurationKey: 'cfg-ed1f5ab85f1f3c39e19531ce822aaf76',
    configurationVersion: 1,
    displayName: 'Saved strategy',
    kind: 'COMPOSITE',
    rootDefinitionId: '4e547adb-3cc2-40ca-9b12-b3500c09f833',
    selection: { provider: 'BINANCE', pair: 'BTCUSDT', timeframe: '15m' },
    members: [
      {
        strategyId: 'ma',
        strategyVersion: '1.0.0',
        definitionId: '00000000-0000-0000-0000-00000000238d',
        parameters: { period: 20 },
        weight: null,
      },
      {
        strategyId: 'rsi',
        strategyVersion: '1.0.0',
        definitionId: '00000000-0000-0000-0000-00000000238e',
        parameters: { period: 14, lowerThreshold: '30', upperThreshold: '70' },
        weight: null,
      },
    ],
    combination: {
      method: 'MAJORITY',
      tieAction: 'HOLD',
      buyThreshold: '0.3',
      sellThreshold: '-0.3',
    },
    contentFingerprint: fingerprint,
    createdAt: '2026-09-03T00:00:00.000Z',
    ...overrides,
  }
}

describe('saved configuration backtest mapping', () => {
  it('maps a composite to its root definition strategy ID instead of its cfg key', () => {
    const saved = configuration()

    expect(configurationStrategy(saved).strategyId).toBe(`saved:${saved.configurationId}`)
    expect(configurationDefinition(saved).strategyId).toBe(`composite-${fingerprint.slice(0, 54)}`)
    expect(configurationDefinition(saved).strategyId).not.toBe(saved.configurationKey)
  })

  it('keeps the member strategy identity for a single configuration', () => {
    const member = configuration().members[0]
    const saved = configuration({
      kind: 'SINGLE',
      rootDefinitionId: member.definitionId,
      members: [member],
      combination: null,
    })

    expect(configurationDefinition(saved)).toMatchObject({
      definitionId: member.definitionId,
      strategyId: 'ma',
      strategyVersion: '1.0.0',
      parameters: { period: 20 },
    })
  })
})
