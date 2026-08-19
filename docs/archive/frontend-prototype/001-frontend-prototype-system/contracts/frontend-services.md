# Frontend Service Contracts

These UI-facing contracts isolate feature modules from fixture storage and future transport DTOs. Methods are asynchronous even when implemented by deterministic mock adapters.

## Contract Rules

- Pages and presentational components MUST NOT import fixture modules or call `fetch`/WebSocket directly.
- Service instances are provided by the application composition root.
- Queries accept an optional cancellation signal.
- Subscriptions return an unsubscribe function and MUST clean up timers/listeners.
- Remote adapters preserve raw version, source status, decimal values, identifiers, and provenance before mapping to normalized domain records.
- Mock adapters expose deterministic loading, success, empty, error, stale, reconnecting, and degraded scenarios.
- Contracts without an authoritative backend specification remain frontend-semantic only; no speculative URL is assigned.

## Market Gateway

```ts
interface MarketGateway {
  listMarkets(query?: string, signal?: AbortSignal): Promise<Market[]>;
  getSnapshot(marketId: string, signal?: AbortSignal): Promise<Market>;
  getCandles(input: CandleQuery, signal?: AbortSignal): Promise<CandleSeries>;
  subscribeConnection(listener: (state: ConnectionState) => void): Unsubscribe;
}
```

Behavior:

- Search is case-insensitive across pair, base asset, and display name.
- Unavailable markets remain discoverable but cannot replace the active workspace market.
- Each chart slot requests candles independently; a future remote stream adapter owns one shared connection for up to four slot bindings.
- Last successful candles remain visible during stale/reconnecting states.

Prospective mapping:

- `GET /api/v1/market-data/dimensions`
- `GET /api/v1/market-data/candles`
- Future shared `WS /ws/v1/market-data`

## Strategy Gateway

```ts
interface StrategyGateway {
  listMethods(signal?: AbortSignal): Promise<AnalysisMethodDefinition[]>;
  listPresets(signal?: AbortSignal): Promise<StrategyPreset[]>;
  getStrategy(id: string, signal?: AbortSignal): Promise<SavedStrategy>;
  saveStrategy(draft: StrategyDraft, signal?: AbortSignal): Promise<SavedStrategy>;
}
```

Behavior:

- Parameter forms and validators are generated from definitions and typed constraints.
- Saving through the mock adapter creates a deterministic versioned record.
- Remote save has no authoritative endpoint yet and remains adapter-pending.

## Backtest Gateway

```ts
interface BacktestGateway {
  run(configuration: BacktestConfiguration, signal?: AbortSignal): Promise<BacktestRun>;
  getRun(runId: string, signal?: AbortSignal): Promise<BacktestRun>;
  listRuns(query: RunQuery, signal?: AbortSignal): Promise<BacktestRun[]>;
  subscribeRun(runId: string, listener: (run: BacktestRun) => void): Unsubscribe;
  startSearch(configuration: SearchConfiguration, signal?: AbortSignal): Promise<StrategySearch>;
  stopSearch(searchId: string, signal?: AbortSignal): Promise<StrategySearch>;
  subscribeSearch(searchId: string, listener: (search: StrategySearch) => void): Unsubscribe;
}
```

Behavior:

- The gateway hides dataset materialization, strategy resolution, run creation/start, and evaluation orchestration.
- No-trade or failed metrics remain unavailable rather than becoming zero.
- Search progress is capped at its candidate limit and timer/subscription cleanup is mandatory.
- Search/list/cancel endpoints are not authoritative yet; mock behavior is explicitly simulated.

## Leaderboard Gateway

```ts
interface LeaderboardGateway {
  listEntries(query: LeaderboardQuery, signal?: AbortSignal): Promise<LeaderboardEntry[]>;
  getEntry(entryId: string, signal?: AbortSignal): Promise<LeaderboardEntryDetail>;
}
```

Behavior:

- Sorting is stable, honors metric direction, and keeps filters during detail inspection.
- A future WebSocket acts only as invalidation; the adapter refetches the authoritative REST snapshot after deduplication/gap checks.

## News Gateway

```ts
interface NewsGateway {
  listNews(query: NewsQuery, signal?: AbortSignal): Promise<NewsItem[]>;
  getSentimentSummary(query: NewsQuery, signal?: AbortSignal): Promise<SentimentSummary>;
}
```

Behavior:

- Market, sentiment, and date-range filters compose.
- Sentiment provider degradation removes classification values without blocking article access or other product features.
- No authoritative backend contract exists yet.

## Operations Gateway

```ts
interface OperationsGateway {
  getSnapshot(signal?: AbortSignal): Promise<OperationalSnapshot>;
  subscribeSnapshot(listener: (snapshot: OperationalSnapshot) => void): Unsubscribe;
  startLoop(signal?: AbortSignal): Promise<OperationalSnapshot>;
  stopLoop(signal?: AbortSignal): Promise<OperationalSnapshot>;
}
```

Behavior:

- Optional dependency degradation does not imply the core pipeline is unavailable.
- Stop requires UI confirmation; counters stop after the adapter acknowledges stopped state and resume after start.
- Production operator controls will require environment-protected authorization; no authoritative endpoint exists yet.

## Shared Contract Tests

Every mock or future remote adapter must pass the same behavioral suite for:

- cancellation and subscription cleanup;
- normalized status and source-status retention;
- loading/empty/error/degraded behavior;
- deterministic sorting/filtering semantics;
- lossless identifiers, versions, and provenance;
- page independence from transport DTO/envelope shape.
