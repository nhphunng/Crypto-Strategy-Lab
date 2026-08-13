# Leaderboard and Visualization Requirements Checklist: Leaderboard and Trade Visualization

**Purpose**: Reviewer gate for the completeness, clarity, consistency, and measurability of TV5 ranking, realtime, provenance, chart, and accessibility requirements
**Created**: 2026-08-13
**Feature**: [spec.md](../spec.md)

**Depth/Audience**: Standard PR-review gate. Focus: deterministic/idempotent leaderboard behavior and explainable, accessible trade visualization.

## Requirement Completeness

- [x] CHK001 Are Top-K scope, K behavior, metric/policy selection, compatibility, and inclusion rules all specified? [Completeness, Spec §FR-001, §FR-006]
- [x] CHK002 Are all assignment-required row values—Return, Win Rate, MDD, Number of Trades, strategy/version, context, and score—documented? [Completeness, Spec §FR-003, §FR-004]
- [x] CHK003 Are sort, filter, and pagination requirements defined for every required leaderboard dimension? [Completeness, Spec §FR-005]
- [x] CHK004 Are snapshot, incremental update, stale, reconnect, and recovery requirements documented as a complete lifecycle? [Completeness, Spec §FR-008, §FR-010]
- [x] CHK005 Are Candles, strategy overlays, Buy/Sell, Entry/Exit, Trade table, selection highlight, and provenance all covered? [Completeness, Spec §FR-011–§FR-015]
- [x] CHK006 Are empty, loading, no-trade, partial, failed, stale, and unavailable-overlay requirements explicitly defined? [Completeness, Spec §FR-016]

## Requirement Clarity

- [x] CHK007 Is deterministic order defined through a versioned policy and complete tie-breaker rather than vague “best strategy” language? [Clarity, Spec §FR-002]
- [x] CHK008 Are metric direction and units explicit, especially the interpretation of Maximum Drawdown? [Clarity, Spec §FR-004]
- [x] CHK009 Is “without refresh” distinguished from update correctness, ordering, and snapshot recovery? [Clarity, Spec §FR-008–§FR-010]
- [x] CHK010 Are marker alignment rules based on recorded timestamp/price rather than an ambiguous nearest-Candle rule? [Clarity, Spec §FR-013]
- [x] CHK011 Is non-color differentiation specified for Buy, Sell, Hold, Entry, and Exit through text/shape and keyboard-equivalent detail access? [Clarity, Spec §FR-012–§FR-014, SC-007]
- [x] CHK012 Is historical provenance defined as exact immutable versions and contexts rather than current registry state? [Clarity, Spec §FR-015]

## Requirement Consistency

- [x] CHK013 Do Top-K requirements agree across user scenarios, FRs, Success Criteria, data model, and REST contract? [Consistency, Spec US1/§FR-001–§FR-006, Plan Phase 1]
- [x] CHK014 Do duplicate/out-of-order semantics agree across FRs, event contract, projection data model, and acceptance guide? [Consistency, Spec §FR-009–§FR-010]
- [x] CHK015 Do Strategy Definition, Evaluation Result, Leaderboard Entry, Backtest Run, Candle, Signal, and Trade terms match the constitution/SRS glossary? [Consistency, Spec §Key Entities]
- [x] CHK016 Is the separation between upstream Evaluation/Backtest responsibilities and TV5 ranking/visualization consistently bounded? [Consistency, Spec §Assumptions, §Out of Scope]
- [x] CHK017 Is strategy-neutral rendering consistent with the MACD/replaceability scenario and generic overlay contract? [Consistency, Spec §FR-012, §FR-017]

## Acceptance Criteria Quality

- [x] CHK018 Can deterministic Top-K and tie behavior be objectively verified from fixed Evaluation Result identifiers? [Measurability, SC-001]
- [x] CHK019 Are snapshot and live update latency targets quantified with percentile, threshold, and load-condition requirements? [Measurability, SC-003, SC-004]
- [x] CHK020 Can duplicate delivery success be measured as exactly one entry and one visible transition? [Measurability, SC-005]
- [x] CHK021 Can marker alignment and unaligned behavior be measured without subjective chart inspection alone? [Measurability, SC-006]
- [x] CHK022 Can provenance completeness be verified for every displayed entry/trade fixture? [Measurability, SC-008]

## Scenario and Edge-Case Coverage

- [x] CHK023 Are primary flows independently testable for Top-K, live update, and ranked-result visualization? [Coverage, Spec US1–US3]
- [x] CHK024 Are fewer-than-K, ties, invalid K/page, no-trade, missing/non-finite metrics, and incompatible contexts covered? [Coverage, Spec §Edge Cases]
- [x] CHK025 Are concurrent qualification, displacement from Top-K, duplicate delivery, stale delivery, and missed-event recovery covered? [Coverage, Spec §Edge Cases, §FR-007–§FR-010]
- [x] CHK026 Are overlapping and unaligned markers, unavailable referenced data, and large ranges covered without guessing/unbounded loading? [Coverage, Spec §Edge Cases]
- [x] CHK027 Is optional News/Sentiment failure isolated without fabricating overlay data or blocking technical results? [Coverage, Spec §Edge Cases]

## Non-Functional Requirements

- [x] CHK028 Are p95 read/update targets, page limits, K bounds, and bounded chart ranges specified? [Performance, Spec SC-003–SC-004, Assumptions]
- [x] CHK029 Are idempotency, atomic contiguous ranks, projection ordering, and last-valid-snapshot recovery specified? [Reliability, Spec §FR-002, §FR-009–§FR-010]
- [x] CHK030 Are accessibility requirements specified for marker identity, keyboard interaction, focus/detail equivalence, and data-heavy tables? [Accessibility, Spec §FR-013–§FR-014, SC-007]
- [x] CHK031 Are security/privacy boundaries explicit enough to require the non-investment-advice disclaimer and prevent guaranteed-profit claims, live order behavior, secrets, and internal traces from entering this feature? [Security, Spec §FR-018, SC-010, §Out of Scope]
- [x] CHK032 Are observability/correlation expectations traceable through projection version, update time, run/job, strategy, and current Top-1? [Observability, Plan §Constitution Check]

## Dependencies, Assumptions, and Traceability

- [x] CHK033 Are upstream Candle, Backtest, Signal, Trade, Evaluation Result, and Scoring Policy dependencies documented without silently assigning them to TV5? [Dependency, Spec §Assumptions]
- [x] CHK034 Is the default K=10 identified as a demo assumption while configurability remains a requirement? [Assumption, Spec §Assumptions]
- [x] CHK035 Does every canonical SRS story and applicable `EV-FR-03..06`/Visualization requirement map to user scenarios and FRs? [Traceability, Spec §Source Traceability]
- [x] CHK036 Are contracts and quickstart scenarios synchronized with all three canonical story IDs? [Traceability, Plan §Phase 1]

## Notes

- 36/36 requirements-quality checks pass at generation time.
- This checklist tests whether the written requirements are implementation-ready; implementation verification belongs to `tasks.md` and `quickstart.md`.
