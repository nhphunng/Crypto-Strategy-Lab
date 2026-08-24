// Load and soak validation for the realtime market-data channel.
//
// Run against the deterministic stub backend (no Binance/DB required):
//
//   backend/.venv/Scripts/python.exe backend/scripts/realtime_stub_server.py
//
// then, from the repository root:
//
//   k6 run tests/load/realtime-market-data.js               # all scenarios
//   k6 run --env SCENARIO=latency tests/load/realtime-market-data.js
//   k6 run --env SCENARIO=soak tests/load/realtime-market-data.js
//   k6 run --env SCENARIO=smoke tests/load/realtime-market-data.js
//
// Scenario budgets (override with SESSION_SECONDS):
//   latency_10m  10 sessions x 10 minutes, 4 slots each
//   soak_30m     1 session x 30 minutes,  4 slots each
//   smoke_30s    2 sessions x 40 seconds, 4 slots each
//
// Thresholds:
//   candle_within_1s_ratio             rate >= 0.95  (ingestion-to-publish latency)
//   candle_no_duplicate_identity_ratio  rate == 1    (no repeated (identity, revision, closed))
//   candle_no_time_regression_ratio     rate == 1    (openTime/revision never go backward)
//
// NOTE: uses the legacy k6/ws module. k6 v2.0.0's k6/websockets module never
// dispatches the `open` event for this server's handshake (readyState stays
// CONNECTING while the server sees the connection), so k6/websockets cannot be
// used here.

import { check } from "k6";
import { Rate } from "k6/metrics";
import ws from "k6/ws";

const WS_URL = __ENV.WS_URL || "ws://localhost:8000/ws/v1/market-data";
const PROVIDER = __ENV.PROVIDER || "BINANCE";
const PAIR = __ENV.PAIR || "BTCUSDT";
const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"];
const MAX_SLOTS = 4;

const scenario = __ENV.SCENARIO || "";
const sessionSeconds =
  parseInt(__ENV.SESSION_SECONDS || "0", 10) ||
  (scenario === "soak" ? 1800 : scenario === "smoke" ? 40 : 600);

const scenarios = {};
if (!scenario || scenario === "latency") {
  scenarios.latency_10m = {
    executor: "per-vu-iterations",
    vus: 10,
    iterations: 1,
    maxDuration: (sessionSeconds + 120).toString() + "s",
  };
}
if (!scenario || scenario === "soak") {
  scenarios.soak_30m = {
    executor: "per-vu-iterations",
    vus: 1,
    iterations: 1,
    maxDuration: (sessionSeconds + 120).toString() + "s",
  };
}
if (scenario === "smoke") {
  scenarios.smoke_30s = {
    executor: "per-vu-iterations",
    vus: 2,
    iterations: 1,
    maxDuration: (sessionSeconds + 120).toString() + "s",
  };
}

const sessionMs = sessionSeconds * 1000;

const candleWithin1s = new Rate("candle_within_1s_ratio");
const noDuplicateIdentity = new Rate("candle_no_duplicate_identity_ratio");
const noTimeRegression = new Rate("candle_no_time_regression_ratio");

export const options = {
  scenarios,
  thresholds: {
    candle_within_1s_ratio: ["rate>=0.95"],
    candle_no_duplicate_identity_ratio: ["rate==1"],
    candle_no_time_regression_ratio: ["rate==1"],
  },
};

function newSession() {
  return {
    slots: {}, // slotId -> latest state
    bindings: {}, // slotId -> selection key
    seenSelections: {},
    identitySet: {},
    latestOpenTime: {}, // selection key -> openTime (ms)
    latestRevision: {}, // selection key -> revision
    candles: 0,
    beyond1s: 0,
    recoveryEvents: 0,
    limitRejected: false,
    closed: false,
  };
}

function selectionKey(payload) {
  return payload.selection.provider + "|" + payload.selection.pair + "|" + payload.selection.timeframe;
}

