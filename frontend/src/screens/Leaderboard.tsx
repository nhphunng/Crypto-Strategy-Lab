import { useMemo, useState } from 'react'
import { ArrowDown, ArrowUp, ChevronDown, ExternalLink, HelpCircle, LineChart } from 'lucide-react'
import { useStore } from '../lib/store'
import type { LeaderRow } from '../domain'
import { BACKTEST_DEFAULTS } from '../config'
import { useServices } from '../services/registry'
import { PageHeader } from '../components/Shell'
import { CandleChart } from '../components/CandleChart'
import { TradeTable } from './Backtests'
import {
  Button,
  cn,
  Delta,
  Drawer,
  DrawerSection,
  InfoPopover,
  KV,
  Segmented,
  StatusBadge,
} from '../components/ui'

type SortKey = 'score' | 'ret' | 'winRate' | 'mdd' | 'trades' | 'sharpe'

const COL_INFO: Partial<Record<SortKey, string>> = {
  score: 'A single number blending return, win rate, drawdown and Sharpe. It reflects how well a strategy performed under these historical test conditions — not a guaranteed winner.',
  ret: 'Total simulated gain or loss over the test period, after fees.',
  winRate: 'Share of simulated trades that ended profitably.',
  mdd: 'Largest drop from a previous high during the test. Closer to 0% is smoother.',
  sharpe: 'Return earned per unit of risk. Higher generally means steadier returns.',
  trades: 'How many simulated trades were taken. Very few trades makes results less reliable.',
}

const COLS: { key: SortKey | 'rank' | 'strategy' | 'updated'; label: string; sortable?: boolean; better?: 'high' | 'low' }[] = [
  { key: 'rank', label: 'Rank' },
  { key: 'strategy', label: 'Strategy' },
  { key: 'score', label: 'Score', sortable: true, better: 'high' },
  { key: 'ret', label: 'Return', sortable: true, better: 'high' },
  { key: 'winRate', label: 'Win Rate', sortable: true, better: 'high' },
  { key: 'mdd', label: 'MDD', sortable: true, better: 'high' },
  { key: 'trades', label: 'Trades', sortable: true },
  { key: 'sharpe', label: 'Sharpe', sortable: true, better: 'high' },
  { key: 'updated', label: 'Updated' },
]

