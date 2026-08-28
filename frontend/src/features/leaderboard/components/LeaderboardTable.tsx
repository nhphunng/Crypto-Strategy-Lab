import type { KeyboardEvent } from 'react'
import type {
  LeaderboardSnapshot,
  LeaderboardSortField,
  LeaderboardViewState,
  MetricDescriptor,
  MetricName,
  SortDirection,
} from '../types'

export type LeaderboardTableProps = {
  snapshot: LeaderboardSnapshot | null
  view: LeaderboardViewState
  status: 'loading' | 'ready' | 'error'
  errorMessage?: string
  stale?: boolean
  onViewChange: (next: LeaderboardViewState) => void
  onSelect?: (evaluationResultId: string) => void
  selectedId?: string | null
  onRetry?: () => void
}

type Column = {
  key: LeaderboardSortField | 'STRATEGY' | 'CONTEXT'
  label: string
  metric?: MetricName
  sortable: boolean
}

const COLUMNS: Column[] = [
  { key: 'RANK', label: 'Rank', sortable: true },
  { key: 'STRATEGY', label: 'Strategy', sortable: false },
  { key: 'OVERALL_SCORE', label: 'Score', metric: 'OVERALL_SCORE', sortable: true },
  { key: 'TOTAL_RETURN', label: 'Return', metric: 'TOTAL_RETURN', sortable: true },
  { key: 'WIN_RATE', label: 'Win Rate', metric: 'WIN_RATE', sortable: true },
  { key: 'MAX_DRAWDOWN', label: 'Max Drawdown', metric: 'MAX_DRAWDOWN', sortable: true },
  { key: 'SHARPE_RATIO', label: 'Sharpe', metric: 'SHARPE_RATIO', sortable: true },
  { key: 'CONTEXT', label: 'Context', sortable: false },
]

const UNIT_SUFFIX: Record<string, string> = {
  PERCENT: '%',
  RATIO: '',
  COUNT: '',
  SCORE: '',
}

const DIRECTION_LABEL: Record<SortDirection, string> = {
  ASC: 'lower is better',
  DESC: 'higher is better',
}

function describe(metadata: MetricDescriptor[], metric?: MetricName): MetricDescriptor | undefined {
  return metric ? metadata.find((item) => item.metric === metric) : undefined
}

/**
 * Round for reading only. The exact backend decimal stays in the `title`, so no
 * displayed value silently replaces the recorded one.
 */
export function formatDecimal(value: string, fractionDigits = 2): string {
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return value
  return parsed.toFixed(fractionDigits)
}

function formatMetric(value: string | null, descriptor?: MetricDescriptor): string {
  if (value === null) return 'n/a'
  return `${formatDecimal(value)}${descriptor ? UNIT_SUFFIX[descriptor.unit] : ''}`
}

