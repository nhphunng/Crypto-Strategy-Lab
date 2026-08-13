# Data Model: Leaderboard and Trade Visualization

## Modeling Rules

- `EvaluationResult` and `ScoringPolicy` are immutable upstream records and the authoritative ranking inputs.
- `Leaderboard` is a versioned projection scoped to comparable evaluations; `LeaderboardEntry` is owned by that projection.
- JSON/API fields are camelCase; Python/database fields are snake_case. Decimal values serialize as strings and instants as UTC ISO-8601.
- No entity contains a concrete strategy-name discriminator for ranking or rendering behavior.

## Entity: ScoringPolicy (upstream reference)

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | Stable logical identity |
| version | positive integer/string | Immutable; unique with `id` |
| name | string | Human-readable |
| defaultRankMetric | enum | Default selection from `OVERALL_SCORE`, `TOTAL_RETURN`, `WIN_RATE`, `MAX_DRAWDOWN`, `SHARPE_RATIO` |
| metricDirections | map | `ASC`/`DESC` per supported ranking metric; MDD semantics explicit |
| weights/normalization | versioned configuration | Required for overall score |
| eligibilityRules | configuration | Includes non-finite/no-trade behavior |
| tieBreakers | ordered list | Complete deterministic key ending in immutable Evaluation Result ID |

## Entity: EvaluationResult (upstream reference)

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | Immutable |
| jobId / runId | UUID | Correlation and idempotency identity |
| backtestResultId | UUID | Required, immutable |
| strategyId / strategyVersion | string | Required immutable provenance |
| datasetId | UUID | Required immutable provenance |
| pair / timeframe / startTime / endTime | value fields | Defines comparison/display context |
| totalReturn | decimal | Finite |
| winRate | decimal | Finite, documented scale |
| maxDrawdown | decimal | Finite, direction documented |
| numberOfTrades | non-negative integer | Zero supported |
| sharpeRatio | nullable decimal | Null for undefined; never NaN/infinite |
| score | decimal | Required versioned overall score; raw-metric ranking does not remove it |
| scoringPolicyId / scoringPolicyVersion | identity | Required |
| evaluatedAt | UTC instant | Required |

## Entity: Leaderboard

Represents one current Top-K projection.

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | Primary key |
| scopeKey | string | Canonical comparison scope derived from optional run/pair/timeframe filters; excludes presentation sort/filter/page state |
| scoringPolicyId / scoringPolicyVersion | identity | Required immutable policy reference |
| rankMetric | enum | Metric that determines Top-K membership and authoritative rank |
| k | integer | `1..200`; assignment demo default `10` |
| projectionVersion | non-negative integer | Monotonically increments on each visible projection change |
| updatedAt | UTC instant | Commit time for current projection |
| sourceRunId | nullable UUID | Run associated with most recent change |
| entryCount | integer | `0..k` and equals stored active entries |

**Identity**: unique `(scope_key, scoring_policy_id, scoring_policy_version, rank_metric, k)`. Every REST query and WebSocket subscription resolves this complete identity; a different K or ranking metric is a different projection.

**Indices**: unique identity above; `(updated_at)` for history/operations.

## Entity: LeaderboardEntry

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | Stable row identity |
| leaderboardId | UUID | Owning projection |
| evaluationResultId | UUID | Required immutable reference |
| rank | positive integer | `1..k`, contiguous within projection |
| sortKey | structured/normalized values | Derived from the selected rank metric plus policy tie-breakers; supports deterministic comparison |
| projectionVersion | integer | Version at which this row became current; returned with the row contract |
| enteredAt / updatedAt | UTC instant | Audit timestamps |

**Constraints**:

- Unique `(leaderboard_id, rank)`.
- Unique `(leaderboard_id, evaluation_result_id)`.
- The referenced Evaluation Result policy version equals the Leaderboard policy version.
- Entry count never exceeds K and ranks are contiguous after transaction commit.

**Recommended persistence mapping**: store only identity/rank/audit/sort key; read display metrics and provenance from immutable referenced records to avoid semantic duplication.

