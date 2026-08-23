import { useCallback, useEffect, useMemo, useState } from 'react'
import { CandlestickChart } from '../../market-chart/components/CandlestickChart'
import {
  fetchRankedResultDetail,
  fetchRankedResultTrades,
  fetchRankedResultVisualization,
} from '../api/leaderboardApi'
import { StrategyOverlayLayer } from './StrategyOverlayLayer'
import { TradeSignalMarkers } from './TradeSignalMarkers'
import { TradeTable, type TradeSortField } from './TradeTable'
import type {
  Availability,
  RankedResultDetail as RankedResultDetailData,
  SortDirection,
  TradePage,
  VisualizationData,
} from '../types'

export const ANALYSIS_DISCLAIMER =
  'Simulated historical analysis only. Past simulated performance is not investment advice and does not guarantee future results.'

export type RankedResultDetailProps = {
  leaderboardId: string
  evaluationResultId: string
  onClose?: () => void
  loadDetail?: typeof fetchRankedResultDetail
  loadVisualization?: typeof fetchRankedResultVisualization
  loadTrades?: typeof fetchRankedResultTrades
}

type LoadState = 'loading' | 'ready' | 'error'

function AvailabilityNote({ label, availability }: { label: string; availability: Availability }) {
  return (
    <span
      data-testid={`availability-${label.toLowerCase()}`}
      data-state={availability.state}
      className="rounded-[3px] border border-subtle px-1.5 py-0.5 text-[10px] uppercase text-faint"
      title={availability.reason ?? undefined}
    >
      {label}: {availability.state}
      {availability.count ? ` (${availability.count})` : ''}
    </span>
  )
}

