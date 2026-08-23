# Implementation Plan: Historical Market Data

**Branch**: `feat/001-market-data-spec-plan` | **Feature Context**: `001-historical-market-data` | **Date**: 2026-08-13 | **Spec**: [spec.md](spec.md)

**Input**: Approved Feature 001 specification plus the shared TV1/TV2 Candle contract and TV3/TV4 immutable-dataset dependency.

## Summary

Deliver a Python backend vertical slice that validates provider-neutral market selections and half-open UTC ranges, reads PostgreSQL coverage first, fetches only missing closed Binance Klines through an adapter, persists immutable normalized Candles, reports exact completeness/gaps, and materializes content-addressed immutable CandleDatasets. FastAPI exposes versioned bounded range, dimension, dataset-materialization, metadata, and paginated-membership endpoints. Domain/application layers depend only on protocols; SQLAlchemy, httpx, FastAPI, and Binance payloads remain in outer layers.

The implementation intentionally does not contain a chart or realtime socket. It supplies the versioned REST/history and provider ports that TV2 consumes for bootstrap and reconnect backfill, while preserving a single owner for chart/subscription behavior.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2 async, Alembic, asyncpg, httpx, Uvicorn  
**Storage**: PostgreSQL 16 with immutable Alembic migrations; NUMERIC market values; indexed Candle identity/time range; dataset membership table  
**Testing**: pytest, pytest-asyncio, HTTPX ASGI/MockTransport, Testcontainers PostgreSQL when Docker is available, Ruff, mypy  
**Target Platform**: Linux container and local Windows/macOS development using Docker Compose for PostgreSQL  
**Project Type**: Modular-monolith backend web service with reusable domain/application package  
**Performance Goals**: p95 under 300 ms for a locally complete 500-Candle read; deterministic-fixture ingestion of 10,000 Candles within 60 seconds; upstream pages no larger than 1,000  
**Constraints**: UTC only, exact decimals, no open/future Candle in a complete dataset, no provider DTO leakage, maximum 1,000 Candles per public range response, bounded retry, no silent closed-Candle correction  
**Scale/Scope**: MVP `BINANCE`/`BTCUSDT`, eight canonical timeframes, one API instance initially, PostgreSQL durable sharing, dataset builds limited by configured expected-Candle count and consumed through paginated reads

## Constitution Check

*GATE: Evaluated before research and re-checked after design.*

| Gate | Result | Evidence |
|---|---|---|
| Spec-driven traceability | PASS | Spec maps local US1–US4 to `MD-US-01`, the TV2 recovery boundary, `MD-FR-01/03/04/05/06`, and `BR-01/02/03/05`. |
| Independent vertical slice | PASS WITH OWNERSHIP NOTE | Historical acquisition/storage/API is independently testable. Rendering remains TV2-owned per the current team plan, superseding the older packaging label “+ single chart.” |
| Simplicity over premature scale | PASS | One modular-monolith backend and PostgreSQL; no Kafka, Kubernetes, TimescaleDB, Redis, Celery, CQRS, or microservice is added. Dataset materialization is synchronous and bounded until measured evidence requires a job path. |
| Cross-document consistency | PASS | Canonical Candle/timeframe/range/completeness values match Feature 002. Immutable complete datasets satisfy Feature 003/004 provenance needs. |
| Architecture/ADR governance | PASS | Architecture and ADR-001/002/003/005 are Accepted. Feature-local details remain recorded in research and the accepted contracts. |
| Layered architecture | PASS | Domain owns Candle/range/dataset rules; application uses provider/repository/clock ports; infrastructure maps PostgreSQL/Binance; API only binds and maps. |
| Integration over mocking | PASS | Domain and application tests use fakes; SQL repository/migration tests target real PostgreSQL; Binance adapter uses raw HTTP fixture contract tests. |
| Migration-first storage | PASS | Alembic revision creates all tables/indexes; application startup never calls `create_all`. |
| API standards | PASS | `/api/v1/**`, standardized envelopes, stable uppercase error codes, bounded cursor pagination, request ID propagation. |
| Validation/security | PASS | Provider/pair/timeframe allowlists, server-controlled upstream URL, exact decimal validation, bounded ranges/retries, sanitized logs/errors, no secrets. |
| Performance/observability | PASS | Indexed range access, bounded collections, structured request/provider/dataset records, health endpoints, explicit benchmarks. |
| Definition of Done | PASS BY PLAN | Tasks include unit, contract, PostgreSQL integration, migration, API, performance, quickstart, lint/type/test, risk review, and convergence gates. |

### Architecture Decision References

- **Architecture baseline**: `docs/ARCHITECTURE.md` — Status: **Accepted**; component boundaries and historical flow are binding and consistent with the Constitution and feature requirements.
- **ADR-001**: Modular Monolith with Separate Worker Processes — **Accepted**; Feature 001 remains inside the monolith and introduces no worker.
- **ADR-002**: Layered Boundaries — **Accepted**; implemented through domain/application/infrastructure/api dependency direction.
- **ADR-003**: Provider-Neutral Market Data Contract — **Accepted**; its identity and isolation rules bind the shared market-data boundary.
- **ADR-005**: Reproducible Backtesting — **Accepted**; informs immutable dataset/checksum behavior without implementing backtesting.
- **Deviations**: None from an Accepted ADR. The team confirmed these authorities and the cross-feature contract review on 2026-08-19.

