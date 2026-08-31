import { useEffect, useMemo, useRef, useState } from 'react'
import { ChevronDown, Fingerprint, Play, Square } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { useStore } from '../lib/store'
import type { Trade } from '../domain'
import type { Candle, Marker } from '../lib/mock'
import { BACKTEST_DEFAULTS } from '../config'
import {
  BacktestApiError,
  createBacktestApi,
  type BacktestStrategy,
  type ParameterValue,
  type PolicyBundle,
  type SingleBacktestOutput,
  type StrategyDefinition,
  createSearchApi,
  type SearchCandidate,
  type SearchRun,
  type BacktestRunSummary,
} from '../features/backtests'
import {
  getStrategyConfiguration,
  type SavedStrategyConfiguration,
} from '../services/strategyConfigurations'
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

function LegacySingleBacktest() {
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

const backtestApi = createBacktestApi()

function SingleBacktest() {
  const { showExplain, market, setMarket, timeframe, setTimeframe, setActiveStrategy, toast } = useStore()
  const [searchParams, setSearchParams] = useSearchParams()
  const requestedConfigurationId = searchParams.get('configurationId')
  const [strategies, setStrategies] = useState<BacktestStrategy[]>([])
  const [policies, setPolicies] = useState<PolicyBundle | null>(null)
  const [strategyId, setStrategyId] = useState('')
  const [parameters, setParameters] = useState<Record<string, ParameterValue>>({})
  const [startDate, setStartDate] = useState('2026-08-01')
  const [endDate, setEndDate] = useState('2026-08-08')
  const [capital, setCapital] = useState(String(BACKTEST_DEFAULTS.capital))
  const [feeRate, setFeeRate] = useState(String(BACKTEST_DEFAULTS.feeRate))
  const [slippageRate, setSlippageRate] = useState(String(BACKTEST_DEFAULTS.slippageRate))
  const [randomSeed, setRandomSeed] = useState(String(BACKTEST_DEFAULTS.seed))
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [output, setOutput] = useState<SingleBacktestOutput | null>(null)
  const [provenance, setProvenance] = useState(false)
  const [subView, setSubView] = useState<'equity' | 'drawdown'>('equity')
  const [selectedTrade, setSelectedTrade] = useState<number | null>(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [savedConfiguration, setSavedConfiguration] = useState<SavedStrategyConfiguration | null>(null)
  const activeRequest = useRef<AbortController | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([
      backtestApi.loadCatalog(controller.signal),
      requestedConfigurationId
        ? getStrategyConfiguration(requestedConfigurationId, controller.signal)
        : Promise.resolve(null),
    ]).then(([catalog, configuration]) => {
      let nextStrategies = catalog.strategies
      setPolicies(catalog.policies)
      if (configuration) {
        const configuredStrategy = configurationStrategy(configuration)
        nextStrategies = [
          configuredStrategy,
          ...nextStrategies.filter((item) => item.strategyId !== configuredStrategy.strategyId),
        ]
        setSavedConfiguration(configuration)
        setStrategyId(configuredStrategy.strategyId)
        setActiveStrategy(configuration.displayName)
        setParameters(configuration.kind === 'SINGLE' ? configuration.members[0].parameters : {})
        setMarket(configuration.selection.pair)
        setTimeframe(configuration.selection.timeframe as typeof timeframe)
      }
      setStrategies(nextStrategies)
      const first = nextStrategies[0]
      if (first && !configuration) {
        setStrategyId(first.strategyId)
        setActiveStrategy(first.displayName)
        setParameters(defaultParameters(first))
      }
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(backtestErrorMessage(reason))
    }).finally(() => {
      if (!controller.signal.aborted) setCatalogLoading(false)
    })
    return () => controller.abort()
  }, [requestedConfigurationId, setActiveStrategy, setMarket, setTimeframe])

  useEffect(() => () => activeRequest.current?.abort(), [])

  const selectedStrategy = strategies.find((item) => item.strategyId === strategyId) ?? null
  const candles = useMemo<Candle[]>(() => (output?.candles ?? []).map((item) => ({
    t: Date.parse(item.openTime),
    o: Number(item.open),
    h: Number(item.high),
    l: Number(item.low),
    c: Number(item.close),
    v: Number(item.volume),
  })), [output])
  const candleIndex = useMemo(
    () => new Map(candles.map((item, index) => [item.t, index])),
    [candles],
  )
  const trades = useMemo<Trade[]>(() => (output?.trades ?? []).map((item) => ({
    n: item.sequence + 1,
    entryTime: shortBacktestTime(item.entryTime),
    side: 'BUY',
    entryPrice: Number(item.entryPrice),
    exitTime: shortBacktestTime(item.exitTime),
    exitPrice: Number(item.exitPrice),
    pl: Number(item.returnPercent),
    result: Number(item.profitLoss) >= 0 ? 'WIN' : 'LOSS',
    entryIndex: candleIndex.get(Date.parse(item.entryTime)) ?? 0,
    exitIndex: candleIndex.get(Date.parse(item.exitTime)) ?? Math.max(0, candles.length - 1),
  })), [candleIndex, candles.length, output])
  const markers = useMemo<Marker[]>(
    () => trades.flatMap((trade) => [
      { index: trade.entryIndex, kind: 'entry' as const },
      { index: trade.exitIndex, kind: 'exit' as const },
    ]),
    [trades],
  )
  const selected = trades.find((trade) => trade.n === selectedTrade)
  const equity = useMemo(() => {
    const points = (output?.equity ?? []).map((item) => Number(item.equity))
    return points.length === 1 ? [points[0], points[0]] : points
  }, [output])
  const metrics = output?.evaluation.metrics

  const execute = async () => {
    if (!selectedStrategy || !policies) return
    if (startDate >= endDate) {
      setError('Start date must be before end date.')
      return
    }
    if (!Number.isSafeInteger(Number(randomSeed))) {
      setError('Seed must be a safe integer.')
      return
    }
    activeRequest.current?.abort()
    const controller = new AbortController()
    activeRequest.current = controller
    setRunning(true)
    setError(null)
    try {
      const result = await backtestApi.runSingleBacktest({
        strategy: selectedStrategy,
        parameters,
        definition: savedConfiguration ? configurationDefinition(savedConfiguration) : undefined,
        policies,
        selection: { provider: 'BINANCE', pair: market.pair, timeframe },
        range: {
          startTime: `${startDate}T00:00:00.000Z`,
          endTime: `${endDate}T00:00:00.000Z`,
        },
        initialCapital: capital,
        feeRate,
        slippageRate,
        randomSeed: Number(randomSeed),
        jobId: crypto.randomUUID(),
        signal: controller.signal,
      })
      setOutput(result)
      setSelectedTrade(null)
      toast(`Backtest completed · score ${displayBacktestNumber(result.evaluation.score)}`, 'positive')
    } catch (reason) {
      if (!controller.signal.aborted) {
        const message = backtestErrorMessage(reason)
        setError(message)
        toast(message, 'warning')
      }
    } finally {
      setRunning(false)
      if (activeRequest.current === controller) activeRequest.current = null
    }
  }

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {showExplain && (
        <div className="shrink-0 border-b border-subtle bg-surface px-4 py-3">
          <InfoNote>
            The browser requests an immutable Dataset and Strategy Definition, then the backend calculates
            all Signals, simulated Trades, Equity Points, metrics and score. No real trades are placed.
          </InfoNote>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-subtle bg-surface px-4 py-2.5 text-[12px]">
        <label className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wide text-faint">Strategy</span>
          <select
            id="select-strategy-backtest"
            value={strategyId}
            disabled={catalogLoading || running}
            onChange={(event) => {
              const next = strategies.find((item) => item.strategyId === event.target.value)
              if (!next) return
              setStrategyId(next.strategyId)
              setSavedConfiguration(null)
              setSearchParams({}, { replace: true })
              setActiveStrategy(next.displayName)
              setParameters(defaultParameters(next))
              setOutput(null)
            }}
            className="border-0 bg-transparent font-mono text-[12px] text-accent outline-none"
          >
            {strategies.map((item) => (
              <option key={`${item.strategyId}@${item.strategyVersion}`} value={item.strategyId}>
                {item.displayName} · {item.strategyVersion}
              </option>
            ))}
          </select>
        </label>
        <Field label="Pair" value={market.pair} />
        <label className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wide text-faint">Timeframe</span>
          <select
            value={timeframe}
            disabled={running}
            onChange={(event) => {
              setTimeframe(event.target.value as typeof timeframe)
              setOutput(null)
            }}
            className="border-0 bg-transparent font-mono text-[12px] text-ink outline-none"
          >
            {['1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d'].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <DateInput label="Start" value={startDate} onChange={(value) => { setStartDate(value); setOutput(null) }} disabled={running} />
        <DateInput label="End (exclusive)" value={endDate} onChange={(value) => { setEndDate(value); setOutput(null) }} disabled={running} />
        <div className="ml-auto flex items-center gap-2">
          {output && <IconBtn onClick={() => setProvenance(true)} title="Provenance"><Fingerprint size={15} /></IconBtn>}
          <Button
            id="btn-run-backtest"
            variant="primary"
            onClick={() => void execute()}
            disabled={running || catalogLoading || !selectedStrategy || !policies}
          >
            <Play size={14} /> {catalogLoading ? 'Loading contract…' : running ? 'Running…' : 'Run Backtest'}
          </Button>
        </div>
      </div>

      <div className="shrink-0 border-b border-subtle bg-surface px-4 py-2">
        <button onClick={() => setShowAdvanced((value) => !value)} className="inline-flex items-center gap-1.5 text-[12px] font-medium text-dim hover:text-ink">
          <ChevronDown size={13} className={cn('transition-transform', showAdvanced && 'rotate-180')} />
          Exact execution settings
        </button>
        {showAdvanced && (
          <div className="mt-2.5 flex flex-wrap items-start gap-x-6 gap-y-2">
            <ExactInput label="Capital" value={capital} onChange={setCapital} disabled={running} />
            <ExactInput label="Fee rate" value={feeRate} onChange={setFeeRate} disabled={running} />
            <ExactInput label="Slippage rate" value={slippageRate} onChange={setSlippageRate} disabled={running} />
            <Field label="Position size" value="100% available cash" />
            <ExactInput label="Seed" value={randomSeed} onChange={setRandomSeed} disabled={running} />
            {selectedStrategy?.parameters.map((parameter) => (
              <ExactInput
                key={parameter.name}
                label={parameter.name}
                value={String(parameters[parameter.name] ?? '')}
                disabled={running || savedConfiguration !== null}
                onChange={(value) => setParameters((current) => ({
                  ...current,
                  [parameter.name]: parameter.valueType === 'INTEGER' ? Number(value) : value,
                }))}
              />
            ))}
          </div>
        )}
      </div>

      {error && (
        <div id="message-error" role="alert" className="border-b border-neg/30 bg-neg/10 px-4 py-2 text-[12px] text-neg">
          {error}
        </div>
      )}

      {!output ? (
        <EmptyState
          title={running ? 'Backtest workflow is running' : 'No backend result loaded'}
          hint={running ? 'Materializing Dataset, executing the exact Strategy and evaluating the immutable result.' : 'Choose an exact strategy and range, then run the first real backend Backtest.'}
          action={!running ? <Button variant="primary" onClick={() => void execute()} disabled={catalogLoading || !selectedStrategy || !policies}><Play size={14} /> Run Backtest</Button> : undefined}
        />
      ) : (
        <>
          <MetricStrip>
            <Metric label="Return" value={signedBacktestPercent(metrics?.totalReturn ?? '0')} tone={Number(metrics?.totalReturn ?? 0) >= 0 ? 'pos' : 'neg'} sub={`score ${displayBacktestNumber(output.evaluation.score)}`} info="Backend-calculated Total Return after fees and slippage." />
            <Metric label="Win Rate" value={`${displayBacktestNumber(metrics?.winRate ?? '0')}%`} sub={`${metrics?.numberOfTrades ?? 0} closed trades`} info="Backend-calculated winning Trade percentage." />
            <Metric label="Max Drawdown" value={`-${displayBacktestNumber(metrics?.maxDrawdown ?? '0')}%`} tone="neg" sub="peak-to-trough" info="Backend-calculated maximum peak-to-trough decline." />
            <Metric label="Trades" value={String(metrics?.numberOfTrades ?? 0)} sub="simulated" info="Closed simulated Trades persisted by Feature 004." />
            <Metric label="Sharpe" value={metrics?.sharpeRatio === null ? 'N/A' : displayBacktestNumber(metrics?.sharpeRatio ?? '0')} sub="annualized" info="Null when the immutable result has insufficient or zero-variance returns." />
            <Metric label="Profit Factor" value={metrics?.profitFactor === null ? 'N/A' : displayBacktestNumber(metrics?.profitFactor ?? '0')} info="Null when the result has no gross loss." />
          </MetricStrip>

          <div className="grid min-h-0 flex-1 grid-cols-[1.6fr_1fr] gap-px bg-subtle">
            <div className="flex min-h-0 flex-col bg-surface">
              <div className="flex h-8 items-center gap-2 border-b border-subtle px-3 text-[12px]">
                <span className="font-medium text-ink">Persisted Dataset and Trade markers</span>
                <span className="font-mono text-[11px] text-faint">{output.dataset.selection.pair} · {output.dataset.selection.timeframe}</span>
                <div className="ml-auto flex items-center gap-2 text-[10px] text-faint"><span className="font-mono">E / X persisted fills</span></div>
              </div>
              <div className="min-h-0 flex-1">
                {candles.length > 0 && <CandleChart candles={candles} overlays={{}} markers={markers} height={300} selectedInterval={selected ? [selected.entryIndex, selected.exitIndex] : null} />}
              </div>
              <div className="border-t border-subtle">
                <div className="flex h-8 items-center gap-2 px-3">
                  <Segmented ariaLabel="Result chart" options={[{ value: 'equity', label: 'Equity Curve' }, { value: 'drawdown', label: 'Drawdown' }]} value={subView} onChange={(value) => setSubView(value as typeof subView)} />
                </div>
                {equity.length > 0 && <Sparkline points={equity} mode={subView} />}
              </div>
            </div>
            <div className="flex min-h-0 flex-col bg-surface">
              <div className="flex h-8 items-center justify-between border-b border-subtle px-3 text-[12px]"><span className="font-medium text-ink">Simulated trades</span><span className="font-mono text-[11px] text-faint">{trades.length} trades</span></div>
              <div className="min-h-0 flex-1"><TradeTable trades={trades} selected={selectedTrade} onSelect={setSelectedTrade} /></div>
            </div>
          </div>
        </>
      )}

      <Drawer open={provenance && !!output} onClose={() => setProvenance(false)} title="Provenance" subtitle={`${output?.run.id ?? ''} · immutable record`}>
        <DrawerSection title="Strategy">
          <KV k="Definition" v={output?.definition.definitionId ?? '—'} />
          <KV k="Version" v={output ? `${output.definition.strategyId}@${output.definition.strategyVersion}` : '—'} />
          <KV k="Parameters" v={output ? JSON.stringify(output.definition.parameters) : '—'} />
        </DrawerSection>
        <DrawerSection title="Dataset">
          <KV k="Dataset" v={output?.dataset.datasetId ?? '—'} />
          <KV k="Candles" v={output?.dataset.candleCount ?? '—'} />
          <KV k="Checksum" v={output?.dataset.checksum ?? '—'} />
        </DrawerSection>
        <DrawerSection title="Execution and Evaluation">
          <KV k="Run" v={output?.run.id ?? '—'} />
          <KV k="Result checksum" v={output?.result.resultChecksum ?? '—'} />
          <KV k="Execution policy" v={output ? `${output.run.executionPolicyId}@${output.run.executionPolicyVersion}` : '—'} />
          <KV k="Evaluation policy" v={output ? `${output.evaluation.evaluationPolicyId}@${output.evaluation.evaluationPolicyVersion}` : '—'} />
          <KV k="Scoring policy" v={output ? `${output.evaluation.scoringPolicyId}@${output.evaluation.scoringPolicyVersion}` : '—'} />
        </DrawerSection>
        <DrawerSection title="Analysis boundary"><p className="text-[11px] text-dim">{output?.result.disclaimer}</p></DrawerSection>
      </Drawer>
    </div>
  )
}

function defaultParameters(strategy: BacktestStrategy): Record<string, ParameterValue> {
  return Object.fromEntries(
    strategy.parameters
      .filter((parameter) => parameter.defaultValue !== null)
      .map((parameter) => [parameter.name, parameter.defaultValue as ParameterValue]),
  )
}

function configurationStrategy(configuration: SavedStrategyConfiguration): BacktestStrategy {
  const single = configuration.kind === 'SINGLE' ? configuration.members[0] : null
  return {
    strategyId: `saved:${configuration.configurationId}`,
    strategyType: configuration.kind,
    displayName: `${configuration.displayName} · config v${configuration.configurationVersion}`,
    strategyVersion: single?.strategyVersion ?? '1.0.0',
    contractVersion: '1.0.0',
    status: 'AVAILABLE',
    origin: 'SAVED_CONFIGURATION',
    parameters: [],
  }
}

function configurationDefinition(configuration: SavedStrategyConfiguration): StrategyDefinition {
  const single = configuration.kind === 'SINGLE' ? configuration.members[0] : null
  return {
    definitionId: configuration.rootDefinitionId,
    strategyId: single?.strategyId ?? configuration.configurationKey,
    strategyType: configuration.kind,
    strategyVersion: single?.strategyVersion ?? '1.0.0',
    contractVersion: '1.0.0',
    parameters: single?.parameters ?? {},
    parameterSchemaFingerprint: configuration.contentFingerprint,
    contentFingerprint: configuration.contentFingerprint,
    createdAt: configuration.createdAt,
    origin: 'BUILT_IN',
  }
}

function backtestErrorMessage(reason: unknown): string {
  if (reason instanceof BacktestApiError) return `${reason.code}: ${reason.message}`
  return reason instanceof Error ? reason.message : 'The Backtest could not be completed.'
}

function shortBacktestTime(value: string): string {
  return value.replace('T', ' ').slice(0, 16)
}

function displayBacktestNumber(value: string): string {
  const number = Number(value)
  return Number.isFinite(number)
    ? number.toLocaleString('en-US', { maximumFractionDigits: 4 })
    : 'N/A'
}

function signedBacktestPercent(value: string): string {
  return `${Number(value) >= 0 ? '+' : ''}${displayBacktestNumber(value)}%`
}

function ExactInput({ label, value, onChange, disabled }: { label: string; value: string; onChange: (value: string) => void; disabled?: boolean }) {
  return (
    <label className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-faint">{label}</span>
      <input value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} className="w-28 border-b border-subtle bg-transparent font-mono text-[12px] text-ink outline-none focus:border-accent" />
    </label>
  )
}

function DateInput({ label, value, onChange, disabled }: { label: string; value: string; onChange: (value: string) => void; disabled?: boolean }) {
  return (
    <label className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-faint">{label}</span>
      <input type="date" value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} className="bg-transparent font-mono text-[12px] text-ink" />
    </label>
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
  const { toast, showExplain, market, timeframe, setTimeframe } = useStore()
  const api = useMemo(() => createSearchApi(), [])
  const catalogApi = useMemo(() => createBacktestApi(), [])
  const [confirmStop, setConfirmStop] = useState(false)
  const [level, setLevel] = useState<'basic' | 'advanced'>('basic')
  const [run, setRun] = useState<SearchRun | null>(null)
  const [feed, setFeed] = useState<SearchCandidate[]>([])
  const [top, setTop] = useState<SearchCandidate[]>([])
  const [availableStrategyIds, setAvailableStrategyIds] = useState<string[]>([])
  const [strategyIds, setStrategyIds] = useState<string[]>([])
  const [strategyNames, setStrategyNames] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [startDate, setStartDate] = useState('2026-08-01')
  const [endDate, setEndDate] = useState('2026-08-02')
  const [candidateLimit, setCandidateLimit] = useState('100')
  const [minimumSize, setMinimumSize] = useState('2')
  const [maximumSize, setMaximumSize] = useState('4')
  const [seed, setSeed] = useState(String(BACKTEST_DEFAULTS.seed))
  const [timeoutSeconds, setTimeoutSeconds] = useState('900')
  const [noImprovementLimit, setNoImprovementLimit] = useState('100')
  const limit = Number(candidateLimit) || 100
  const tested = (run?.succeeded ?? 0) + (run?.failed ?? 0)
  const pct = Math.min(100, ((run?.generated ?? 0) / (run?.candidateLimit ?? limit)) * 100)

  useEffect(() => {
    const controller = new AbortController()
    Promise.all([api.listSearchRuns(controller.signal), catalogApi.loadCatalog(controller.signal)])
      .then(([runs, catalog]) => {
        setRun(runs[0] ?? null)
        const ids = catalog.strategies.map((item) => item.strategyId)
        setAvailableStrategyIds(ids)
        setStrategyIds(ids)
        setStrategyNames(Object.fromEntries(catalog.strategies.map((item) => [item.strategyId, item.displayName])))
      })
      .catch(() => undefined)
    return () => controller.abort()
  }, [api, catalogApi])

  useEffect(() => {
    if (!run) return
    Promise.all([api.candidates(run.id, 'recent'), api.candidates(run.id, 'score')])
      .then(([recent, ranked]) => { setFeed(recent); setTop(ranked.slice(0, 10)) })
      .catch(() => undefined)
    if (run.status !== 'QUEUED' && run.status !== 'RUNNING') return
    return api.subscribe(run.id, (next) => {
      setRun(next)
      Promise.all([api.candidates(next.id, 'recent'), api.candidates(next.id, 'score')])
        .then(([recent, ranked]) => { setFeed(recent); setTop(ranked.slice(0, 10)) })
        .catch(() => undefined)
    })
  }, [api, run?.id, run?.status])

  async function start() {
    if (strategyIds.length < 2) return toast('At least two strategies must be available', 'warning')
    const numeric = {
      minimumSize: level === 'basic' ? 2 : Number(minimumSize),
      maximumSize: level === 'basic' ? Math.min(4, strategyIds.length) : Number(maximumSize),
      candidateLimit: Number(candidateLimit), timeoutSeconds: Number(timeoutSeconds),
      noImprovementLimit: Number(noImprovementLimit), seed: Number(seed),
    }
    if (startDate >= endDate) return toast('Start date must be before end date', 'warning')
    if (!Object.values(numeric).every(Number.isSafeInteger)) return toast('Search settings must be whole numbers', 'warning')
    if (numeric.minimumSize < 2 || numeric.maximumSize > Math.min(4, strategyIds.length) || numeric.minimumSize > numeric.maximumSize) {
      return toast('Combination size must be between 2 and the selected strategy count', 'warning')
    }
    if (numeric.candidateLimit < 1 || numeric.candidateLimit > 2000) return toast('Candidate limit must be between 1 and 2,000', 'warning')
    if (numeric.timeoutSeconds < 1 || numeric.timeoutSeconds > 7200) return toast('Timeout must be between 1 and 7,200 seconds', 'warning')
    if (numeric.noImprovementLimit < 1 || numeric.noImprovementLimit > 2000) return toast('No-improvement limit must be between 1 and 2,000', 'warning')
    setBusy(true)
    try {
      const datasetId = await api.prepareDataset(market.pair, timeframe, startDate, endDate)
      const created = await api.start({ datasetId, strategyIds, ...numeric })
      setFeed([]); setTop([]); setRun(created)
      toast(`Search queued — ${limit.toLocaleString()} real candidates`, 'info')
    } catch (error) {
      toast(error instanceof Error ? error.message : 'Search could not start', 'warning')
    } finally { setBusy(false) }
  }

  const active = run?.status === 'QUEUED' || run?.status === 'RUNNING'

  function toggleStrategy(id: string) {
    if (active || busy) return
    setStrategyIds((current) => current.includes(id)
      ? current.length > 2 ? current.filter((item) => item !== id) : current
      : [...current, id])
  }

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
              onChange={(v) => {
                const next = v as typeof level
                setLevel(next)
                setCandidateLimit(next === 'basic' ? '100' : '2000')
                setNoImprovementLimit('100')
              }}
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
            <label className="flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-wide text-faint">Timeframe</span>
              <select value={timeframe} disabled={active || busy} onChange={(event) => setTimeframe(event.target.value as typeof timeframe)} className="border border-subtle bg-workspace px-2 py-1 font-mono text-[12px] text-ink">
                {['5m', '15m', '1h', '4h'].map((value) => <option key={value}>{value}</option>)}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <DateInput label="Start" value={startDate} onChange={setStartDate} disabled={active || busy} />
              <DateInput label="End" value={endDate} onChange={setEndDate} disabled={active || busy} />
            </div>
            <div>
              <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-faint">Strategies to combine</div>
              <div className="flex flex-wrap gap-1.5">
                {availableStrategyIds.map((s) => (
                  <button type="button" disabled={active || busy} onClick={() => toggleStrategy(s)} key={s} className={cn(
                    'rounded-[4px] border px-2 py-1 text-left font-mono text-[11px] disabled:opacity-60',
                    strategyIds.includes(s) ? 'border-accent/40 bg-accent/10 text-accent' : 'border-subtle bg-workspace text-faint',
                  )}>
                    {strategyNames[s] ?? s}
                  </button>
                ))}
              </div>
            </div>
            {level === 'basic' ? (
              <label className="flex items-center justify-between">
                <span className="text-[11px] uppercase tracking-wide text-faint">Candidates to try</span>
                <select value={candidateLimit} disabled={active || busy} onChange={(event) => setCandidateLimit(event.target.value)} className="border border-subtle bg-workspace px-2 py-1 font-mono text-[12px] text-ink">
                  {['25', '50', '100'].map((value) => <option key={value}>{value}</option>)}
                </select>
              </label>
            ) : (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <ExactInput label="Min combination" value={minimumSize} onChange={setMinimumSize} disabled={active || busy} />
                  <ExactInput label="Max combination" value={maximumSize} onChange={setMaximumSize} disabled={active || busy} />
                </div>
                <ExactInput label="Candidate limit" value={candidateLimit} onChange={setCandidateLimit} disabled={active || busy} />
              </>
            )}

            {level === 'advanced' && (
              <>
                <div className="border-t border-subtle pt-3">
                  <ConfigRow label="Generator" value="Random Search v1" ml />
                </div>
                <ConfigRow label="Parameter ranges" value="Default" />
                <ExactInput label="Seed" value={seed} onChange={setSeed} disabled={active || busy} />
                <ExactInput label="Timeout seconds" value={timeoutSeconds} onChange={setTimeoutSeconds} disabled={active || busy} />
                <ExactInput label="No improvement" value={noImprovementLimit} onChange={setNoImprovementLimit} disabled={active || busy} />
                <ConfigRow label="Dataset" value={`${market.pair} · ${timeframe} · ${startDate} → ${endDate}`} />
              </>
            )}

            <div className="pt-1">
              {active ? (
                <Button variant="danger" className="w-full" onClick={() => setConfirmStop(true)}>
                  <Square size={13} /> Stop Search
                </Button>
              ) : (
                <Button
                  variant="primary"
                  className="w-full"
                  disabled={busy}
                  onClick={start}
                >
                  <Play size={14} /> {busy ? 'Preparing Dataset…' : level === 'basic' ? 'Find Strategy Combinations' : 'Start Search'}
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
              {active && <StatusBadge tone="running" pulse>{run?.status}</StatusBadge>}
              {!run && <StatusBadge tone="queued">Ready</StatusBadge>}
              {run?.status === 'CANCELLED' && <StatusBadge tone="cancelled">Stopped</StatusBadge>}
              {run?.status === 'COMPLETED' && <StatusBadge tone="completed">Completed</StatusBadge>}
              {run?.status === 'FAILED' && <StatusBadge tone="failed">Failed</StatusBadge>}
              <span className="ml-auto font-mono text-[11px] text-faint">{run?.id ?? 'No search run'}</span>
            </div>
            <div className="mt-3 flex items-center gap-3">
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-active">
                <div className="h-full rounded-full bg-accent transition-[width] duration-500" style={{ width: `${pct}%` }} />
              </div>
              <span className="font-mono text-[13px] font-semibold tabular-nums text-ink">
                {run?.generated ?? 0} / {run?.candidateLimit ?? limit}
              </span>
              <span className="font-mono text-[12px] tabular-nums text-faint">combinations</span>
            </div>
            <div className="mt-3 flex items-center justify-between rounded-[6px] border border-accent/30 bg-accent/10 px-3 py-2">
              <span className="text-[12px] text-dim">Current best combination</span>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[12px] text-ink">{run?.topCandidate ?? 'Waiting for a completed candidate'}</span>
                <span className="font-mono text-[13px] font-semibold tabular-nums text-ml">
                  {run?.topScore ? Number(run.topScore).toFixed(2) : '—'}
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
                ['Generated', run?.generated ?? 0],
                ['Tested', tested],
                ['Succeeded', run?.succeeded ?? 0],
                ['Failed', run?.failed ?? 0],
                ['Remaining', Math.max(0, (run?.candidateLimit ?? limit) - (run?.generated ?? 0))],
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
                    i === 0 && active && 'csl-flash',
                  )}
                >
                  <span className="text-faint">#{String(f.sequence).padStart(4, '0')}</span>
                  <span className="flex-1 text-dim">{f.displayName}</span>
                  {f.status === 'FAILED' ? (
                    <StatusBadge tone="failed">Failed · {f.failureCode}</StatusBadge>
                  ) : (
                    <>
                      <span className="text-ml">{f.score ? `Score ${Number(f.score).toFixed(2)}` : f.status}</span>
                      {f.id === top[0]?.id && <StatusBadge tone="new">Top</StatusBadge>}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* health strip */}
          <div className="grid grid-cols-6 divide-x divide-subtle border-t border-subtle bg-workspace text-center">
            {[
              ['Workers', active ? '1 / 1' : '0 / 1'],
              ['Queued', String(Math.max(0, (run?.candidateLimit ?? limit) - (run?.generated ?? 0)))],
              ['Failed', String(run?.failed ?? 0)],
              ['Tested', String(tested)],
              ['Stop', run?.stopReason ?? '—'],
              ['Top-1', run?.topScore ? Number(run.topScore).toFixed(2) : '—'],
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
            {top.map((r, index) => (
              <div
                key={r.id}
                className={cn(
                  'flex items-center gap-2 border-b border-subtle px-3 py-2.5',
                  index === 0 && 'border-l-2 border-l-accent',
                )}
              >
                <span className="w-4 font-mono text-[12px] text-faint">{index + 1}</span>
                <span className={cn('flex-1 truncate text-[12px]', index === 0 ? 'text-ink' : 'text-dim')}>
                  {r.displayName}
                </span>
                <span className="font-mono text-[13px] font-semibold tabular-nums text-ml">{Number(r.score).toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Modal
        open={confirmStop}
        onClose={() => setConfirmStop(false)}
        title={`Stop search ${run?.id.slice(0, 8) ?? ''}?`}
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmStop(false)}>Cancel</Button>
            <Button
              variant="danger"
              onClick={() => {
                if (run) api.cancel(run.id).then(setRun).catch((error) => toast(String(error), 'warning'))
                setConfirmStop(false); toast('Stop requested — completed candidates are preserved', 'warning')
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

type RuntimeRun = {
  id: string; type: 'Search' | 'Backtest'; space: string
  status: keyof typeof RUN_TONE; started: string; duration: string
  tested: number | null; failed: number; top1: string | null
  generator: string; seed: number; datasetId: string; reason?: string
  parentSearchRunId?: string | null; candidateName?: string | null
}

function elapsed(start: string, end: string | null) {
  const seconds = Math.max(0, Math.round((Date.parse(end ?? new Date().toISOString()) - Date.parse(start)) / 1000))
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

function Runs() {
  const api = useMemo(() => createSearchApi(), [])
  const [runs, setRuns] = useState<RuntimeRun[]>([])
  const [selected, setSelected] = useState<RuntimeRun | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'search' | 'backtest'>('all')
  useEffect(() => {
    let active = true
    const load = () => Promise.all([api.listSearchRuns(), api.listBacktestRuns()]).then(([searches, backtests]) => {
      if (!active) return
      const searchRows: RuntimeRun[] = searches.map((run) => ({
        id: run.id, type: 'Search', space: run.strategyIds.join(' + '), status: run.status,
        started: new Date(run.startedAt ?? run.createdAt).toLocaleString(), duration: elapsed(run.startedAt ?? run.createdAt, run.completedAt),
        tested: run.succeeded + run.failed, failed: run.failed, top1: run.topScore, generator: run.generator,
        seed: run.seed, datasetId: run.datasetId, reason: run.failureDetail ?? run.stopReason ?? undefined,
      }))
      const backtestRows: RuntimeRun[] = backtests.map((run: BacktestRunSummary) => ({
        id: run.id, type: 'Backtest', space: run.candidateDisplayName ?? `${run.strategyId} · ${run.pair} · ${run.timeframe}`, status: run.status,
        started: new Date(run.requestedAt).toLocaleString(), duration: elapsed(run.requestedAt, run.completedAt),
        tested: null, failed: run.status === 'FAILED' ? 1 : 0, top1: null, generator: '—',
        seed: run.randomSeed, datasetId: run.datasetId, reason: run.failureCode ?? undefined,
        parentSearchRunId: run.parentSearchRunId, candidateName: run.candidateDisplayName,
      }))
      setRuns([...searchRows, ...backtestRows]); setError(null)
    }).catch((value) => active && setError(value instanceof Error ? value.message : 'Runs could not be loaded'))
    void load()
    const timer = globalThis.setInterval(load, 3000)
    return () => { active = false; globalThis.clearInterval(timer) }
  }, [api])
  const visibleRuns = runs.filter((run) => filter === 'all' || run.type.toLowerCase() === filter)
  return (
    <div className="flex h-full min-h-0 flex-col">
      {error && <div className="border-b border-neg/30 bg-neg/10 px-3 py-2 text-[12px] text-neg">{error}</div>}
      <div className="flex items-center justify-between border-b border-subtle bg-surface px-3 py-2">
        <span className="text-[12px] text-dim">Durable search and backtest history</span>
        <Segmented ariaLabel="Run type filter" options={[
          { value: 'all', label: 'All' }, { value: 'search', label: 'Search' }, { value: 'backtest', label: 'Backtest' },
        ]} value={filter} onChange={(value) => setFilter(value as typeof filter)} />
      </div>
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
            {visibleRuns.map((r) => (
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
              {selected.parentSearchRunId && <KV k="Parent search" v={selected.parentSearchRunId} />}
              {selected.candidateName && <KV k="Candidate" v={selected.candidateName} />}
              <KV k="Started" v={selected.started} />
              <KV k="Duration" v={selected.duration} />
              <KV k="Tested" v={selected.tested ?? '—'} />
              <KV k="Failed" v={selected.failed} />
              <KV k="Top-1 score" v={selected.top1 ?? '—'} />
            </DrawerSection>
            <DrawerSection title="Reproducibility">
              <KV k="Generator" v={selected.generator} />
              <KV k="Seed" v={selected.seed} />
              <KV k="Dataset" v={selected.datasetId} />
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
