# Quickstart: Historical Market Data

This guide demonstrates TV1's independently testable backend outcome: acquire normalized closed Binance Candles, reuse local coverage, materialize one immutable dataset, and read it without another provider call.

## Prerequisites

- Python 3.12
- Docker Desktop with Compose
- `curl` or another HTTP client
- Internet access only for the optional real-Binance smoke step

No Binance key is needed for public Spot Klines. Never place exchange trading/withdrawal credentials in this project.

## 1. Clean setup

From the repository root:

```powershell
docker compose up -d postgres
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install --constraint ".\backend\requirements.runtime.lock" -e ".\backend[dev]"
.\.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head
```

Compose publishes PostgreSQL on host port `55432` by default to avoid collisions with an existing local PostgreSQL on `5432`; set `CSL_POSTGRES_PORT` only when another explicit host port is required.

Copy `.env.example` to `.env` only for local overrides. The committed example contains no secrets.

## 2. Run quality gates

```powershell
.\.venv\Scripts\ruff.exe check backend
.\.venv\Scripts\mypy.exe backend/src
.\.venv\Scripts\pytest.exe backend/tests/unit backend/tests/contract -q
.\.venv\Scripts\pytest.exe backend/tests/integration -q
```

Integration tests use `TEST_DATABASE_URL` when supplied. When Docker is available, the documented test command targets the PostgreSQL 16 Compose service; it never substitutes SQLite for database semantics.

Migration gate:

```powershell
.\.venv\Scripts\alembic.exe -c backend/alembic.ini downgrade base
.\.venv\Scripts\alembic.exe -c backend/alembic.ini upgrade head
```

## 3. Start the API

```powershell
.\.venv\Scripts\uvicorn.exe crypto_lab.main:app --app-dir backend/src --host 127.0.0.1 --port 8000 --no-access-log
```

Readiness must report success only after the database migration is present and PostgreSQL is reachable:

```powershell
curl.exe http://127.0.0.1:8000/health/live
curl.exe http://127.0.0.1:8000/health/ready
```

## 4. Inspect contract dimensions

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/market-data/dimensions"
```

Expected data includes:

- contract version `1`;
- provider `BINANCE`;
- pair `BTCUSDT`;
- `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `1d`;
- default range limit `500`, maximum `1000`.

This endpoint must not call Binance.

## 5. Acquire and normalize a bounded historical range

Use a closed, UTC-aligned range:

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/market-data/candles?provider=BINANCE&pair=BTCUSDT&timeframe=5m&startTime=2024-01-01T00%3A00%3A00.000Z&endTime=2024-01-01T01%3A00%3A00.000Z&limit=12&schemaVersion=1"
```

Acceptance checks:

- envelope has `success: true` and a request ID;
- `data.completeness` is `COMPLETE` when Binance has all 12 expected closed intervals;
- `missingRanges` is empty;
- exactly 12 unique Candles are chronological from `00:00` through `00:55` UTC;
- decimal values are JSON strings and provider array fields never appear;
- every `closeTime` is four minutes, 59.999 seconds after its `openTime`.

Run the same request again. Structured records should show a local complete hit and zero acquired rows/provider pages for the second call.

## 6. Prove boundary validation happens before provider access

The unaligned request must return `422` and `MARKET_RANGE_UNALIGNED`:

```powershell
curl.exe -i "http://127.0.0.1:8000/api/v1/market-data/candles?provider=BINANCE&pair=BTCUSDT&timeframe=5m&startTime=2024-01-01T00%3A01%3A00.000Z&endTime=2024-01-01T01%3A00%3A00.000Z&limit=12"
```

The over-limit request must return `422` and `MARKET_RANGE_TOO_LARGE`, not a truncated success.

## 7. Materialize an immutable dataset

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/market-data/datasets" -H "Content-Type: application/json" -d '{"schemaVersion":"1","selection":{"provider":"BINANCE","pair":"BTCUSDT","timeframe":"5m"},"range":{"startTime":"2024-01-01T00:00:00.000Z","endTime":"2024-01-01T01:00:00.000Z"}}'
```

