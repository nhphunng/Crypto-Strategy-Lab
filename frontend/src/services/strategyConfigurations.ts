export type SavedConfigurationMember = {
  strategyId: string
  strategyVersion: string
  definitionId: string
  parameters: Record<string, string | number>
  weight: string | null
}

export type SavedStrategyConfiguration = {
  configurationId: string
  configurationKey: string
  configurationVersion: number
  displayName: string
  kind: 'SINGLE' | 'COMPOSITE'
  rootDefinitionId: string
  selection: { provider: string; pair: string; timeframe: string }
  members: SavedConfigurationMember[]
  combination: null | {
    method: 'MAJORITY' | 'WEIGHTED'
    tieAction: 'BUY' | 'SELL' | 'HOLD'
    buyThreshold: string
    sellThreshold: string
  }
  contentFingerprint: string
  createdAt: string
}

export type SaveStrategyConfigurationInput = {
  displayName: string
  selection: { provider: string; pair: string; timeframe: string }
  members: Array<{
    strategyId: string
    strategyVersion: string
    parameters: Record<string, string | number>
    weight?: string
  }>
  combination: null | {
    method: 'MAJORITY' | 'WEIGHTED'
    tieAction: 'BUY' | 'SELL' | 'HOLD'
    buyThreshold: string
    sellThreshold: string
  }
}

export async function saveStrategyConfiguration(
  input: SaveStrategyConfigurationInput,
  signal?: AbortSignal,
): Promise<SavedStrategyConfiguration> {
  const response = await fetch('/api/v1/strategy-configurations', {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
    signal,
  })
  return parseResponse(response)
}

export async function getStrategyConfiguration(
  configurationId: string,
  signal?: AbortSignal,
): Promise<SavedStrategyConfiguration> {
  const response = await fetch(`/api/v1/strategy-configurations/${encodeURIComponent(configurationId)}`, {
    headers: { Accept: 'application/json' },
    signal,
  })
  return parseResponse(response)
}

export async function listStrategyConfigurations(
  signal?: AbortSignal,
): Promise<SavedStrategyConfiguration[]> {
  const response = await fetch('/api/v1/strategy-configurations', {
    headers: { Accept: 'application/json' },
    signal,
  })
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const message = object(body)?.message
    throw new Error(
      typeof message === 'string' ? message : 'Unable to load strategy configurations',
    )
  }
  const data = object(object(body)?.data)
  const configurations = data?.configurations
  if (!Array.isArray(configurations)) {
    throw new Error('Strategy configuration list response is invalid')
  }
  return configurations.map((entry) => {
    const parsed = object(entry)
    if (!parsed || typeof parsed.configurationId !== 'string') {
      throw new Error('Strategy configuration list entry is invalid')
    }
    return parsed as SavedStrategyConfiguration
  })
}

async function parseResponse(response: Response): Promise<SavedStrategyConfiguration> {
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const message = object(body)?.message
    throw new Error(typeof message === 'string' ? message : 'Unable to save the strategy configuration')
  }
  const data = object(object(body)?.data)
  if (!data || typeof data.configurationId !== 'string' || typeof data.rootDefinitionId !== 'string') {
    throw new Error('Strategy configuration response is invalid')
  }
  return data as SavedStrategyConfiguration
}

function object(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null
}
