/**
 * Runtime contract validation for every leaderboard payload.
 *
 * A response that does not match the published contract is rejected instead of
 * being rendered, so a backend change can never silently corrupt the view.
 */

import {
  LEADERBOARD_SORT_FIELDS,
  METRIC_NAMES,
  RANK_METRICS,
  type Availability,
  type Candle,
  type LeaderboardEntry,
  type LeaderboardSnapshot,
  type LeaderboardUpdatedEvent,
  type Marker,
  type MetricDescriptor,
  type MetricSet,
  type Overlay,
  type PageMeta,
  type RankedResultDetail,
  type Trade,
  type TradePage,
  type VisualizationData,
} from './types'

export class ContractError extends Error {
  constructor(readonly path: string, message: string) {
    super(`${path}: ${message}`)
    this.name = 'ContractError'
  }
}

const DECIMAL = /^-?[0-9]+(\.[0-9]+)?$/
const MARKER_TYPES = ['BUY', 'SELL', 'HOLD', 'ENTRY', 'EXIT']
const MARKER_SHAPES = [
  'ARROW_UP',
  'ARROW_DOWN',
  'TRIANGLE_UP',
  'TRIANGLE_DOWN',
  'DIAMOND',
  'DOT',
  'ENTRY_OUTLINED',
  'EXIT_OUTLINED',
]
const OVERLAY_KINDS = ['LINE', 'BAND', 'ZONE']
const AVAILABILITY_STATES = ['AVAILABLE', 'EMPTY', 'PARTIAL', 'UNAVAILABLE']

function record(value: unknown, path: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ContractError(path, 'expected an object')
  }
  return value as Record<string, unknown>
}

function str(value: unknown, path: string): string {
  if (typeof value !== 'string') throw new ContractError(path, 'expected a string')
  return value
}

function optionalStr(value: unknown, path: string): string | null {
  if (value === null || value === undefined) return null
  return str(value, path)
}

function int(value: unknown, path: string): number {
  if (typeof value !== 'number' || !Number.isInteger(value)) {
    throw new ContractError(path, 'expected an integer')
  }
  return value
}

function decimal(value: unknown, path: string): string {
  const raw = str(value, path)
  if (!DECIMAL.test(raw)) throw new ContractError(path, 'expected a decimal string')
  return raw
}

function optionalDecimal(value: unknown, path: string): string | null {
  if (value === null || value === undefined) return null
  return decimal(value, path)
}

function instant(value: unknown, path: string): string {
  const raw = str(value, path)
  if (Number.isNaN(Date.parse(raw))) throw new ContractError(path, 'expected a UTC instant')
  return raw
}

function list(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) throw new ContractError(path, 'expected an array')
  return value
}

function member<T extends string>(value: unknown, allowed: readonly T[], path: string): T {
  const raw = str(value, path)
  if (!allowed.includes(raw as T)) throw new ContractError(path, `unsupported value ${raw}`)
  return raw as T
}

function pageMeta(value: unknown, path: string): PageMeta {
  const raw = record(value, path)
  return {
    page: int(raw.page, `${path}.page`),
    pageSize: int(raw.pageSize, `${path}.pageSize`),
    total: int(raw.total, `${path}.total`),
  }
}

function metricSet(value: unknown, path: string): MetricSet {
  const raw = record(value, path)
  return {
    totalReturn: decimal(raw.totalReturn, `${path}.totalReturn`),
    winRate: decimal(raw.winRate, `${path}.winRate`),
    maxDrawdown: decimal(raw.maxDrawdown, `${path}.maxDrawdown`),
    numberOfTrades: int(raw.numberOfTrades, `${path}.numberOfTrades`),
    sharpeRatio: optionalDecimal(raw.sharpeRatio, `${path}.sharpeRatio`),
  }
}