Expected first completed response is `201`; reuse may return `200`. Save `data.datasetId`. A concurrent claimant may receive `202` with the same ID and `BUILDING`, never a second logical dataset.

Acceptance checks for a completed response:

- `status` is `COMPLETE`;
- `candleCount` is `12`;
- `checksum` is 64 lowercase hexadecimal characters;
- selection/range/version exactly match the request;
- no build token, provider URL, or raw payload is exposed.

Submit the same body again. The returned dataset ID and checksum must be unchanged and no provider call should occur.

## 8. Resolve and page the dataset without provider access

```powershell
curl.exe "http://127.0.0.1:8000/api/v1/market-data/datasets/<dataset-id>"
curl.exe "http://127.0.0.1:8000/api/v1/market-data/datasets/<dataset-id>/candles?pageSize=5"
```

Follow `nextCursor` until `hasMore` is false. Concatenated pages must contain the same 12 chronological Candles and reproduce the recorded checksum. Stop network access to Binance and repeat both dataset reads; they must still succeed.

## 9. Demonstrate explicit gap behavior deterministically

Provider outages and genuine historical gaps are not reliable to reproduce against live Binance. Run the contract scenarios:

```powershell
.\.venv\Scripts\pytest.exe backend/tests/contract/test_historical_service.py -k "partial or empty or backfill" -q
```

The scenarios prove:

- a locally missing interval is fetched without refetching covered intervals;
- a successful provider response that cannot fill every expected open returns `PARTIAL` with the exact gap;
- zero available Candles returns `EMPTY`;
- neither partial nor empty coverage finalizes a `COMPLETE` dataset.

## 10. Run performance checks

Performance tests are opt-in and record Python, PostgreSQL, OS, CPU, sample size, warm-up, and percentile conditions:

```powershell
.\.venv\Scripts\pytest.exe backend/tests/performance -m performance -q
```

Targets:

- locally complete 500-Candle reads: p95 under 300 ms;
- deterministic provider acquisition/persistence of 10,000 Candles: under 60 seconds.

## Expected traceability outcome

| Demonstration | Feature coverage |
|---|---|
| Dimensions and invalid request | FR-001, FR-024–FR-026; SC-006 |
| First historical range | US1; FR-002–FR-016; SC-001, SC-003 |
| Repeat local read | US1; FR-011; SC-002 |
| Dataset build/reuse/read | US2; FR-017–FR-021; SC-002, SC-004 |
| Gap fixtures | US3; FR-014–FR-015, FR-028; SC-003 |
| Provider contract suite | US4; FR-002, FR-022, FR-027; SC-005 |
| Performance | NFR-001–NFR-002; SC-007 |

## Executed checkpoint (2026-08-13)

Reference environment: Python 3.12.4, PostgreSQL 16.14, Docker 29.4.2, Docker Compose 5.1.3, AMD64 Windows host.

- Ruff format/lint passed; mypy strict reported no issues in 32 source files.
- All 54 tests passed in 9.57 seconds, including real PostgreSQL repository/migration and performance scenarios.
- The locked multi-stage Docker image built successfully; the one-shot Alembic migration container exited `0`, then API readiness returned `UP`.
- A real Binance request for three closed `BTCUSDT` 5m intervals returned canonical decimal strings and `COMPLETE`. The repeat log changed from `local_count=0, fetched_count=3` to `local_count=3, fetched_count=0`.
- Dataset materialization returned `COMPLETE`, `candleCount=3`, a stable SHA-256 checksum, provider-free metadata/membership reads, and a `pageSize=2` page with an opaque next cursor.

These results are execution evidence for T029, T038, T046, and T052. Deterministic partial/empty, concurrency, retry, invalid-provider, and integrity cases remain automated because live upstream failures are not reproducible acceptance inputs.

Final Spec Kit convergence found 54/54 completed tasks, zero open feature-checklist items, no unresolved clarification marker, no OpenAPI/consumer/architecture drift, and no missing local link in the HTML decision record. No task was appended: **Converged**.
