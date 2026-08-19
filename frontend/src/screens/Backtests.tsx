import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, Fingerprint, Play, Square } from 'lucide-react'
import { useStore } from '../lib/store'
import type { RunRow, Trade } from '../domain'
import { BACKTEST_DEFAULTS } from '../config'
import { useServices } from '../services/registry'
import { PageHeader } from '../components/Shell'
import { CandleChart } from '../components/CandleChart'
import {
  Button,
  cn,
  Delta,
  Drawer,
  DrawerSection,
  EmptyState,
  HelperText,
  IconBtn,
  InfoNote,
  KV,
  Metric,
  MetricStrip,
  Modal,
  RecoBadge,
  Segmented,
  SignalTag,
  StatusBadge,
} from '../components/ui'

type Tab = 'single' | 'search' | 'runs'

// ---------------------------------------------------------------------------
// Trade table (shared shape with Leaderboard inspector)
// ---------------------------------------------------------------------------

export function TradeTable({
  trades,
  selected,
  onSelect,
  dense,
}: {
  trades: Trade[]
  selected: number | null
  onSelect: (n: number) => void
  dense?: boolean
}) {
  if (trades.length === 0) {
    return (
      <EmptyState
        title="Backtest completed with 0 simulated trades."
        hint="Metrics that require trades are unavailable."
      />
    )
  }
  return (
    <div className="h-full overflow-auto">
      <table className="w-full border-collapse text-[12px]">
        <thead className="sticky top-0 z-10">
          <tr className="border-b border-line bg-surface text-left text-faint">
            {['#', 'Entry Time', 'Side', 'Entry', 'Exit Time', 'Exit', 'P/L', 'Result'].map((h) => (
              <th key={h} className="h-[34px] whitespace-nowrap px-3 text-[11px] font-semibold uppercase tracking-wide">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr
              key={t.n}
              onClick={() => onSelect(t.n)}
              className={cn(
                'h-9 cursor-pointer border-b border-subtle transition-colors',
                selected === t.n ? 'bg-surface-active' : 'hover:bg-surface-hover',
              )}
            >
              <td className="px-3 font-mono text-faint">{t.n}</td>
              <td className="whitespace-nowrap px-3 font-mono tabular-nums text-dim">{t.entryTime}</td>
              <td className="px-3"><SignalTag side={t.side === 'BUY' ? 'buy' : 'sell'} /></td>
              <td className="px-3 font-mono tabular-nums text-ink">{t.entryPrice.toLocaleString()}</td>
              <td className="whitespace-nowrap px-3 font-mono tabular-nums text-dim">{t.exitTime}</td>
              <td className="px-3 font-mono tabular-nums text-ink">{t.exitPrice.toLocaleString()}</td>
              <td className="px-3"><Delta value={t.pl} /></td>
              <td className="px-3">
                <StatusBadge tone={t.result === 'WIN' ? 'win' : 'loss'}>{t.result}</StatusBadge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TAB A — Single Backtest
// ---------------------------------------------------------------------------

function SingleBacktest() {
  const { activeStrategy, showExplain, market } = useStore()
  const services = useServices()
  const [ran, setRan] = useState(true)
  const [running, setRunning] = useState(false)
  const [provenance, setProvenance] = useState(false)
  const [subView, setSubView] = useState<'equity' | 'drawdown'>('equity')
  const [selectedTrade, setSelectedTrade] = useState<number | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)

  const candles = useMemo(
    () => services.market.getCandles(BACKTEST_DEFAULTS.timeframe, 100),
    [services],
  )
  const markers = useMemo(() => services.market.getSignalMarkers(candles, 5), [candles, services])
  const trades = useMemo(() => services.backtests.makeTrades(3, 20), [services])
  const sel = trades.find((t) => t.n === selectedTrade)

  const run = () => {
    setRunning(true)
    setTimeout(() => {
      setRunning(false)
      setRan(true)
    }, 1200)
  }

  // equity curve derived from trades (deterministic)
  const equity = useMemo(() => {
    let e = 10000
    const pts = [e]
    for (const t of trades) {
      e += (t.pl / 100) * 1600
      pts.push(Math.round(e))
    }
    return pts
  }, [trades])

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {showExplain && (
        <div className="shrink-0 border-b border-subtle bg-surface px-4 py-3">
          <InfoNote>
            <span className="font-medium text-ink">What am I testing?</span> This replays{' '}
            <span className="font-medium text-ink">{activeStrategy}</span> over {market.display}{' '}
            {BACKTEST_DEFAULTS.timeframe} history
            (Jan–Jul 2026) and records the trades it would have signalled. Results show historical
            performance only — no real trades will be placed, and past results don't guarantee future
            outcomes.
          </InfoNote>
        </div>
      )}

      {/* config toolbar */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-subtle bg-surface px-4 py-2.5 text-[12px]">
        <Field label="Strategy" value={activeStrategy} accent />
        <Field label="Pair" value={market.pair} />
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wide text-faint">Timeframe</span>
          <span className="inline-flex items-center gap-1.5 font-mono text-[12px] text-ink">
            {BACKTEST_DEFAULTS.timeframe} {showExplain && <RecoBadge>Recommended</RecoBadge>}
          </span>
        </div>
        <Field label="Range" value={BACKTEST_DEFAULTS.rangeLabel} />
        <div className="ml-auto flex items-center gap-2">
          <IconBtn onClick={() => setProvenance(true)} title="Provenance"><Fingerprint size={15} /></IconBtn>
          <Button variant="primary" onClick={run} disabled={running}>
            <Play size={14} /> {running ? 'Running…' : 'Run Backtest'}
          </Button>
        </div>
      </div>

      {/* advanced execution settings */}
      <div className="shrink-0 border-b border-subtle bg-surface px-4 py-2">
        <button
          onClick={() => setShowAdvanced((v) => !v)}
          className="inline-flex items-center gap-1.5 text-[12px] font-medium text-dim hover:text-ink"
        >
          <ChevronDown size={13} className={cn('transition-transform', showAdvanced && 'rotate-180')} />
          Advanced execution settings
        </button>
        {showExplain && !showAdvanced && (
          <span className="ml-2 text-[11.5px] text-faint">
            Beginner-friendly defaults are applied. Open to fine-tune fees, slippage and sizing.
          </span>
        )}
        {showAdvanced && (
          <div className="mt-2.5 flex flex-wrap items-start gap-x-6 gap-y-2">
            <Field label="Dataset" value={BACKTEST_DEFAULTS.datasetId} />
            <Field label="Capital" value={`$${BACKTEST_DEFAULTS.capital.toLocaleString('en-US')}`} />
            <Field label="Fee" value={`${BACKTEST_DEFAULTS.feeRate * 100}%`} />
            <Field label="Slippage" value={`${BACKTEST_DEFAULTS.slippageRate * 100}%`} />
            <Field label="Position size" value={BACKTEST_DEFAULTS.positionSizing} />
            <Field label="Seed" value={String(BACKTEST_DEFAULTS.seed)} />
          </div>
        )}
      </div>

      {!ran ? (
        <EmptyState
          title="No backtests yet"
          hint="Pick a strategy and run your first backtest to see simulated trades and historical performance."
          action={
            <Button variant="primary" onClick={run}>
              <Play size={14} /> Run First Backtest
            </Button>
          }
        />
      ) : (
        <>
          <MetricStrip>
            <Metric
              label="Return"
              value="+24.2%"
              tone="pos"
              sub="vs baseline +4.8%"
              info="Total simulated gain or loss over the test period, after fees. Historical only."
            />
            <Metric
              label="Win Rate"
              value="62%"
              sub="50 / 81 trades"
              info="Share of simulated trades that ended profitably. A high win rate alone does not make a strategy good."
            />
            <Metric
              label="Max Drawdown"
              value="-7.1%"
              tone="neg"
              sub="peak-to-trough"
              info="The largest drop from a previous high during the test. Lower (closer to 0%) means a smoother ride."
            />
            <Metric label="Trades" value="81" sub="simulated" info="How many simulated trades the strategy took. Very few trades makes results less reliable." />
            <Metric
              label="Sharpe"
              value="1.56"
              sub="annualized"
              info="Return earned per unit of risk taken. Higher generally means steadier returns."
            />
            <Metric label="Profit Factor" value="1.94" info="Gross profit divided by gross loss. Above 1.0 means winners outweighed losers in this test." />
          </MetricStrip>

          {showExplain && (
            <div className="border-b border-subtle bg-surface px-4 py-2.5">
              <p className="text-[12.5px] leading-relaxed text-dim">
                <span className="font-medium text-ink">What happened?</span> Over this period the
                strategy produced a positive historical return of{' '}
                <span className="font-mono text-pos">+24.2%</span> across 81 simulated trades, winning
                about 62% of them. Along the way it experienced a{' '}
                <span className="font-mono text-neg">-7.1%</span> maximum drawdown — the worst dip from
                a prior high. This is one historical test, not a prediction.
              </p>
            </div>
          )}

          <div className="grid min-h-0 flex-1 grid-cols-[1.6fr_1fr] gap-px bg-subtle">
            {/* left: chart + equity */}
            <div className="flex min-h-0 flex-col bg-surface">
              <div className="flex h-8 items-center gap-2 border-b border-subtle px-3 text-[12px]">
                <span className="font-medium text-ink">Strategy visualization</span>
                <span className="font-mono text-[11px] text-faint">BTCUSDT · 15m</span>
                <div className="ml-auto flex items-center gap-2 text-[10px] text-faint">
                  <SignalTag side="buy" /> <SignalTag side="sell" />
                  <span className="font-mono">E / X entries</span>
                </div>
              </div>
              <div className="min-h-0 flex-1">
                <CandleChart
                  candles={candles}
                  overlays={{ ma20: true, sr: true }}
                  markers={markers}
                  height={300}
                  selectedInterval={sel ? [sel.entryIndex, sel.exitIndex] : null}
                />
              </div>
              <div className="border-t border-subtle">
                <div className="flex h-8 items-center gap-2 px-3">
                  <Segmented
                    ariaLabel="Result chart"
                    options={[
                      { value: 'equity', label: 'Equity Curve' },
                      { value: 'drawdown', label: 'Drawdown' },
                    ]}
                    value={subView}
                    onChange={(v) => setSubView(v as typeof subView)}
                  />
                </div>
                <Sparkline points={equity} mode={subView} />
              </div>
            </div>

            {/* right: trades */}
            <div className="flex min-h-0 flex-col bg-surface">
              <div className="flex h-8 items-center justify-between border-b border-subtle px-3 text-[12px]">
                <span className="font-medium text-ink">Simulated trades</span>
                <span className="font-mono text-[11px] text-faint">{trades.length} trades</span>
              </div>
              <div className="min-h-0 flex-1">
                <TradeTable trades={trades} selected={selectedTrade} onSelect={setSelectedTrade} />
              </div>
            </div>
          </div>
        </>
      )}

      <Drawer open={provenance} onClose={() => setProvenance(false)} title="Provenance" subtitle="BT-1846 · reproducibility record">
        <DrawerSection title="Strategy">
          <KV k="Definition" v={activeStrategy} />
          <KV k="Version" v={<span className="text-ml">v2 (immutable)</span>} />
          <KV k="Parameters" v="MA 20/50 · RSI 14 · SR 120" />
        </DrawerSection>
        <DrawerSection title="Dataset">
          <KV k="Dataset" v="BINANCE-BTCUSDT-15M-2026H1" />
          <KV k="Range" v="2026-01-01 → 2026-07-01" />
          <KV k="Checksum" v="a3f9…c210" />
        </DrawerSection>
        <DrawerSection title="Execution">
          <KV k="Fee" v="0.04%" />
          <KV k="Slippage" v="0.02%" />
          <KV k="Position size" v="100% equity" />
          <KV k="Scoring policy" v="Balanced v2" />
        </DrawerSection>
        <DrawerSection title="Run">
          <KV k="Backtest Run ID" v="BT-1846" />
          <KV k="Generator" v="—" />
          <KV k="Seed" v="424242" />
          <KV k="Timestamp" v="2026-08-16 18:24:05" />
        </DrawerSection>
      </Drawer>
    </div>
  )
}

function Field({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-faint">{label}</span>
      <span className={cn('font-mono text-[12px]', accent ? 'text-accent' : 'text-ink')}>{value}</span>
    </div>
  )
}

function Sparkline({ points, mode }: { points: number[]; mode: 'equity' | 'drawdown' }) {
  const w = 700
  const h = 90
  const data = useMemo(() => {
    if (mode === 'equity') return points
    // drawdown: distance below running max
    let peak = points[0]
    return points.map((p) => {
      peak = Math.max(peak, p)
      return ((p - peak) / peak) * 100
    })
  }, [points, mode])
  const min = Math.min(...data)
  const max = Math.max(...data)
  const x = (i: number) => (i / (data.length - 1)) * w
  const y = (v: number) => h - ((v - min) / (max - min || 1)) * (h - 8) - 4
  const path = data.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const color = mode === 'equity' ? '#21C58B' : '#F05B64'
  return (
    <div className="px-3 pb-3">
      <svg viewBox={`0 0 ${w} ${h}`} className="h-[90px] w-full" preserveAspectRatio="none">
        <path d={`${path} L${w},${h} L0,${h} Z`} fill={`${color}18`} />
        <path d={path} fill="none" stroke={color} strokeWidth={1.5} />
      </svg>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TAB B — Strategy Search
// ---------------------------------------------------------------------------

function StrategySearch() {
  const { searchStatus, searchTested, startSearch, stopSearch, toast, showExplain, market } = useStore()
  const services = useServices()
  const searchRun = services.backtests.searchRun
  const leaderboard = services.leaderboard.listEntries()
  const [confirmStop, setConfirmStop] = useState(false)
  const [level, setLevel] = useState<'basic' | 'advanced'>('basic')
  const limit = level === 'basic' ? 100 : searchRun.candidateLimit
  const shownTested = Math.min(searchTested, limit)
  const pct = Math.min(100, (shownTested / limit) * 100)

  // deterministic rolling candidate feed
  const feed = useMemo(() => {
    const items: { id: number; name: string; score: number; isTop?: boolean; failed?: boolean }[] = []
    for (let i = 0; i < 7; i++) {
      const id = searchTested - i
      if (id < 0) break
      const name = services.backtests.candidateNames[id % services.backtests.candidateNames.length]
      const score = 70 + ((id * 37) % 160) / 10
      items.push({
        id,
        name,
        score: Math.round(score * 10) / 10,
        isTop: i === 0 && score > 83,
        failed: id % 41 === 0,
      })
    }
    return items
  }, [searchTested])

  return (
    <div className="flex h-full flex-col">
      <div className="csl-search-grid grid min-h-0 flex-1 grid-cols-[340px_1fr_300px] gap-px bg-subtle">
        {/* left config */}
        <div className="flex min-h-0 flex-col overflow-y-auto bg-surface">
          <div className="flex h-9 items-center justify-between border-b border-subtle px-3 text-[13px] font-semibold text-ink">
            Search Configuration
            <Segmented
              ariaLabel="Search configuration level"
              options={[
                { value: 'basic', label: 'Basic' },
                { value: 'advanced', label: 'Advanced' },
              ]}
              value={level}
              onChange={(v) => setLevel(v as typeof level)}
            />
          </div>
          <div className="space-y-4 p-3 text-[12px]">
            {showExplain && (
              <HelperText>
                A search tries many strategy combinations for you and ranks them, so you don't have to
                build each one by hand.
              </HelperText>
            )}
            <ConfigRow label="Market" value={market.pair} />
            <ConfigRow label="Timeframe" value={BACKTEST_DEFAULTS.timeframe} />
            <div>
              <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-faint">Strategies to combine</div>
              <div className="flex flex-wrap gap-1.5">
                {['MA', 'RSI', 'Bollinger', 'S/R'].map((s) => (
                  <span key={s} className="rounded-[4px] border border-accent/40 bg-accent/10 px-2 py-1 font-mono text-[11px] text-accent">
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <ConfigRow label="Combination size" value="2 – 4" />
            <ConfigRow label="Candidates to try" value={level === 'basic' ? '100' : '2,000'} />

            {level === 'advanced' && (
              <>
                <div className="border-t border-subtle pt-3">
                  <ConfigRow label="Generator" value="Random Search v1" ml />
                </div>
                <ConfigRow label="Parameter ranges" value="Default" />
                <ConfigRow label="Seed" value={String(BACKTEST_DEFAULTS.seed)} />
                <ConfigRow label="Dataset" value={`${market.pair} · ${BACKTEST_DEFAULTS.timeframe} · 2026 H1`} />
                <ConfigRow label="Workers" value={String(searchRun.workers)} />
                <ConfigRow label="Stop condition" value="Candidate limit reached" />
              </>
            )}

            <div className="pt-1">
              {searchStatus === 'running' ? (
                <Button variant="danger" className="w-full" onClick={() => setConfirmStop(true)}>
                  <Square size={13} /> Stop Search
                </Button>
              ) : (
                <Button
                  variant="primary"
                  className="w-full"
                  onClick={() => {
                    startSearch()
                    toast(`Search started — ${limit.toLocaleString()} candidates`, 'info')
                  }}
                >
                  <Play size={14} /> {level === 'basic' ? 'Find Strategy Combinations' : 'Start Search'}
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* center run */}
        <div className="flex min-h-0 flex-col overflow-y-auto bg-surface">
          <div className="border-b border-subtle p-4">
            <div className="flex items-center gap-2">
              <span className="text-[13px] font-semibold text-ink">Experiment Progress</span>
              {searchStatus === 'running' && <StatusBadge tone="running" pulse>Running</StatusBadge>}
              {searchStatus === 'ready' && <StatusBadge tone="queued">Ready</StatusBadge>}
              {searchStatus === 'stopped' && <StatusBadge tone="cancelled">Stopped</StatusBadge>}
              {searchStatus === 'completed' && <StatusBadge tone="completed">Completed</StatusBadge>}
              <span className="ml-auto font-mono text-[11px] text-faint">{searchRun.id}</span>
            </div>
            <div className="mt-3 flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-active">
                <div className="h-full rounded-full bg-accent transition-[width] duration-500" style={{ width: `${pct}%` }} />
              </div>
              <span className="font-mono text-[13px] font-semibold tabular-nums text-ink">
                {shownTested} / {limit}
              </span>
              <span className="font-mono text-[12px] tabular-nums text-faint">combinations</span>
            </div>
            <div className="mt-3 flex items-center justify-between rounded-[6px] border border-accent/30 bg-accent/10 px-3 py-2">
              <span className="text-[12px] text-dim">Current best combination</span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[12px] text-ink">{leaderboard[0].strategy}</span>
                <span className="font-mono text-[13px] font-semibold tabular-nums text-ml">
                  {leaderboard[0].score}
                </span>
              </div>
            </div>
            {showExplain && (
              <p className="mt-2 text-[11.5px] leading-relaxed text-faint">
                The metrics below show how the system is processing experiments behind the scenes —
                you don't need them to read the results.
              </p>
            )}
            <div className="mt-3 grid grid-cols-5 gap-2 text-center">
              {[
                ['Generated', searchTested],
                ['Completed', searchTested - 6],
                ['Queued', searchRun.queue],
                ['Failed', searchRun.failed],
                ['Retried', searchRun.retried],
              ].map(([l, v]) => (
                <div key={l as string} className="rounded-[6px] border border-subtle bg-workspace py-2">
                  <div className="font-mono text-[14px] font-semibold tabular-nums text-ink">{v as number}</div>
                  <div className="text-[10px] uppercase text-faint">{l as string}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex-1 p-3">
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-faint">Live candidate feed</div>
            <div className="space-y-1">
              {feed.map((f, i) => (
                <div
                  key={f.id}
                  className={cn(
                    'flex items-center gap-2 rounded-[5px] border border-subtle px-2.5 py-1.5 font-mono text-[11px]',
                    i === 0 && searchStatus === 'running' && 'csl-flash',
                  )}
                >
                  <span className="text-faint">#{String(f.id).padStart(4, '0')}</span>
                  <span className="flex-1 text-dim">{f.name}</span>
                  {f.failed ? (
                    <StatusBadge tone="failed">Failed · retry 1/3</StatusBadge>
                  ) : (
                    <>
                      <span className="text-ml">Score {f.score.toFixed(1)}</span>
                      {f.isTop && <StatusBadge tone="new">New Top</StatusBadge>}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* health strip */}
          <div className="grid grid-cols-6 divide-x divide-subtle border-t border-subtle bg-workspace text-center">
            {[
              ['Workers', '4 / 4'],
              ['Queue', '218'],
              ['Failed', '3'],
              ['Retried', '2'],
              ['Throughput', '6.8/s'],
              ['Top-1', '84.1'],
            ].map(([l, v]) => (
              <div key={l} className="py-2">
                <div className="font-mono text-[12px] font-semibold tabular-nums text-ink">{v}</div>
                <div className="text-[10px] uppercase text-faint">{l}</div>
              </div>
            ))}
          </div>
        </div>

        {/* right top-k */}
        <div className="flex min-h-0 flex-col bg-surface">
          <div className="flex h-9 items-center gap-2 border-b border-subtle px-3 text-[13px] font-semibold text-ink">
            Live Top-K
            <StatusBadge tone="running" pulse>Live</StatusBadge>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">
            {leaderboard.map((r) => (
              <div
                key={r.rank}
                className={cn(
                  'flex items-center gap-2 border-b border-subtle px-3 py-2.5',
                  r.rank === 1 && 'border-l-2 border-l-accent',
                )}
              >
                <span className="w-4 font-mono text-[12px] text-faint">{r.rank}</span>
                <span className={cn('flex-1 truncate text-[12px]', r.rank === 1 ? 'text-ink' : 'text-dim')}>
                  {r.strategy}
                </span>
                <span className="font-mono text-[13px] font-semibold tabular-nums text-ml">{r.score}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Modal
        open={confirmStop}
        onClose={() => setConfirmStop(false)}
        title="Stop search SR-0184?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmStop(false)}>Cancel</Button>
            <Button
              variant="danger"
              onClick={() => {
                stopSearch()
                setConfirmStop(false)
                toast('Search stopped — completed candidates preserved', 'warning')
              }}
            >
              Stop Search
            </Button>
          </>
        }
      >
        Stopping the run will let currently running jobs finish, stop generating new candidates, and
        preserve all completed results and the current Top-K. Queued jobs will be discarded.
      </Modal>
    </div>
  )
}

function ConfigRow({ label, value, ml }: { label: string; value: string; ml?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-[11px] uppercase tracking-wide text-faint">{label}</span>
      <span className={cn('font-mono text-[12px]', ml ? 'text-ml' : 'text-ink')}>{value}</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// TAB C — Runs
// ---------------------------------------------------------------------------

const RUN_TONE = {
  QUEUED: 'queued',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
} as const

function Runs() {
  const services = useServices()
  const runs = services.backtests.listRuns()
  const [selected, setSelected] = useState<RunRow | null>(null)
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead className="sticky top-0 z-10">
            <tr className="border-b border-line bg-surface text-left text-faint">
              {['Run ID', 'Type', 'Strategy / Search Space', 'Status', 'Started', 'Duration', 'Tested', 'Failed', 'Top-1', 'Generator', 'Seed'].map((h) => (
                <th key={h} className="h-[34px] whitespace-nowrap px-3 text-[11px] font-semibold uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr
                key={r.id}
                onClick={() => setSelected(r)}
                className={cn(
                  'h-9 cursor-pointer border-b border-subtle transition-colors',
                  selected?.id === r.id ? 'bg-surface-active' : 'hover:bg-surface-hover',
                )}
              >
                <td className="px-3 font-mono text-accent">{r.id}</td>
                <td className="px-3">
                  <span className={cn('font-mono text-[11px]', r.type === 'Search' ? 'text-ml' : 'text-dim')}>{r.type}</span>
                </td>
                <td className="px-3 font-mono text-dim">{r.space}</td>
                <td className="px-3"><StatusBadge tone={RUN_TONE[r.status]} pulse={r.status === 'RUNNING'}>{r.status}</StatusBadge></td>
                <td className="px-3 font-mono tabular-nums text-dim">{r.started}</td>
                <td className="px-3 font-mono tabular-nums text-dim">{r.duration}</td>
                <td className="px-3 font-mono tabular-nums text-ink">{r.tested ?? '—'}</td>
                <td className="px-3 font-mono tabular-nums text-neg">{r.failed || '—'}</td>
                <td className="px-3 font-mono tabular-nums text-ml">{r.top1 ?? '—'}</td>
                <td className="px-3 font-mono text-faint">{r.generator}</td>
                <td className="px-3 font-mono tabular-nums text-faint">{r.seed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Drawer open={!!selected} onClose={() => setSelected(null)} title={selected?.id ?? ''} subtitle={selected ? `${selected.type} run` : ''}>
        {selected && (
          <>
            <DrawerSection title="Status">
              <div className="mb-2"><StatusBadge tone={RUN_TONE[selected.status]}>{selected.status}</StatusBadge></div>
              {selected.reason && (
                <div className="rounded-[5px] border border-neg/30 bg-neg/10 px-2 py-1.5 text-[11px] text-neg">
                  {selected.reason}
                </div>
              )}
            </DrawerSection>
            <DrawerSection title="Summary">
              <KV k="Search space" v={selected.space} />
              <KV k="Started" v={selected.started} />
              <KV k="Duration" v={selected.duration} />
              <KV k="Tested" v={selected.tested ?? '—'} />
              <KV k="Failed" v={selected.failed} />
              <KV k="Top-1 score" v={selected.top1 ?? '—'} />
            </DrawerSection>
            <DrawerSection title="Reproducibility">
              <KV k="Generator" v={selected.generator} />
              <KV k="Seed" v={selected.seed} />
              <KV k="Dataset" v="BINANCE-BTCUSDT-15M-2026H1" />
              <KV k="Scoring policy" v="Balanced v2" />
            </DrawerSection>
          </>
        )}
      </Drawer>
    </div>
  )
}

// ---------------------------------------------------------------------------

export function Backtests() {
  const { requestedBacktestTab, consumeBacktestTab } = useStore()
  const [tab, setTab] = useState<Tab>('single')

  useEffect(() => {
    if (requestedBacktestTab) {
      setTab(requestedBacktestTab)
      consumeBacktestTab()
    }
  }, [requestedBacktestTab, consumeBacktestTab])

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="Backtests">
        <Segmented
          ariaLabel="Backtest section"
          size="md"
          options={[
            { value: 'single', label: 'Single Backtest' },
            { value: 'search', label: 'Strategy Search' },
            { value: 'runs', label: 'Runs' },
          ]}
          value={tab}
          onChange={(v) => setTab(v as Tab)}
        />
      </PageHeader>
      <div className="min-h-0 flex-1">
        {tab === 'single' && <SingleBacktest />}
        {tab === 'search' && <StrategySearch />}
        {tab === 'runs' && <Runs />}
      </div>
    </div>
  )
}