function metricDescriptor(value: unknown, path: string): MetricDescriptor {
  const raw = record(value, path)
  return {
    metric: member(raw.metric, METRIC_NAMES, `${path}.metric`),
    direction: member(raw.direction, ['ASC', 'DESC'] as const, `${path}.direction`),
    unit: member(raw.unit, ['PERCENT', 'RATIO', 'COUNT', 'SCORE'] as const, `${path}.unit`),
  }
}

export function parseLeaderboardEntry(value: unknown, path = 'entry'): LeaderboardEntry {
  const raw = record(value, path)
  const strategy = record(raw.strategy, `${path}.strategy`)
  return {
    evaluationResultId: str(raw.evaluationResultId, `${path}.evaluationResultId`),
    rank: int(raw.rank, `${path}.rank`),
    projectionVersion: int(raw.projectionVersion, `${path}.projectionVersion`),
    score: decimal(raw.score, `${path}.score`),
    strategy: {
      strategyId: str(strategy.strategyId, `${path}.strategy.strategyId`),
      strategyVersion: str(strategy.strategyVersion, `${path}.strategy.strategyVersion`),
      displayName: str(strategy.displayName, `${path}.strategy.displayName`),
      members: list(strategy.members ?? [], `${path}.strategy.members`).map((item, index) => {
        const memberRaw = record(item, `${path}.strategy.members[${index}]`)
        return {
          strategyId: str(memberRaw.strategyId, `${path}.strategy.members[${index}].strategyId`),
          strategyVersion: str(
            memberRaw.strategyVersion,
            `${path}.strategy.members[${index}].strategyVersion`,
          ),
          displayName: str(
            memberRaw.displayName ?? memberRaw.strategyId,
            `${path}.strategy.members[${index}].displayName`,
          ),
        }
      }),
    },
    pair: str(raw.pair, `${path}.pair`),
    timeframe: str(raw.timeframe, `${path}.timeframe`),
    datasetId: str(raw.datasetId, `${path}.datasetId`),
    startTime: instant(raw.startTime, `${path}.startTime`),
    endTime: instant(raw.endTime, `${path}.endTime`),
    metrics: metricSet(raw.metrics, `${path}.metrics`),
    scoringPolicyId: str(raw.scoringPolicyId, `${path}.scoringPolicyId`),
    scoringPolicyVersion: str(raw.scoringPolicyVersion, `${path}.scoringPolicyVersion`),
    updatedAt: instant(raw.updatedAt, `${path}.updatedAt`),
  }
}

export function parseLeaderboardSnapshot(value: unknown): LeaderboardSnapshot {
  const path = 'snapshot'
  const raw = record(value, path)
  const entries = list(raw.entries, `${path}.entries`).map((item, index) =>
    parseLeaderboardEntry(item, `${path}.entries[${index}]`),
  )
  const k = int(raw.k, `${path}.k`)
  if (entries.length > k) throw new ContractError(`${path}.entries`, 'more entries than K')
  return {
    leaderboardId: str(raw.leaderboardId, `${path}.leaderboardId`),
    scopeKey: str(raw.scopeKey, `${path}.scopeKey`),
    scoringPolicyId: str(raw.scoringPolicyId, `${path}.scoringPolicyId`),
    scoringPolicyVersion: str(raw.scoringPolicyVersion, `${path}.scoringPolicyVersion`),
    rankBy: member(raw.rankBy, RANK_METRICS, `${path}.rankBy`),
    k,
    projectionVersion: int(raw.projectionVersion, `${path}.projectionVersion`),
    updatedAt: instant(raw.updatedAt, `${path}.updatedAt`),
    runState: raw.runState === null || raw.runState === undefined
      ? null
      : member(
          raw.runState,
          ['QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'] as const,
          `${path}.runState`,
        ),
    metricMetadata: list(raw.metricMetadata, `${path}.metricMetadata`).map((item, index) =>
      metricDescriptor(item, `${path}.metricMetadata[${index}]`),
    ),
    entries,
    pagination: pageMeta(raw.pagination, `${path}.pagination`),
    disclaimer: str(raw.disclaimer, `${path}.disclaimer`),
  }
}

