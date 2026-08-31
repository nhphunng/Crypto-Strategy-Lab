# Realtime Multi-Chart Requirements Checklist: Realtime Multi-Chart Dashboard

**Purpose**: Reviewer gate for completeness, clarity, consistency, and measurability of TV2 Candle, subscription, recovery, multi-slot, responsive, and accessibility requirements
**Created**: 2026-08-13
**Feature**: [spec.md](../spec.md)

**Depth/Audience**: Standard PR-review gate. Focus: realtime reliability/shared contracts and independently configurable chart UX.

## Requirement Completeness

- [x] CHK001 Are one-to-four slot behavior, stable identity, fifth-slot rejection, and dashboard-level pair scope all specified? [Completeness, Spec §FR-001–§FR-003, §Assumptions]
- [x] CHK002 Are historical bootstrap, realtime delivery, Candle update, and closed-Candle recovery requirements documented as one complete flow? [Completeness, Spec §FR-004–§FR-013]
- [x] CHK003 Are all canonical timeframe values and unsupported-selection behavior specified? [Completeness, Spec §FR-003, §Edge Cases]
- [x] CHK004 Are loading, live, stale, reconnecting, error, empty, partial, rate-limited, and provider-error states covered? [Completeness, Spec §FR-002, §FR-013]
- [x] CHK005 Are responsive layout, bounded history, keyboard operation, focus, and non-color status requirements included? [Completeness, Spec §FR-014–§FR-016]
- [x] CHK006 Are TV1, TV3, TV5, News/Sentiment, and real-trading boundaries explicitly assigned or excluded? [Completeness, Spec §FR-017–§FR-018, §Traceability and Dependencies]

## Requirement Clarity

- [x] CHK007 Is Candle identity defined by provider, pair, timeframe, and UTC opening time rather than arrival order? [Clarity, Spec §FR-005–§FR-007]
- [x] CHK008 Are open-to-open, open-to-closed, duplicate, conflicting closed, and out-of-order merge meanings explicit? [Clarity, Data Model §Candle]
- [x] CHK009 Is “realtime” quantified by an ingestion-to-visible percentile target and documented load conditions? [Clarity, Spec §NFR-001, §SC-002; Quickstart §Realtime propagation]
- [x] CHK010 Is `LIVE` defined as healthy delivery plus restored closed-Candle continuity rather than merely an open socket? [Clarity, Spec §FR-011–§FR-013]
- [x] CHK011 Is slot independence defined to include timeframe, data, state, viewport, and chart instance? [Clarity, Spec §FR-008–§FR-010, §SC-004]
- [x] CHK012 Is bounded history quantified with initial and hard limits and explicit completeness states? [Clarity, Plan §Technical Context; Data Model §Historical Candle Range]

## Requirement Consistency

- [x] CHK013 Do provider, pair, timeframe, timestamp, decimal, closed flag, and identity rules agree across spec, model, REST, and event contracts? [Consistency, Spec §FR-003–§FR-007; Contracts]
- [x] CHK014 Do slot count and subscription limits agree across spec, plan, event contract, chart contract, and quickstart? [Consistency, Spec §FR-001, §NFR-003]
- [x] CHK015 Do recovery attempts, states, backfill conditions, exhaustion, and manual retry agree across research, model, event contract, and acceptance scenarios? [Consistency, Spec US4; Research Decision 4]
- [x] CHK016 Does the one-dashboard-pair assumption remain consistent while each timeframe is independently configurable? [Consistency, Spec §Assumptions, Chart Contract §Grid rules]
- [x] CHK017 Does the base chart extension seam remain generic and free of TV3 strategy or TV5 overlay/trade ownership? [Consistency, Spec §FR-018, Chart Contract §TV5 composition seam]

## Acceptance Criteria Quality

- [x] CHK018 Can correct live merging be measured as one Candle per identity, no time regression, and a terminal closed state? [Measurability, Spec US1, §SC-003]
- [x] CHK019 Can one-to-four layouts and fifth-slot rejection be objectively demonstrated for each supported count? [Measurability, Spec US2, §SC-001]
- [x] CHK020 Can timeframe isolation be verified by unchanged data, state, timeframe, viewport, and instance for every unaffected slot? [Measurability, Spec US3, §SC-004]
- [x] CHK021 Can recovery success be verified through exact missing intervals and the condition for returning to `LIVE`? [Measurability, Spec US4, §SC-005]
- [x] CHK022 Can accessibility and narrow-layout outcomes be evaluated without subjective wording? [Measurability, Spec §SC-006–§SC-007; Chart Contract §Accessibility]

## Scenario and Edge-Case Coverage

- [x] CHK023 Are the four canonical SRS stories independently testable? [Coverage, Spec US1–US4]
- [x] CHK024 Are duplicate/out-of-order updates, partial history, late old-generation work, and same-selection slots covered? [Coverage, Spec §Edge Cases]
- [x] CHK025 Are provider disconnect, browser offline, rate limit, retry exhaustion, manual retry, and gap-backfill paths defined? [Coverage, Spec US4; Event Contract §Reconnect and gap recovery]
- [x] CHK026 Is one-slot failure isolated from healthy selections and optional service failure isolated from all market charts? [Coverage, Spec §FR-012, §FR-017]
- [x] CHK027 Is the bootstrap race between history response and live events addressed without losing or duplicating an update? [Coverage, Event Contract §Bootstrap race handling]

## Non-Functional Requirements

- [x] CHK028 Are p95 propagation, four-slot soak, range bounds, and subscription caps specified with measurable conditions? [Performance, Spec §NFR-001–§NFR-003, §SC-002–§SC-003]
- [x] CHK029 Are logs and metrics defined for lifecycle, freshness, reconnect, gap, invalid event, and logical-versus-upstream subscription counts? [Observability, Spec §NFR-004; Research Decision 7]
- [x] CHK030 Are secret, raw-payload, stack-trace, validation, and version compatibility boundaries explicit? [Security, Spec §NFR-005–§NFR-006; Event Contract §Compatibility]
- [x] CHK031 Are required unit, contract, integration, frontend, E2E, and propagation checks documented? [Testability, Spec §NFR-007; Plan §Verification Strategy]

## Dependencies, Assumptions, and Traceability

- [x] CHK032 Is TV1 ownership of Candle/history fields and TV2 ownership of realtime/slot lifecycle explicit enough for cross-review? [Dependency, Spec §Traceability and Dependencies]
- [x] CHK033 Are Accepted Architecture, ADR-002, and ADR-003 identified as binding implementation authority? [Governance, Plan §Architecture Decision References]
- [x] CHK034 Does every applicable SRS FR, business flow, NFR, and canonical story map into the feature artifacts? [Traceability, Spec §Traceability and Dependencies]
- [x] CHK035 Are the completed contract cross-review and architecture acceptance recorded with explicit evidence rather than hidden assumptions? [Governance, Plan §Architecture Decision References; Quickstart §Approval gates]

## Notes

- 35/35 requirements-quality checks pass at generation time.
- This checklist evaluates the written requirements. Implementation verification belongs to `tasks.md` and `quickstart.md`.
