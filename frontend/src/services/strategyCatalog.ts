import type { Strategy } from '../domain'

export const STRATEGY_CATALOG_QUERY_KEY = ['strategies', 'available'] as const

export type StrategyParameterDto = {
  name: string
  description: string
  valueType: 'INTEGER' | 'DECIMAL'
  defaultValue: string | number | null
  minimum: string | number | null
  maximum: string | number | null
  required: boolean
}

export type StrategyMetadataDto = {
  strategyId: string
  strategyType: string
  displayName: string
  strategyVersion: string
  contractVersion: string
  status: 'AVAILABLE' | 'DEPRECATED' | 'UNAVAILABLE'
  capabilities: string[]
  origin: 'BUILT_IN' | 'LLM_GENERATED'
  generationProvenanceId: string | null
  generatedArtifactFingerprint: string | null
  parameters: StrategyParameterDto[]
}

type Envelope<T> = {
  success: true
  message: string
  data: T
  timestamp: string
  requestId: string
}

export function strategyCatalogKey(strategyId: string, strategyVersion: string) {
  return `${strategyId}@${strategyVersion}`
}

export function mapStrategyMetadata(metadata: StrategyMetadataDto): Strategy {
  return {
    id: strategyCatalogKey(metadata.strategyId, metadata.strategyVersion),
    strategyId: metadata.strategyId,
    strategyType: metadata.strategyType,
    name: metadata.displayName,
    category: metadata.strategyType,
    version: metadata.strategyVersion,
    contractVersion: metadata.contractVersion,
    origin: metadata.origin,
    capabilities: metadata.capabilities,
    generationProvenanceId: metadata.generationProvenanceId,
    generatedArtifactFingerprint: metadata.generatedArtifactFingerprint,
    summary: metadata.parameters
      .map((parameter) => `${parameter.name} ${parameter.defaultValue ?? 'required'}`)
      .join(' · '),
    status: metadata.status,
    params: metadata.parameters.map((parameter) => ({
      key: parameter.name,
      label: parameter.description || parameter.name,
      value: numericValue(parameter.defaultValue),
      min: numericBound(parameter.minimum, Number.MIN_SAFE_INTEGER),
      max: numericBound(parameter.maximum, Number.MAX_SAFE_INTEGER),
      step: parameter.valueType === 'INTEGER' ? 1 : 0.01,
    })),
    rules: [],
  }
}

export async function discoverStrategies(): Promise<Strategy[]> {
  const response = await fetch('/api/v1/strategies')
  const body: unknown = await response.json()
  if (!response.ok) throw new Error(readApiMessage(body) ?? 'Unable to load the strategy catalog')
  const envelope = parseEnvelope(body)
  return envelope.data.strategies.map(mapStrategyMetadata)
}

function parseEnvelope(value: unknown): Envelope<{ strategies: StrategyMetadataDto[] }> {
  const root = record(value, 'strategy response')
  if (root.success !== true) throw new Error('Strategy response was not successful')
  const data = record(root.data, 'strategy response data')
  if (!Array.isArray(data.strategies)) throw new Error('Strategy response data.strategies must be an array')
  return {
    success: true,
    message: stringValue(root.message, 'message'),
    data: { strategies: data.strategies.map(parseMetadata) },
    timestamp: stringValue(root.timestamp, 'timestamp'),
    requestId: stringValue(root.requestId, 'requestId'),
  }
}

function parseMetadata(value: unknown): StrategyMetadataDto {
  const item = record(value, 'strategy metadata')
  const status = stringValue(item.status, 'status')
  const origin = stringValue(item.origin, 'origin')
  if (!['AVAILABLE', 'DEPRECATED', 'UNAVAILABLE'].includes(status)) {
    throw new Error(`Unsupported strategy status: ${status}`)
  }
  if (!['BUILT_IN', 'LLM_GENERATED'].includes(origin)) {
    throw new Error(`Unsupported strategy origin: ${origin}`)
  }
  if (!Array.isArray(item.capabilities) || !Array.isArray(item.parameters)) {
    throw new Error('Strategy capabilities and parameters must be arrays')
  }
  return {
    strategyId: stringValue(item.strategyId, 'strategyId'),
    strategyType: stringValue(item.strategyType, 'strategyType'),
    displayName: stringValue(item.displayName, 'displayName'),
    strategyVersion: stringValue(item.strategyVersion, 'strategyVersion'),
    contractVersion: stringValue(item.contractVersion, 'contractVersion'),
    status: status as StrategyMetadataDto['status'],
    capabilities: item.capabilities.map((entry) => stringValue(entry, 'capability')),
    origin: origin as StrategyMetadataDto['origin'],
    generationProvenanceId: nullableString(item.generationProvenanceId, 'generationProvenanceId'),
    generatedArtifactFingerprint: nullableString(
      item.generatedArtifactFingerprint,
      'generatedArtifactFingerprint',
    ),
    parameters: item.parameters.map(parseParameter),
  }
}

function parseParameter(value: unknown): StrategyParameterDto {
  const item = record(value, 'strategy parameter')
  const valueType = stringValue(item.valueType, 'valueType')
  if (valueType !== 'INTEGER' && valueType !== 'DECIMAL') {
    throw new Error(`Unsupported strategy parameter type: ${valueType}`)
  }
  if (typeof item.required !== 'boolean') throw new Error('Strategy parameter required must be boolean')
  return {
    name: stringValue(item.name, 'parameter name'),
    description: stringValue(item.description, 'parameter description'),
    valueType,
    defaultValue: nullableScalar(item.defaultValue, 'defaultValue'),
    minimum: nullableScalar(item.minimum, 'minimum'),
    maximum: nullableScalar(item.maximum, 'maximum'),
    required: item.required,
  }
}

function record(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`${label} must be an object`)
  }
  return value as Record<string, unknown>
}

function stringValue(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.length === 0) throw new Error(`${label} must be a non-empty string`)
  return value
}

function nullableString(value: unknown, label: string): string | null {
  return value === null || value === undefined ? null : stringValue(value, label)
}

function nullableScalar(value: unknown, label: string): string | number | null {
  if (value === null || value === undefined) return null
  if (typeof value === 'string' || typeof value === 'number') return value
  throw new Error(`${label} must be a string, number, or null`)
}

function numericValue(value: string | number | null): number {
  if (value === null) return Number.NaN
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : Number.NaN
}

function numericBound(value: string | number | null, fallback: number): number {
  const parsed = numericValue(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function readApiMessage(value: unknown): string | null {
  if (typeof value !== 'object' || value === null) return null
  const message = (value as Record<string, unknown>).message
  return typeof message === 'string' ? message : null
}