function availability(value: unknown, path: string): Availability {
  const raw = record(value, path)
  return {
    state: member(raw.state, AVAILABILITY_STATES, `${path}.state`) as Availability['state'],
    count: int(raw.count ?? 0, `${path}.count`),
    reason: optionalStr(raw.reason, `${path}.reason`),
  }
}

export function parseRankedResultDetail(value: unknown): RankedResultDetail {
  const path = 'rankedResult'
  const raw = record(value, path)
  const provenance = record(raw.provenance, `${path}.provenance`)
  return {
    entry: parseLeaderboardEntry(raw.entry, `${path}.entry`),
    provenance: {
      evaluationResultId: str(
        provenance.evaluationResultId,
        `${path}.provenance.evaluationResultId`,
      ),
      backtestResultId: str(provenance.backtestResultId, `${path}.provenance.backtestResultId`),
      runId: str(provenance.runId, `${path}.provenance.runId`),
      jobId: str(provenance.jobId, `${path}.provenance.jobId`),
      strategyId: str(provenance.strategyId, `${path}.provenance.strategyId`),
      strategyVersion: str(provenance.strategyVersion, `${path}.provenance.strategyVersion`),
      datasetId: str(provenance.datasetId, `${path}.provenance.datasetId`),
      executionConfig: record(
        provenance.executionConfig ?? {},
        `${path}.provenance.executionConfig`,
      ),
      resultChecksum: str(provenance.resultChecksum, `${path}.provenance.resultChecksum`),
      scoringPolicyId: str(provenance.scoringPolicyId, `${path}.provenance.scoringPolicyId`),
      scoringPolicyVersion: str(
        provenance.scoringPolicyVersion,
        `${path}.provenance.scoringPolicyVersion`,
      ),
    },
    candles: availability(raw.candles, `${path}.candles`),
    overlays: availability(raw.overlays, `${path}.overlays`),
    signals: availability(raw.signals, `${path}.signals`),
    trades: availability(raw.trades, `${path}.trades`),
    disclaimer: str(raw.disclaimer, `${path}.disclaimer`),
  }
}

function candle(value: unknown, path: string): Candle {
  const raw = record(value, path)
  return {
    openTime: instant(raw.openTime, `${path}.openTime`),
    open: decimal(raw.open, `${path}.open`),
    high: decimal(raw.high, `${path}.high`),
    low: decimal(raw.low, `${path}.low`),
    close: decimal(raw.close, `${path}.close`),
    volume: decimal(raw.volume, `${path}.volume`),
  }
}

export function parseMarker(value: unknown, path = 'marker'): Marker {
  const raw = record(value, path)
  return {
    id: str(raw.id, `${path}.id`),
    type: member(raw.type, MARKER_TYPES, `${path}.type`) as Marker['type'],
    time: instant(raw.time, `${path}.time`),
    price: optionalDecimal(raw.price, `${path}.price`),
    label: str(raw.label, `${path}.label`),
    shape: member(raw.shape, MARKER_SHAPES, `${path}.shape`) as Marker['shape'],
    tone: raw.tone === null || raw.tone === undefined
      ? null
      : (member(
          raw.tone,
          ['POSITIVE', 'NEGATIVE', 'NEUTRAL', 'INFO'] as const,
          `${path}.tone`,
        ) as Marker['tone']),
    sourceStrategyId: str(raw.sourceStrategyId, `${path}.sourceStrategyId`),
    sourceStrategyVersion: str(raw.sourceStrategyVersion, `${path}.sourceStrategyVersion`),
    signalId: optionalStr(raw.signalId, `${path}.signalId`),
    tradeId: optionalStr(raw.tradeId, `${path}.tradeId`),
  }
}

