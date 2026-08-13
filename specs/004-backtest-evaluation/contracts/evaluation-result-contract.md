# Contract: Evaluation Result for TV5

**Owner**: TV4 | **Consumer**: TV5 Leaderboard and Visualization | **Version**: `1.0.0`

## Required Record

An immutable `EvaluationResult` exposes:

- `id`, `jobId`, `runId`, `backtestResultId`;
- Strategy Definition ID, Strategy ID/type/version, parameter fingerprint;
- dataset ID/schema version/checksum, provider, Market Pair, Timeframe, `[startTime,endTime)`;
- execution policy ID/version, complete immutable execution-configuration summary, and configuration fingerprint;
- Total Return, Win Rate, Maximum Drawdown, Number of Trades, nullable Profit Factor, nullable Sharpe Ratio;
- score, eligibility, exclusion reasons, Scoring Policy ID/version;
- Evaluation Policy ID/version, evaluated time, and content fingerprint.
- `analysisType=HISTORICAL_SIMULATION` and the approved non-investment-advice disclaimer.

Decimals are plain strings; timestamps are UTC ISO-8601; null is distinct from zero. NaN/infinity are forbidden.

## Trade Read Contract

Each Trade provides stable UUID, entry/exit Signal Snapshot UUID references, UTC entry/exit times, reference/fill prices, `LONG` side, quantity, entry/exit fees, profit/loss, return percent, and close reason. The Signal Snapshot also retains the exact upstream Feature 003 source Signal ID. Pages default to 25 and max at 200.

## Compatibility and Idempotency

- Feature 005 consumes metrics/score and never recalculates them.
- Duplicate source/policy identity resolves one Evaluation Result.
- New policy version creates a new immutable Evaluation Result.
- Breaking changes to metric meaning, unit, null semantics, score eligibility, or required provenance require a new contract major and TV4/TV5 review.