export function RankedResultDetail({
  leaderboardId,
  evaluationResultId,
  onClose,
  loadDetail = fetchRankedResultDetail,
  loadVisualization = fetchRankedResultVisualization,
  loadTrades = fetchRankedResultTrades,
}: RankedResultDetailProps) {
  const [detail, setDetail] = useState<RankedResultDetailData | null>(null)
  const [visualization, setVisualization] = useState<VisualizationData | null>(null)
  const [trades, setTrades] = useState<TradePage | null>(null)
  const [status, setStatus] = useState<LoadState>('loading')
  const [tradeStatus, setTradeStatus] = useState<LoadState>('loading')
  const [errorMessage, setErrorMessage] = useState<string>()
  const [showHold, setShowHold] = useState(false)
  const [selectedTradeId, setSelectedTradeId] = useState<string | null>(null)
  const [sortBy, setSortBy] = useState<TradeSortField>('ENTRY_TIME')
  const [sortDirection, setSortDirection] = useState<SortDirection>('ASC')
  const [tradePage, setTradePage] = useState(1)

  useEffect(() => {
    let cancelled = false
    setStatus('loading')
    setSelectedTradeId(null)
    loadDetail(leaderboardId, evaluationResultId)
      .then(async (next) => {
        if (cancelled) return
        setDetail(next)
        const view = await loadVisualization(leaderboardId, evaluationResultId, {
          startTime: next.entry.startTime,
          endTime: next.entry.endTime,
        })
        if (cancelled) return
        setVisualization(view)
        setStatus('ready')
      })
      .catch((error: Error) => {
        if (cancelled) return
        setErrorMessage(error.message)
        setStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [leaderboardId, evaluationResultId, loadDetail, loadVisualization])

  useEffect(() => {
    let cancelled = false
    setTradeStatus('loading')
    loadTrades(leaderboardId, evaluationResultId, {
      page: tradePage,
      pageSize: 25,
      sortBy,
      sortDirection,
    })
      .then((next) => {
        if (cancelled) return
        setTrades(next)
        setTradeStatus('ready')
      })
      .catch(() => {
        if (cancelled) return
        setTradeStatus('error')
      })
    return () => {
      cancelled = true
    }
  }, [leaderboardId, evaluationResultId, tradePage, sortBy, sortDirection, loadTrades])

  const selectedTrade = useMemo(
    () => trades?.items.find((item) => item.tradeId === selectedTradeId) ?? null,
    [trades, selectedTradeId],
  )

  const onSort = useCallback((field: TradeSortField) => {
    setSortBy((current) => {
      if (current === field) {
        setSortDirection((direction) => (direction === 'ASC' ? 'DESC' : 'ASC'))
        return current
      }
      setSortDirection('ASC')
      return field
    })
    setTradePage(1)
  }, [])

  if (status === 'error') {
    return (
      <aside
        data-testid="detail-ranked-result"
        className="w-[480px] shrink-0 border-l border-line bg-surface p-4"
      >
        <p data-testid="state-detail-error" role="alert" className="text-[12px] text-neg">
          The ranked result could not be loaded. {errorMessage}
        </p>
      </aside>
    )
  }

  if (status === 'loading' || !detail) {
    return (
      <aside
        data-testid="detail-ranked-result"
        className="w-[480px] shrink-0 border-l border-line bg-surface p-4"
      >
        <p data-testid="state-detail-loading" role="status" className="text-[12px] text-dim">
          Loading the ranked result…
        </p>
      </aside>
    )
  }

  const entry = detail.entry
  const provenance = detail.provenance

  return (
    <aside
      data-testid="detail-ranked-result"
      aria-label={`Ranked result ${entry.rank}: ${entry.strategy.displayName}`}
      className="flex w-[480px] shrink-0 flex-col overflow-auto border-l border-line bg-surface"
    >
      <header className="flex items-start gap-2 border-b border-subtle px-4 py-3">
        <div>
          <h2 className="text-[14px] font-semibold text-ink">
            #{entry.rank} {entry.strategy.displayName}
          </h2>
          <p data-testid="detail-context" className="font-mono text-[11px] text-faint">
            {entry.pair} · {entry.timeframe} · {entry.startTime.slice(0, 10)} →{' '}
            {entry.endTime.slice(0, 10)} · strategy v{entry.strategy.strategyVersion} · policy{' '}
            {entry.scoringPolicyId} v{entry.scoringPolicyVersion}
          </p>
        </div>
        {onClose && (
          <button
            type="button"
            data-testid="control-detail-close"
            onClick={onClose}
            className="ml-auto rounded-[4px] border border-subtle px-2 py-1 text-[11px] text-dim hover:bg-surface-hover"
          >
            Close
          </button>
        )}
      </header>

      <p
        data-testid="disclaimer-ranked-result"
        className="border-b border-subtle bg-workspace px-4 py-1.5 text-[11px] text-dim"
      >
        {detail.disclaimer || ANALYSIS_DISCLAIMER}
      </p>

      <div className="flex flex-wrap items-center gap-1.5 px-4 py-2">
        <AvailabilityNote label="Candles" availability={detail.candles} />
        <AvailabilityNote label="Overlays" availability={detail.overlays} />
        <AvailabilityNote label="Signals" availability={detail.signals} />
        <AvailabilityNote label="Trades" availability={detail.trades} />
        <label className="ml-auto flex items-center gap-1 text-[11px] text-faint" htmlFor="control-show-hold">
          <input
            id="control-show-hold"
            data-testid="control-show-hold"
            type="checkbox"
            checked={showHold}
            onChange={(event) => setShowHold(event.target.checked)}
          />
          Show HOLD markers
        </label>
      </div>

      <div className="px-4 pb-3">
        <CandlestickChart
          candles={visualization?.candles ?? []}
          height={260}
          highlightRange={
            selectedTrade
              ? { startTime: selectedTrade.entryTime, endTime: selectedTrade.exitTime }
              : null
          }
          overlays={(scale) => (
            <StrategyOverlayLayer overlays={visualization?.overlays ?? []} scale={scale} />
          )}
          markers={(scale) => (
            <TradeSignalMarkers
              markers={visualization?.markers ?? []}
              scale={scale}
              showHold={showHold}
              selectedTradeId={selectedTradeId}
            />
          )}
        />
        {visualization && visualization.unalignedMarkers.length > 0 && (
          <p
            data-testid="state-unaligned-markers"
            role="status"
            className="mt-2 rounded-[4px] border border-subtle bg-workspace px-2 py-1 text-[11px] text-warn"
          >
            {visualization.unalignedMarkers.length} marker(s) could not be aligned to a Candle and
            are listed instead of being placed:{' '}
            {visualization.unalignedMarkers
              .map((item) => `${item.marker.label} at ${item.marker.time} (${item.reason})`)
              .join('; ')}
          </p>
        )}
        {detail.overlays.state === 'UNAVAILABLE' && (
          <p data-testid="state-overlays-unavailable" className="mt-2 text-[11px] text-faint">
            {detail.overlays.reason}
          </p>
        )}
      </div>

      <section aria-label="Simulated trades" className="border-t border-subtle">
        <TradeTable
          page={trades}
          status={
            tradeStatus === 'ready' && (trades?.items.length ?? 0) === 0 ? 'empty' : tradeStatus
          }
          emptyReason={detail.trades.reason}
          sortBy={sortBy}
          sortDirection={sortDirection}
          selectedTradeId={selectedTradeId}
          onSort={onSort}
          onSelect={setSelectedTradeId}
          onPage={setTradePage}
        />
      </section>

      {selectedTrade && (
        <dl
          data-testid="detail-selected-trade"
          className="grid grid-cols-2 gap-x-3 gap-y-1 border-t border-subtle px-4 py-3 text-[11px]"
        >
          <dt className="text-faint">Entry</dt>
          <dd className="font-mono text-ink">
            {selectedTrade.entryTime} @ {selectedTrade.entryPrice}
          </dd>
          <dt className="text-faint">Exit</dt>
          <dd className="font-mono text-ink">
            {selectedTrade.exitTime} @ {selectedTrade.exitPrice}
          </dd>
          <dt className="text-faint">Side / quantity</dt>
          <dd className="font-mono text-ink">
            {selectedTrade.side} · {selectedTrade.quantity}
          </dd>
          <dt className="text-faint">Result</dt>
          <dd className="font-mono text-ink">
            {selectedTrade.profitLoss} ({selectedTrade.returnPercent}%)
          </dd>
          <dt className="text-faint">Entry signal</dt>
          <dd className="font-mono text-ink">{selectedTrade.entrySignalId ?? 'n/a'}</dd>
          <dt className="text-faint">Exit signal</dt>
          <dd className="font-mono text-ink">{selectedTrade.exitSignalId ?? 'n/a'}</dd>
        </dl>
      )}

      <dl
        data-testid="detail-provenance"
        className="grid grid-cols-2 gap-x-3 gap-y-1 border-t border-subtle px-4 py-3 text-[11px]"
      >
        <dt className="text-faint">Evaluation Result</dt>
        <dd className="font-mono text-ink">{provenance.evaluationResultId}</dd>
        <dt className="text-faint">Backtest Result</dt>
        <dd className="font-mono text-ink">{provenance.backtestResultId}</dd>
        <dt className="text-faint">Backtest Run</dt>
        <dd className="font-mono text-ink">{provenance.runId}</dd>
        <dt className="text-faint">Job</dt>
        <dd className="font-mono text-ink">{provenance.jobId}</dd>
        <dt className="text-faint">Strategy</dt>
        <dd className="font-mono text-ink">
          {provenance.strategyId} v{provenance.strategyVersion}
        </dd>
        <dt className="text-faint">Dataset</dt>
        <dd className="font-mono text-ink">{provenance.datasetId}</dd>
        <dt className="text-faint">Result checksum</dt>
        <dd className="truncate font-mono text-ink">{provenance.resultChecksum}</dd>
        <dt className="text-faint">Scoring policy</dt>
        <dd className="font-mono text-ink">
          {provenance.scoringPolicyId} v{provenance.scoringPolicyVersion}
        </dd>
        <dt className="text-faint">Execution config</dt>
        <dd className="font-mono text-ink">
          {Object.entries(provenance.executionConfig)
            .map(([key, value]) => `${key}=${String(value)}`)
            .join(' · ')}
        </dd>
      </dl>
    </aside>
  )
}
