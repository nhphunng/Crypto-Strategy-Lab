import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { fetchLeaderboardSnapshot } from '../../features/leaderboard/api/leaderboardApi'
import { LeaderboardStatus } from '../../features/leaderboard/components/LeaderboardStatus'
import { LeaderboardTable } from '../../features/leaderboard/components/LeaderboardTable'
import {
  useLeaderboardUpdates,
  type SocketFactory,
} from '../../features/leaderboard/hooks/useLeaderboardUpdates'
import type {
  LeaderboardIdentity,
  LeaderboardSnapshot,
  LeaderboardViewState,
  RankMetric,
} from '../../features/leaderboard/types'
import { RANK_METRICS } from '../../features/leaderboard/types'

export const ANALYSIS_DISCLAIMER =
  'Simulated historical analysis only. Past simulated performance is not investment advice and does not guarantee future results.'

export const DEFAULT_IDENTITY: LeaderboardIdentity = {
  scoringPolicyId: (import.meta.env?.VITE_SCORING_POLICY_ID as string | undefined) ?? 'balanced',
  scoringPolicyVersion:
    (import.meta.env?.VITE_SCORING_POLICY_VERSION as string | undefined) ?? '2',
  rankBy: 'OVERALL_SCORE',
  k: 10,
  pair: 'BTCUSDT',
  timeframe: '15m',
}

const DEFAULT_VIEW: LeaderboardViewState = {
  sortBy: 'RANK',
  sortDirection: 'ASC',
  page: 1,
  pageSize: 25,
}

export type LeaderboardRouteProps = {
  identity?: LeaderboardIdentity
  loadSnapshot?: typeof fetchLeaderboardSnapshot
  renderDetail?: (selection: { leaderboardId: string; evaluationResultId: string }) => ReactNode
  onSelect?: (evaluationResultId: string) => void
  socketFactory?: SocketFactory
  liveUpdates?: boolean
}

export function LeaderboardRoute({
  identity: initialIdentity = DEFAULT_IDENTITY,
  loadSnapshot = fetchLeaderboardSnapshot,
  renderDetail,
  onSelect,
  socketFactory,
  liveUpdates = true,
}: LeaderboardRouteProps) {
  const [identity, setIdentity] = useState<LeaderboardIdentity>(initialIdentity)
  const [view, setView] = useState<LeaderboardViewState>(DEFAULT_VIEW)
  const [snapshot, setSnapshot] = useState<LeaderboardSnapshot | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState<string>()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)

  const refresh = useCallback(() => setReloadToken((token) => token + 1), [])

  useEffect(() => {
    let cancelled = false
    setStatus((current) => (snapshot ? current : 'loading'))
    loadSnapshot(identity, view)
      .then((next) => {
        if (cancelled) return
        setSnapshot(next)
        setStatus('ready')
        setErrorMessage(undefined)
      })
      .catch((error: Error) => {
        if (cancelled) return
        setStatus('error')
        setErrorMessage(error.message)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [identity, view, reloadToken, loadSnapshot])

  const live = useLeaderboardUpdates({
    identity,
    projectionVersion: snapshot?.projectionVersion ?? null,
    onRefetch: refresh,
    socketFactory,
    enabled: liveUpdates,
  })

  const selection = useMemo(
    () =>
      snapshot && selectedId
        ? { leaderboardId: snapshot.leaderboardId, evaluationResultId: selectedId }
        : null,
    [snapshot, selectedId],
  )

  return (
    <div className="flex h-full min-h-0 flex-col" data-testid="route-leaderboard">
      <header className="flex flex-wrap items-center gap-3 border-b border-line bg-canvas px-4 py-2">
        <div>
          <h1 className="text-[15px] font-semibold text-ink">Leaderboard</h1>
          <p data-testid="label-simulated-analysis" className="text-[11px] text-faint">
            Simulated historical analysis · projection v{snapshot?.projectionVersion ?? '—'} ·
            updated {snapshot?.updatedAt ?? '—'}
            {snapshot?.runState ? ` · run ${snapshot.runState}` : ''}
          </p>
        </div>
        <label className="ml-auto flex items-center gap-1.5 text-[12px] text-faint" htmlFor="control-rank-by">
          Rank by
          <select
            id="control-rank-by"
            data-testid="control-rank-by"
            value={identity.rankBy}
            onChange={(event) => {
              setSnapshot(null)
              setIdentity({ ...identity, rankBy: event.target.value as RankMetric })
              setView({ ...DEFAULT_VIEW })
            }}
            className="rounded-[4px] border border-subtle bg-workspace px-1.5 py-1 text-ink"
          >
            {RANK_METRICS.map((metric) => (
              <option key={metric} value={metric}>
                {metric}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[12px] text-faint" htmlFor="control-top-k">
          Top-K
          <select
            id="control-top-k"
            data-testid="control-top-k"
            value={identity.k}
            onChange={(event) => {
              setSnapshot(null)
              setIdentity({ ...identity, k: Number(event.target.value) })
              setView({ ...DEFAULT_VIEW })
            }}
            className="rounded-[4px] border border-subtle bg-workspace px-1.5 py-1 text-ink"
          >
            {[3, 5, 10, 25].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </header>

      <LeaderboardStatus
        status={live.status}
        stale={live.stale}
        attempts={live.attempts}
        projectionVersion={snapshot?.projectionVersion ?? null}
        updatedAt={snapshot?.updatedAt ?? null}
        runState={snapshot?.runState ?? null}
        lastEvent={live.lastEvent}
      />

      <p
        data-testid="disclaimer-leaderboard"
        className="border-b border-subtle bg-workspace px-4 py-1.5 text-[11px] text-dim"
      >
        {snapshot?.disclaimer ?? ANALYSIS_DISCLAIMER}
      </p>

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          <LeaderboardTable
            snapshot={snapshot}
            view={view}
            status={status}
            errorMessage={errorMessage}
            stale={live.stale}
            onViewChange={setView}
            onRetry={refresh}
            selectedId={selectedId}
            onSelect={(evaluationResultId) => {
              setSelectedId(evaluationResultId)
              onSelect?.(evaluationResultId)
            }}
          />
        </div>
        {selection && renderDetail ? renderDetail(selection) : null}
      </div>
    </div>
  )
}

export default LeaderboardRoute
