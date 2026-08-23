import { afterEach, describe, expect, it, vi } from 'vitest'
import { discoverStrategies, strategyCatalogKey } from '../../services/strategyCatalog'

const envelope = {
  success: true,
  message: 'Strategies loaded.',
  data: {
    strategies: [
      {
        strategyId: 'ma',
        strategyType: 'MA',
        displayName: 'Moving Average',
        strategyVersion: '1.0.0',
        contractVersion: '1.0.0',
        status: 'AVAILABLE',
        capabilities: ['REASON'],
        origin: 'BUILT_IN',
        generationProvenanceId: null,
        generatedArtifactFingerprint: null,
        parameters: [
          {
            name: 'period',
            description: 'Moving-average period',
            valueType: 'INTEGER',
            defaultValue: 20,
            minimum: 2,
            maximum: 500,
            required: true,
          },
        ],
      },
    ],
  },
  timestamp: '2026-08-23T00:00:00Z',
  requestId: 'request-1',
}

afterEach(() => vi.unstubAllGlobals())

describe('strategy catalog boundary', () => {
  it('maps canonical backend identity and parameter metadata without mock aliases', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(envelope))))
    const strategies = await discoverStrategies()
    expect(fetch).toHaveBeenCalledWith('/api/v1/strategies')
    expect(strategies[0]).toMatchObject({
      id: strategyCatalogKey('ma', '1.0.0'),
      strategyId: 'ma',
      version: '1.0.0',
      origin: 'BUILT_IN',
      params: [{ key: 'period', value: 20, min: 2, max: 500, step: 1 }],
    })
  })

  it('fails closed when backend metadata does not match the runtime contract', async () => {
    const invalid = structuredClone(envelope)
    invalid.data.strategies[0].parameters[0].valueType = 'TEXT'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(invalid))))
    await expect(discoverStrategies()).rejects.toThrow('Unsupported strategy parameter type')
  })
})