## Design Overview

### Historical range flow

1. API validates the version, supported selection, UTC/aligned `[startTime, endTime)`, and expected count before external access.
2. Application reads immutable closed Candles from the repository and computes missing interval ranges.
3. Each missing range is requested from the provider port. The Binance adapter paginates Klines, maps exact decimals and UTC instants, and rejects malformed/out-of-range rows.
4. Repository inserts new immutable closed Candles, ignores content-identical duplicates, and rejects a conflicting identity/content pair.
5. Application rereads canonical storage, computes `COMPLETE`, `PARTIAL`, or `EMPTY`, and returns sorted Candles plus bounded missing ranges.

### Dataset materialization flow

1. A deterministic request key identifies provider/pair/timeframe/range/contract version.
2. Repository atomically claims a build lease or returns the existing logical dataset. A concurrent non-owner receives the same dataset identity/state rather than starting another fetch.
3. The owner executes the historical range flow in bounded provider pages.
4. Only complete closed coverage can finalize. Finalization transaction locks the dataset, validates the build token, inserts ordered membership, computes/validates SHA-256 canonical content checksum, and transitions to `COMPLETE`.
5. Metadata and membership cannot be modified after completion. Reads by dataset ID never contact the provider.

### Dependency direction

```text
api ────────────────┐
                    v
application ─────> domain
    ^               ^
    |               |
infrastructure -----┘
```

- `domain`: pure value objects, invariants, expected-range/gap/checksum rules.
- `application`: use cases and `Protocol` ports for provider, repository, clock, and transaction-safe dataset claim/finalization.
- `infrastructure`: Binance/httpx adapter, SQLAlchemy mappings/repository, settings/logging.
- `api`: Pydantic DTOs, response envelopes, error/status mapping, request-ID middleware, composition root.

## Contract Decisions

- Public Candle/history version `1` is aligned with Feature 002.
- REST uses camelCase; Python/domain/database use snake_case with explicit mappers.
- Decimal public values are strings; domain uses `Decimal`; PostgreSQL uses `NUMERIC(38,18)`.
- Timestamps serialize as UTC ISO-8601 with millisecond precision. Range boundaries align to timeframe opens.
- Historical ranges include closed Candles only and use `[startTime, endTime)`.
- `closeTime = next openTime - 1 millisecond`, matching Binance Kline semantics and the Feature 002 event example.
- Public range results contain at most 1,000 Candles; default is 500. Dataset membership uses cursor pagination with the same maximum.
- Closed Candle identity/content is immutable in v1. Exact duplicate is idempotent; conflicting duplicate is `MARKET_CANDLE_CONFLICT` and requires explicit future repair/versioning.
- Complete dataset checksum is SHA-256 over deterministic UTF-8 canonical Candle lines in chronological order.

## Error and Failure Policy

| Category | Public code | HTTP | Retry behavior |
|---|---|---:|---|
| Malformed request/version | `MARKET_REQUEST_MALFORMED`, `MARKET_VERSION_UNSUPPORTED` | 400 | No |
| Unsupported selection | `MARKET_PROVIDER_UNSUPPORTED`, `MARKET_PAIR_UNSUPPORTED`, `MARKET_TIMEFRAME_UNSUPPORTED` | 422 | After configuration change |
| Invalid/unaligned/future/large range | `MARKET_RANGE_INVALID`, `MARKET_RANGE_UNALIGNED`, `MARKET_RANGE_NOT_CLOSED`, `MARKET_RANGE_TOO_LARGE` | 422 | After request change |
| Provider throttle | `PROVIDER_RATE_LIMITED` | 429 | Bounded; expose sanitized retry delay |
| Provider/transient/schema failure | `MARKET_PROVIDER_UNAVAILABLE`, `MARKET_PROVIDER_PAYLOAD_INVALID` | 503 / 502 | Bounded only for transient failures |
| Immutable Candle conflict | `MARKET_CANDLE_CONFLICT` | 409 | No automatic overwrite |
| Dataset building/incomplete/integrity | `MARKET_DATASET_BUILDING`, `MARKET_DATASET_INCOMPLETE`, `MARKET_DATASET_INTEGRITY_FAILED` | 202 / 409 / 500 | Poll building; explicit remediation otherwise |
| Dataset not found | `MARKET_DATASET_NOT_FOUND` | 404 | No |

## Project Structure

### Documentation (this feature)

