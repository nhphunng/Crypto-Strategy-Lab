import { useState } from 'react'
import { ArrowRight, CircleCheck, Play, Square } from 'lucide-react'
import { useStore } from '../lib/store'
import { useServices } from '../services/registry'
import { PageHeader } from '../components/Shell'
import { Button, cn, Modal, Panel, StatusBadge } from '../components/ui'

function fmtElapsed(s: number) {
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

export function Operations() {
  const { loopStatus, loopTested, loopElapsed, toggleLoop, toast, showExplain } = useStore()
  const snapshot = useServices().operations.getSnapshot()
  const [confirmStop, setConfirmStop] = useState(false)
  const [eventFilter, setEventFilter] = useState('All')
  const running = loopStatus === 'running'

  const events = snapshot.events.filter((e) => eventFilter === 'All' || e.cat === eventFilter)

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <PageHeader title="Operations">
        <StatusBadge tone="neutral">Advanced</StatusBadge>
      </PageHeader>

      {showExplain && (
        <div className="border-b border-subtle bg-surface px-4 py-2.5">
          <p className="text-[12.5px] leading-relaxed text-dim">
            <span className="font-medium text-ink">System health and continuous strategy search.</span>{' '}
            This screen shows how Crypto Strategy Lab processes experiments behind the scenes. You
            don't need it to build, backtest or compare strategies — it's here if you want to see the
            machinery.
          </p>
        </div>
      )}

      {/* Continuous loop */}
      <div className="border-b border-subtle bg-surface p-4">
        <div className="flex items-center gap-3">
          <h2 className="text-[15px] font-semibold text-ink">Continuous Strategy Loop</h2>
          {running ? <StatusBadge tone="running" pulse>Running</StatusBadge> : <StatusBadge tone="cancelled">Stopped</StatusBadge>}
          <div className="ml-auto">
            {running ? (
              <Button variant="danger" onClick={() => setConfirmStop(true)}><Square size={13} /> Stop Loop</Button>
            ) : (
              <Button variant="primary" onClick={() => { toggleLoop(true); toast('Continuous loop resumed', 'positive') }}>
                <Play size={14} /> Start Loop
              </Button>
            )}
          </div>
        </div>

        {/* pipeline */}
        <div className="mt-4 flex items-center gap-2">
          {snapshot.pipeline.map((p, i) => (
            <div key={p} className="flex items-center gap-2">
              <div className={cn(
                'flex items-center gap-1.5 rounded-[6px] border px-3 py-1.5 text-[12px]',
                running ? 'border-pos/30 bg-pos/10 text-pos' : 'border-subtle bg-workspace text-faint',
              )}>
                <CircleCheck size={13} className={running ? '' : 'opacity-40'} />
                {p}
              </div>
              {i < snapshot.pipeline.length - 1 && <ArrowRight size={14} className="text-faint" />}
            </div>
          ))}
        </div>

        {/* metrics */}
        <div className="mt-4 grid grid-cols-3 gap-px overflow-hidden rounded-[8px] border border-subtle bg-subtle md:grid-cols-6">
          {[
            ['Candidates Tested', loopTested.toLocaleString(), 'ink'],
            ['Elapsed', fmtElapsed(loopElapsed), 'ink'],
            ['Top Strategy', 'MA20 + RSI14 + SR', 'ink'],
            ['Top Score', '86.4', 'ml'],
            ['Failures', '7', 'neg'],
            ['Retries', '5', 'warn'],
          ].map(([l, v, c]) => (
            <div key={l} className="bg-surface px-3 py-2.5">
              <div className="text-[10px] uppercase tracking-wide text-faint">{l}</div>
              <div className={cn(
                'truncate font-mono text-[13px] font-semibold tabular-nums',
                c === 'ml' && 'text-ml', c === 'neg' && 'text-neg', c === 'warn' && 'text-warn', c === 'ink' && 'text-ink',
              )}>{v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* two-column: dependencies+workers | queue+active run */}
      <div className="grid gap-px bg-subtle p-px lg:grid-cols-2">
        {/* dependency health */}
        <Panel title="Dependency Health" className="border-0">
          <table className="w-full border-collapse text-[12px]">
            <thead>
              <tr className="border-b border-subtle text-left text-faint">
                {['Component', 'Status', 'Latency / lag', 'Last healthy'].map((h) => (
                  <th key={h} className="h-8 px-3 text-[10px] font-semibold uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {snapshot.dependencies.map((d) => (
                <tr key={d.name} className="h-9 border-b border-subtle">
                  <td className="px-3">
                    <span className="text-ink">{d.name}</span>
                    <span className={cn('ml-2 rounded-[3px] px-1 text-[9px] uppercase', d.required ? 'bg-accent/15 text-accent' : 'bg-surface-active text-faint')}>
                      {d.required ? 'Required' : 'Optional'}
                    </span>
                  </td>
                  <td className="px-3">
                    <StatusBadge tone={d.status === 'DEGRADED' ? 'degraded' : d.status === 'CONNECTED' ? 'connected' : 'healthy'}>
                      {d.status}
                    </StatusBadge>
                  </td>
                  <td className="px-3 font-mono tabular-nums text-dim">{d.lag}</td>
                  <td className="px-3 font-mono text-faint">{d.last}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="px-3 py-2 text-[11px] text-faint">
            News provider is an optional dependency — its degradation does not stop the technical pipeline.
          </p>
        </Panel>

        {/* workers */}
        <Panel title="Workers" className="border-0" right={<span className="font-mono text-[11px] text-faint">3 / 4 active</span>}>
          <div className="divide-y divide-subtle">
            {snapshot.workers.map((w) => (
              <div key={w.id} className="flex items-center gap-3 px-3 py-2.5">
                <span className="w-20 font-mono text-[12px] text-ink">{w.id}</span>
                <StatusBadge tone={w.status === 'RUNNING' ? 'running' : 'idle'} pulse={w.status === 'RUNNING'}>{w.status}</StatusBadge>
                <span className="font-mono text-[11px] text-dim">{w.job ? `job ${w.job}` : '—'}</span>
                <div className="ml-auto flex items-center gap-2">
                  <div className="h-1.5 w-24 overflow-hidden rounded-full bg-surface-active">
                    <div className={cn('h-full rounded-full', w.util > 0 ? 'bg-accent' : '')} style={{ width: `${w.util}%` }} />
                  </div>
                  <span className="w-9 text-right font-mono text-[11px] tabular-nums text-faint">{w.util}%</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        {/* queue */}
        <Panel title="Queue" className="border-0">
          <div className="grid grid-cols-3 gap-px bg-subtle">
            {[
              ['Queue depth', '27'],
              ['Oldest job', '12s'],
              ['Running', '3'],
              ['Retrying', '1'],
              ['Failed', '2'],
              ['Processing rate', '6.8/s'],
            ].map(([l, v]) => (
              <div key={l} className="bg-surface px-3 py-3">
                <div className="font-mono text-[16px] font-semibold tabular-nums text-ink">{v}</div>
                <div className="text-[10px] uppercase tracking-wide text-faint">{l}</div>
              </div>
            ))}
          </div>
        </Panel>

        {/* active run */}
        <Panel title="Active Run Health" className="border-0" right={<StatusBadge tone="running" pulse>SR-0184</StatusBadge>}>
          <div className="space-y-2 p-3 text-[12px]">
            {[
              ['Generator', 'Random Search v1', 'ml'],
              ['Candidates', '1,842 / 2,000', 'ink'],
              ['Top-1', '86.4', 'ml'],
              ['Failures', '7', 'neg'],
              ['Retries', '5', 'warn'],
            ].map(([l, v, c]) => (
              <div key={l} className="flex items-center justify-between border-b border-subtle pb-2 last:border-0">
                <span className="text-faint">{l}</span>
                <span className={cn('font-mono tabular-nums', c === 'ml' && 'text-ml', c === 'neg' && 'text-neg', c === 'warn' && 'text-warn', c === 'ink' && 'text-ink')}>{v}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* event log */}
      <div className="border-t border-subtle bg-surface">
        <div className="flex items-center gap-2 border-b border-subtle px-4 py-2">
          <span className="text-[13px] font-semibold text-ink">Event Log</span>
          <div className="ml-2 flex flex-wrap gap-1">
          {snapshot.eventCategories.map((c) => (
              <button
                key={c}
                onClick={() => setEventFilter(c)}
                className={cn(
                  'rounded-[4px] px-2 py-0.5 text-[11px]',
                  eventFilter === c ? 'bg-surface-active text-accent' : 'text-faint hover:text-dim',
                )}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
        <div className="max-h-64 overflow-y-auto p-2 font-mono text-[11.5px] leading-relaxed">
          {events.map((e, i) => (
            <div key={i} className="flex gap-3 px-2 py-0.5 hover:bg-surface-hover">
              <span className="text-faint">{e.t}</span>
              <span className={cn('w-40', e.cat === 'News' ? 'text-warn' : e.cat === 'Ranking' ? 'text-accent' : e.cat === 'Search' ? 'text-ml' : 'text-dim')}>
                {e.kind}
              </span>
              <span className="w-24 text-ink">{e.ref}</span>
              <span className="text-faint">{e.detail}</span>
            </div>
          ))}
        </div>
      </div>

      <Modal
        open={confirmStop}
        onClose={() => setConfirmStop(false)}
        title="Stop the continuous loop?"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmStop(false)}>Cancel</Button>
            <Button variant="danger" onClick={() => { toggleLoop(false); setConfirmStop(false); toast('Continuous loop stopped — results preserved', 'warning') }}>
              Stop Loop
            </Button>
          </>
        }
      >
        Stopping will halt generation of new candidates and let in-flight jobs finish. All completed
        backtests, evaluations and the current leaderboard are preserved.
      </Modal>
    </div>
  )
}
