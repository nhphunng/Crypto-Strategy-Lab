import type { Strategy } from '../domain'

export type StrategySignal = 'buy' | 'sell' | 'hold'

export type StrategyPresentation = {
  friendly: string
  tech: string
  catLabel: string
  question: string
  plain: string
  short: string
  abbr: string
  purpose: string
  signal: StrategySignal
}

export type StrategyPreset = {
  id: string
  name: string
  ids: string[]
  tagline: string
  recommended?: boolean
}

export type ParameterConstraint = {
  strategyId: string
  kind: 'lessThan'
  left: string
  right: string
  message: string
}

export const STRATEGY_PRESENTATION: Record<string, StrategyPresentation> = {
  'ma-cross-v3': {
    friendly: 'Moving Average', tech: 'MA Cross · v3', catLabel: 'Trend',
    question: 'Which direction is price generally moving?',
    plain: 'Compares short-term and long-term average prices to detect changes in trend.',
    short: 'Detects general market direction', abbr: 'MA',
    purpose: 'Detect changes in market direction.', signal: 'buy',
  },
  'rsi-reversal-v2': {
    friendly: 'RSI', tech: 'RSI Reversal · v2', catLabel: 'Momentum',
    question: 'How strong is the recent price move?',
    plain: 'Measures recent buying and selling strength.',
    short: 'Measures recent buying / selling strength', abbr: 'RSI',
    purpose: 'Gauge whether a move is over-extended.', signal: 'sell',
  },
  'bb-mean-rev-v1': {
    friendly: 'Bollinger Bands', tech: 'Bollinger · v1', catLabel: 'Volatility',
    question: 'Is price moving unusually far from its recent average?',
    plain: 'Shows when price moves unusually far from its recent average.',
    short: 'Measures how far price stretches from its average', abbr: 'BB',
    purpose: 'Spot stretched, mean-reverting prices.', signal: 'hold',
  },
  'sr-v4': {
    friendly: 'Support / Resistance', tech: 'Support Resistance · v4', catLabel: 'Market Structure',
    question: 'Where has price reacted repeatedly before?',
    plain: 'Highlights price areas where the market reacted before.',
    short: 'Finds important price areas', abbr: 'S/R',
    purpose: 'Locate key price levels.', signal: 'buy',
  },
}

export const STRATEGY_PRESETS: StrategyPreset[] = [
  { id: 'trend', name: 'Trend Starter', ids: ['ma-cross-v3'], tagline: 'A simple way to understand market direction.' },
  {
    id: 'balanced', name: 'Balanced Starter', ids: ['ma-cross-v3', 'rsi-reversal-v2'],
    tagline: 'Combines market direction with momentum.', recommended: true,
  },
  {
    id: 'multi', name: 'Multi-Signal Starter', ids: ['ma-cross-v3', 'rsi-reversal-v2', 'sr-v4'],
    tagline: 'Combines trend, momentum and market structure.',
  },
]

export const STRATEGY_PARAMETER_CONSTRAINTS: ParameterConstraint[] = [
  {
    strategyId: 'ma-cross-v3', kind: 'lessThan', left: 'fast', right: 'slow',
    message: 'Fast MA must be shorter than Slow MA.',
  },
  {
    strategyId: 'rsi-reversal-v2', kind: 'lessThan', left: 'buy', right: 'sell',
    message: 'Oversold level must be below the Overbought level.',
  },
]

export function recommendedStrategyValues(strategy: Strategy) {
  return Object.fromEntries(strategy.params.map((parameter) => [parameter.key, parameter.value])) as Record<string, number>
}

export function validateStrategyParameters(
  strategy: Strategy,
  values: Record<string, number>,
  constraints = STRATEGY_PARAMETER_CONSTRAINTS,
): string | null {
  for (const parameter of strategy.params) {
    const value = values[parameter.key]
    if (value == null || !Number.isFinite(value)) return `Enter a value for ${parameter.label}.`
    if (value < parameter.min || value > parameter.max) {
      return `${parameter.label} must be between ${parameter.min} and ${parameter.max}.`
    }
  }
  for (const constraint of constraints.filter((item) => item.strategyId === strategy.id)) {
    if (constraint.kind === 'lessThan' && values[constraint.left] >= values[constraint.right]) return constraint.message
  }
  return null
}

export function validateStrategyWeights(selected: string[], weights: Record<string, number>) {
  const total = selected.reduce((sum, id) => sum + (Number.isFinite(weights[id]) ? weights[id] : 0), 0)
  return { total, valid: selected.length > 0 && total === 100 }
}
