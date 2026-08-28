import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  fetchLeaderboardSnapshot,
  fetchScoringPolicies,
} from '../../features/leaderboard/api/leaderboardApi'
import { LeaderboardStatus } from '../../features/leaderboard/components/LeaderboardStatus'
import { RankedResultDetail } from '../../features/leaderboard/components/RankedResultDetail'
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
  ScoringPolicySummary,
} from '../../features/leaderboard/types'
import { RANK_METRICS } from '../../features/leaderboard/types'

export const ANALYSIS_DISCLAIMER =
  'Simulated historical analysis only. Past simulated performance is not investment advice and does not guarantee future results.'

/**
 * Scope defaults only. The ranking definition itself is never guessed: the
 * route asks the backend which scoring policies exist, because an environment
 * whose Evaluation feature has published nothing has no policy to rank by.
 */
export const DEFAULT_SCOPE = {
  rankBy: 'OVERALL_SCORE' as RankMetric,
  k: 10,
  pair: (import.meta.env?.VITE_LEADERBOARD_PAIR as string | undefined) ?? 'BTCUSDT',
  timeframe: (import.meta.env?.VITE_LEADERBOARD_TIMEFRAME as string | undefined) ?? '15m',
}

const PREFERRED_POLICY_ID = import.meta.env?.VITE_SCORING_POLICY_ID as string | undefined
const PREFERRED_POLICY_VERSION = import.meta.env?.VITE_SCORING_POLICY_VERSION as string | undefined

export function selectPolicy(
  policies: readonly ScoringPolicySummary[],
): ScoringPolicySummary | null {
  if (policies.length === 0) return null
  const preferred = policies.find(
    (policy) =>
      policy.scoringPolicyId === PREFERRED_POLICY_ID &&
      (PREFERRED_POLICY_VERSION === undefined ||
        policy.scoringPolicyVersion === PREFERRED_POLICY_VERSION),
  )
  if (preferred) return preferred
  // Prefer a policy that actually has evaluated candidates behind it.
  return policies.find((policy) => policy.evaluationCount > 0) ?? policies[0]
}

export function identityFor(policy: ScoringPolicySummary): LeaderboardIdentity {
  return {
    scoringPolicyId: policy.scoringPolicyId,
    scoringPolicyVersion: policy.scoringPolicyVersion,
    rankBy: policy.defaultRankMetric,
    k: DEFAULT_SCOPE.k,
    pair: DEFAULT_SCOPE.pair,
    timeframe: DEFAULT_SCOPE.timeframe,
  }
}

const DEFAULT_VIEW: LeaderboardViewState = {
  sortBy: 'RANK',
  sortDirection: 'ASC',
  page: 1,
  pageSize: 25,
}

export type LeaderboardRouteProps = {
  identity?: LeaderboardIdentity
  loadPolicies?: typeof fetchScoringPolicies
  loadSnapshot?: typeof fetchLeaderboardSnapshot
  renderDetail?: (selection: { leaderboardId: string; evaluationResultId: string }) => ReactNode
  onSelect?: (evaluationResultId: string) => void
  socketFactory?: SocketFactory
  liveUpdates?: boolean
}

