# Feature Specification: Realtime Multi-Chart Dashboard

**Feature Branch**: `feat/002-realtime-chart-spec-plan`

**Created**: 2026-08-13

**Status**: Accepted

**Accepted**: 2026-08-19 by the Crypto Strategy Lab Team; the TV1/TV2 shared Candle/history version 1 boundary is cross-reviewed and locked for implementation.

**Input**: User description: "TV2 — 002-realtime-multi-chart — Dữ liệu realtime, tối đa 4 biểu đồ"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive Realtime Candles (Priority: P1)

As an `ANALYST`, I want each visible chart to receive current candle updates so that I can follow the market without refreshing the page or repeatedly requesting new data.

**SRS Traceability**: `MD-US-02`; `MD-FR-02`, `MD-FR-03`, `MD-FR-04`, `MD-FR-06`; Business Flow §6.1.

**Why this priority**: Realtime delivery is the core value of this feature and supplies every chart slot.

**Independent Test**: Open one chart with valid historical candles, publish open-candle and closed-candle updates for its market selection, and confirm the same slot updates in chronological order without a page refresh.

**Acceptance Scenarios**:

1. **Given** a chart is subscribed to a supported pair and timeframe, **When** a new open-candle update arrives, **Then** the current candle is updated without adding a duplicate interval.
2. **Given** the current candle is open, **When** its closed update arrives, **Then** the chart marks that interval closed and can begin the next interval.
3. **Given** duplicate or out-of-order updates arrive, **When** the chart processes them, **Then** the series remains unique and never moves backward in time.

---

### User Story 2 - View Up to Four Charts (Priority: P1)

As an `ANALYST`, I want to view one to four candlestick charts at once so that I can compare the same market across several timeframes.

**SRS Traceability**: `MTC-US-01`; `MTC-FR-01`, `MTC-FR-03`, `MTC-FR-05`; Business Flow §6.2 and §6.3.

**Why this priority**: Multi-timeframe comparison is the primary dashboard outcome required by the project.

**Independent Test**: Select one, two, three, and four slots and confirm every slot keeps a stable identity, selected timeframe, candles, and honest connection status.

**Acceptance Scenarios**:

1. **Given** the dashboard is available, **When** the analyst selects between one and four chart slots, **Then** exactly that number of independently identified charts is visible.
2. **Given** four active charts, **When** a fifth chart is requested, **Then** the dashboard keeps the four-slot limit and explains the limit.
3. **Given** a narrow display, **When** multiple charts are visible, **Then** the charts use a readable single-column layout without losing their controls or status.

---

### User Story 3 - Change One Timeframe Independently (Priority: P2)

As an `ANALYST`, I want to change one chart's timeframe so that I can inspect another interval without disturbing the other charts.

**SRS Traceability**: `MTC-US-02`; `MTC-FR-02`, `MTC-FR-04`; Business Flow §6.3.

**Why this priority**: Independent configuration turns the dashboard from repeated charts into a useful comparison tool.

**Independent Test**: Change one slot from `5m` to `1h` and confirm only that slot replaces its data and subscription while all other slots retain data, timeframe, connection state, and viewport.

**Acceptance Scenarios**:

1. **Given** several live charts, **When** the analyst changes one slot's timeframe, **Then** only that slot enters loading and moves to the new timeframe.
2. **Given** a slot changes timeframe, **When** the change completes, **Then** its previous live subscription is released and exactly one subscription remains for its new selection.
3. **Given** two slots use the same timeframe, **When** one slot changes or is removed, **Then** the other slot retains its own state and continues receiving updates.

---

### User Story 4 - Recover a Market Data Connection (Priority: P2)

As an `OPERATOR`, I want a disconnected market stream to recover automatically so that charts do not present interrupted or outdated data as live.

**SRS Traceability**: `MD-US-03`; `MD-FR-05`, `MTC-FR-05`; Business Flow §6.1 and §6.3.

**Why this priority**: A 24/7 data source will disconnect; explicit recovery protects data continuity and user trust.

**Independent Test**: Interrupt one active market stream, allow updates to be missed, restore the source, and confirm the affected slots show recovery states, receive missing closed candles, and return to live only after continuity is restored.

**Acceptance Scenarios**:

