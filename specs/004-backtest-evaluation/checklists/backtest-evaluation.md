# Backtest and Evaluation Requirements Checklist

**Purpose**: Standard PR-review gate for completeness, clarity, consistency, measurability, and cross-feature compatibility of TV4 requirements
**Created**: 2026-08-13
**Feature**: [spec.md](../spec.md)

**Depth/Audience**: Standard reviewer gate. Focus: look-ahead-safe deterministic execution, accounting reconciliation, metric/scoring semantics, immutable provenance, and TV1/TV3/TV5 boundaries.

## Requirement Completeness

- [x] CHK001 Are exact Dataset, Strategy Definition, execution configuration, policy, and seed inputs all specified? [Completeness, Spec §FR-001–FR-003]
- [x] CHK002 Are execution timing, supported side/position count, sizing, fees, slippage, redundant Signals, and end-of-range behavior all defined? [Completeness, Spec §FR-006]
- [x] CHK003 Are Backtest Result, Signal snapshot, Trade, Equity Curve, final equity, status, and checksum outputs documented? [Completeness, Spec §FR-007–FR-010]
- [x] CHK004 Are required and extended metrics, units, directions, observation frequency, precision, and null semantics specified? [Completeness, Spec §FR-011–FR-013; Research R5]
- [x] CHK005 Are Scoring Policy weights, normalization, eligibility, undefined-value behavior, and complete tie-break semantics documented? [Completeness, Spec §FR-014–FR-017; Research R6]
- [x] CHK006 Are comparison dimensions, strict/contextual behavior, and immutable audit retrieval requirements covered? [Completeness, Spec §FR-018–FR-019]

## Requirement Clarity

- [x] CHK007 Is next-Candle-open execution distinguished clearly from Signal timestamp and final-Candle behavior? [Clarity, Spec §Clarifications; FR-006]
- [x] CHK008 Are adverse slippage and two-sided fee semantics objectively defined rather than described as generic transaction costs? [Clarity, Research R2; Domain Contract]
- [x] CHK009 Are no-op Signal cases and forced-close provenance expressed with stable meanings? [Clarity, Spec §Edge Cases; Research R3]
- [x] CHK010 Is the accounting identity precise enough to reconcile cash, quantity, costs, Trades, Equity Points, and final equity? [Clarity, Spec §FR-009; Data Model]
- [x] CHK011 Are no-trade zero values and no-loss/zero-variance/insufficient-observation null values distinguished explicitly? [Clarity, Spec §FR-013]
- [x] CHK012 Is a score's reproducibility independent of the changing candidate population? [Clarity, Research R6]

## Requirement Consistency

- [x] CHK013 Do Dataset version/checksum/range/Candle semantics agree with Feature 001 contract version `1`? [Consistency, Assumption; TV1 Consumer Boundary]
- [x] CHK014 Do Strategy Definition, Strategy Context, Signal ordering, warm-up, and error semantics agree with Feature 003 contract `1.0.0`? [Consistency, Spec §FR-003–FR-005]
- [x] CHK015 Do Evaluation Result, Trade, score, policy, and provenance outputs satisfy Feature 005's upstream assumptions? [Consistency, Evaluation Result Contract]
- [x] CHK016 Are `BacktestRun`, `BacktestResult`, `Trade`, `EvaluationResult`, Market Pair, Timeframe, and Signal terms consistent with the Constitution/SRS glossary? [Consistency, Spec §Key Entities]
- [x] CHK017 Is scoring kept separate from Strategy calculation and ranking kept outside TV4 throughout spec, plan, and contracts? [Consistency, Spec §Out of Scope]
- [x] CHK018 Are all Proposed architecture/ADR inputs identified as review inputs rather than falsely treated as Accepted? [Governance, Plan §Architecture Decision References]

## Acceptance Criteria Quality

- [x] CHK019 Can repeated-run determinism be measured through canonical content and checksum rather than audit timestamps? [Measurability, SC-001]
- [x] CHK020 Can look-ahead rejection be verified for future, open, misaligned, duplicate, unsorted, gap-marked, and incomplete inputs? [Measurability, SC-002]
- [x] CHK021 Can the accounting identity be objectively verified at the documented decimal precision? [Measurability, SC-003]
- [x] CHK022 Can every metric edge case be checked against a deterministic fixture without NaN/infinity? [Measurability, SC-004]
- [x] CHK023 Can idempotency be measured as exactly one durable result per declared identity? [Measurability, SC-005]
- [x] CHK024 Can complete provenance and comparison-difference coverage be verified for every fixture? [Measurability, SC-006, SC-008]

## Scenario and Edge-Case Coverage

- [x] CHK025 Are all five canonical included SRS stories represented as independently testable user stories? [Coverage, Spec US1–US5]
- [x] CHK026 Are zero-Candle dataset rejection, insufficient-history, all-HOLD/WARMUP, final-Candle Signal, and no-trade scenarios addressed? [Coverage, Spec §Edge Cases]
- [x] CHK027 Are redundant Signals, insufficient capital after costs, and forced final closure addressed? [Coverage, Spec §Edge Cases]
- [x] CHK028 Are duplicate run/evaluation submissions, conflicting identity reuse, and partial-failure behavior addressed? [Coverage, Spec §FR-016, FR-020]
- [x] CHK029 Are incompatible contract versions, unavailable Strategy versions, Dataset integrity failure, and unavailable required context covered? [Coverage, Spec US1; Edge Cases]
- [x] CHK030 Are compatible and incompatible comparison flows both defined without changing stored metric values? [Coverage, Spec US5]

## Non-Functional Requirements

- [x] CHK031 Are simulation benchmark and bounded read performance targets quantified with test conditions to be recorded? [Performance, Plan §Technical Context; Quickstart]
- [x] CHK032 Are immutable persistence, atomic child writes, idempotency, and fail-closed integrity semantics specified? [Reliability, Data Model]
- [x] CHK033 Are correlation identifiers, safe categorized errors, permanent audit provenance, and duration observations required? [Observability, Spec §FR-020; Data Model]
- [x] CHK034 Are decimal precision, canonical serialization, and checksum exclusions documented consistently? [Determinism, Research R4]
- [x] CHK035 Are analysis-only labeling, no-guaranteed-profit language, and the no-live-order boundary explicit? [Security, Spec §FR-022]

## Dependencies, Assumptions, and Traceability

- [x] CHK036 Is Feature 001's unmerged-branch status explicitly recorded as a re-review dependency? [Dependency, Spec §Assumptions]
- [x] CHK037 Are Feature 003 and Feature 005 owner/consumer responsibilities documented without duplication? [Dependency, Plan §Boundary Ownership]
- [x] CHK038 Are deferred worker, retry, search, leaderboard, visualization, and Composite Strategy scopes clearly excluded? [Scope, Spec §Out of Scope]
- [x] CHK039 Does every FR map to at least one user story or an explicit cross-cutting concern? [Traceability, Spec §Source Traceability]
- [x] CHK040 Do quickstart scenarios and contracts cover determinism, execution, evaluation/scoring, comparison, and handoff? [Traceability, Quickstart]

## Notes

- 40/40 requirements-quality checks pass at generation time.
- Feature 001 must be re-reviewed after merge, and the initial scoring policy requires team governance review before it becomes a project-wide default.
