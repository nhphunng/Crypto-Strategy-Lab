<!--
Sync Impact Report
- Version change: 1.1.0 -> 1.2.0
- Modified principles:
  - Spec-Driven Development (SDD): added the project architecture and ADRs as planning inputs.
  - Cross-Document Consistency: added architecture and decision records to the consistency chain.
  - Technology Stack: made the job broker and worker implementation subject to an Accepted ADR.
  - Development Workflow: added the architecture/ADR review gate before speckit-plan.
- Added sections:
  - Architecture and ADR Governance.
- Removed sections: None.
- Dependent templates updated:
  - `.specify/templates/plan-template.md`: added explicit Architecture Decision References.
- Follow-up TODOs:
  - Team must review the Proposed architecture and ADRs before accepting them for implementation.
-->

# Crypto Strategy Lab Constitution

## Table of Contents

- [Crypto Strategy Lab Constitution](#crypto-strategy-lab-constitution)
  - [Table of Contents](#table-of-contents)
  - [Part 1: Common Engineering Principles](#part-1-common-engineering-principles)
    - [Spec-Driven Development (SDD)](#spec-driven-development-sdd)
    - [Simplicity Over Premature Scale](#simplicity-over-premature-scale)
    - [Cross-Document Consistency](#cross-document-consistency)
    - [Architecture and ADR Governance](#architecture-and-adr-governance)
    - [Governance](#governance)
    - [AIF-SDLC Workflow](#aif-sdlc-workflow)
    - [Feature Derivation Method](#feature-derivation-method)
    - [User Story Conventions](#user-story-conventions)
    - [Layered Architecture](#layered-architecture)
    - [Integration Testing Over Mocking](#integration-testing-over-mocking)
  - [Part 2: Project-Specific Rules](#part-2-project-specific-rules)
    - [Business Terminology](#business-terminology)
    - [Business Rules](#business-rules)
    - [Technical Principles](#technical-principles)
    - [Access Control](#access-control)
    - [API Design Standards](#api-design-standards)
    - [Naming Conventions](#naming-conventions)
    - [Frontend Conventions](#frontend-conventions)
    - [Validation Rules](#validation-rules)
    - [Logging \& Audit](#logging--audit)
    - [Performance Standards](#performance-standards)
    - [Definition of Done](#definition-of-done)
    - [Technology Stack](#technology-stack)
    - [Development Workflow](#development-workflow)
    - [Security Requirements](#security-requirements)

---

## Part 1: Common Engineering Principles

<!-- Principles applicable to any spec-driven layered web application; not feature-specific -->

### Spec-Driven Development (SDD)

Every functionality MUST have a corresponding Spec Kit feature specification before application
code is written.

- `docs/REQUIREMENT.md` is the source of the original assignment, project scope and architectural
  drivers.
- `docs/SRS.md` is the approved product-requirement baseline for features, actors, business flows,
  functional requirements, non-functional requirements, User Story IDs and acceptance criteria.
- `docs/ARCHITECTURE.md` is the project-wide architecture baseline for system boundaries, module
  responsibilities, dependency rules, data flows and deployment shape.
- `docs/ADR/README.md` indexes architectural decisions. Only ADRs with `Accepted` status are binding;
  `Proposed` ADRs are review inputs and MUST NOT be treated as approved implementation decisions.
- `specs/{feature-id}-{name}/spec.md` is the source of truth for WHAT one feature does and WHY.
- `plan.md`, `research.md`, `data-model.md` and `contracts/` are the source of truth for HOW that
  feature is designed.
- `tasks.md` is the executable, dependency-ordered implementation scope.
- Implementation that diverges from these artifacts MUST amend the relevant artifact first. Code
  does not silently redefine intent.

Each Spec Kit feature folder maps 1:1 to a reviewable vertical slice.

- Before creating or updating a feature, `$speckit-specify` MUST read `docs/SRS.md`, identify the
  relevant feature, functional-requirement and business-flow sections, and include their IDs in the
  feature spec's traceability references.
- A feature spec MUST preserve the meaning and canonical User Story IDs defined by `docs/SRS.md`.
  Splitting a story into smaller feature-spec stories is permitted only when every derived story maps
  back to the original SRS ID and none of its acceptance criteria is silently dropped.
- A feature MUST remain independently demonstrable and testable.
- `spec.md`, clarification decisions, `plan.md` and `tasks.md` MUST be committed before the related
  implementation is considered complete.
- `.specify/feature.json` identifies the active feature; Git branch names MUST NOT be treated as the
  only source of active-feature state.

### Simplicity Over Premature Scale

Do not add abstractions, patterns, deployable services or dependencies beyond a measured current
need. No speculative generality.

The initial system MUST be a modular monolith plus independently scalable backtest worker processes.
Redis, Celery and process-level workers are permitted because queued backtesting is a stated scale
driver. Kafka, Kubernetes, CQRS, event sourcing and additional microservices require an ADR containing
measured evidence that the simpler architecture cannot satisfy a requirement.

Every new dependency MUST state the problem it solves, why the standard library or current stack is
insufficient, and its operational/test impact.

### Cross-Document Consistency

`docs/REQUIREMENT.md`, `docs/SRS.md`, `docs/ARCHITECTURE.md`, ADRs, feature artifacts and code are
different views of the same system. Any change to one that affects another is incomplete until all
affected views are updated. Inconsistency is a defect, not a backlog item.

**The SRS and active `spec.md` are the source of truth for domain language.** Terms such as `Candle`,
`StrategyDefinition`, `BacktestRun`, `EvaluationResult` and `LeaderboardEntry` MUST be used consistently
in plan, contracts, tests, code and UI. Alternative technical mappings MUST be documented in
`data-model.md`.

**Traceability is end-to-end and bidirectional.** Every feature spec MUST identify its source
`docs/SRS.md` feature section, User Story IDs, applicable business flow and functional/non-functional
requirements. Every plan, task, test and delivered behavior MUST trace forward through the active
feature spec. If `docs/REQUIREMENT.md` and `docs/SRS.md` conflict, work MUST stop until the SRS is
reconciled with the original assignment and the approved decision is recorded.

**Spec amendments require same-change design review.** Adding, renaming or removing an entity,
requirement or state transition in `spec.md` MUST trigger a review of `plan.md`, `data-model.md`,
`contracts/`, `tasks.md` and affected tests in the same change.

**Feature specs MUST NOT contain design decisions.** Languages, frameworks, database engines, provider
class names, endpoint paths, queue mechanisms and schema field names belong in planning artifacts.
The spec describes user-visible behavior, constraints and measurable outcomes.

**Heading and identifier changes cascade to all references.** Renaming a requirement, user story,
section or contract requires updating links and traceability references in all sibling artifacts.

**The complete feature set remains internally consistent.** Market data, strategy, composite,
backtest, evaluation, search, leaderboard, news and sentiment artifacts MUST use compatible contracts.
A change that crosses a boundary is incomplete without contract and integration-test updates.

### Architecture and ADR Governance

Architecture guides how approved requirements are implemented without replacing those requirements.
Before `$speckit-plan`, the feature owner MUST read `docs/ARCHITECTURE.md`, `docs/ADR/README.md` and
every ADR relevant to the feature.

- `plan.md` MUST identify the architecture baseline, the relevant ADR IDs and statuses, and any
  proposed deviation. A link alone is insufficient when the plan changes a documented boundary.
- An `Accepted` ADR is binding. A `Proposed` ADR supports discussion but does not approve an
  implementation choice.
- The Constitution and approved SRS take precedence over architecture documents. If they conflict,
  planning MUST stop until the documents and decision are reconciled.
- A cross-feature, costly-to-reverse or infrastructure-level decision MUST be recorded in an ADR.
  Feature-local and reversible choices belong in that feature's `research.md` or `plan.md`.
- A deviation from an Accepted architecture baseline requires a new or superseding ADR before plan
  approval. Code MUST NOT silently establish a new architecture.
- Moving an ADR from `Proposed` to `Accepted` requires team review. Replacing an Accepted ADR requires
  marking it `Superseded` and linking both the old and replacement records.

### Governance

This constitution supersedes project practices, implementation preferences and ad-hoc decisions. An
amendment requires:

1. A documented reason and affected principles.
2. Team review and explicit approval.
3. A semantic version decision and amendment date update.
4. A migration or compatibility plan when current artifacts or code are affected.

Constitution versions follow semantic versioning:

- **MAJOR** for removed/redefined principles or governance changes that invalidate existing compliant
  designs.
- **MINOR** for new principles, mandatory gates or materially expanded guidance.
- **PATCH** for wording, examples and clarifications that do not change obligations.

All reviews MUST verify constitution compliance. Exceptions and added complexity MUST be justified in
an ADR or review description, not hidden in code comments. A constitution `MUST` violation blocks
planning approval, implementation and merge. `$speckit-plan` MUST record Constitution Check results,
and `$speckit-analyze` MUST treat any conflict with a constitution `MUST` as CRITICAL.

### AIF-SDLC Workflow

1. **Constitution Step** - `$speckit-constitution` establishes project-wide governance.
2. **Specification Step** - `$speckit-specify` MUST read `docs/SRS.md` and create one feature from its
   relevant feature, User Story, flow, FR and NFR sections. The resulting `spec.md` MUST record those
   source IDs and measurable requirements.
3. **Clarification Step** - `$speckit-clarify` resolves high-impact ambiguity before design.
4. **Design Step** - `$speckit-plan` creates research, data model, contracts and quickstart artifacts.
5. **Requirements Quality Step** - `$speckit-checklist` validates the quality of written requirements.
6. **Tasking Step** - `$speckit-tasks` produces dependency-ordered, file-specific work.
7. **Consistency Step** - `$speckit-analyze` MUST report no unresolved CRITICAL/HIGH issue before code.
8. **Implementation Step** - `$speckit-implement` executes tasks phase by phase with required tests.
9. **Convergence Step** - `$speckit-converge` compares current code to intent. Appended convergence
   tasks MUST be implemented, and convergence repeated until it reports `Converged`.
10. **Review/Demo Step** - the feature is demonstrated through `quickstart.md` and acceptance tests.

Constitution compliance is required on every pull request. Spec Kit feature folders live under
`specs/{feature-id}-{name}/` and are committed with implementation. A feature is not done until all
affected documents, contracts, tasks and tests are synchronized with the delivered behavior.

### Feature Derivation Method

When creating or reviewing features, apply this method in order:

1. **Start with the approved SRS.** Derive each vertical slice from one `docs/SRS.md` feature group in
   section 7, together with its related functional requirement in section 3 and business flow in
   section 6. Market Data, Multi-Timeframe Chart, Strategy Plugin, Composite Strategy, Backtest,
   Evaluation, Search, Leaderboard, Visualization, News and Sentiment remain required MVP coverage.
2. **Trace the complete user flow.** Every step from data acquisition through strategy generation,
   backtest, evaluation, ranking and visualization MUST belong to a feature or carry an explicit
   out-of-scope traceability note.
3. **Trace architectural drivers.** Modifiability, scalability, realtime behavior, reliability,
   performance, maintainability and observability MUST have measurable acceptance criteria and tasks.
4. **Prove replaceability with scenarios.** Feature design MUST cover adding MACD, replacing Random
   Search, adding a Market Data Provider, scaling workers, losing News Service, changing the sentiment
   model and reconnecting Binance WebSocket.
5. **One story, one actor, one outcome.** A user story MUST describe a single actor goal with an
   independently testable result. Split a story when it cannot be demonstrated independently.

### User Story Conventions

These rules apply whenever a Feature or User Story is created, renamed, renumbered or removed.
Violations are specification defects.

**1. Prefix derivation.**
Story identifiers use the uppercase initials of the feature's significant words, followed by
`-US-<NN>`. Examples:

| Feature name | Prefix |
|---|---|
| Market Data | `MD` |
| Strategy Plugin | `SP` |
| Backtest Evaluation | `BE` |
| Queued Random Search | `QRS` |

**2. Sequential numbering, no gaps.**
Story numbers within a feature start at `01` and increment without gaps. Renumbering requires updating
all references in the spec, plan, contracts, tasks and tests in the same change.

**3. Feature artifact synchronization is mandatory and immediate.**
Whenever a feature or story changes, its acceptance scenarios, contracts, task labels and quickstart
references MUST be reviewed in the same edit.

**4. User stories and tasks remain traceable.**
Every story is labelled `[US1]`, `[US2]`, etc. in `tasks.md`. Every functional requirement MUST map to
at least one story or explicitly state why it is cross-cutting. The feature spec MUST also retain the
canonical `docs/SRS.md` story ID, such as `MD-US-01`, as a source reference. Local `[US1]` labels do not
replace SRS IDs; they provide ordering inside one feature artifact.

**5. Prioritized stories MUST remain independently testable.**
A feature may contain multiple P1/P2/P3 stories as supported by Spec Kit, but each story MUST have a
goal, acceptance scenarios and an independent test. P1 defines the smallest demonstrable slice;
lower-priority stories MUST NOT be hidden prerequisites for P1.

### Layered Architecture

**AR-01: Domain Owns Business Rules**
Strategy contracts, signal semantics, composite rules, backtest simulation, evaluation formulas and
search abstractions MUST live in the framework-independent domain. Domain code MUST NOT import FastAPI,
Celery, Redis, SQLAlchemy or Binance-specific payloads.

**AR-02: Thin API and Worker Entrypoints**
HTTP/WebSocket handlers and worker tasks may bind input, validate boundary schemas, invoke application
use cases and map responses. They MUST NOT implement indicators, backtest accounting, scoring or direct
database queries.

**AR-03: Repository and Provider Isolation**
Repositories perform persistence only. Market Data Providers and News Providers perform external
integration only. They MUST NOT decide strategy signals, evaluation scores or business state
transitions.

**AR-04: DTO and Event Anti-Corruption Layer**
External payloads, API DTOs, queue jobs and domain objects are separate contracts. Explicit mappers MUST
normalize Binance/other provider payloads into internal `Candle`/`NewsItem` models. Frontend and domain
MUST NOT depend on provider schemas.

**AR-05: Transactional and Idempotent Atomicity**
Multi-record state changes MUST be atomic. Backtest result persistence MUST be idempotent by `job_id`;
a retried job MUST NOT create duplicate results, leaderboard updates or audit events.

### Integration Testing Over Mocking

Do not mock PostgreSQL or Redis behavior in integration tests. Backend integration tests MUST use real
service instances through Testcontainers or Docker Compose. External Binance and news integrations MAY
use deterministic recorded/contract fixtures, but adapter contract tests MUST validate mapping, retry,
rate-limit and reconnect behavior.

Unit tests are permitted for pure strategy, combination, backtest, evaluation and search logic with no
I/O. New API/WebSocket boundaries and job workflows require integration tests covering happy path and
critical failure/retry paths before merge.

---

## Part 2: Project-Specific Rules

<!-- Crypto Strategy Lab domain rules, technical choices, naming, and operational standards -->

### Business Terminology

Use these terms consistently across code, API contracts, database and UI:

| Term | Not |
|---|---|
| Market Pair | Coin pair, ticker pair when referring to a tradable pair |
| Candle | Kline, bar in user-facing text |
| Timeframe | Interval when referring to candle duration |
| Strategy | Indicator when referring to a component that emits signals |
| Strategy Definition | Strategy config, strategy object |
| Strategy Version | Latest strategy, overwritten strategy |
| Signal | Recommendation, order |
| Composite Strategy | Combination strategy, mixed strategy |
| Candidate Strategy | Random result, generated strategy |
| Backtest Run | Simulation job, experiment when referring to execution |
| Evaluation Result | Score record, metric bundle |
| Leaderboard Entry | Ranking row, top strategy record |
| News Item | Article record, crawler result |
| Sentiment Result | ML output, mood score |

Field mappings MUST remain explicit:

- `pair` is the canonical market identifier, for example `BTCUSDT`.
- `openTime` identifies a candle within a pair/timeframe; database mapping is `open_time`.
- `strategyId` identifies a logical strategy and `strategyVersion` identifies immutable behavior.
- `jobId` identifies one retryable backtest job; `runId` groups jobs in one search run.
- `publishedAt` is provider publication time; `collectedAt` is local ingestion time.

---

### Business Rules

**BR-01: Canonical Candle Identity**
A candle is unique by `(provider, pair, timeframe, openTime)`. Open, high, low, close and volume MUST be
validated before persistence. Duplicate delivery MUST update/ignore the same logical candle, never
create a duplicate row.

**BR-02: Immutable Strategy Version**
Every backtest references an immutable `StrategyDefinition` version, its parameters, dataset identity,
timeframe, date range and execution configuration. Changing implementation or parameters creates a new
version; historical experiment provenance MUST NOT be overwritten.

**BR-03: Deterministic, Look-Ahead-Safe Backtest**
The same dataset, strategy version, parameters, fees, slippage, initial capital and random seed MUST
produce the same result. Strategy/backtest code MUST NOT access candles or news published after the
simulated decision timestamp.

**BR-04: Explicit Composite Resolution**
Every Composite Strategy MUST record its members, versions, weights and conflict-resolution rule.
BUY/SELL/HOLD conflicts MUST be resolved by the configured majority/weighted policy, never by member
execution order.

**BR-05: Evaluation Is Separate From Strategy**
Strategies emit signals; they MUST NOT calculate their own rank. Evaluator computes at least Total
Return, Win Rate, Maximum Drawdown and Number of Trades. Profit Factor and Sharpe Ratio MAY be added
without changing Strategy implementations.

**BR-06: Reproducible Leaderboard Ranking**
Leaderboard rank MUST be derived from a versioned scoring policy and persisted evaluation result. Top-K
ties MUST use a documented deterministic tie-breaker. Changing scoring policy MUST NOT rewrite the
meaning of historical ranks without preserving the prior policy version.

**BR-07: At-Least-Once Job Safety**
Workers acknowledge a backtest job only after durable result persistence. Expired/unacknowledged jobs
MUST be retried with bounded attempts. Result and evaluation writes MUST be idempotent by `jobId`;
permanent failures move to a visible terminal/dead-letter state.

**BR-08: Realtime Continuity and Gap Recovery**
Binance disconnect MUST trigger bounded backoff reconnect. After reconnect, the adapter MUST compare
the last persisted candle with provider history and recover missing closed candles before declaring the
stream healthy. The UI MUST distinguish stale/reconnecting data from live data.

**BR-09: News and Sentiment Decoupling**
News Providers only collect and normalize `NewsItem`. Sentiment analysis consumes normalized news and
produces a versioned `SentimentResult`. News collection failure MUST NOT stop market charts, backtests or
technical strategies.

**BR-10: Analysis Only, No Live Trading**
The platform generates analytical signals and simulated trades only. It MUST NOT place, modify or cancel
real exchange orders. Any future live-trading capability requires a separate constitution amendment,
threat model and feature boundary.

---

### Technical Principles

**I. Monorepo Boundaries**
Backend and frontend are separate modules in one repository. Shared Docker Compose, CI and operational
configuration live at the root. Backend exposes API and worker entrypoints that share the same domain
package; copied domain implementations across processes are forbidden.

**II. Migration-First Schema Management**
All PostgreSQL schema changes MUST use immutable Alembic migrations. Application startup MUST NOT
silently create or mutate production schema. A merged migration is never edited; corrections require a
new migration and upgrade/downgrade validation.

**III. Strict TypeScript (NON-NEGOTIABLE)**
Frontend source is TypeScript-only. No `.js` or `.jsx` in `frontend/src/`. `any` requires an inline
justification. Component props, state, REST/WebSocket messages and chart data MUST be typed. Runtime
validation at untrusted boundaries MUST stay aligned with backend contracts.

**IV. Replaceable Ports and Plugins**
Market providers, news providers, strategies, search generators, repositories and job queues MUST be
accessed through stable protocols. Adding MACD MUST NOT modify Backtester, Evaluator or Leaderboard.
Replacing Random Search MUST NOT modify downstream execution. Adding OKX MUST NOT change frontend
market models.

**V. Observability**
Use structured JSON logs and metrics. Every HTTP/WebSocket request carries `request_id`; every search
run carries `run_id`; every queued backtest carries `job_id`; and every strategy execution carries
`strategy_id` plus `strategy_version`. These identifiers MUST propagate across API, queue, worker,
persistence and emitted events. Health endpoints and metrics for queue depth, job duration, retries,
failures, stream freshness, connected clients and current Top-1 MUST remain available.

---

### Access Control

**AC-01: Feature-Scoped Access Requirements**
`REQUIREMENT.md` does not prescribe user accounts or a fixed human role model. A feature that introduces
authentication, multi-user ownership or privileged configuration MUST define its actors, permissions
and denial scenarios in `spec.md` before implementation. Until such a feature is approved, the system
MUST NOT invent role-dependent business behavior. Internal workers remain non-human service identities
with only job-consumption and result-persistence permissions.

**AC-02: Backend Enforces All Authorization**
Authorization decisions MUST be enforced by backend application boundaries. Hiding UI controls is UX,
not security. Unauthenticated access returns `401`; insufficient permission returns `403`.

**AC-03: Ownership and Scope Validation**
If a feature introduces ownership, the backend MUST validate it for every read/write/action covered by
that feature. Completed runs, immutable strategy versions and experiment provenance MUST NOT become
editable merely because an actor owns the originating run.

**AC-04: Internal Boundary Protection**
Worker callbacks, operational endpoints and provider credentials MUST NOT be exposed to browser clients.
API responses MUST exclude secrets, raw credentials, internal exception traces and private job payloads.

**AC-05: WebSocket Authorization and Subscription Scope**
When authentication is enabled, WebSocket connections MUST authenticate consistently with HTTP APIs.
In every mode, the backend validates requested pairs/channels and enforces subscription limits;
client-provided channel names MUST NOT bypass access or resource-limit rules.

---

### API Design Standards

**API-01: Base Path and Versioning**
REST APIs use `/api/v1/**`; WebSocket channels use `/ws/v1/**`. Resource paths are kebab-case plural.
Breaking contract changes require a version decision, migration plan and backward compatibility review.

**API-02: Standardized Response Envelope**
Non-streaming business API responses use a consistent envelope:

```json
{
  "success": true,
  "message": "Human-readable message",
  "data": {},
  "timestamp": "ISO-8601 UTC",
  "requestId": "correlation-id"
}
```

WebSocket and queue messages instead use an explicitly versioned event schema with `eventType`,
`version`, `occurredAt`, correlation identifiers and typed payload.

**API-03: HTTP Status Mapping**
Status codes MUST map consistently:

| Code | Meaning |
|---|---|
| 200 | Successful read/update/action |
| 201 | Successful creation |
| 202 | Long-running run/job accepted |
| 400 | Malformed request |
| 401 | Unauthenticated |
| 403 | Forbidden |
| 404 | Resource not found |
| 409 | Duplicate/version/state conflict |
| 422 | Semantically invalid parameters |
| 429 | Rate or subscription limit exceeded |
| 500 | Unexpected server error |
| 503 | Required dependency unavailable |

**API-04: Error Code Format**
Error codes use `UPPER_SNAKE_CASE` with a domain prefix, for example `MARKET_PAIR_UNSUPPORTED`,
`STRATEGY_VERSION_NOT_FOUND`, `BACKTEST_JOB_ALREADY_COMPLETED` and `PROVIDER_RATE_LIMITED`.

**API-05: Explicit Lifecycle Endpoints**
Do not expose generic `updateStatus`. Use explicit actions such as:

- `POST /api/v1/backtest-runs/{id}/start`
- `POST /api/v1/backtest-runs/{id}/cancel`
- `POST /api/v1/search-runs/{id}/pause`
- `POST /api/v1/search-runs/{id}/resume`

**API-06: Pagination on List Endpoints**
Experiments, trades, news and leaderboard history endpoints MUST support cursor or page pagination.
Default page size is 25 and maximum is 200 unless a contract documents a measured exception. Page-based
responses include `page`, `pageSize` and `total`; cursor-based responses include `nextCursor` and
`hasMore`.

---

### Naming Conventions

**NC-01: Python Package Naming**
Backend packages use lowercase snake_case under `crypto_lab.<layer>.<feature>`, for example
`crypto_lab.domain.strategy` and `crypto_lab.infrastructure.binance`. Domain packages MUST NOT be named
after frameworks.

**NC-02: Entity and DTO Naming**

- Domain entities/value objects: PascalCase singular, for example `Candle`, `StrategyDefinition`.
- Request/response DTOs: PascalCase with `Request`/`Response` suffix.
- Queue/event contracts: PascalCase with `Job`/`Event` suffix.
- Python fields and database models: snake_case; JSON/TypeScript fields: camelCase.

**NC-03: API Path Naming**
Resource paths are kebab-case plural. Action endpoints use POST with a descriptive verb. Pair and
timeframe are values/query parameters, not ad-hoc path naming conventions.

**NC-04: Database Naming**

- Table names: snake_case plural, for example `strategy_definitions`, `backtest_results`.
- Column names: snake_case lowercase.
- Primary keys: `id` or documented domain key; external/provider IDs are separate fields.
- Foreign keys: `<entity>_id`; unique constraints MUST express domain identity explicitly.

**NC-05: Enum and Event Serialization**
Enums and event types use stable uppercase values such as `BUY`, `SELL`, `HOLD`, `RUNNING`,
`COMPLETED`, `FAILED`, `CANDLE_CLOSED` and `LEADERBOARD_UPDATED`. Changing a serialized value is a
contract change and requires versioning.

---

### Frontend Conventions

**FE-01: Contract-Aligned Runtime Validation**
Generated/shared TypeScript types and boundary validation MUST align with backend OpenAPI/WebSocket
contracts. A contract change updates frontend types, runtime parsing and contract tests in the same
change.

**FE-02: Role-Aware Navigation**
Navigation and action visibility reflect the current role. The frontend MUST NOT present worker/admin
operations to unauthorized users, while backend enforcement remains mandatory.

**FE-03: Shared Primitives Before Feature Abstraction**
Use `shared/ui` for domain-neutral primitives and `shared/charts` for chart primitives used by at least
two features. Domain components remain under `features/<feature>/components`. Promote a component to
`shared` only after real reuse, with no feature-specific rule in its public API.

**FE-04: Icon Library Consistency**
Use one approved icon library (Lucide React) throughout the application. Custom SVGs require a documented
visual or functional need.

**FE-05: Component ID Naming Convention**
Interactive/testable elements MUST have stable IDs:

| Element | Pattern | Example |
|---|---|---|
| Pair selector | `select-pair` | `select-pair` |
| Timeframe selector | `select-timeframe-{slot}` | `select-timeframe-1` |
| Chart container | `chart-{pair}-{timeframe}-{slot}` | `chart-btcusdt-5m-1` |
| Strategy selector | `select-strategy-{name}` | `select-strategy-rsi` |
| Start search | `btn-start-search` | `btn-start-search` |
| Cancel run | `btn-cancel-run-{id}` | `btn-cancel-run-42` |
| Leaderboard | `table-leaderboard` | `table-leaderboard` |
| Error message | `message-error` | `message-error` |

IDs MUST be stable across renders and are breaking selectors when changed.

**FE-06: Form and Async Feedback Standards**
Forms and long-running actions display field errors, action-level errors, loading/submitted state,
success state and retry/cancel affordances where allowed. Search/backtest progress MUST distinguish
queued, running, completed, failed and cancelled states.

**FE-07: Chart and Table Standards**
The dashboard supports up to four independently configurable charts. Candles update without full-page
reload. Chart overlays identify Buy/Sell and Entry/Exit. Large trade/news/experiment tables use
sorting, filtering and pagination rather than unbounded rendering.

**FE-08: Backend API Boundary**
Browser code communicates only with the Crypto Strategy Lab REST/WebSocket API. Direct Binance, news
provider, database or Redis access from frontend is forbidden. Frontend MUST NOT calculate strategy
signals, backtests, evaluation metrics or leaderboard ranking.

---

### Validation Rules

**VL-01: Dual Validation - Frontend and Backend**
Backend validation is authoritative. Frontend validation provides immediate feedback but is never a
security, integrity or reproducibility gate.

**VL-02: Market Data Integrity**
Validate supported pair/timeframe, chronological ordering, OHLC invariants (`low <= open/close <= high`),
non-negative volume, timestamp alignment and provider identity. Invalid external payloads MUST be
quarantined/logged, not silently coerced.

**VL-03: Strategy Parameter Validation**
Each strategy owns a typed, versioned parameter schema. Parameters are validated before registration or
job creation. Examples: periods are positive; fast period is less than slow period; weights are finite;
thresholds remain in declared ranges.

**VL-04: Backtest Range and Configuration Validation**
Backtests require an existing immutable dataset, `startTime < endTime`, sufficient warm-up data,
positive initial capital, non-negative fees/slippage and a supported timeframe. Invalid configurations
fail before a job is enqueued.

**VL-05: Numeric and Metric Constraints**
Prices, quantities and money use explicit precision rules. NaN/infinite metrics MUST NOT enter ranking.
Division-by-zero cases such as no losing trades or zero variance require documented metric semantics,
not arbitrary sentinel values.

---

### Logging & Audit

**LA-01: No Sensitive Data in Logs**
API keys, secrets, tokens, cookies, full provider credentials and private user data MUST never appear in
logs. Log sanitized identifiers and provider names instead.

**LA-02: Domain Event Logging**
Significant events log UTC timestamp, correlation IDs, actor/service identity, entity type/ID, action,
duration and result. This includes provider connect/disconnect, run lifecycle, job retry/failure,
strategy version creation and leaderboard change.

**LA-03: Dependency and Authorization Failures**
Authentication failures, forbidden operations, provider rate limits, WebSocket disconnects, queue
timeouts and exhausted retries MUST be logged at an appropriate level with actionable context and no
sensitive payload.

**LA-04: Permanent Experiment Audit Trail**
Every completed/failed backtest retains strategy ID/version, parameters, dataset, execution settings,
worker attempt history, evaluation policy version and result checksum/status. Audit records MUST support
reproducing how a leaderboard entry was created.

---

### Performance Standards

**PF-01: Indexed Time-Series and Run Queries**
Columns used to retrieve candles by pair/timeframe/time range and jobs/results by run/status MUST be
indexed. Query plans for critical ranges MUST be inspected before adding caching.

**PF-02: Narrow DTO and Event Payloads**
REST/WebSocket/queue messages MUST exclude unnecessary entity graphs. Candle updates send the minimum
fields needed; large equity curves and trade lists use pagination, compression or separate retrieval.

**PF-03: Interactive API and Realtime Latency Target**
Under documented demo load, 95% of non-job read APIs MUST complete within 300 ms, and 95% of received
market updates MUST reach subscribed browser clients within 1 second of backend ingestion. Measurements
exclude upstream provider delay and MUST state test conditions.

**PF-04: Backtest Scale Target**
A fixed benchmark MUST compare one and four workers. With adequate CPU and no measured shared bottleneck,
four workers SHOULD achieve at least 3x one-worker throughput while producing an identical result set.
Any lower result requires a documented bottleneck analysis, not hidden relaxation.

**PF-05: Bounded Collections and Subscriptions**
List endpoints are paginated, search runs have explicit candidate limits, and the dashboard permits no
more than four active chart subscriptions per configured workspace unless a feature spec raises the
limit with a load test.

---

### Definition of Done

A feature is not done until all of the following are true:

**DOD-01: Requirement Traceability**
Every delivered behavior traces to a canonical `docs/SRS.md` User Story ID, a `spec.md` user story and
requirement ID, design artifact and completed task. The feature spec contains no unresolved omission
of an applicable SRS acceptance criterion. `quickstart.md` demonstrates the primary acceptance
scenario.

**DOD-02: Contracts and Architecture Documented**
Changed REST/WebSocket/job/provider contracts are documented and tested. Relevant architecture flow,
component responsibilities and ADRs are updated when a boundary or infrastructure choice changes.

**DOD-03: Architectural Replaceability Verified**
Fitness/contract tests prove applicable drivers: adding a test strategy does not modify Backtester,
Evaluator or Leaderboard; replacing a generator does not modify Backtester; provider mapping keeps the
frontend contract stable; worker count is configuration, not producer/consumer code.

**DOD-04: Reliability and Validation Implemented**
External data, strategy parameters and backtest configuration are validated. Retry, idempotency,
reconnect, terminal failure and stale-data behavior are tested wherever the feature owns those paths.

**DOD-05: Frontend and Backend in Sync**
Frontend types/runtime validation match backend contracts. Realtime loading/error/reconnect states and
accessibility for changed interactive elements are covered.

**DOD-06: Test and Spec Kit Quality Gates**
Required unit, contract, integration, E2E and load tests pass. `$speckit-analyze` has no unresolved
CRITICAL/HIGH findings, all required tasks are `[X]`, and `$speckit-converge` reports `Converged` without
appending new tasks.

**Project-Level MVP Release Gate**
The project is not ready for final submission until the integrated demo proves: Binance historical and
realtime candles; up to four independent timeframes; at least four single strategies; one Composite
Strategy policy; historical backtesting; Return, Win Rate, Maximum Drawdown and Number of Trades;
Random Search; Top-K Leaderboard; Buy/Sell and Entry/Exit visualization; and the Collect -> Store ->
Sentiment pipeline. Each result shown on the Leaderboard MUST trace to an immutable strategy version,
dataset and evaluation policy.

---

### Technology Stack

Approved stack - major upgrades or new core dependencies require team approval and an ADR.

**Backend**

- Python 3.12
- FastAPI and Pydantic
- SQLAlchemy 2 and Alembic
- PostgreSQL 16
- A durable job broker and horizontally scalable worker implementation selected by the relevant
  Accepted ADR; Redis and Celery remain candidates until that ADR is accepted
- NumPy and Pandas; Polars/Numba only after profiling evidence
- httpx and websockets for provider adapters
- pytest, pytest-asyncio and Testcontainers
- Ruff and mypy

**Frontend**

- Node.js active LTS
- React 19 with TypeScript 5 and Vite
- Tailwind CSS
- TradingView Lightweight Charts
- TanStack Query
- React state first; Zustand only for demonstrated cross-feature client state
- Vitest, React Testing Library and Playwright
- ESLint and Lucide React

**Infrastructure**

- Docker Desktop and Docker Compose for local orchestration
- PostgreSQL and feature-required broker/cache services selected by Accepted ADRs
- Multi-stage Dockerfiles with non-root runtime users
- GitHub Actions for lint, type-check, test, migration and build gates
- k6 for realtime/API/worker submission load tests
- Prometheus-compatible metrics
- Grafana or OpenTelemetry requires either a feature requirement for dashboards/traces or an ADR with
  a measured diagnosis need; neither is added solely as speculative infrastructure

---

### Development Workflow

- Local development MUST start from a documented clean setup using Docker Compose for PostgreSQL and
  infrastructure required by the active feature's Accepted ADRs; API, worker and frontend may run in
  containers or documented local dev commands.
- One active feature proceeds through constitution -> specify -> clarify -> plan -> checklist -> tasks
  -> analyze -> implement -> converge.
- Before `$speckit-specify` creates or updates that feature, the workflow MUST read `docs/SRS.md`, cite
  the selected feature/User Story IDs and identify the applicable section 3 requirements, section 6
  flow and cross-cutting NFRs. A prompt that does not provide those references does not waive this
  gate; the agent MUST discover them from the SRS.
- Before `$speckit-plan`, the workflow MUST complete the Architecture and ADR Governance gate and
  record its references and compliance results in `plan.md`.
- Domain tests are written before implementation when the spec/constitution requires TDD. Contract and
  integration tests precede boundary implementations.
- Pull requests MUST NOT merge with failing lint, type checks, tests, migrations or unresolved
  constitution violations.
- Database migrations are tested from an empty database and from the previous supported schema.
- Each phase uses small reviewable commits; unrelated feature scope is not bundled into the same change.
- Production-like configuration is injected through environment variables; `.env.example` documents
  required keys without values.

---

### Security Requirements

- No secrets, API keys, credentials or tokens in source, logs, fixtures or committed `.env` files.
- Provider credentials are read-only/minimum-scope. The project MUST NOT request exchange trading or
  withdrawal permissions.
- All external Binance/news payloads, HTTP inputs and WebSocket subscriptions are validated at trust
  boundaries.
- Dependency versions are locked and reviewed; critical known vulnerabilities block release.
- Containers run as non-root users and expose only required ports.
- CORS, trusted origins, authentication cookies/tokens and TLS termination are explicitly configured
  per environment; permissive development settings MUST NOT be production defaults.
- Rate limiting and bounded resource requests protect expensive backtest/search endpoints.
- Analysis output MUST display a non-investment-advice disclaimer and MUST NOT imply guaranteed profit.

**Version**: 1.2.0 | **Ratified**: 2026-08-11 | **Last Amended**: 2026-08-13
