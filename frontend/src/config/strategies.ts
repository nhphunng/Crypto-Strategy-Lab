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
  ma: {
    friendly: 'Moving Average', tech: 'MA · 1.x', catLabel: 'Trend',
    question: 'Which direction is price generally moving?',
    plain: 'Compares price with its recent moving average to detect strict crossings.',
    short: 'Detects price crossings of its average', abbr: 'MA',
    purpose: 'Detect changes in market direction.', signal: 'hold',
  },
  rsi: {
    friendly: 'RSI', tech: 'RSI · 1.x', catLabel: 'Momentum',
    question: 'How strong is the recent price move?',
    plain: 'Measures recent buying and selling strength with Wilder RSI.',
    short: 'Measures recent buying / selling strength', abbr: 'RSI',
    purpose: 'Gauge whether a move is over-extended.', signal: 'hold',
  },
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
  { id: 'trend', name: 'Trend Starter', ids: ['ma'], tagline: 'A simple way to understand market direction.' },
  {
    id: 'balanced', name: 'Balanced Starter', ids: ['ma', 'rsi'],
    tagline: 'Combines market direction with momentum.', recommended: true,
  },
]

export const STRATEGY_PARAMETER_CONSTRAINTS: ParameterConstraint[] = [
  {
    strategyId: 'rsi', kind: 'lessThan', left: 'lower_threshold', right: 'upper_threshold',
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
  for (const constraint of constraints.filter((item) => item.strategyId === (strategy.strategyId ?? strategy.id))) {
    if (constraint.kind === 'lessThan' && values[constraint.left] >= values[constraint.right]) return constraint.message
  }
  return null
}

export function strategyPresentation(strategy: Strategy): StrategyPresentation {
  const canonicalId = strategy.strategyId ?? strategy.id
  const curated = STRATEGY_PRESENTATION[canonicalId] ?? STRATEGY_PRESENTATION[strategy.id]
  if (curated) return { ...curated, tech: `${strategy.name} · ${strategy.version}` }
  const words = strategy.name.trim().split(/\s+/)
  const abbr = words.map((word) => word[0]).join('').slice(0, 5).toUpperCase() || 'GEN'
  const generated = strategy.origin === 'LLM_GENERATED'
  return {
    friendly: strategy.name,
    tech: `${strategy.strategyType ?? 'Strategy'} · ${strategy.version}`,
    catLabel: generated ? 'Generated' : strategy.category,
    question: `How does ${strategy.name} interpret this market?`,
    plain: generated
      ? 'An approved LLM-generated strategy loaded from the immutable system catalog.'
      : 'A registered strategy loaded from the system catalog.',
    short: generated ? 'Approved generated strategy' : 'Registered strategy',
    abbr,
    purpose: 'Apply the registered parameter schema to later analysis workflows.',
    signal: 'hold',
  }
}

export function validateStrategyWeights(selected: string[], weights: Record<string, number>) {
  const total = selected.reduce((sum, id) => sum + (Number.isFinite(weights[id]) ? weights[id] : 0), 0)
  return { total, valid: selected.length > 0 && total === 100 }
}
