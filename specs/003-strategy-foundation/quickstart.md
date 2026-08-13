# Quickstart: Validate Strategy Foundation

This guide validates the four independently demonstrable Strategy Foundation stories after implementation. It uses deterministic fixtures and does not place trades or calculate backtest results.

## Prerequisites

- Docker Desktop with Compose
- Backend dependencies locked for Python 3.12
- PostgreSQL 16 available through the project Compose environment
- Normalized-market-data contract from Feature 001, or its deterministic contract fixture
- TV3 fixture pack containing:
  - MA normal, cross-above, cross-below, equality, warm-up, empty, invalid-period, and insufficient-history cases;
  - RSI normal, threshold exit, equality, constant-price, gains-only, losses-only, warm-up, invalid-period/threshold, and insufficient-history cases;
  - unsorted, duplicate, incomplete, invalid-OHLCV, open, future, and misaligned Strategy Context cases;
  - compatible, duplicate, invalid-metadata, deprecated, unavailable, and incompatible registry/version cases;
  - one generic compliant test strategy used only for extensibility.

Contracts: [REST OpenAPI](contracts/openapi.yaml) and [TV4 domain contract](contracts/strategy-domain-contract.md).

## 1. Start the Required Environment

```bash
docker compose -f infra/compose.yaml up -d postgres
```

Install the locked backend dependencies, apply migrations, and load deterministic normalized Candle fixtures using the repository commands established during implementation. Provider/network data must not be used for acceptance assertions.

## 2. Run Automated Quality Gates

```bash
cd backend
ruff check src tests
mypy src
pytest \
  tests/unit/strategy \
  tests/contract/test_strategy_contract.py \
  tests/contract/test_strategy_api.py \
  tests/contract/test_strategy_extensibility.py \
  tests/integration/test_strategy_definition_repository.py \
  tests/integration/test_strategy_analysis_api.py
```

Expected: all tests pass, repeated fixtures are identical, and no test accesses a live provider.

## 3. Validate `SE-US-01`: Run MA and RSI

1. Analyze the MA fixture with omitted `period`; confirm effective period 20 and one Signal per Candle.
2. Analyze explicit periods 2 and 500; confirm both boundaries are accepted.
3. Analyze period 1, 501, a non-integer, and an unknown parameter; confirm `INVALID_PARAMETERS` and zero Signals.
4. Inspect cross-above, cross-below, and equality fixtures; confirm BUY, SELL, and HOLD follow the specified strict boundaries.
5. Repeat steps 1–4 for RSI defaults 14/30/70 and valid period boundaries 2/200.
6. Confirm invalid thresholds, equal/reversed thresholds, constant prices, gains-only, and losses-only match the fixture outcomes.
7. Run empty and insufficient-history inputs; confirm `EMPTY` with zero Signals and `INSUFFICIENT` with one warm-up HOLD per supplied Candle.
8. Run the same complete fixtures at least 10 times; compare canonical results including Signal IDs, ordering, actions, phase, and reasons.

Expected: 100% identical repeated results, explicit warm-up, and no future Candle dependency.

## 4. Validate `SE-US-02`: Inspect Signals

1. Inspect any MA and RSI result and confirm exact Strategy Definition, parameters, dataset ID/version, context fingerprint, pair, timeframe, range, and decision timestamp.
2. Confirm each Signal timestamp equals its source Candle timestamp and sequence positions are contiguous.
3. Confirm action is only BUY, SELL, or HOLD and phase is WARMUP or EVALUATED.
4. Combine two result sequences that share timestamps and apply the documented cross-result ordering key.
5. Submit unsorted, duplicate, incomplete, invalid-OHLCV, open, future, and misaligned contexts.

Expected: valid Signals are fully traceable; invalid contexts return `INVALID_CONTEXT`, all issues are readable, and zero partial Signals are returned.

## 5. Validate `SP-US-01` and `SP-US-03`: Register and Discover

1. Start the application with built-in registration and request `GET /api/v1/strategies`.
2. Confirm MA and RSI use the same metadata shape and deterministic order.
3. Resolve each exact version and inspect its parameter definition, defaults, ranges, contract version, status, and capabilities.
4. In contract tests, attempt duplicate, invalid-metadata, invalid-parameter-schema, and incompatible registrations.
5. Register the generic compliant test strategy and repeat discovery/analysis without changing Backtester, Evaluator, or Leaderboard files.

Expected: invalid registration leaves all prior strategies usable; the generic strategy works through the common contract with no strategy-name branch downstream.

## 6. Validate `SP-US-02`: Immutable Versions

1. Create or resolve a Strategy Definition, record its ID and content fingerprint, and reference it from a historical fixture.
2. Repeat with identical canonical content; confirm the same definition resolves idempotently.
3. Change parameters; confirm a distinct immutable definition ID while the original remains unchanged.
4. Register a new behavior version; confirm the historical definition still resolves the original strategy version.
5. Request unknown, unavailable, deprecated, and incompatible versions for new analysis.

Expected: distinct categorized errors, no latest-version fallback, deprecated metadata remains historically resolvable, and all old definition content is unchanged.

## 7. Validate TV4 Contract

1. Give TV4's contract test an exact Strategy Definition and immutable Strategy Context rather than a concrete MA/RSI object.
2. Consume the resulting ordered Signals through the shared domain contract.
3. Repeat with MA, RSI, and the generic compliant strategy.
4. Search TV4 Backtester, Evaluator, and Leaderboard code for concrete strategy names.

Expected: all three strategies are consumed through one contract and no MA-, RSI-, or generic-strategy-specific branch exists downstream.

## 8. Benchmark and Architecture Fitness

Run the 10,000-Candle MA and RSI benchmark fixture on the documented reference environment. Record Python version, CPU, memory, fixture fingerprint, repetitions, and p95 duration.

Expected: each strategy completes in linear time with p95 below 1 second, repeated output remains identical, and calculation performs no database, HTTP, queue, provider, clock, or random access.

## Acceptance Summary

| Story | Pass signal |
|-------|-------------|
| `SE-US-01` | MA/RSI normal, boundary, warm-up, invalid, and repeated fixtures all match exact outcomes. |
| `SE-US-02` | Every Signal is ordered, aligned, categorized, and traceable; bad contexts yield no partial output. |
| `SP-US-01` / `SP-US-03` | MA, RSI, and a generic strategy register/discover uniformly; failure is atomic. |
| `SP-US-02` | Historical definitions remain immutable/resolvable and version-state errors never fall back. |
| TV4 contract | TV4 consumes every compliant strategy without concrete-strategy behavior. |

