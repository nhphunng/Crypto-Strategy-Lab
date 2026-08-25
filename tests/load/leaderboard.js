/**
 * TV5 demo-load benchmark.
 *
 * Measures the two published targets:
 *   SC-003  p95 leaderboard snapshot / filter / sort / page reads <= 300 ms
 *   SC-004  p95 qualifying update visible to a connected client <= 1 s
 *
 * Snapshot load runs on its own. To exercise the event target, publish updates
 * while the test runs, for example:
 *
 *   while true; do python backend/scripts/seed_leaderboard_demo.py --complete; sleep 5; done
 *
 * Run with:
 *   k6 run tests/load/leaderboard.js
 *   k6 run -e BASE_URL=http://localhost:8000 -e EVENTS=1 tests/load/leaderboard.js
 */

import http from 'k6/http'
import ws from 'k6/ws'
import { check, group } from 'k6'
import { Trend } from 'k6/metrics'

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000'
const WS_URL = BASE_URL.replace(/^http/, 'ws') + '/ws/v1/leaderboards'
const WITH_EVENTS = __ENV.EVENTS === '1'
const POLICY_ID = __ENV.SCORING_POLICY_ID || 'balanced'
const POLICY_VERSION = __ENV.SCORING_POLICY_VERSION || '2'
const PAIR = __ENV.PAIR || 'BTCUSDT'
const TIMEFRAME = __ENV.TIMEFRAME || '15m'
const K = __ENV.K || '10'

const eventLatency = new Trend('leaderboard_event_latency_ms', true)

export const options = {
  scenarios: {
    snapshots: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 10),
      duration: __ENV.DURATION || '30s',
      exec: 'snapshotLoad',
    },
    ...(WITH_EVENTS
      ? {
          events: {
            executor: 'constant-vus',
            vus: 1,
            duration: __ENV.DURATION || '30s',
            exec: 'eventLoad',
          },
        }
      : {}),
  },
  thresholds: {
    'http_req_duration{scenario:snapshots}': ['p(95)<300'],
    'http_req_failed{scenario:snapshots}': ['rate<0.01'],
    ...(WITH_EVENTS ? { leaderboard_event_latency_ms: ['p(95)<1000'] } : {}),
  },
}

function identity(extra) {
  const params = {
    scoringPolicyId: POLICY_ID,
    scoringPolicyVersion: POLICY_VERSION,
    rankBy: 'OVERALL_SCORE',
    pair: PAIR,
    timeframe: TIMEFRAME,
    k: K,
    ...extra,
  }
  return Object.entries(params)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join('&')
}

function readSnapshot(name, extra) {
  const response = http.get(`${BASE_URL}/api/v1/leaderboards?${identity(extra)}`, {
    tags: { name },
  })
  check(response, {
    [`${name}: status is 200`]: (item) => item.status === 200,
    [`${name}: bounded by K`]: (item) => {
      if (item.status !== 200) return false
      const data = item.json('data')
      return data.entries.length <= Number(data.k)
    },
  })
  return response
}

export function snapshotLoad() {
  group('snapshot', () => readSnapshot('snapshot'))
  group('filter', () => readSnapshot('filter', { minScore: '60' }))
  group('sort', () => readSnapshot('sort', { sortBy: 'MAX_DRAWDOWN', sortDirection: 'ASC' }))
  group('page', () => readSnapshot('page', { page: '2', pageSize: '4' }))
}

export function eventLoad() {
  ws.connect(WS_URL, {}, (socket) => {
    socket.on('open', () => {
      socket.send(
        JSON.stringify({
          eventType: 'LEADERBOARD_SUBSCRIBE',
          version: 1,
          requestId: 'k6',
          payload: {
            scoringPolicyId: POLICY_ID,
            scoringPolicyVersion: POLICY_VERSION,
            rankBy: 'OVERALL_SCORE',
            pair: PAIR,
            timeframe: TIMEFRAME,
            k: Number(K),
            runId: null,
            lastProjectionVersion: null,
          },
        }),
      )
    })
    socket.on('message', (raw) => {
      const message = JSON.parse(raw)
      if (message.eventType !== 'LEADERBOARD_UPDATED') return
      const occurred = Date.parse(message.occurredAt)
      eventLatency.add(Date.now() - occurred)
      check(message, {
        'event: carries a projection version': (item) => item.payload.projectionVersion > 0,
      })
    })
    socket.setTimeout(() => socket.close(), Number(__ENV.WS_MS || 30000))
  })
}
