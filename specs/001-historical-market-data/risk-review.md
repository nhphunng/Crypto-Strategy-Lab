# Risk Review: Historical Market Data

**Feature**: `001-historical-market-data`  
**Branch**: `feat/001-market-data-spec-plan`  
**Reviewed**: 2026-08-13  
**Scope**: TV1 historical acquisition, canonical contracts, PostgreSQL persistence, immutable datasets, public REST API, packaging, and TV2/TV3/TV4 consumer boundaries.

## Result

No unresolved **CRITICAL** or **HIGH** implementation risk remains. Every high-impact finding below was reproduced or converted into a deterministic test before being closed. Two deliberate product trade-offs remain accepted at **MEDIUM**: synchronous dataset materialization is capped at 10,000 expected Candles, and provider corrections require an explicit future revision workflow rather than silent overwrite. Proposed ADRs still require the team's governance approval; this implementation does not change their status.

## Review Matrix

| ID | Area | Initial severity | Finding | Remediation and evidence | Residual |
|---|---|---:|---|---|---:|
| R01 | Timestamp contract | HIGH | TV3 drafts used an ambiguous Signal/Candle timestamp while TV1/TV2 identity is `openTime`; this could shift a signal to arrival or close time. | Updated Feature 003 data model/domain contract to require `Signal.timestamp == Candle.openTime`; compatibility tests lock UTC millisecond precision, timeframe values, and `[start,end)` semantics. | LOW |
| R02 | Numeric precision | HIGH | Binary float would make duplicate equality, checksums, indicators, and later accounting non-reproducible. | Domain rejects floats/non-finite values, parses provider strings directly to `Decimal`, persists `NUMERIC(38,18)`, and emits canonical fixed decimal strings. Domain/provider/repository tests cover it. | LOW |
| R03 | Completeness | CRITICAL | Partial or open/future coverage could be mislabeled reusable and poison strategy/backtest results. | Historical results derive `COMPLETE/PARTIAL/EMPTY` from every expected open; missing ranges are exact. Dataset finalization accepts only closed complete coverage. Negative contract tests prove partial/empty/future inputs cannot become `COMPLETE`. | LOW |
| R04 | Closed-Candle correction | HIGH | Last-write-wins could silently rewrite historical inputs behind an old result. | Exact duplicates are idempotent; conflicting canonical hashes raise `MARKET_CANDLE_CONFLICT` and roll back. Complete dataset membership/checksum is immutable and verified fail-closed. | LOW |
| R05 | Concurrent materialization | HIGH | Multiple API processes could duplicate provider work or publish two logical datasets for one range. | Deterministic request key plus PostgreSQL atomic claim, build token, and expiring lease. Only the token owner may finalize/fail; repeated/concurrent requests resolve the same dataset. Real-PostgreSQL tests cover claim/reclaim/token behavior. | LOW |
| R06 | Provider pagination/retry | HIGH | Overlap, repeated pages, invalid rows, throttling, or infinite retry could loop or exhaust resources. | Provider pages are limited to 1–1,000 rows; cursor progress is monotonic; overlap/repeat terminates; retries are finite (maximum three), time-bounded, and honor capped `Retry-After`. Adapter/application contract violations map to stable safe provider errors. | LOW |
| R07 | PostgreSQL parameter ceiling | HIGH | A single 10,000-row multi-value insert exceeded asyncpg/PostgreSQL's 32,767 bind-parameter ceiling. | Candle writes are chunked at 1,000 rows; dataset membership writes at 5,000 rows. The deterministic 10,000-Candle real-PostgreSQL performance scenario now passes under 60 seconds. | LOW |
| R08 | SSRF and log leakage | HIGH | A user-selectable upstream or dependency access logs could expose internal hosts, query credentials, or raw provider details. | Provider base URL is server-controlled, HTTPS-only, and rejects userinfo; public request values cannot choose a host. Structured fields redact sensitive keys. `httpx/httpcore` INFO URL logs and Uvicorn access logs are disabled; application records log only controlled market/outcome fields. Tests cover URL validation, redaction, and logger levels. | LOW |
| R09 | Migration/startup ordering | HIGH | API readiness before schema migration would produce runtime failures or tempt `create_all` mutation. | Alembic owns schema. Compose runs a one-shot non-root `migrate` job after PostgreSQL health and starts API only after exit code 0. Readiness verifies PostgreSQL plus required tables. Empty-upgrade/downgrade/upgrade integration test passes. | LOW |
| R10 | Cross-feature contract drift | HIGH | Feature 002 allowed only 100 `missingRanges`, which contradicted an exact 1,000-interval alternating-gap worst case (500 ranges). | Feature 001/002 contracts now use a maximum of 500 exact coalesced ranges; Feature 002 names Feature 001 as historical owner. Consumer compatibility/OpenAPI tests lock the shared values. | LOW |
| R11 | Dependency direction | MEDIUM | Framework/provider imports in domain/application would defeat provider replacement and modular-monolith boundaries. | Static AST architecture tests forbid FastAPI, SQLAlchemy, asyncpg, Alembic, and httpx in domain/application and forbid Binance Kline terms outside infrastructure. Provider fitness proves fake and Binance adapters emit equal canonical lines. | LOW |
| R12 | Dependency reproducibility | MEDIUM | Exact direct versions still allowed transitive packages to change between image builds. | Added a reviewed runtime dependency-closure lock. Docker installs the lock in a cacheable layer and installs the application with `--no-deps`; removed unnecessary Uvicorn extras. Final image build succeeds. | LOW |
| R13 | Local port collision | MEDIUM | Host PostgreSQL port 5432 was already occupied, making the documented environment non-deterministic. | Compose and `.env.example` use configurable host port `55432` while containers retain standard 5432. Quickstart documents the override. | LOW |
| R14 | Provider-port fault mapping | MEDIUM | A faulty conforming adapter could return an empty/oversized/out-of-range page and trigger a generic 500. | Application validates every page independently and maps a port-contract breach to `MARKET_PROVIDER_PAYLOAD_INVALID`; regression test added. | LOW |
| R15 | Dataset read size | MEDIUM | Returning full immutable datasets could produce unbounded memory/API responses. | Public range reads are capped at 1,000; dataset builds at 10,000; membership uses validated opaque cursor pages of 1–1,000. Invalid cursors fail safely. | LOW |
| R16 | Synchronous materialization | MEDIUM | A dataset near the cap occupies one request while fetching multiple provider pages. | Deliberately accepted for MVP with bounded size, timeout/retry, durable claim/lease, and observed 10,000-row target. Revisit when measured builds routinely exceed the API timeout/cap; move orchestration to a job without changing Candle/provider/repository contracts. | MEDIUM (accepted) |
| R17 | Official historical corrections | MEDIUM | Rejecting changed closed content means an official provider correction cannot be ingested automatically. | Deliberately fail closed to preserve old checksums/results. Revisit only with a real correction case by adding explicit Candle/dataset revisioning; never mutate old complete datasets. | MEDIUM (accepted) |
| R18 | Governance | MEDIUM | Architecture and ADR-001/002/003/005 remain `Proposed`; code cannot confer team approval. | Implementation follows the SRS/Constitution-compatible direction and records evidence, but leaves status unchanged. TV2/TV4 cross-review and team acceptance remain human merge gates. | MEDIUM (governance) |

