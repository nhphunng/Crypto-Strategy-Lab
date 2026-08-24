/**
 * Live leaderboard reconciliation.
 *
 * The REST snapshot stays authoritative: events only tell the view that a
 * newer projection version exists. Duplicates are ignored, gaps mark the view
 * stale and force a refetch, and a disconnect never discards the last snapshot.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { leaderboardWebSocketUrl } from '../api/leaderboardApi'
import { parseLeaderboardEvent } from '../schemas'
import type { ConnectionStatus, LeaderboardIdentity, LeaderboardUpdatedEvent } from '../types'

export type SocketLike = {
  send: (data: string) => void
  close: () => void
  onopen: ((event: unknown) => void) | null
  onmessage: ((event: { data: string }) => void) | null
  onerror: ((event: unknown) => void) | null
  onclose: ((event: unknown) => void) | null
}

export type SocketFactory = (url: string) => SocketLike

export type UseLeaderboardUpdatesOptions = {
  identity: LeaderboardIdentity
  projectionVersion: number | null
  onRefetch: () => void
  socketFactory?: SocketFactory
  enabled?: boolean
  maxAttempts?: number
  reconnectDelayMs?: number
  scheduleReconnect?: (retry: () => void, delayMs: number) => void
}

export type LeaderboardUpdatesState = {
  status: ConnectionStatus
  stale: boolean
  lastEvent: LeaderboardUpdatedEvent | null
  appliedVersion: number | null
  attempts: number
}

const DEFAULT_MAX_ATTEMPTS = 5
const DEFAULT_RECONNECT_DELAY_MS = 1000

function subscribeMessage(identity: LeaderboardIdentity, lastProjectionVersion: number | null) {
  return JSON.stringify({
    eventType: 'LEADERBOARD_SUBSCRIBE',
    version: 1,
    requestId: `sub-${identity.scoringPolicyId}-${identity.rankBy}-${identity.k}`,
    payload: {
      scoringPolicyId: identity.scoringPolicyId,
      scoringPolicyVersion: identity.scoringPolicyVersion,
      rankBy: identity.rankBy,
      k: identity.k,
      pair: identity.pair ?? null,
      timeframe: identity.timeframe ?? null,
      runId: identity.runId ?? null,
      lastProjectionVersion,
    },
  })
}

export function useLeaderboardUpdates({
  identity,
  projectionVersion,
  onRefetch,
  socketFactory,
  enabled = true,
  maxAttempts = DEFAULT_MAX_ATTEMPTS,
  reconnectDelayMs = DEFAULT_RECONNECT_DELAY_MS,
  scheduleReconnect,
}: UseLeaderboardUpdatesOptions): LeaderboardUpdatesState {
  const [status, setStatus] = useState<ConnectionStatus>(enabled ? 'CONNECTING' : 'STALE')
  const [stale, setStale] = useState(false)
  const [lastEvent, setLastEvent] = useState<LeaderboardUpdatedEvent | null>(null)
  const [attempts, setAttempts] = useState(0)

  const appliedVersion = useRef<number | null>(projectionVersion)
  const staleRef = useRef(false)
  const reconnectedRef = useRef(false)
  const seenEventIds = useRef<Set<string>>(new Set())
  const refetch = useRef(onRefetch)
  refetch.current = onRefetch

  useEffect(() => {
    appliedVersion.current = projectionVersion
    if (projectionVersion !== null) {
      staleRef.current = false
      setStale(false)
    }
  }, [projectionVersion])

  const identityKey = useMemo(
    () =>
      [
        identity.scoringPolicyId,
        identity.scoringPolicyVersion,
        identity.rankBy,
        identity.k,
        identity.pair ?? '*',
        identity.timeframe ?? '*',
        identity.runId ?? '*',
      ].join('|'),
    [identity],
  )

  const handleMessage = useCallback((raw: string) => {
    let event: LeaderboardUpdatedEvent
    try {
      const parsed: unknown = JSON.parse(raw)
      if (
        typeof parsed === 'object' &&
        parsed !== null &&
        (parsed as { eventType?: string }).eventType !== 'LEADERBOARD_UPDATED'
      ) {
        // Acknowledgements and protocol errors never mutate visible state.
        return
      }
      event = parseLeaderboardEvent(parsed)
    } catch {
      return
    }
    if (seenEventIds.current.has(event.eventId)) return
    seenEventIds.current.add(event.eventId)

    const current = appliedVersion.current
    const incoming = event.payload.projectionVersion
    setLastEvent(event)
    if (current !== null && incoming <= current) return
    if (current !== null && incoming > current + 1) {
      staleRef.current = true
      setStale(true)
    }
    refetch.current()
  }, [])

  useEffect(() => {
    if (!enabled) return
    const factory = socketFactory ?? ((url: string) => new WebSocket(url) as unknown as SocketLike)
    let closedByEffect = false
    let attempt = 0
    let socket: SocketLike | null = null

    const connect = () => {
      setStatus((current) => (current === 'LIVE' ? 'RECONNECTING' : current))
      socket = factory(leaderboardWebSocketUrl())
      socket.onopen = () => {
        attempt = 0
        setAttempts(0)
        setStatus('LIVE')
        socket?.send(subscribeMessage(identity, appliedVersion.current))
        // A reconnected or stale view always recovers from the authoritative
        // snapshot before it may claim to be live.
        if (staleRef.current || reconnectedRef.current) {
          reconnectedRef.current = false
          refetch.current()
        }
      }
      socket.onmessage = (message) => handleMessage(message.data)
      socket.onerror = () => setStatus('RECONNECTING')
      socket.onclose = () => {
        if (closedByEffect) return
        attempt += 1
        reconnectedRef.current = true
        setAttempts(attempt)
        staleRef.current = true
        setStale(true)
        if (attempt > maxAttempts) {
          setStatus('STALE')
          return
        }
        setStatus('RECONNECTING')
        const retry = () => connect()
        if (scheduleReconnect) scheduleReconnect(retry, reconnectDelayMs * attempt)
        else setTimeout(retry, reconnectDelayMs * attempt)
      }
    }

    connect()
    return () => {
      closedByEffect = true
      socket?.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [identityKey, enabled, handleMessage, maxAttempts, reconnectDelayMs])

  return {
    status,
    stale,
    lastEvent,
    appliedVersion: appliedVersion.current,
    attempts,
  }
}