export function LeaderboardTable({
  snapshot,
  view,
  status,
  errorMessage,
  stale = false,
  onViewChange,
  onSelect,
  selectedId,
  onRetry,
}: LeaderboardTableProps) {
  const metadata = snapshot?.metricMetadata ?? []

  const toggleSort = (column: Column) => {
    if (!column.sortable) return
    const field = column.key as LeaderboardSortField
    const descriptor = describe(metadata, column.metric)
    const semantic: SortDirection = field === 'RANK' ? 'ASC' : (descriptor?.direction ?? 'DESC')
    const nextDirection: SortDirection =
      view.sortBy === field
        ? view.sortDirection === 'ASC'
          ? 'DESC'
          : 'ASC'
        : semantic
    onViewChange({ ...view, sortBy: field, sortDirection: nextDirection, page: 1 })
  }

  const setFilter = (key: keyof LeaderboardViewState, value: string) => {
    onViewChange({ ...view, [key]: value, page: 1 })
  }

  const rows = snapshot?.entries ?? []
  const pagination = snapshot?.pagination ?? { page: view.page, pageSize: view.pageSize, total: 0 }
  const lastPage = Math.max(1, Math.ceil(pagination.total / Math.max(1, pagination.pageSize)))

  return (
    <section aria-labelledby="leaderboard-heading" className="flex h-full min-h-0 flex-col">
      <h2 id="leaderboard-heading" className="sr-only">
        Top-K simulated strategy results
      </h2>

      <div
        className="flex flex-wrap items-center gap-2 border-b border-subtle bg-surface px-4 py-2 text-[12px]"
        data-testid="filter-leaderboard"
      >
        <label className="flex items-center gap-1.5 text-faint" htmlFor="control-filter-min-score">
          Min score
          <input
            id="control-filter-min-score"
            data-testid="control-filter-min-score"
            className="w-20 rounded-[4px] border border-subtle bg-workspace px-1.5 py-1 font-mono text-ink"
            value={view.minScore ?? ''}
            inputMode="decimal"
            onChange={(event) => setFilter('minScore', event.target.value)}
          />
        </label>
        <label
          className="flex items-center gap-1.5 text-faint"
          htmlFor="control-filter-max-drawdown"
        >
          Max drawdown
          <input
            id="control-filter-max-drawdown"
            data-testid="control-filter-max-drawdown"
            className="w-20 rounded-[4px] border border-subtle bg-workspace px-1.5 py-1 font-mono text-ink"
            value={view.maxDrawdown ?? ''}
            inputMode="decimal"
            onChange={(event) => setFilter('maxDrawdown', event.target.value)}
          />
        </label>
        <label
          className="flex items-center gap-1.5 text-faint"
          htmlFor="control-filter-min-win-rate"
        >
          Min win rate
          <input
            id="control-filter-min-win-rate"
            data-testid="control-filter-min-win-rate"
            className="w-20 rounded-[4px] border border-subtle bg-workspace px-1.5 py-1 font-mono text-ink"
            value={view.minWinRate ?? ''}
            inputMode="decimal"
            onChange={(event) => setFilter('minWinRate', event.target.value)}
          />
        </label>
        <span className="ml-auto text-[11px] text-faint" data-testid="metric-direction-legend">
          {metadata
            .filter((item) => item.metric !== 'NUMBER_OF_TRADES')
            .map((item) => `${item.metric}: ${DIRECTION_LABEL[item.direction]}`)
            .join(' · ')}
        </span>
      </div>

      {stale && (
        <p
          role="status"
          data-testid="state-leaderboard-stale"
          className="border-b border-subtle bg-workspace px-4 py-1.5 text-[11px] text-warn"
        >
          Showing the last confirmed snapshot while live updates reconnect.
        </p>
      )}

      <div className="min-h-0 flex-1 overflow-auto bg-surface">
        {status === 'error' && (
          <div data-testid="state-leaderboard-error" role="alert" className="p-6 text-[13px]">
            <p className="font-medium text-neg">The leaderboard could not be loaded.</p>
            <p className="mt-1 text-dim">{errorMessage}</p>
            {onRetry && (
              <button
                type="button"
                data-testid="control-leaderboard-retry"
                onClick={onRetry}
                className="mt-3 rounded-[5px] border border-subtle px-2 py-1 text-ink hover:bg-surface-hover"
              >
                Try again
              </button>
            )}
          </div>
        )}

        {status === 'loading' && (
          <p data-testid="state-leaderboard-loading" role="status" className="p-6 text-[13px] text-dim">
            Loading the current ranking…
          </p>
        )}

        {status === 'ready' && rows.length === 0 && (
          <p data-testid="state-leaderboard-empty" className="p-6 text-[13px] text-dim">
            No evaluated candidate matches this ranking definition yet.
          </p>
        )}

        {status === 'ready' && rows.length > 0 && (
          <table
            id="table-leaderboard"
            data-testid="table-leaderboard"
            className="w-full border-collapse text-[13px]"
          >
            <caption className="sr-only">
              Simulated historical analysis. Ranked by {snapshot?.rankBy} with K={snapshot?.k}.
            </caption>
            <thead className="sticky top-0 z-10">
              <tr className="border-b border-line bg-surface text-left text-faint">
                {COLUMNS.map((column) => {
                  const descriptor = describe(metadata, column.metric)
                  const active = view.sortBy === column.key
                  return (
                    <th
                      key={column.key}
                      scope="col"
                      aria-sort={
                        column.sortable
                          ? active
                            ? view.sortDirection === 'DESC'
                              ? 'descending'
                              : 'ascending'
                            : 'none'
                          : undefined
                      }
                      className="h-[34px] whitespace-nowrap px-3 text-[11px] font-semibold uppercase tracking-wide"
                    >
                      {column.sortable ? (
                        <button
                          type="button"
                          data-testid={`control-sort-${column.key}`}
                          onClick={() => toggleSort(column)}
                          className="inline-flex items-center gap-1 rounded-[3px] hover:text-ink"
                        >
                          {column.label}
                          {descriptor && (
                            <span className="text-[10px] font-normal normal-case text-faint">
                              ({descriptor.unit.toLowerCase()},{' '}
                              {DIRECTION_LABEL[descriptor.direction]})
                            </span>
                          )}
                        </button>
                      ) : (
                        column.label
                      )}
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((entry) => {
                const selected = selectedId === entry.evaluationResultId
                const open = () => onSelect?.(entry.evaluationResultId)
                const onKeyDown = (event: KeyboardEvent<HTMLTableRowElement>) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    open()
                  }
                }
                return (
                  <tr
                    key={entry.evaluationResultId}
                    data-testid={`row-leaderboard-${entry.evaluationResultId}`}
                    tabIndex={0}
                    role="button"
                    aria-label={`Open rank ${entry.rank}, ${entry.strategy.displayName}`}
                    aria-selected={selected}
                    onClick={open}
                    onKeyDown={onKeyDown}
                    className={`h-9 cursor-pointer border-b border-subtle ${
                      selected ? 'bg-surface-active' : 'hover:bg-surface-hover'
                    }`}
                  >
                    <td className="px-3 font-mono tabular-nums text-faint">#{entry.rank}</td>
                    <td className="px-3 text-ink">
                      <span className="font-medium">{entry.strategy.displayName}</span>
                      <span className="ml-1.5 font-mono text-[11px] text-faint">
                        v{entry.strategy.strategyVersion}
                      </span>
                      {entry.metrics.numberOfTrades === 0 && (
                        <span
                          data-testid={`state-no-trade-${entry.evaluationResultId}`}
                          className="ml-2 rounded-[3px] border border-subtle px-1 text-[10px] uppercase text-warn"
                        >
                          No trades
                        </span>
                      )}
                    </td>
                    <td
                      className="px-3 font-mono font-semibold tabular-nums text-ml"
                      title={entry.score}
                    >
                      {formatDecimal(entry.score)}
                    </td>
                    <td className="px-3 font-mono tabular-nums text-ink">
                      <span title={entry.metrics.totalReturn ?? 'n/a'}>
                        {formatMetric(entry.metrics.totalReturn, describe(metadata, 'TOTAL_RETURN'))}
                      </span>
                    </td>
                    <td className="px-3 font-mono tabular-nums text-dim">
                      <span title={entry.metrics.winRate ?? 'n/a'}>
                        {formatMetric(entry.metrics.winRate, describe(metadata, 'WIN_RATE'))}
                      </span>
                    </td>
                    <td className="px-3 font-mono tabular-nums text-neg">
                      <span title={entry.metrics.maxDrawdown ?? 'n/a'}>
                        {formatMetric(entry.metrics.maxDrawdown, describe(metadata, 'MAX_DRAWDOWN'))}
                      </span>
                    </td>
                    <td className="px-3 font-mono tabular-nums text-ink">
                      <span title={entry.metrics.sharpeRatio ?? 'n/a'}>
                        {formatMetric(entry.metrics.sharpeRatio, describe(metadata, 'SHARPE_RATIO'))}
                      </span>
                    </td>
                    <td className="px-3 text-[11px] text-faint">
                      <span className="font-mono">
                        {entry.pair} · {entry.timeframe}
                      </span>
                      <br />
                      <span className="font-mono">
                        {entry.startTime.slice(0, 10)} → {entry.endTime.slice(0, 10)} ·{' '}
                        {entry.metrics.numberOfTrades} trades · policy{' '}
                        {entry.scoringPolicyId} v{entry.scoringPolicyVersion}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      <nav
        aria-label="Leaderboard pagination"
        className="flex items-center gap-2 border-t border-subtle bg-surface px-4 py-2 text-[12px]"
      >
        <button
          type="button"
          data-testid="control-page-previous"
          disabled={pagination.page <= 1}
          onClick={() => onViewChange({ ...view, page: Math.max(1, pagination.page - 1) })}
          className="rounded-[5px] border border-subtle px-2 py-1 text-ink disabled:opacity-40"
        >
          Previous
        </button>
        <span data-testid="label-page" className="font-mono text-faint">
          Page {pagination.page} of {lastPage} · {pagination.total} shown
        </span>
        <button
          type="button"
          data-testid="control-page-next"
          disabled={pagination.page >= lastPage}
          onClick={() => onViewChange({ ...view, page: pagination.page + 1 })}
          className="rounded-[5px] border border-subtle px-2 py-1 text-ink disabled:opacity-40"
        >
          Next
        </button>
        <label className="ml-auto flex items-center gap-1.5 text-faint" htmlFor="control-page-size">
          Rows
          <select
            id="control-page-size"
            data-testid="control-page-size"
            value={view.pageSize}
            onChange={(event) =>
              onViewChange({ ...view, pageSize: Number(event.target.value), page: 1 })
            }
            className="rounded-[4px] border border-subtle bg-workspace px-1.5 py-1 text-ink"
          >
            {[10, 25, 50].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </label>
      </nav>
    </section>
  )
}
