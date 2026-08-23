import type { ConnectionStatus, LeaderboardUpdatedEvent, RunState } from '../types'

export type LeaderboardStatusProps = {
  status: ConnectionStatus
  stale: boolean
  projectionVersion: number | null
  updatedAt: string | null
  runState?: RunState | null
  lastEvent?: LeaderboardUpdatedEvent | null
  attempts?: number
}

const LABEL: Record<ConnectionStatus, string> = {
  CONNECTING: 'Connecting',
  LIVE: 'Live',
  RECONNECTING: 'Reconnecting',
  STALE: 'Stale',
}

const TONE: Record<ConnectionStatus, string> = {
  CONNECTING: 'text-dim',
  LIVE: 'text-pos',
  RECONNECTING: 'text-warn',
  STALE: 'text-warn',
}

export function LeaderboardStatus({
  status,
  stale,
  projectionVersion,
  updatedAt,
  runState,
  lastEvent,
  attempts = 0,
}: LeaderboardStatusProps) {
  return (
    <div
      data-testid="status-leaderboard"
      data-status={status}
      role="status"
      aria-live="polite"
      className="flex flex-wrap items-center gap-2 border-b border-subtle bg-workspace px-4 py-1.5 text-[11px]"
    >
      <span className={`font-medium ${TONE[status]}`} data-testid="status-leaderboard-label">
        {LABEL[status]}
        {status === 'RECONNECTING' && attempts > 0 ? ` · attempt ${attempts}` : ''}
      </span>
      <span className="font-mono text-faint" data-testid="status-projection-version">
        projection v{projectionVersion ?? '—'}
      </span>
      <span className="font-mono text-faint" data-testid="status-updated-at">
        updated {updatedAt ?? '—'}
      </span>
      {runState && (
        <span className="font-mono text-faint" data-testid="status-run-state">
          run {runState}
        </span>
      )}
      {lastEvent && (
        <span className="font-mono text-faint" data-testid="status-last-event">
          last event v{lastEvent.payload.projectionVersion}
        </span>
      )}
      {stale && (
        <span className="text-warn" data-testid="status-stale-note">
          Showing the last confirmed snapshot until the current one is recovered.
        </span>
      )}
    </div>
  )
}