function Inspector({ row, onClose }: { row: LeaderRow; onClose: () => void }) {
  const { navigate, toast } = useStore()
  const services = useServices()
  const [tab, setTab] = useState<'overview' | 'trades' | 'provenance'>('overview')
  const [selectedTrade, setSelectedTrade] = useState<number | null>(null)

  const candles = useMemo(
    () => services.market.getCandles(BACKTEST_DEFAULTS.timeframe, 100),
    [services],
  )
  const markers = useMemo(
    () => services.market.getSignalMarkers(candles, row.rank + 2),
    [candles, row.rank, services],
  )
  const trades = useMemo(
    () => services.backtests.makeTrades(row.rank + 1, Math.min(row.trades, 18)),
    [row.rank, row.trades, services],
  )
  const sel = trades.find((t) => t.n === selectedTrade)

  return (
    <Drawer
      open
      onClose={onClose}
      width={420}
      title={row.strategy}
      subtitle={`Rank #${row.rank} · Balanced v2 scoring`}
      footer={
        <div className="flex gap-2">
          <Button
            variant="default"
            className="flex-1"
            onClick={() => {
              navigate('backtests', { backtestTab: 'single', strategyName: row.strategy })
              toast(`Opened ${row.strategy} in Backtests`, 'info')
            }}
          >
            <ExternalLink size={13} /> Open in Backtests
          </Button>
          <Button
            variant="primary"
            className="flex-1"
            onClick={() => {
              navigate('market', { overlayContext: row.strategy })
              toast(`Visualizing ${row.strategy} on Market`, 'info')
            }}
          >
            <LineChart size={13} /> Visualize on Market
          </Button>
        </div>
      }
    >
      <div className="border-b border-subtle px-4 py-2">
        <Segmented
          ariaLabel="Inspector section"
          options={[
            { value: 'overview', label: 'Overview' },
            { value: 'trades', label: 'Trades' },
            { value: 'provenance', label: 'Provenance' },
          ]}
          value={tab}
          onChange={(v) => setTab(v as typeof tab)}
        />
      </div>

      {tab === 'overview' && (
        <>
          <div className="grid grid-cols-3 gap-px border-b border-subtle bg-subtle">
            {[
              ['Score', row.score, 'ml'],
              ['Return', `+${row.ret}%`, 'pos'],
              ['Win Rate', `${row.winRate}%`, 'ink'],
              ['MDD', `${row.mdd}%`, 'neg'],
              ['Sharpe', row.sharpe, 'ink'],
              ['Trades', row.trades, 'ink'],
            ].map(([l, v, c]) => (
              <div key={l as string} className="bg-surface px-3 py-2.5">
                <div className="text-[10px] uppercase text-faint">{l as string}</div>
                <div
                  className={cn(
                    'font-mono text-[15px] font-semibold tabular-nums',
                    c === 'pos' && 'text-pos',
                    c === 'neg' && 'text-neg',
                    c === 'ml' && 'text-ml',
                    c === 'ink' && 'text-ink',
                  )}
                >
                  {v as string | number}
                </div>
              </div>
            ))}
          </div>
          <DrawerSection title="Members & versions">
            {row.members.map((m) => (
              <KV key={m} k={m.replace(/ v\d+$/, '')} v={m.match(/v\d+$/)?.[0] ?? '—'} />
            ))}
          </DrawerSection>
          <DrawerSection title="Decision method">
            <KV k="Method" v="Weighted" mono={false} />
            <KV k="BUY threshold" v="0.30" />
            <KV k="SELL threshold" v="-0.30" />
          </DrawerSection>
          <div className="p-3">
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-faint">Strategy visualization</div>
            <div className="overflow-hidden rounded-[6px] border border-subtle bg-workspace">
              <CandleChart candles={candles} overlays={{ ma20: true, sr: true }} markers={markers} height={200} volume={false} compact />
            </div>
          </div>
        </>
      )}

      {tab === 'trades' && (
        <div className="h-[calc(100vh-190px)]">
          <TradeTable trades={trades} selected={selectedTrade} onSelect={setSelectedTrade} />
          {sel && (
            <div className="border-t border-subtle px-3 py-2 text-[11px] text-faint">
              Trade #{sel.n} highlighted — interval {sel.entryIndex}–{sel.exitIndex} on the visualization.
            </div>
          )}
        </div>
      )}

      {tab === 'provenance' && (
        <>
          <DrawerSection title="Runs">
            <KV k="Backtest Run" v="BT-1841" />
            <KV k="Search Run" v="SR-0184" />
          </DrawerSection>
          <DrawerSection title="Generator">
            <KV k="Generator" v="Random Search" />
            <KV k="Version" v="v1" />
            <KV k="Seed" v="424242" />
          </DrawerSection>
          <DrawerSection title="Dataset">
            <KV k="Dataset" v="BINANCE-BTCUSDT-15M-2026H1" />
            <KV k="Dataset version" v="2026H1.3" />
          </DrawerSection>
          <DrawerSection title="Scoring & execution">
            <KV k="Scoring policy" v="Balanced v2" />
            <KV k="Fee / slippage" v="0.04% / 0.02%" />
            <KV k="Position size" v="100% equity" />
          </DrawerSection>
        </>
      )}
    </Drawer>
  )
}