function overlay(value: unknown, path: string): Overlay {
  const raw = record(value, path)
  return {
    id: str(raw.id, `${path}.id`),
    kind: member(raw.kind, OVERLAY_KINDS, `${path}.kind`) as Overlay['kind'],
    label: str(raw.label, `${path}.label`),
    styleToken: str(raw.styleToken, `${path}.styleToken`),
    sourceStrategyId: str(raw.sourceStrategyId, `${path}.sourceStrategyId`),
    sourceStrategyVersion: str(raw.sourceStrategyVersion, `${path}.sourceStrategyVersion`),
    points: list(raw.points ?? [], `${path}.points`).map((item, index) => {
      const point = record(item, `${path}.points[${index}]`)
      return {
        time: point.time === undefined ? null : instant(point.time, `${path}.points[${index}].time`),
        value: optionalDecimal(point.value, `${path}.points[${index}].value`),
        upper: optionalDecimal(point.upper, `${path}.points[${index}].upper`),
        middle: optionalDecimal(point.middle, `${path}.points[${index}].middle`),
        lower: optionalDecimal(point.lower, `${path}.points[${index}].lower`),
        startTime:
          point.startTime === undefined
            ? null
            : instant(point.startTime, `${path}.points[${index}].startTime`),
        endTime:
          point.endTime === undefined
            ? null
            : instant(point.endTime, `${path}.points[${index}].endTime`),
      }
    }),
  }
}

export function parseVisualization(value: unknown): VisualizationData {
  const path = 'visualization'
  const raw = record(value, path)
  const state = record(raw.availability, `${path}.availability`)
  return {
    pair: str(raw.pair, `${path}.pair`),
    timeframe: str(raw.timeframe, `${path}.timeframe`),
    startTime: instant(raw.startTime, `${path}.startTime`),
    endTime: instant(raw.endTime, `${path}.endTime`),
    availability: {
      candles: availability(state.candles, `${path}.availability.candles`),
      overlays: availability(state.overlays, `${path}.availability.overlays`),
      signals: availability(state.signals, `${path}.availability.signals`),
      trades: availability(state.trades, `${path}.availability.trades`),
    },
    candles: list(raw.candles, `${path}.candles`).map((item, index) =>
      candle(item, `${path}.candles[${index}]`),
    ),
    overlays: list(raw.overlays, `${path}.overlays`).map((item, index) =>
      overlay(item, `${path}.overlays[${index}]`),
    ),
    markers: list(raw.markers, `${path}.markers`).map((item, index) =>
      parseMarker(item, `${path}.markers[${index}]`),
    ),
    unalignedMarkers: list(raw.unalignedMarkers, `${path}.unalignedMarkers`).map((item, index) => {
      const entry = record(item, `${path}.unalignedMarkers[${index}]`)
      return {
        marker: parseMarker(entry.marker, `${path}.unalignedMarkers[${index}].marker`),
        reason: str(entry.reason, `${path}.unalignedMarkers[${index}].reason`),
      }
    }),
  }
}

function trade(value: unknown, path: string): Trade {
  const raw = record(value, path)
  return {
    tradeId: str(raw.tradeId, `${path}.tradeId`),
    entrySignalId: optionalStr(raw.entrySignalId, `${path}.entrySignalId`),
    exitSignalId: optionalStr(raw.exitSignalId, `${path}.exitSignalId`),
    entryTime: instant(raw.entryTime, `${path}.entryTime`),
    entryPrice: decimal(raw.entryPrice, `${path}.entryPrice`),
    exitTime: instant(raw.exitTime, `${path}.exitTime`),
    exitPrice: decimal(raw.exitPrice, `${path}.exitPrice`),
    side: str(raw.side, `${path}.side`),
    quantity: decimal(raw.quantity, `${path}.quantity`),
    profitLoss: decimal(raw.profitLoss, `${path}.profitLoss`),
    returnPercent: decimal(raw.returnPercent, `${path}.returnPercent`),
  }
}

