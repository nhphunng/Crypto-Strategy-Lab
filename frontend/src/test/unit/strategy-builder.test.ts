import { describe, expect, it } from 'vitest'
import {
  recommendedStrategyValues,
  validateStrategyParameters,
  validateStrategyWeights,
} from '../../config'
import { createMockServices } from '../../services/mock/createMockServices'

const catalog = createMockServices().strategies

describe('strategy builder validation', () => {
  it('validates configured bounds and missing values from the method schema', () => {
    const method = catalog.getMethod('ma-cross-v3')!
    expect(validateStrategyParameters(method, { fast: Number.NaN, slow: 50 })).toMatch(/Enter a value/)
    expect(validateStrategyParameters(method, { fast: 1, slow: 50 })).toMatch(/between/)
  })

  it('applies canonical declarative cross-field constraints without page-owned id branches', () => {
    const rsiMock = catalog.getMethod('rsi-reversal-v2')!
    const rsiWithProviderRanges = {
      ...rsiMock,
      strategyId: 'rsi',
      params: rsiMock.params.map((parameter) => ({
        ...parameter,
        key: parameter.key === 'buy' ? 'lower_threshold' : parameter.key === 'sell' ? 'upper_threshold' : parameter.key,
        min: 0,
        max: 100,
      })),
    }
    expect(validateStrategyParameters(rsiWithProviderRanges, { period: 14, lower_threshold: 70, upper_threshold: 30 })).toBe(
      'Oversold level must be below the Overbought level.',
    )
    expect(validateStrategyParameters(rsiWithProviderRanges, recommendedStrategyValues(rsiWithProviderRanges))).toBeNull()
  })

  it('requires selected strategy weights to total exactly 100 percent', () => {
    expect(validateStrategyWeights(['a', 'b'], { a: 50, b: 50 })).toEqual({ total: 100, valid: true })
    expect(validateStrategyWeights(['a', 'b'], { a: 60, b: 30 })).toEqual({ total: 90, valid: false })
  })
})
