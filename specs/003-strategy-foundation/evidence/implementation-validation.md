# Implementation Validation Evidence

Date: 2026-08-23  
Branch: `feat/implement-003-strategy-foundation`  
Validated revision baseline: `7d7e177` plus the benchmark/evidence changes recorded by this file.

## Reference environment

- macOS arm64; Docker Desktop Linux VM: 10 CPUs, 7.653 GiB memory.
- Python 3.12.4; Node 25.2.1.
- PostgreSQL 16 Compose service: `healthy` on `localhost:55432`.
- Sandbox image: `crypto-lab-strategy-sandbox:1`, arm64, user `65532:65532`, image ID
  `sha256:b48748692826a83a296b39aaa184931ed6e7a4511b7e22bf4f286c223d3d86c5`.
- AppArmor is unavailable on Docker Desktop and the optional profile setting remained unset. The
  mandatory seccomp, network, filesystem, user, capability, process, CPU, memory, output, and timeout
  controls were exercised against the actual image.

## Commands and results

| Command | Result |
|---|---|
| `docker compose -f docker-compose.yml up -d postgres` | PASS; PostgreSQL became healthy |
| `docker compose -f infra/compose.yaml --profile strategy-sandbox-build-only build strategy-sandbox` | PASS; multi-architecture digest selected native arm64 image |
| `cd backend && .venv/bin/ruff check src tests` | PASS |
| `cd backend && .venv/bin/mypy src` | PASS; 118 source files |
| `cd backend && .venv/bin/pytest -q` | PASS; 226 tests, zero skip/failure |
| `cd backend && .venv/bin/pytest -q tests/contract/test_generated_strategy_sandbox.py` | PASS; 5 tests against built image |
| `cd backend && .venv/bin/pytest -q tests/performance/test_strategy_benchmark.py` | PASS; 3 tests |
| 20 repetitions of the 10,000-candle MA fixture | PASS; p95 0.759004 s, min 0.654890 s, max 0.760975 s |
| `cd frontend && npm run typecheck` | PASS |
| `cd frontend && npm test` | PASS; 87 tests |
| `cd frontend && npm run build` | PASS |

No acceptance assertion used a live market provider or live LLM response.

## Quickstart scenario coverage

| Quickstart section | Executed evidence | Result |
|---|---|---|
| 3. MA and RSI | `tests/unit/strategy/test_moving_average.py`, `test_rsi.py`, parameter/context fixtures | PASS: normal, boundaries, crossing/equality, warm-up, invalid, empty, repeated determinism |
| 4. Signal inspection | `test_signal.py`, `test_context.py`, `test_tv4_strategy_contract.py`, `test_strategy_analysis_api.py` | PASS: provenance/order/action/phase and zero-partial invalid contexts |
| 5. Register/discover | `test_registry.py`, `test_strategy_discovery_api.py`, `test_strategy_extensibility.py` | PASS: MA/RSI/generic discovery and atomic failure |
| 6. Immutable versions | `test_strategy_definition_migration.py`, `test_strategy_definition_repository.py`, `test_strategy_version_resolution.py`, full migration round trip | PASS: exact historical resolution and categorized no-fallback errors |
| 7. TV4 contract | `test_tv4_strategy_contract.py`, `test_generated_strategy_downstream.py`, architecture fitness tests | PASS: no concrete built-in/generated branch |
| 8. Benchmark/fitness | `test_strategy_benchmark.py`, `test_strategy_architecture.py` | PASS: deterministic 10,000-candle p95 below 1 s; discovery below 300 ms; forbidden dependencies absent |
| 9. Generate by name | name fixtures, `test_generation_draft.py`, `test_strategy_generation_failures.py`, `test_generated_strategy_activation.py`, generated-review frontend tests | PASS: ambiguity/failure isolation, exact confirmation, atomic activation, duplicate reuse |
| 10. Text/URL extraction | `test_strategy_source_extraction.py`, `test_strategy_source_access.py`, `test_strategy_source_retention.py` | PASS: zero-to-many evidence, hostile source policy, encryption and retention |
| 11. Restart/reuse | `test_generated_strategy_reuse.py`, `test_generated_strategy_versioning.py`, `test_generated_strategy_downstream.py`, frontend catalog-remount test | PASS: exact durable reuse without model/source regeneration |
| 12. Isolation | built-image sandbox, validation, and security boundary suites | PASS: non-root UID; zero effective capabilities; no-new-privileges; no `CSL_` environment; network/rootfs/process denial; 256 MiB and 32 PID cgroups; 5-second timeout cleanup with no leaked container |

## Remaining non-technical gate

SC-011, SC-012, and SC-020 require representative human participants. Their approved protocol and
pending status remain in `usability-validation.md`; this does not invalidate the completed technical
Quickstart scenarios but prevents closing T085 and the final aggregate T086 gate.
