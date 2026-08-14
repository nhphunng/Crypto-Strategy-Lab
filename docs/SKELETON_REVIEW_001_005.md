# Skeleton Review: Features 001–005

**Source reviewed**: `TECH_STACK_SKELETON_SPECKIT_FLOW.md`, Constitution,
Feature 001 artifacts and implementation merged into `main` at `4f89e0f`, and Feature 002–005
`spec.md`/`plan.md`/`tasks.md`.
**Date**: 2026-08-14
**Result**: Approved after the corrections below.

## Corrections applied

| Finding | Resolution |
|---|---|
| Feature 001 was shown as owning a chart | Feature 001 now owns historical Market Data only; Feature 002 owns Market Chart UI |
| `domain/market` differed from the implemented/spec name | Standardized on `domain/market_data` |
| Feature 004 was represented as one `backtesting` application package | Standardized on `application/backtests` and `application/evaluations` |
| The common skeleton created Strategy/Backtest frontend modules too early | Current baseline creates frontend only for Feature 002 Market Chart and Feature 005 Leaderboard |
| Queue, Celery worker, Search, News and Sentiment appeared in the immediate skeleton | Classified as future Feature 006–010 ownership; excluded from setup 001–005 |
| `persistence/models.py` would collide semantically with a `persistence/models/` package | Feature-owned mappings use `strategy_models.py`, `backtest_models.py`, `evaluation_models.py`, and `leaderboard_models.py`, all sharing Feature 001's `Base` |
| `api/dependencies.py` would collide with an `api/dependencies/` package | Feature 005 composition moves to `api/leaderboard_dependencies.py` |

## Setup scope

The repository skeleton now contains package/directory boundaries for all five
features without pretending business tasks are implemented:

- 001: shared backend package/config and reserved `market_data` ownership;
- 002: chart delivery, realtime provider/WebSocket, Market Chart frontend;
- 003: Strategy domain/application/bootstrap/persistence boundaries;
- 004: Backtest and Evaluation boundaries;
- 005: Leaderboard domain/application/persistence/API and frontend boundaries.

Feature 001's implementation files, Alembic environment, Docker runtime, and
locks are now the integrated backend baseline on `main`. Frontend dependency
pins and build configuration remain the first
implementation setup task of Feature 002; empty directory scaffolding does not
complete that task.

## Guardrails

- One shared SQLAlchemy metadata registry originates in Feature 001.
- No migration revision is guessed before integrated Alembic heads are known.
- No worker, Redis, Celery, Search, Composite, News, or Sentiment package is
  created during the 001–005 setup.
- Placeholder modules contain no domain behavior and do not satisfy
  implementation tasks by themselves.