export function parseTradePage(value: unknown): TradePage {
  const path = 'trades'
  const raw = record(value, path)
  return {
    items: list(raw.items, `${path}.items`).map((item, index) =>
      trade(item, `${path}.items[${index}]`),
    ),
    pagination: pageMeta(raw.pagination, `${path}.pagination`),
  }
}

export function parseLeaderboardEvent(value: unknown): LeaderboardUpdatedEvent {
  const path = 'event'
  const raw = record(value, path)
  if (raw.eventType !== 'LEADERBOARD_UPDATED') {
    throw new ContractError(`${path}.eventType`, 'unsupported event type')
  }
  if (raw.version !== 1) {
    throw new ContractError(`${path}.version`, 'unsupported event version')
  }
  const payload = record(raw.payload, `${path}.payload`)
  const changed = record(payload.changed, `${path}.payload.changed`)
  const topOneRaw = payload.topOne
  return {
    eventType: 'LEADERBOARD_UPDATED',
    version: 1,
    eventId: str(raw.eventId, `${path}.eventId`),
    occurredAt: instant(raw.occurredAt, `${path}.occurredAt`),
    requestId: optionalStr(raw.requestId, `${path}.requestId`),
    runId: optionalStr(raw.runId, `${path}.runId`),
    jobId: optionalStr(raw.jobId, `${path}.jobId`),
    payload: {
      leaderboardId: str(payload.leaderboardId, `${path}.payload.leaderboardId`),
      scopeKey: str(payload.scopeKey, `${path}.payload.scopeKey`),
      scoringPolicyId: str(payload.scoringPolicyId, `${path}.payload.scoringPolicyId`),
      scoringPolicyVersion: str(
        payload.scoringPolicyVersion,
        `${path}.payload.scoringPolicyVersion`,
      ),
      rankBy: member(payload.rankBy, RANK_METRICS, `${path}.payload.rankBy`),
      k: int(payload.k, `${path}.payload.k`),
      projectionVersion: int(payload.projectionVersion, `${path}.payload.projectionVersion`),
      updatedAt: instant(payload.updatedAt, `${path}.payload.updatedAt`),
      entryCount: int(payload.entryCount, `${path}.payload.entryCount`),
      changed: {
        addedEvaluationResultIds: list(
          changed.addedEvaluationResultIds ?? [],
          `${path}.payload.changed.addedEvaluationResultIds`,
        ).map((item, index) =>
          str(item, `${path}.payload.changed.addedEvaluationResultIds[${index}]`),
        ),
        removedEvaluationResultIds: list(
          changed.removedEvaluationResultIds ?? [],
          `${path}.payload.changed.removedEvaluationResultIds`,
        ).map((item, index) =>
          str(item, `${path}.payload.changed.removedEvaluationResultIds[${index}]`),
        ),
        movedEvaluationResultIds: list(
          changed.movedEvaluationResultIds ?? [],
          `${path}.payload.changed.movedEvaluationResultIds`,
        ).map((item, index) =>
          str(item, `${path}.payload.changed.movedEvaluationResultIds[${index}]`),
        ),
      },
      topOne:
        topOneRaw === null || topOneRaw === undefined
          ? null
          : (() => {
              const top = record(topOneRaw, `${path}.payload.topOne`)
              return {
                evaluationResultId: str(
                  top.evaluationResultId,
                  `${path}.payload.topOne.evaluationResultId`,
                ),
                strategyId: str(top.strategyId, `${path}.payload.topOne.strategyId`),
                strategyVersion: str(top.strategyVersion, `${path}.payload.topOne.strategyVersion`),
                rank: int(top.rank, `${path}.payload.topOne.rank`),
                score: decimal(top.score, `${path}.payload.topOne.score`),
              }
            })(),
      runState:
        payload.runState === null || payload.runState === undefined
          ? null
          : member(
              payload.runState,
              ['QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'] as const,
              `${path}.payload.runState`,
            ),
    },
  }
}

export const CONTRACT_SORT_FIELDS = LEADERBOARD_SORT_FIELDS