export function Leaderboard() {
  const services = useServices()
  const [sort, setSort] = useState<SortKey>('score')
  const [dir, setDir] = useState<'asc' | 'desc'>('desc')
  const [typeFilter, setTypeFilter] = useState('All')
  const [selected, setSelected] = useState<LeaderRow | null>(null)

  const rows = useMemo(() => {
    return services.leaderboard
      .listEntries()
      .filter((row) =>
        typeFilter === 'All'
          ? true
          : typeFilter === 'Composite'
            ? row.members.length > 1
            : row.members.length === 1,
      )
      .map((row, index) => ({ row, index }))
      .sort((left, right) => {
        const av = left.row[sort]
        const bv = right.row[sort]
        const delta = dir === 'desc' ? bv - av : av - bv
        return delta || left.index - right.index
      })
      .map(({ row }) => row)
  }, [services, sort, dir, typeFilter])

  const toggleSort = (k: SortKey) => {
    if (sort === k) setDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    else {
      setSort(k)
      setDir('desc')
    }
  }

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Leaderboard">
        <InfoPopover
          align="right"
          width={300}
          title="How ranking works"
          trigger={({ onClick }) => (
            <button
              onClick={onClick}
              className="inline-flex items-center gap-1 text-[12px] font-medium text-accent hover:text-accent-hover"
            >
              <HelpCircle size={13} /> How ranking works
            </button>
          )}
        >
          Strategies are scored on several historical metrics at once — return, win rate, maximum
          drawdown and Sharpe — blended by the Balanced v2 policy. Ranking by this combined Score
          rewards balanced performance rather than raw profit. A higher rank means a strategy did
          better under these test conditions; it is not a prediction or a guaranteed winner.
        </InfoPopover>
        <div className="flex items-center gap-1.5 rounded-[5px] border border-subtle bg-workspace px-2 py-1 text-[12px]">
          <span className="text-faint">Scoring</span>
          <span className="font-mono text-ink">Balanced v2</span>
        </div>
        <div className="flex items-center gap-1.5 rounded-[5px] border border-subtle bg-workspace px-2 py-1 text-[12px]">
          <span className="text-faint">Top-K</span>
          <span className="font-mono text-ink">10</span>
        </div>
      </PageHeader>

      {/* filter bar */}
      <div className="flex items-center gap-2 border-b border-subtle bg-surface px-4 py-2 text-[12px]">
        <Segmented
          ariaLabel="Strategy type filter"
          options={[
            { value: 'All', label: 'All' },
            { value: 'Composite', label: 'Composite' },
            { value: 'Single', label: 'Single' },
          ]}
          value={typeFilter}
          onChange={setTypeFilter}
        />
        <FilterChip label="Run" value="SR-0184" />
        <FilterChip label="Range" value="2026 H1" />
        <FilterChip label="Status" value="Completed" />
        <span className="ml-auto text-[11px] text-faint">Higher Score / Return / Win Rate / Sharpe is better · less severe MDD is better</span>
      </div>

      <div className="min-h-0 flex-1 overflow-auto bg-surface">
        <table className="w-full border-collapse text-[13px]">
          <thead className="sticky top-0 z-10">
            <tr className="border-b border-line bg-surface text-left text-faint">
              {COLS.map((c) => (
                <th
                  key={c.key}
                  aria-sort={
                    c.sortable && sort === c.key
                      ? dir === 'desc' ? 'descending' : 'ascending'
                      : c.sortable ? 'none' : undefined
                  }
                  className={cn(
                    'h-[34px] whitespace-nowrap px-3 text-[11px] font-semibold uppercase tracking-wide',
                  )}
                >
                  {c.sortable ? (
                    <button
                      type="button"
                      title={COL_INFO[c.key as SortKey]}
                      onClick={() => toggleSort(c.key as SortKey)}
                      className="inline-flex items-center gap-1 select-none rounded-[3px] hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
                    >
                      {c.label}
                      {COL_INFO[c.key as SortKey] && <HelpCircle size={11} aria-hidden="true" />}
                      {sort === c.key && (dir === 'desc' ? <ArrowDown size={11} /> : <ArrowUp size={11} />)}
                    </button>
                  ) : (
                    c.label
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.rank}
                tabIndex={0}
                aria-label={`Open ${r.strategy}, rank ${r.rank}`}
                aria-selected={selected?.rank === r.rank}
                onClick={() => setSelected(r)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    setSelected(r)
                  }
                }}
                className={cn(
                  'h-9 cursor-pointer border-b border-subtle transition-colors',
                  selected?.rank === r.rank ? 'bg-surface-active' : 'hover:bg-surface-hover',
                  r.rank === 1 && 'border-l-2 border-l-accent',
                )}
              >
                <td className="px-3 font-mono tabular-nums text-faint">
                  {r.rank === 1 ? <span className="text-accent">#1</span> : `#${r.rank}`}
                </td>
                <td className="px-3 font-medium text-ink">{r.strategy}</td>
                <td className="px-3 font-mono font-semibold tabular-nums text-ml">{r.score}</td>
                <td className="px-3"><Delta value={r.ret} /></td>
                <td className="px-3 font-mono tabular-nums text-dim">{r.winRate}%</td>
                <td className="px-3 font-mono tabular-nums text-neg">{r.mdd}%</td>
                <td className="px-3 font-mono tabular-nums text-dim">{r.trades}</td>
                <td className="px-3 font-mono tabular-nums text-ink">{r.sharpe}</td>
                <td className="px-3 font-mono text-[11px] text-faint">{r.updated}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && <Inspector row={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function FilterChip({ label, value }: { label: string; value: string }) {
  return (
    <button className="inline-flex items-center gap-1.5 rounded-[5px] border border-subtle bg-workspace px-2 py-1 hover:bg-surface-hover">
      <span className="text-faint">{label}</span>
      <span className="font-mono text-ink">{value}</span>
      <ChevronDown size={12} className="text-faint" />
    </button>
  )
}
