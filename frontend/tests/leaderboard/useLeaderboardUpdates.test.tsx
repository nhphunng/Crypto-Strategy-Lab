import { describe, expect, it, vi } from 'vitest'
import { act, render, screen, waitFor } from '@testing-library/react'
import {
  useLeaderboardUpdates,
  type SocketLike,
} from '../../src/features/leaderboard/hooks/useLeaderboardUpdates'
import { LeaderboardRoute } from '../../src/app/routes/leaderboard'
import type { LeaderboardIdentity } from '../../src/features/leaderboard/types'
import { eventFixture, policiesFixture, snapshotFixture } from './fixtures'

const IDENTITY: LeaderboardIdentity = {
  scoringPolicyId: 'balanced',
  scoringPolicyVersion: '2',
  rankBy: 'OVERALL_SCORE',
  k: 10,
  pair: 'BTCUSDT',
  timeframe: '15m',
}

class FakeSocket implements SocketLike {
  static instances: FakeSocket[] = []
  sent: string[] = []
  closed = false
  onopen: ((event: unknown) => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: ((event: unknown) => void) | null = null
  onclose: ((event: unknown) => void) | null = null

  constructor() {
    FakeSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.closed = true
  }

  open() {
    act(() => this.onopen?.({}))
  }

  deliver(payload: unknown) {
    act(() => this.onmessage?.({ data: JSON.stringify(payload) }))
  }

  drop() {
    act(() => this.onclose?.({}))
  }
}

function Harness({
  projectionVersion,
  onRefetch,
  maxAttempts = 2,
}: {
  projectionVersion: number | null
  onRefetch: () => void
  maxAttempts?: number
}) {
  const state = useLeaderboardUpdates({
    identity: IDENTITY,
    projectionVersion,
    onRefetch,
    socketFactory: () => new FakeSocket(),
    maxAttempts,
    scheduleReconnect: (retry) => retry(),
  })
  return (
    <div>
      <span data-testid="status">{state.status}</span>
      <span data-testid="stale">{String(state.stale)}</span>
      <span data-testid="attempts">{state.attempts}</span>
      <span data-testid="last-event">{state.lastEvent?.payload.projectionVersion ?? 'none'}</span>
    </div>
  )
}

function setup(projectionVersion: number | null = 41, maxAttempts = 2) {
  FakeSocket.instances = []
  const onRefetch = vi.fn()
  render(
    <Harness projectionVersion={projectionVersion} onRefetch={onRefetch} maxAttempts={maxAttempts} />,
  )
  const socket = FakeSocket.instances[0]
  socket.open()
  return { socket, onRefetch }
}

describe('useLeaderboardUpdates', () => {
  it('subscribes with the complete ranking definition once connected', () => {
    const { socket } = setup()

    expect(screen.getByTestId('status')).toHaveTextContent('LIVE')
    const payload = JSON.parse(socket.sent[0])
    expect(payload.eventType).toBe('LEADERBOARD_SUBSCRIBE')
    expect(payload.version).toBe(1)
    expect(payload.payload).toMatchObject({
      scoringPolicyId: 'balanced',
      scoringPolicyVersion: '2',
      rankBy: 'OVERALL_SCORE',
      k: 10,
      pair: 'BTCUSDT',
      timeframe: '15m',
      lastProjectionVersion: 41,
    })
  })

  it('refetches the authoritative snapshot on the next projection version', () => {
    const { socket, onRefetch } = setup(41)

    socket.deliver(eventFixture(42))

    expect(onRefetch).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('stale')).toHaveTextContent('false')
    expect(screen.getByTestId('last-event')).toHaveTextContent('42')
  })

  it('ignores a duplicate delivery of the same event', () => {
    const { socket, onRefetch } = setup(41)

    socket.deliver(eventFixture(42))
    socket.deliver(eventFixture(42))

    expect(onRefetch).toHaveBeenCalledTimes(1)
  })

  it('never regresses on an older or equal projection version', () => {
    const { socket, onRefetch } = setup(41)

    socket.deliver(eventFixture(40, {}, 'event-old'))
    socket.deliver(eventFixture(41, {}, 'event-same'))

    expect(onRefetch).not.toHaveBeenCalled()
    expect(screen.getByTestId('stale')).toHaveTextContent('false')
  })

  it('marks the view stale and recovers when a version gap arrives', () => {
    const { socket, onRefetch } = setup(41)

    socket.deliver(eventFixture(45))

    expect(screen.getByTestId('stale')).toHaveTextContent('true')
    expect(onRefetch).toHaveBeenCalledTimes(1)
  })

  it('ignores payloads that do not match the event contract', () => {
    const { socket, onRefetch } = setup(41)

    socket.deliver({ eventType: 'LEADERBOARD_UPDATED', version: 2, payload: {} })
    socket.deliver({ eventType: 'LEADERBOARD_UPDATED', version: 1, payload: { broken: true } })
    socket.deliver({ eventType: 'ERROR', version: 1, payload: { code: 'X', message: 'y' } })

    expect(onRefetch).not.toHaveBeenCalled()
    expect(screen.getByTestId('status')).toHaveTextContent('LIVE')
  })

  it('reconnects after a drop and refetches once live again', () => {
    const { socket, onRefetch } = setup(41)

    socket.drop()

    expect(FakeSocket.instances).toHaveLength(2)
    const reconnected = FakeSocket.instances[1]
    reconnected.open()
    expect(screen.getByTestId('status')).toHaveTextContent('LIVE')
    expect(onRefetch).toHaveBeenCalled()
  })

  it('falls back to STALE after the bounded reconnect attempts', () => {
    FakeSocket.instances = []
    const onRefetch = vi.fn()
    render(<Harness projectionVersion={41} onRefetch={onRefetch} maxAttempts={1} />)
    const socket = FakeSocket.instances[0]
    socket.open()

    socket.drop()
    FakeSocket.instances[1].drop()

    expect(screen.getByTestId('status')).toHaveTextContent('STALE')
    expect(screen.getByTestId('stale')).toHaveTextContent('true')
  })
})

