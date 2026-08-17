# Data Model: Crypto Strategy Lab Frontend System

## Shared State Types

### Resource State

- `status`: `idle | loading | success | empty | error`
- `freshness`: `live | partial | stale | reconnecting | degraded`
- `data`: optional typed payload
- `error`: optional user-safe problem description
- `updatedAt`: optional timestamp
- Validation: `success` requires data; `empty` contains no records; `error` requires a problem description.

### Workspace Context

- `selectedMarketId`
- `watchlistMarketIds`
- `showExplanations`
- `connectionState`
- `activeStrategyId`
- `toasts`
- Persisted: selected market, watchlist, explanation preference
- Transient: connection state, active toast queue

## Market Domain

### Market

- `id`, `provider`, `pair`, `baseAsset`, `quoteAsset`, `displayName`
- `price`, `change24h`, `volume24h`
- `availability`: `available | unavailable | delayed`
- `iconTone`
- Uniqueness: `(provider, pair)`
- Validation: price/volume are non-negative; unavailable markets cannot replace the active selection.

### Candle

- `openTime`, `closeTime`
- `open`, `high`, `low`, `close`, `volume`
- `closed`, `sourceEventId`, `receivedAt`
- Validation: `low <= open/close <= high`; times are ordered; source decimal strings are preserved by adapters before numeric chart conversion.

### Chart Pane

- `slotId`: stable slot identity
- `timeframe`
- `indicators`
- `status`
- `candles`, `overlays`, `markers`
- State transitions: `loading -> live`; `live -> stale/reconnecting/error`; reconnect may return to `live` without discarding last visible data.
- Constraint: at most four active slots; hidden slots retain their configuration.

## Strategy Domain

### Analysis Method Definition

- `id`, `version`, `friendlyName`, `technicalName`
- `category`, `purpose`, `signalDescription`
- `availability`
- `parameters`: parameter definitions
- `constraints`: typed cross-field validation rules
- Extensibility: adding a method requires a new definition and optional adapter support, not page conditionals.

### Parameter Definition

- `key`, `label`, `description`
- `valueType`: `integer | decimal | boolean | select`
- `defaultValue`, optional `min`, `max`, `step`, `options`
- Validation: current value matches its declared type and bounds.

### Strategy Draft

- `name`
- `marketId`, `timeframe`
- `selectedMethodIds`
- `parameterValues` keyed by method and parameter
- `combination`: composite rule
- `step`: `choose | configure | combine | review`
- Validation: at least one available method; all parameters valid; combination valid before review.

### Composite Rule

- `mode`: `majority | weighted`
- `weights` keyed by selected method
- `tieBehavior`: `hold | buy | sell`
- `buyThreshold`, `sellThreshold`
- Validation: weighted total equals 100%; thresholds are finite and `sellThreshold < buyThreshold`.

### Saved Strategy

- `id`, `version`, `displayName`
- `marketId`, `timeframe`
- configured methods and composite rule
- `createdAt`, `provenance`
- State: `draft -> reviewed -> saved`; reviewed drafts can be transferred directly to backtesting.

## Evaluation Domain

### Backtest Configuration

- `strategyId`, `strategyVersion`
- `marketId`, `timeframe`, `startTime`, `endTime`
- `initialCapital`, `feeRate`, `slippageRate`, `positionSizing`
- `datasetId`, `datasetChecksum`, `seed`
- Validation: ordered range; positive capital; non-negative costs; exact strategy/dataset versions.

### Backtest Run

- `id`, `sourceStatus`, `status`
- `configuration`, `progress`, `startedAt`, `completedAt`
- `metrics`, `trades`, `equityCurve`, `drawdownCurve`
- `provenance`, optional `failure`
- State transitions: `ready -> running -> completed | failed | stopped`; completed/failed states are terminal for a run record.

### Strategy Search

- `id`, `status`, `tested`, `candidateLimit`
- `configuration`, `topCandidates`, `eventFeed`
- State transitions: `ready -> running -> stopped | completed`; stopped searches can restart as a new execution while preserving prior results.

### Metric Set

- `totalReturn`, `winRate`, `maxDrawdown`, `tradeCount`
- `sharpeRatio`, `profitFactor`, `overallScore`
- Each metric carries display direction/unit metadata outside page markup.

### Trade

- `id`, `side`, `entryTime`, `exitTime`, `entryPrice`, `exitPrice`
- `quantity`, `pnl`, `returnPercent`, `exitReason`
- Relation: belongs to one backtest run and can select a chart interval.

### Provenance

- `strategyId`, `strategyVersion`
- `datasetId`, `datasetChecksum`, `schemaVersion`
- `executionAssumptions`, `seed`, `runId`
- Required for every completed evaluation and leaderboard detail.

## Leaderboard Domain

### Leaderboard Entry

- `rank`, `strategyId`, `strategyVersion`, `strategyName`, `strategyType`
- `metrics`, `score`, `status`
- `evaluationRunId`, `provenance`
- Sorting: stable for ties; metric direction determines ascending/descending behavior; less severe drawdown ranks above more severe drawdown.

### Leaderboard Query

- `marketId`, `timeframe`, `runId`, `strategyType`, `status`
- `sortKey`, `sortDirection`, `limit`
- State is preserved while opening and closing an entry inspector.

## News Domain

### News Item

- `id`, `headline`, `summary`, `source`, `publishedAt`, `url`
- `marketIds`, `sentiment`, `sentimentScore`
- `classification`: model/version/analyzed time
- Sentiment: `positive | neutral | negative | unavailable`
- Degraded behavior: article content remains available while classification fields become unavailable.

### News Query

- `marketId`, `sentiment`, `range`
- Filters compose rather than replace one another.

## Operations Domain

### Operational Snapshot

- `loop`: status, tested count, elapsed time, best score
- `dependencies`: service health records
- `workers`: active/idle/error worker records
- `queue`: queued/running counts and recent jobs
- `activeRun`: progress, throughput, estimate
- `events`: timestamped categorized event records
- Overall availability distinguishes optional degraded dependencies from core pipeline failures.

### Continuous Loop

- `status`: `running | stopping | stopped | starting | error`
- `tested`, `elapsedSeconds`, `bestScore`
- State transitions require confirmation for `running -> stopping -> stopped`; `stopped -> starting -> running` is immediate in the mock adapter.
