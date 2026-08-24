import type { KeyboardEvent } from 'react'
import type { SortDirection, Trade, TradePage } from '../types'

export type TradeSortField = 'ENTRY_TIME' | 'EXIT_TIME' | 'RETURN_PERCENT'

export type TradeTableProps = {
  page: TradePage | null
  status: 'loading' | 'ready' | 'error' | 'empty'
  sortBy: TradeSortField
  sortDirection: SortDirection
  selectedTradeId: string | null
  emptyReason?: string | null
  errorMessage?: string
  onSort: (field: TradeSortField) => void
  onSelect: (tradeId: string | null) => void
  onPage: (page: number) => void
}

const COLUMNS: { key: TradeSortField | 'NUMBER' | 'SIDE' | 'QUANTITY' | 'RESULT'; label: string }[] =
  [
    { key: 'NUMBER', label: '#' },
    { key: 'ENTRY_TIME', label: 'Entry' },
    { key: 'EXIT_TIME', label: 'Exit' },
    { key: 'SIDE', label: 'Side' },
    { key: 'QUANTITY', label: 'Quantity' },
    { key: 'RESULT', label: 'P/L' },
    { key: 'RETURN_PERCENT', label: 'Return' },
  ]

const SORTABLE: TradeSortField[] = ['ENTRY_TIME', 'EXIT_TIME', 'RETURN_PERCENT']

export function TradeTable({
  page,
  status,
  sortBy,
  sortDirection,
  selectedTradeId,
  emptyReason,
  errorMessage,
  onSort,
  onSelect,
  onPage,
}: TradeTableProps) {
  if (status === 'loading') {
    return (
      <p data-testid="state-trades-loading" role="status" className="p-4 text-[12px] text-dim">
        Loading simulated Trades…
      </p>
    )
  }

  if (status === 'error') {
    return (
      <p data-testid="state-trades-error" role="alert" className="p-4 text-[12px] text-neg">
        {errorMessage ?? 'The Trade list could not be loaded.'}
      </p>
    )
  }

  const trades = page?.items ?? []
  if (status === 'empty' || trades.length === 0) {
    return (
      <p data-testid="state-trades-empty" className="p-4 text-[12px] text-dim">
        This result produced no simulated Trade.{emptyReason ? ` ${emptyReason}` : ''}
      </p>
    )
  }

  const pagination = page?.pagination ?? { page: 1, pageSize: 25, total: trades.length }
  const lastPage = Math.max(1, Math.ceil(pagination.total / Math.max(1, pagination.pageSize)))
  const offset = (pagination.page - 1) * pagination.pageSize

  const select = (trade: Trade) =>
    onSelect(trade.tradeId === selectedTradeId ? null : trade.tradeId)

  return (
    <div className="flex flex-col">
      <table
        id="table-trades"
        data-testid="table-trades"
        className="w-full border-collapse text-[12px]"
      >
        <caption className="sr-only">Simulated Trades for the selected ranked result</caption>
        <thead>
          <tr className="border-b border-line text-left text-faint">
            {COLUMNS.map((column) => {
              const sortable = SORTABLE.includes(column.key as TradeSortField)
              const active = sortBy === column.key
              return (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={
                    sortable
                      ? active
                        ? sortDirection === 'DESC'
                          ? 'descending'
                          : 'ascending'
                        : 'none'
                      : undefined
                  }
                  className="h-8 whitespace-nowrap px-2 text-[10px] font-semibold uppercase tracking-wide"
                >
                  {sortable ? (
                    <button
                      type="button"
                      data-testid={`control-trade-sort-${column.key}`}
                      onClick={() => onSort(column.key as TradeSortField)}
                      className="hover:text-ink"
                    >
                      {column.label}
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
          {trades.map((trade, index) => {
            const selected = trade.tradeId === selectedTradeId
            const onKeyDown = (event: KeyboardEvent<HTMLTableRowElement>) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                select(trade)
              }
            }
            const number = offset + index + 1
            return (
              <tr
                key={trade.tradeId}
                data-testid={`row-trade-${trade.tradeId}`}
                tabIndex={0}
                role="button"
                aria-label={`Select trade ${number}`}
                aria-selected={selected}
                onClick={() => select(trade)}
                onKeyDown={onKeyDown}
                className={`h-8 cursor-pointer border-b border-subtle ${
                  selected ? 'bg-surface-active' : 'hover:bg-surface-hover'
                }`}
              >
                <td className="px-2 font-mono text-faint">#{number}</td>
                <td className="px-2 font-mono text-dim">
                  {trade.entryTime.replace('T', ' ').slice(0, 16)}
                  <span className="ml-1 text-ink">{trade.entryPrice}</span>
                </td>
                <td className="px-2 font-mono text-dim">
                  {trade.exitTime.replace('T', ' ').slice(0, 16)}
                  <span className="ml-1 text-ink">{trade.exitPrice}</span>
                </td>
                <td className="px-2 font-mono text-dim">{trade.side}</td>
                <td className="px-2 font-mono text-dim">{trade.quantity}</td>
                <td
                  className={`px-2 font-mono ${
                    Number(trade.profitLoss) >= 0 ? 'text-pos' : 'text-neg'
                  }`}
                >
                  {trade.profitLoss}
                </td>
                <td
                  className={`px-2 font-mono ${
                    Number(trade.returnPercent) >= 0 ? 'text-pos' : 'text-neg'
                  }`}
                >
                  {trade.returnPercent}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <nav
        aria-label="Trade pagination"
        className="flex items-center gap-2 border-t border-subtle px-2 py-1.5 text-[11px]"
      >
        <button
          type="button"
          data-testid="control-trade-page-previous"
          disabled={pagination.page <= 1}
          onClick={() => onPage(pagination.page - 1)}
          className="rounded-[4px] border border-subtle px-2 py-0.5 disabled:opacity-40"
        >
          Previous
        </button>
        <span data-testid="label-trade-page" className="font-mono text-faint">
          Page {pagination.page} of {lastPage} · {pagination.total} trades
        </span>
        <button
          type="button"
          data-testid="control-trade-page-next"
          disabled={pagination.page >= lastPage}
          onClick={() => onPage(pagination.page + 1)}
          className="rounded-[4px] border border-subtle px-2 py-0.5 disabled:opacity-40"
        >
          Next
        </button>
      </nav>
    </div>
  )
}