```text
specs/001-historical-market-data/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   └── market-data-provider.md
├── checklists/
│   ├── requirements.md
│   └── market-data.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/0001_historical_market_data.py
├── src/crypto_lab/
│   ├── domain/market_data/
│   │   ├── candle.py
│   │   ├── dataset.py
│   │   ├── timeframe.py
│   │   └── ranges.py
│   ├── application/market_data/
│   │   ├── errors.py
│   │   ├── ports.py
│   │   ├── historical_service.py
│   │   └── dataset_service.py
│   ├── infrastructure/
│   │   ├── binance/market_data_provider.py
│   │   ├── persistence/models.py
│   │   ├── persistence/market_data_repository.py
│   │   ├── database.py
│   │   └── settings.py
│   ├── api/
│   │   ├── routes/market_data.py
│   │   ├── schemas/market_data.py
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   └── middleware.py
│   └── main.py
└── tests/
    ├── unit/market_data/
    ├── contract/
    ├── integration/
    ├── performance/
    └── fixtures/

docker-compose.yml
Dockerfile
.env.example
```

**Structure Decision**: Use the Constitution's modular-monolith backend package and shared `crypto_lab` namespace. No frontend files are created because current team ownership assigns charts to Feature 002. Paths intentionally match Feature 002/003 plans so later branches can merge one shared backend rather than create parallel applications.

## Test Strategy

1. **Domain unit tests first**: timeframe alignment, Candle invariants, exact Decimal handling, expected opens/gaps, canonical checksum, dataset transitions.
2. **Provider contract tests before adapter**: valid/invalid Binance rows, pagination overlap/order, range filtering, throttling/retry hints, transport/schema failure, no float conversion.
3. **Application tests before use cases**: cache hit, partial coverage fetch-only-gap, empty/partial results, conflicting duplicate, dataset claim/reuse/building/lease/finalize failure.
4. **Repository integration tests**: real PostgreSQL unique/index/NUMERIC/timestamptz behavior, exact duplicate vs conflict, concurrent claim, immutable finalization, paginated membership, migration upgrade/downgrade/upgrade.
5. **API contract tests**: OpenAPI examples, envelope/error/status, camelCase, version/dimension/range validation before provider, dataset resolution.
6. **Performance tests**: local 500-Candle read p95 and deterministic 10,000-Candle acquisition; opt-in marker with environment fields.
7. **Quickstart smoke**: clean Docker PostgreSQL, migrate, run API, import fixture or Binance range, prove cache reuse and dataset read.

## Operational Plan

- `DATABASE_URL`, `BINANCE_BASE_URL`, HTTP timeouts, retry attempts, dataset expected-Candle limit, dataset build lease, and log level are environment settings with safe defaults.
- Production-like startup runs Alembic explicitly, then launches a non-root API container; it never auto-creates schema.
- Health liveness checks process availability. Readiness verifies PostgreSQL and validates configured provider registry without making an upstream call.
- Structured JSON records include request ID, provider/pair/timeframe, range, local hit count, fetched count, retry outcome, completeness, dataset ID/state, and duration. Raw rows and URLs are excluded.

## Risk Review and Mitigations Built into the Plan

| Risk | Impact | Planned mitigation |
|---|---|---|
| Off-by-one timestamp/range mismatch with TV2 | Duplicate/missing bars | One timeframe utility, UTC millisecond fixtures, `[start,end)` contract tests shared with Feature 002. |
| Binary float corruption | Nondeterministic strategy/backtest values | Provider strings → `Decimal` → `NUMERIC` → decimal strings; float input rejected. |
| Partial data presented as complete | Invalid backtests/live state | Expected-open computation, explicit missing ranges, completion transaction requires exact membership. |
| Provider correction overwrites old experiment | Lost reproducibility | Immutable closed content; conflict quarantine/error; future explicit dataset revision rather than silent update. |
| Duplicate/concurrent imports | Extra upstream load or duplicate rows | Database unique identity, exact duplicate ignore, deterministic dataset request key, atomic build claim/lease. |
| Provider throttling/outage | Cascading latency/failure | Read local first, bounded exponential retry, honor retry hint, finite timeouts, categorized failure. |
| Large synchronous build exhausts request resources | Availability degradation | Configured expected-Candle cap, 1,000-row provider pages, no unbounded response, paginated reads; move orchestration to worker only after measurement. |
| SSRF/secret/log leakage | Security incident | Server-controlled provider registry and URL, allowlisted dimensions, sanitized structured records. |
| ORM/provider leakage into domain | High change amplification | Static import tests/mypy plus adapter/repository protocols and explicit mappers. |
| Migration/index defects | Startup/query failure | Alembic-only schema, empty/upgrade/downgrade integration test, range index and query-plan inspection. |

## Post-Design Constitution Re-check

PASS. Phase 1 design introduces no Constitution violation or unapproved infrastructure. All schema/API/provider details are confined to plan/data-model/contracts, domain remains framework-independent, storage changes are migration-first, public collections are bounded, and all cross-feature meanings match the current Feature 002/003 artifacts.

## Complexity Tracking

No Constitution violation requires justification. The repository/provider protocols and dataset membership table are required by explicit provider-replaceability and immutable-provenance requirements; they are not speculative layers.