export function LeaderboardRoute({
  identity: initialIdentity,
  loadPolicies = fetchScoringPolicies,
  loadSnapshot = fetchLeaderboardSnapshot,
  renderDetail,
  onSelect,
  socketFactory,
  liveUpdates = true,
}: LeaderboardRouteProps) {
  const [policies, setPolicies] = useState<ScoringPolicySummary[] | null>(
    initialIdentity ? [] : null,
  )
  const [identity, setIdentity] = useState<LeaderboardIdentity | null>(initialIdentity ?? null)
  const [view, setView] = useState<LeaderboardViewState>(DEFAULT_VIEW)
  const [snapshot, setSnapshot] = useState<LeaderboardSnapshot | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState<string>()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)

  const refresh = useCallback(() => setReloadToken((token) => token + 1), [])

  useEffect(() => {
    if (initialIdentity) return
    let cancelled = false
    loadPolicies()
      .then((available) => {
        if (cancelled) return
        setPolicies(available)
        const chosen = selectPolicy(available)
        setIdentity((current) => {
          if (!chosen) return null
          // Re-checking must not rebuild an equivalent identity: that would
          // refetch needlessly and discard the analyst's rankBy/K selection.
          if (
            current &&
            current.scoringPolicyId === chosen.scoringPolicyId &&
            current.scoringPolicyVersion === chosen.scoringPolicyVersion
          ) {
            return current
          }
          return identityFor(chosen)
        })
        if (!chosen) setStatus('ready')
      })
      .catch((error: Error) => {
        if (cancelled) return
        // A failed lookup is a dependency error, not proof that nothing is
        // published, so the empty-ranking state stays out of the way.
        setStatus('error')
        setErrorMessage(error.message)
      })
    return () => {
      cancelled = true
    }
  }, [initialIdentity, loadPolicies, reloadToken])

  useEffect(() => {
    if (identity === null) return
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

  const noPolicyPublished = policies !== null && policies.length === 0 && identity === null

  // Nothing to subscribe to until a ranking definition is resolved.
  const live = useLeaderboardUpdates({
    identity,
    projectionVersion: snapshot?.projectionVersion ?? null,
    onRefetch: refresh,
    socketFactory,
    enabled: liveUpdates && identity !== null,
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
        {identity && (
          <>
            {policies && policies.length > 1 && (
              <label
                className="ml-auto flex items-center gap-1.5 text-[12px] text-faint"
                htmlFor="control-scoring-policy"
              >
                Scoring policy
                <select
                  id="control-scoring-policy"
                  data-testid="control-scoring-policy"
                  value={`${identity.scoringPolicyId}@${identity.scoringPolicyVersion}`}
                  onChange={(event) => {
                    const [policyId, version] = event.target.value.split('@')
                    const chosen = policies.find(
                      (policy) =>
                        policy.scoringPolicyId === policyId &&
                        policy.scoringPolicyVersion === version,
                    )
                    if (!chosen) return
                    setSnapshot(null)
                    setIdentity(identityFor(chosen))
                    setView({ ...DEFAULT_VIEW })
                  }}
                  className="rounded-[4px] border border-subtle bg-workspace px-1.5 py-1 text-ink"
                >
                  {policies.map((policy) => (
                    <option
                      key={`${policy.scoringPolicyId}@${policy.scoringPolicyVersion}`}
                      value={`${policy.scoringPolicyId}@${policy.scoringPolicyVersion}`}
                    >
                      {policy.name} v{policy.scoringPolicyVersion}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label
              className={`${policies && policies.length > 1 ? '' : 'ml-auto '}flex items-center gap-1.5 text-[12px] text-faint`}
              htmlFor="control-rank-by"
            >
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
            <label
              className="flex items-center gap-1.5 text-[12px] text-faint"
              htmlFor="control-top-k"
            >
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
          </>
        )}
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

      {noPolicyPublished ? (
        <div
          data-testid="state-leaderboard-no-policy"
          role="status"
          className="m-4 rounded-[6px] border border-subtle bg-workspace p-6 text-[13px]"
        >
          <p className="font-medium text-ink">No ranking is published yet.</p>
          <p className="mt-1 text-dim">
            The leaderboard ranks completed Evaluation Results using a versioned scoring policy.
            This environment has published none yet, so there is nothing to rank. Run an evaluation,
            or load the demo dataset with{' '}
            <code className="font-mono text-ink">
              python backend/scripts/seed_leaderboard_demo.py
            </code>
            .
          </p>
          <button
            type="button"
            data-testid="control-leaderboard-retry"
            onClick={refresh}
            className="mt-3 rounded-[5px] border border-subtle px-2 py-1 text-ink hover:bg-surface-hover"
          >
            Check again
          </button>
        </div>
      ) : (
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
        {selection ? (
          renderDetail ? (
            renderDetail(selection)
          ) : (
            <RankedResultDetail
              leaderboardId={selection.leaderboardId}
              evaluationResultId={selection.evaluationResultId}
              onClose={() => setSelectedId(null)}
            />
          )
        ) : null}
      </div>
      )}
    </div>
  )
}

export default LeaderboardRoute
