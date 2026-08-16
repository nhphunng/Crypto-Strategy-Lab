# Implementation Plan: Strategy Foundation

**Branch**: `feat/003-strategy-foundation-spec-plan` | **Date**: 2026-08-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-strategy-foundation/spec.md`

## Summary

Build a framework-independent strategy domain for immutable definitions, validated parameters, normalized contexts, deterministic signals, MA and RSI calculations, and a compatibility-aware registry. A thin application layer resolves normalized datasets and exact strategy versions, while a FastAPI boundary exposes discovery and bounded analysis. PostgreSQL stores immutable Strategy Definitions for historical resolution; registry calculation logic remains in trusted application code. TV4 consumes the same domain contract and never branches on MA or RSI.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library (`dataclasses`, `decimal`, `enum`, `hashlib`, `typing`), Pydantic 2 for boundary validation, FastAPI for the public HTTP boundary, SQLAlchemy 2 and Alembic for immutable Strategy Definition persistence

**Storage**: PostgreSQL 16 for immutable Strategy Definitions and parameter snapshots; Strategy Context and Signal sequences are transient in this feature

**Testing**: pytest, pytest-asyncio, real PostgreSQL through Testcontainers for repository/integration tests, Ruff, and mypy

**Target Platform**: Linux containers and local development through Docker Compose

**Project Type**: Backend module within the modular-monolith web application; no frontend implementation is owned by this feature

**Performance Goals**: Linear-time MA/RSI execution; a documented 10,000-candle deterministic fixture completes within 1 second on the reference development environment, while strategy discovery remains within the constitution's 300 ms p95 read target under demo load

**Constraints**: No look-ahead; no database, HTTP, queue, provider, clock, or random access from domain strategy calculation; immutable inputs and definitions; one output Signal per valid input Candle; exact UTC alignment; no dynamic third-party code upload

**Scale/Scope**: Two built-in strategies (MA and RSI), one strategy contract version, bounded normalized datasets up to 10,000 candles for the acceptance benchmark, versioned definitions, and a registry designed to admit additional trusted strategies without downstream changes

## Constitution Check

*GATE: Passed for design generation; architecture approval remains a pre-implementation review gate because all referenced architecture documents and ADRs are Proposed.*

### Pre-Research Gate

| Principle | Result | Evidence |
|-----------|--------|----------|
| Spec-Driven Development | PASS | `spec.md` exists and traces `SE-US-01`, `SE-US-02`, `SP-US-01`, `SP-US-02`, `SP-US-03`, and the relevant SRS FRs. |
| Simplicity Over Premature Scale | PASS | One modular-monolith domain module, one application boundary, no service split, broker, cache, or dynamic plugin runtime. |
| Cross-Document Consistency | PASS | Uses canonical `Strategy`, `StrategyDefinition`, `Signal`, Candle, Strategy Version, pair, timeframe, and UTC semantics. |
| Architecture and ADR Governance | PASS WITH REVIEW GATE | Architecture and ADRs 001–005 were read; all remain Proposed and are treated as review inputs, not binding approval. |
| Domain Owns Business Rules | PASS | MA, RSI, validation, signal semantics, compatibility, and registry rules live in the domain. |
| Thin API and Worker Entrypoints | PASS | HTTP routes bind/validate and delegate; no indicator logic enters delivery code. |
| Repository and Provider Isolation | PASS | Repository persists immutable definitions only; normalized data comes through an application port. |
| Integration Testing Over Mocking | PASS | Pure domain tests use deterministic fixtures; persistence/API integration uses real PostgreSQL. |
| Immutable Strategy Version | PASS | Definition rows and referenced parameter sets are append-only and content-addressed. |
| Deterministic, Look-Ahead-Safe Behavior | PASS | Context validation, UTC ordering, deterministic IDs, Decimal calculation, and no external state are explicit. |
| Replaceable Strategies | PASS | Registry and TV4 fitness test use a generic compliant test strategy with no downstream strategy-name branch. |
| Security and Analysis-Only Boundary | PASS | No code upload, exchange access, secrets, or order placement; public output remains analytical signals only. |

### Post-Design Gate

PASS with the same pre-implementation review gate. The data model keeps calculation objects immutable, the contracts separate domain/application/API concerns, the quickstart proves replaceability and look-ahead safety, and tasks require test-first contract coverage. No constitution violation requires Complexity Tracking.

### Architecture Decision References

- **Architecture baseline**: `docs/ARCHITECTURE.md` — Status: Proposed; used for module boundaries and reviewed before implementation approval.
- **Relevant ADRs**:
  - `ADR-001` Modular Monolith with Separate Worker Processes — Proposed; this feature stays inside the monolith and introduces no worker.
  - `ADR-002` Layered Boundaries and Ports/Adapters — Proposed; domain/application/delivery separation is adopted for this plan.
  - `ADR-003` Provider-Neutral Market Data Contract — Proposed; Strategy Context consumes normalized Candle identity and dataset provenance.
  - `ADR-004` Strategy Contract, Registry, and Immutable Versions — Proposed; primary design input for protocol, registry, and version rules.
  - `ADR-005` Deterministic and Reproducible Backtesting — Proposed; TV4 provenance and no-look-ahead input requirements are preserved.
- **Deviations**: None. Implementation MUST wait for team review of these Proposed inputs or an approved change to the plan.

## Design Overview

### Runtime Flow

1. The API receives a strategy ID/version, parameters, immutable dataset reference, and decision timestamp.
2. The application resolves the exact available registry entry and validates compatibility and lifecycle status.
3. Parameter metadata applies declared defaults and produces an immutable Validated Parameter Set or a categorized validation failure.
4. A market-data port resolves normalized Candles for the immutable dataset reference; the application builds and validates Strategy Context.
5. The selected pure Strategy analyzes the context and returns one deterministic Signal per Candle.
6. The application returns provenance and ordered Signals. TV4 may call the same application/domain contract directly with an already-built Strategy Context.

### Persistence Boundary

- Trusted strategy implementations and registry metadata are registered during application composition.
- A Strategy Definition is persisted before a downstream experiment references it.
- Definitions are insert-only. A matching content fingerprint resolves idempotently to the same definition; conflicting reuse of an identity fails.
- Signal sequences are not persisted by TV3. TV4 owns retention of the exact definition/context/output provenance it consumes.

### Compatibility Rule

- Contract and strategy versions use semantic `MAJOR.MINOR.PATCH` identifiers.
- A consumer supports one contract major and an explicit inclusive minor range. Different majors or an unsupported minor are incompatible; patch differences do not alter contract meaning.
- Strategy behavior changes require a new strategy version. Parameter value changes create a new Strategy Definition identity; parameter-schema semantic changes require a new strategy version.
- Deprecated versions remain resolvable for historical metadata but cannot start new analysis. Unavailable versions cannot be resolved or executed.

## Project Structure

### Documentation (this feature)

```text
specs/003-strategy-foundation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   └── strategy-domain-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── src/crypto_lab/
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── routes/strategies.py
│   │   └── schemas/strategy.py
│   ├── application/strategies/
│   │   ├── analyze_strategy.py
│   │   ├── discover_strategies.py
│   │   └── ports.py
│   ├── bootstrap/strategies.py
│   ├── domain/
│   │   ├── market/candle.py                 # Owned by normalized-market-data feature
│   │   └── strategy/
│   │       ├── context.py
│   │       ├── definition.py
│   │       ├── errors.py
│   │       ├── parameters.py
│   │       ├── protocol.py
│   │       ├── registry.py
│   │       ├── signal.py
│   │       └── implementations/
│   │           ├── moving_average.py
│   │           └── rsi.py
│   └── infrastructure/persistence/
│       ├── strategy_models.py
│       └── repositories/strategy_definition_repository.py
├── migrations/versions/20260813_003_create_strategy_definitions.py
└── tests/
    ├── fixtures/strategy/
    ├── unit/strategy/
    ├── contract/
    │   ├── test_strategy_api.py
    │   ├── test_strategy_contract.py
    │   └── test_strategy_extensibility.py
    └── integration/
        ├── test_strategy_definition_repository.py
        └── test_strategy_analysis_api.py
```

**Structure Decision**: Use the constitution's backend modular-monolith layout. Domain strategy files contain pure rules, application services coordinate dataset/definition ports, infrastructure persists immutable definitions, bootstrap performs trusted registration, and API files expose discovery and analysis. No frontend, worker, queue, or leaderboard file belongs to this feature.

## Test Strategy

- Write contract and domain fixture tests before implementation.
- Use table-driven fixtures for MA/RSI normal, crossing, equality, warm-up, empty, invalid parameter, constant-price, one-directional, insufficient-history, future, duplicate, unsorted, and incomplete contexts.
- Run each deterministic fixture repeatedly and compare the entire ordered output including signal identity and reason.
- Use a generic test strategy to prove registration, discovery, execution, and TV4 consumption without downstream changes.
- Use real PostgreSQL for append-only definition identity, concurrent duplicate insertion, historical resolution, and migration tests.
- Validate OpenAPI examples and Pydantic schemas against the same contract fixtures.
- Benchmark the documented 10,000-candle fixture and record environment and p95 results.

## Complexity Tracking

No constitution violations or exceptional complexity are introduced.