export default function () {
  const session = newSession();
  const res = ws.connect(
    WS_URL,
    { timeout: (sessionSeconds + 30).toString() + "s" },
    function (socket) {
      socket.on("open", function () {
        for (let i = 0; i < MAX_SLOTS; i += 1) {
          socket.send(
            JSON.stringify({
              eventType: "SUBSCRIBE_MARKET_DATA",
              version: "1",
              requestId: "load-" + __VU + "-slot-" + (i + 1),
              occurredAt: new Date().toISOString(),
              payload: {
                slotId: "load-" + __VU + "-slot-" + (i + 1),
                selection: {
                  provider: PROVIDER,
                  pair: PAIR,
                  timeframe: TIMEFRAMES[i % TIMEFRAMES.length],
                },
              },
            }),
          );
        }
        socket.send(
          JSON.stringify({
            eventType: "SUBSCRIBE_MARKET_DATA",
            version: "1",
            requestId: "load-" + __VU + "-slot-limit-probe",
            occurredAt: new Date().toISOString(),
            payload: {
              slotId: "load-" + __VU + "-slot-" + (MAX_SLOTS + 1),
              selection: {
                provider: PROVIDER,
                pair: PAIR,
                timeframe: "5m",
              },
            },
          }),
        );
        socket.setTimeout(function () {
          socket.close();
        }, sessionMs);
      });
      socket.on("message", function (raw) {
        let message;
        try {
          message = JSON.parse(raw);
        } catch (err) {
          return;
        }
        const payload = message.payload || {};
        switch (message.eventType) {
          case "SUBSCRIPTION_STATE_CHANGED": {
            for (const slotId of payload.slotIds || []) {
              session.slots[slotId] = payload.state;
              if (payload.selection) {
                session.bindings[slotId] = selectionKey(payload);
                session.seenSelections[selectionKey(payload)] = true;
              }
              if (payload.state === "RECONNECTING") {
                session.recoveryEvents += 1;
              }
            }
            break;
          }
          case "MARKET_DATA_ERROR": {
            if (payload.code === "MARKET_SUBSCRIPTION_LIMIT_REACHED") {
              session.limitRejected = true;
            }
            if (payload.retryable) {
              session.recoveryEvents += 1;
            }
            break;
          }
          case "CANDLE_UPDATED": {
            const key = selectionKey(payload);
            const candle = payload.candle || {};
            const openTime = Date.parse(candle.openTime);
            const revision = payload.revision || 0;
            const identity =
              candle.provider + "|" + candle.pair + "|" + candle.timeframe + "|" +
              candle.openTime + "|" + revision + "|" + candle.closed;
            // Revisions are monotonic within a bucket; the merge contract resets
            // the revision to 1 when a new bucket opens, so regression is judged
            // per (selection, bucket) pair.
            let regressed = false;
            if (openTime < (session.latestOpenTime[key] || 0)) {
              regressed = true;
            } else if (
              openTime === session.latestOpenTime[key] &&
              revision < (session.latestRevision[key] || 0)
            ) {
              regressed = true;
            }
            noTimeRegression.add(!regressed);
            if (openTime > (session.latestOpenTime[key] || 0)) {
              session.latestOpenTime[key] = openTime;
              session.latestRevision[key] = revision;
            } else if (
              openTime === session.latestOpenTime[key] &&
              revision > (session.latestRevision[key] || 0)
            ) {
              session.latestRevision[key] = revision;
            }
            noDuplicateIdentity.add(!session.identitySet[identity]);
            session.identitySet[identity] = true;
            const latencyMs = Date.now() - Date.parse(message.occurredAt || payload.occurredAt || 0);
            if (latencyMs >= 0 && latencyMs <= 1000) {
              candleWithin1s.add(true);
            } else {
              candleWithin1s.add(false);
              session.beyond1s += 1;
            }
            session.candles += 1;
            break;
          }
          default:
            break;
        }
      });
      socket.on("error", function (error) {
        check(error, { "no websocket error": () => false });
      });
      socket.on("close", function () {
        session.closed = true;
      });
    },
  );
  check(res, { "websocket handshake 101": (r) => r && r.status === 101 });
  const slotIds = Object.keys(session.slots);
  check(session, {
    "all four slots acknowledged": (s) => slotIds.length === 4,
    "at most four logical slot bindings": (s) => slotIds.length <= 4,
    "all bindings are known slot ids": (s) =>
      Object.keys(s.bindings).every((id) => id.indexOf("load-" + __VU + "-slot-") === 0),
    "four distinct selections active": (s) => Object.keys(s.seenSelections).length === 4,
    "fifth slot rejected with limit code": (s) => s.limitRejected,
    "received candle updates": (s) => s.candles > 0,
    "session ended cleanly": (s) => s.closed,
  });
  console.log(
    "VU " + __VU + " summary: slots=" + slotIds.length + " candles=" + session.candles +
      " beyond1s=" + session.beyond1s + " recoveryEvents=" + session.recoveryEvents +
      " limitRejected=" + session.limitRejected,
  );
}