## Verification Evidence

Reference environment: Python 3.12.4; PostgreSQL 16.14; Docker 29.4.2; Docker Compose 5.1.3; AMD64 Windows host.

| Gate | Result |
|---|---|
| Ruff format/lint | PASS — 53 Python files unchanged; no lint findings |
| mypy strict | PASS — no issues in 32 source files |
| pytest | PASS — 54 tests in 9.57 seconds, including real PostgreSQL integration, migrations, contracts, architecture, operations, and performance |
| Performance | PASS — 500-Candle local p95 below 300 ms; deterministic 10,000-Candle acquisition below 60 seconds |
| Docker build | PASS — locked multi-stage Python 3.12 image, non-root runtime, read-only Compose service |
| Migration job | PASS — one-shot Alembic job exited 0 before API startup |
| Live smoke | PASS — liveness/readiness, dimensions, three real Binance 5m Candles, provider-free cache repeat, immutable dataset build/read, and `pageSize=2` cursor page |
| Cache evidence | PASS — first live range recorded `local_count=0, fetched_count=3`; repeat recorded `local_count=3, fetched_count=0` |

## False-Positive Audit

One smoke request used `limit=2` on the dataset-membership endpoint and returned the default page. OpenAPI specifies `pageSize` for that endpoint; `limit` belongs to the historical-range endpoint. Repeating with `pageSize=2` returned two Candles, `hasMore=true`, and cursor `MQ`. No implementation defect existed, and the existing API contract test already covered the correct parameter. This audit is retained so the review record distinguishes a client-contract mistake from a code issue.

## Final Risk Position

- No hidden retry, unbounded public collection, provider DTO leak, floating-point market value, silent historical overwrite, or schema-on-startup path remains.
- The remaining accepted risks have explicit caps and revisit triggers rather than speculative infrastructure.
- Merge approval should require TV2 confirmation of the shared Candle/history contract and TV4 confirmation of immutable dataset consumption; these are organizational gates, not missing TV1 implementation.