1. **Given** a live slot, **When** its source disconnects, **Then** the slot changes to `STALE` or `RECONNECTING` and keeps its last known data visibly marked as old.
2. **Given** closed candles were missed during a disconnect, **When** connectivity returns, **Then** the missing range is restored before the slot becomes `LIVE`.
3. **Given** one subscription cannot recover after bounded automatic attempts, **When** recovery is exhausted, **Then** only affected slots show `ERROR` with a manual retry action while other slots continue.

### Edge Cases

- The requested pair or timeframe is unsupported, disabled, or removed by the provider.
- Initial historical data is empty, partial, stale, or unavailable while the live source is available.
- The same logical candle arrives more than once, arrives out of order, or changes from open to closed.
- A slot is removed or reconfigured while its initial data or subscription request is still pending.
- Two or more slots request the same pair and timeframe, then one slot changes or closes.
- The browser temporarily loses connectivity while the upstream provider remains healthy.
- The optional News or Sentiment service fails while market charts are active.
- Chart history grows beyond the selected display range; the dashboard must not render unbounded history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST support one to four stable chart slots and MUST reject a fifth active slot with an actionable explanation.
- **FR-002**: Each slot MUST expose its pair, timeframe, candle series, and one of these connection states: `LOADING`, `LIVE`, `STALE`, `RECONNECTING`, or `ERROR`.
- **FR-003**: The MVP MUST support `BTCUSDT` and the canonical timeframe values `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, and `1d` when the market provider supports them.
- **FR-004**: The dashboard MUST obtain historical and realtime candles only through the Crypto Strategy Lab boundary and MUST remain independent of provider-specific field names.
- **FR-005**: A realtime update MUST identify its provider, pair, timeframe, opening time, OHLCV values, and whether the candle is closed.
- **FR-006**: A candle MUST be unique by `(provider, pair, timeframe, openTime)`, use UTC time, satisfy OHLCV invariants, and preserve chronological ordering.
- **FR-007**: A repeated update for an open candle MUST update that logical candle rather than append a duplicate; a closed candle MUST NOT regress to open.
- **FR-008**: The analyst MUST be able to change each slot's timeframe without reloading the dashboard or changing unaffected slots.
- **FR-009**: Adding, removing, or reconfiguring a slot MUST acquire only its required live selection and release its obsolete selection without leaving an orphan subscription.
- **FR-010**: Multiple slots MAY use the same pair and timeframe while retaining independent slot identity, controls, status, and viewport.
- **FR-011**: A disconnected or stale selection MUST use bounded automatic reconnect attempts and restore missing closed candles before it is marked `LIVE`.
- **FR-012**: Exhausted automatic recovery MUST expose an actionable error and manual retry for affected slots without stopping healthy chart slots.
- **FR-013**: Loading, empty, partial, stale, reconnecting, unsupported-selection, rate-limited, and provider-error states MUST be distinguishable and MUST NOT present old data as live.
- **FR-014**: The chart grid MUST adapt from one to four charts to the available width and MUST preserve all chart controls in a readable single-column layout on narrow screens.
- **FR-015**: Add/remove controls, timeframe controls, retry actions, and connection states MUST be usable by keyboard, expose visible focus, and convey meaning without relying on color alone.
- **FR-016**: The dashboard MUST retain only a bounded, explicitly selected history range for display and MUST NOT request or render unlimited candle history.
- **FR-017**: Market charts MUST continue when optional News or Sentiment capabilities are unavailable.
- **FR-018**: Strategy calculation, signal/trade overlays, backtesting, ranking, direct exchange access from the browser, and real trading MUST remain outside this feature.

### Non-Functional Requirements

- **NFR-001**: Under the documented demo load, at least 95% of accepted market updates MUST become visible in subscribed chart slots within one second of backend ingestion, excluding upstream delay.
- **NFR-002**: A candle update or one-slot configuration change MUST NOT reload or rebuild the full dashboard or reset unaffected chart viewports.
- **NFR-003**: The system MUST enforce no more than four active chart subscriptions per dashboard session.
- **NFR-004**: Stream connect, disconnect, retry, recovery, rejection, and freshness changes MUST be observable using sanitized timestamps, selection identifiers, state, duration, and correlation identifiers.
- **NFR-005**: Credentials, provider secrets, raw provider payloads, internal errors, and private connection details MUST NOT appear in browser messages or logs.
- **NFR-006**: Public historical and realtime contracts MUST be explicitly versioned; incompatible changes require a new contract version and coordinated review with TV1.
- **NFR-007**: Acceptance must be covered by automated unit, contract, integration, end-to-end, and documented realtime propagation checks appropriate to the changed boundary.

### Key Entities

- **Chart Slot**: A stable dashboard position with slot identity, selected pair/timeframe, viewport, visible candle range, and connection state.
- **Candle**: A provider-neutral OHLCV interval identified by provider, pair, timeframe, and UTC opening time, with an open/closed marker. TV1 owns the shared Candle contract; TV2 consumes it.
- **Market Selection**: A supported provider, pair, and timeframe combination requested by one or more chart slots.
- **Live Subscription**: The lifecycle of receiving updates for a market selection, including subscribing, active delivery, stale/reconnecting, error, and release.
- **Connection Status**: The user-visible freshness and recovery state for a slot or its shared market selection.

### Traceability and Dependencies

| Feature requirement | SRS source |
|---|---|
| FR-001–FR-003, FR-008–FR-010, FR-013–FR-016 | `MTC-US-01`, `MTC-US-02`, `MTC-FR-01`–`MTC-FR-05`, §5, §6.3 |
| FR-004–FR-007 | `MD-US-02`, `MD-FR-02`–`MD-FR-04`, `MD-FR-06`, `BR-01`, `BR-02`, §6.1 |
| FR-011–FR-013 | `MD-US-03`, `MD-FR-05`, §4.2, §4.6 |
| FR-017–FR-018 | `BR-09`, §1.6, §4.2 |
| NFR-001–NFR-007 | SRS §4–§5 and Constitution PF-03, PF-05, DOD-02, DOD-04–DOD-06 |

- **TV1 / Feature 001** owns historical acquisition, persistence, and the shared Candle/history contract. TV1 and TV2 MUST agree on fields, precision, timestamp/timeframe encoding, completeness, range behavior, and error/version rules before implementation.
- **Acceptance record**: TV1 and TV2 completed that cross-review on 2026-08-19. The accepted version 1 boundary is recorded in Feature 001's consumer contract and this feature's `contracts/openapi.yaml` and `data-model.md`; semantic changes require a new coordinated review.
- **TV3 / Feature 003** consumes normalized candles for strategy work but does not change TV2's base chart contract.
- **TV5 / Feature 005** may compose generic overlays with the base chart; TV2 does not own signal, trade, leaderboard, or provenance behavior.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An analyst can display one, two, three, or four live charts and identify each slot's pair, timeframe, and freshness state without consulting technical logs.
- **SC-002**: At least 95% of accepted realtime updates appear in the correct visible slot within one second of backend ingestion under the documented demo load.
- **SC-003**: In a 30-minute four-chart demonstration, no slot exceeds the four-subscription limit, produces a duplicate candle identity, or moves backward in time.
- **SC-004**: Changing one slot's timeframe leaves every unaffected slot's timeframe, data, connection state, and viewport unchanged in all acceptance runs.
- **SC-005**: After a simulated disconnect with missing closed candles, the affected slot returns to `LIVE` only when the restored sequence contains no gap in the requested display range.
- **SC-006**: All add, remove, timeframe, and retry actions can be completed using only a keyboard, and every connection state remains understandable without color.
- **SC-007**: On a narrow viewport, all active charts remain readable in one column with their selection and recovery controls available.
- **SC-008**: Failure of News or Sentiment leaves historical and realtime market charts usable in every isolation test.

## Assumptions

- The MVP uses one dashboard-level pair, initially `BTCUSDT`; chart slots vary timeframe independently. Per-slot pair selection requires a later approved specification change.
- The analyst explicitly chooses between one and four active slots; no product requirement depends on a fixed default slot count or default timeframe set.
- TV1 provides a versioned historical Candle contract and a bounded display range before TV2 implementation begins.
- Automatic reconnect uses capped exponential backoff with jitter and a finite attempt window; exact timings belong in `research.md` and the public connection-state contract.
- Authentication and account-specific saved layouts are outside the current MVP; the four-slot limit applies to one dashboard session.
- Architecture, ADR-002, and ADR-003 are `Accepted` implementation authorities. The TV1/TV2 Candle/history version 1 boundary is also accepted for this feature.