## Entity: LeaderboardUpdateRecord

A durable publication record for snapshot/event consistency.

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | Event ID and idempotency key |
| leaderboardId | UUID | Required |
| projectionVersion | integer | Unique within Leaderboard |
| eventType | enum | `LEADERBOARD_UPDATED` |
| sourceEvaluationResultId | UUID | Candidate that triggered evaluation |
| sourceRunId / sourceJobId | nullable UUID | Correlation identifiers |
| addedIds / removedIds / movedIds | UUID lists | Compact changed-set metadata |
| occurredAt | UTC instant | Required |
| publishedAt | nullable UTC instant | Publication status |

**Identity**: unique `(leaderboard_id, projection_version)` and unique `id`.

## Entity: RankedResultDetail (read model)

| Field group | Contents |
|-------------|----------|
| Ranking | Leaderboard identity, projection version, rank, K, score/policy |
| Strategy | Strategy ID/version, display name, member versions/parameters summary |
| Evaluation | required metrics, evaluated time, Evaluation Result ID |
| Backtest | Backtest Run/result IDs, job/run IDs, execution settings/checksum |
| Dataset | dataset/provider, Market Pair, Timeframe, UTC range |
| Visualization availability | Candle, overlay, Signal and Trade counts/statuses |

This is a composed read DTO, not a mutable aggregate.

## Entity: Signal (upstream reference)

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | Stable identity |
| strategyId / strategyVersion | string | Required |
| timestamp | UTC instant | Must align to normalized market timeline |
| action | enum | `BUY`, `SELL`, `HOLD` |
| price | nullable decimal | Recorded reference price |
| strength / reason | optional | Strategy-provided, bounded text/value |
| overlayRefs | list | Generic overlay IDs only |

## Entity: Trade (upstream reference)

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | Stable within Backtest Result |
| entrySignalId / exitSignalId | nullable UUID | Provenance when available |
| entryTime / exitTime | UTC instant | `entryTime <= exitTime` |
| entryPrice / exitPrice | decimal | Positive and exact |
| side | enum | Supported simulated position side |
| quantity | decimal | Positive |
| profitLoss / returnPercent | decimal | Reconciles with Backtest Result |

## Entity: VisualizationOverlay (read contract)

| Field | Type | Rules |
|-------|------|-------|
| id | string | Stable within ranked result |
| kind | enum | `LINE`, `BAND`, `ZONE` |
| label | string | Required accessible name |
| points | bounded time/value points | Ordered; UTC timestamps; finite decimal values |
| styleToken | enum/token | Presentation hint, not arbitrary executable styling |
| sourceStrategyId / sourceStrategyVersion | string | Required provenance |

## Projection State Transitions

```text
Evaluation persisted
  -> REJECTED (incompatible/ineligible; projection unchanged)
  -> UNCHANGED (eligible but outside Top-K or identical current member)
  -> CHANGED (insert/move/remove atomically; projectionVersion + 1)
  -> PUBLISHED (durable update record delivered at least once)
```

Publication retry does not repeat `CHANGED`. A consumer reconciles event version `n` only when its current version is `n-1`; any gap triggers a REST snapshot.

## Validation and Concurrency Invariants

1. Reject NaN/infinite metrics before ranking; null remains distinct from zero.
2. Ranking comparator is total and deterministic for all eligible inputs.
3. Projection mutation locks/serializes one Leaderboard identity and commits entries, metadata, and update record atomically.
4. Duplicate evaluation/policy input is an idempotent no-op unless the current projection is being repaired from authoritative inputs.
5. Historical Strategy, dataset, Evaluation Result, and policy versions are never overwritten through this feature.
6. Marker coordinates use recorded UTC timestamp/price. Unaligned data is reported, never guessed.
7. REST responses expose metric direction/unit metadata from the selected policy; presentation sorting and metric-range filters never change stored rank or projection version.
8. Realtime connection state is client-owned view state and is not persisted in or returned as part of the authoritative REST snapshot.