describe('LeaderboardRoute live integration', () => {
  it('shows live status and updates rows without a page refresh', async () => {
    FakeSocket.instances = []
    const first = snapshotFixture()
    const second = snapshotFixture()
    second.projectionVersion = 42
    second.entries[0].score = '97.5'
    const loadSnapshot = vi.fn().mockResolvedValueOnce(first).mockResolvedValue(second)

    render(
      <LeaderboardRoute
        loadPolicies={vi.fn().mockResolvedValue(policiesFixture())}
        loadSnapshot={loadSnapshot}
        socketFactory={() => new FakeSocket()}
      />,
    )
    await screen.findByTestId('table-leaderboard')
    FakeSocket.instances[0].open()

    expect(screen.getByTestId('status-leaderboard')).toHaveAttribute('data-status', 'LIVE')
    expect(screen.getByTestId('status-projection-version')).toHaveTextContent('projection v41')

    FakeSocket.instances[0].deliver(eventFixture(42))

    await waitFor(() =>
      expect(screen.getByTestId('status-projection-version')).toHaveTextContent('projection v42'),
    )
    expect(screen.getByText('97.5')).toBeInTheDocument()
    expect(loadSnapshot).toHaveBeenCalledTimes(2)
  })

  it('keeps the last snapshot visible while reconnecting', async () => {
    FakeSocket.instances = []
    const loadSnapshot = vi.fn().mockResolvedValue(snapshotFixture())

    render(
      <LeaderboardRoute
        loadPolicies={vi.fn().mockResolvedValue(policiesFixture())}
        loadSnapshot={loadSnapshot}
        socketFactory={() => new FakeSocket()}
      />,
    )
    await screen.findByTestId('table-leaderboard')
    FakeSocket.instances[0].open()
    FakeSocket.instances[0].drop()

    expect(screen.getByTestId('table-leaderboard')).toBeInTheDocument()
    const status = screen.getByTestId('status-leaderboard').getAttribute('data-status')
    expect(['RECONNECTING', 'STALE', 'LIVE']).toContain(status)
  })
})
