# Phase 0 Research: Realtime Multi-Chart Dashboard

## Decision 1: Bounded REST bootstrap plus versioned WebSocket updates

**Decision**: Load each slot's bounded initial range through `/api/v1/market-data/candles`, then receive incremental updates through one `/ws/v1/market-data` connection. REST remains authoritative for range recovery; WebSocket events carry only incremental state and Candle changes.

**Rationale**: A snapshot plus incremental stream is simple to reason about, lets a reconnect repair missed data, and prevents clients from treating an event stream as permanent storage.

**Alternatives considered**:

- WebSocket-only history and realtime: fewer endpoints but recovery, pagination, and caching become harder.
- Repeated HTTP polling: simpler transport but violates the realtime/no-polling requirement and wastes requests.
- Browser-to-Binance WebSocket: quick demo but violates provider abstraction, credential, validation, and frontend-boundary rules.

## Decision 2: One dashboard connection with slot-scoped commands

**Decision**: Maintain one backend WebSocket per dashboard. Commands include a stable `slotId`; the server maps at most four slot IDs to provider-neutral selections. Equal selections share a reference-counted upstream stream, while every slot retains independent client state.

**Rationale**: One connection lowers browser/server overhead and makes the four-slot resource limit enforceable. Reference counting prevents duplicate provider streams without coupling UI viewports.

**Alternatives considered**:

- One WebSocket per chart: locally simple but multiplies connection/reconnect work and makes duplicate selections wasteful.
- One subscription with four fixed timeframes: too rigid; it prevents independent add/remove/change behavior.
- A shared global frontend chart state store: unnecessary before proven cross-feature state; local reducers and one connection provider are enough.

## Decision 3: Provider-neutral Candle merge rules

**Decision**: Use `(provider, pair, timeframe, openTime)` as identity. Timestamps are UTC and prices/volume cross boundaries as finite decimal strings. A same-identity open update replaces the open values; an open candle may become closed; a closed candle never becomes open. Exact duplicate closed updates are ignored, conflicting closed updates are quarantined/logged, and older incremental events never move the visible series backward. Backfill data is merged, deduplicated, sorted, then published.

**Rationale**: The rule handles normal provider updates while keeping chart, strategy, and backtest inputs deterministic and independent of floating-point serialization.

**Alternatives considered**:

- Append every update: creates duplicate intervals.
- Use arrival order: breaks during reconnect or provider reordering.
- Silently overwrite conflicting closed candles: hides source-quality problems and can change historical analysis without evidence.

## Decision 4: Capped reconnect followed by closed-candle backfill

**Decision**: On provider disconnect or a missed heartbeat, mark affected selections `STALE`, then `RECONNECTING`. Retry with exponential delays of approximately 1, 2, 4, 8, 16, and 30 seconds, capped at 30 seconds with ±20% jitter, for at most eight automatic attempts. After reconnect, request closed candles after the last confirmed closed interval through the historical port, merge them, then mark the selection `LIVE`. Exhaustion produces `ERROR`; manual retry starts a new bounded cycle.

**Rationale**: Bounded exponential backoff avoids reconnect storms, jitter avoids synchronized clients, and backfill proves continuity before the UI claims the data is live.

**Alternatives considered**:

- Infinite rapid retry: can amplify an outage and never provides a terminal user state.
- Resume without backfill: can leave invisible gaps.
- Restart the entire dashboard: violates slot isolation and loses unaffected viewport state.

## Decision 5: Bounded history and explicit range semantics

**Decision**: Each chart requests explicit `startTime` and `endTime`; responses cap at 1,000 candles. The initial UI derives a range of at most 500 intervals. Completeness is `COMPLETE`, `PARTIAL`, or `EMPTY`, and cursors/range extension may be added later without changing Candle identity.

**Rationale**: Explicit ranges make gaps testable and stop unbounded database queries or chart rendering.

**Alternatives considered**:

- Return all stored candles: unsafe for long-running datasets.
- Fixed provider-specific limits: leaks provider constraints into the public contract.
- Client-only truncation: still wastes backend, network, and parsing resources.

## Decision 6: Slot isolation with a shared connection provider

**Decision**: React keeps the dashboard pair and slot list in a route-level reducer. Each `ChartSlot` owns timeframe, bounded Candle buffer, status, error, and viewport through its stable ID. A shared connection hook validates events and dispatches them by selection. Changing a timeframe uses a generation token so late history/events for the old selection are discarded.

**Rationale**: This makes slot isolation explicit, prevents request races, and avoids a new state dependency.

**Alternatives considered**:

- Store every chart in one undifferentiated object: increases accidental cross-slot resets.
- One query key for all charts: invalidating one timeframe reloads all slots.
- Introduce Zustand immediately: adds a dependency without demonstrated reuse.

## Decision 7: Observable freshness and measurable propagation

**Decision**: Every connection and command carries `requestId`; logs/metrics add sanitized `connectionId`, provider, pair, timeframe, state, retry count, gap size, and duration. Metrics include connected clients, active logical slots, unique upstream selections, reconnects, recovery failures, last-event age, invalid events, and backend-ingestion-to-publish latency. Browser test telemetry supplies publish-to-visible timing for the full p95 target.

**Rationale**: The team can distinguish provider delay, backend delay, browser delay, and leaked subscriptions without logging sensitive payloads.

**Alternatives considered**:

- Log raw provider messages: exposes unnecessary data and creates noisy logs.
- Measure only browser arrival: cannot locate a slow stage.
- Add a tracing platform now: not required; structured logs and metrics meet current scope.

## Decision 8: Accessible, responsive base chart with a generic extension seam

**Decision**: Add/remove/timeframe/retry controls are keyboard operable with visible focus. Connection state uses text/icon plus color and an announced live region for meaningful changes. Narrow screens use one column. The base chart accepts generic bounded series/marker descriptors but contains no strategy, trade, or leaderboard branches.

**Rationale**: Canvas charts alone are not accessible, status cannot rely on color, and TV5 needs composition without reversing feature ownership.

**Alternatives considered**:

- Color-only connection badges: fails non-color communication.
- Put TV5 overlay rules into TV2: couples independent features.
- Make the entire chart keyboard navigable at Candle resolution in MVP: high complexity; an accessible textual summary plus operable controls meets the current feature while detailed overlay interaction remains TV5-owned.

## Architecture Approval Status

`docs/ARCHITECTURE.md`, ADR-002, and ADR-003 are `Accepted` and are binding implementation decisions. On 2026-08-19, TV1 and TV2 completed cross-review of the shared Candle/history version 1 boundary, including fields, precision, UTC/timeframe encoding, half-open range behavior, completeness, limits, versions, and errors. No research decision or contract semantic changed during acceptance.
