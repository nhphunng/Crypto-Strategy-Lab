# Implementation Plan: Crypto Strategy Lab Frontend System

**Branch**: `001-frontend-prototype-system` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-frontend-prototype-system/spec.md`

## Summary

Build the seven-screen Crypto Strategy Lab reference as a production-shaped frontend prototype. The system will preserve the source mock's dark, information-dense 1440×900 workspace while replacing page-owned fixture imports and scattered literals with typed domain records, declarative configuration, shared UI primitives, feature-level state, and injected service gateways. Deterministic mock adapters will power complete interactions now; later HTTP/WebSocket adapters can implement the same ports without rewriting pages.

## Technical Context

**Language/Version**: TypeScript 5.7+, React 19.2

**Primary Dependencies**: Vite, Tailwind CSS v4, React Router, lucide-react, local font packages for Inter and JetBrains Mono

**Storage**: Browser storage adapter for explicit preferences only; no application database in this feature

**Testing**: Vitest, React Testing Library, user-event, jest-dom, existing Node Sites worker test, browser interaction and visual QA in the Codex in-app browser

**Target Platform**: Modern evergreen desktop browsers; primary viewport 1440×900, supported compact desktop/tablet width 1024px+

**Project Type**: Client-side web application prototype with future backend integration boundaries

**Performance Goals**: Initial workspace becomes interactive within 2 seconds on a typical development machine; user actions visibly respond within 100ms; chart and progress animation remain visually smooth

**Constraints**: Preserve bundled Sites worker/build files; no real trading, authentication, persistence backend, or invented future API endpoints; maximum four chart slots; no document-level horizontal overflow at supported viewports; WCAG 2.2 AA interaction patterns

**Scale/Scope**: Seven top-level destinations, one persistent workspace shell, up to four chart panes, dozens of deterministic domain records, six service gateway groups, and core responsive states at 1440, 1180, and 1024 widths

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

The nested project has no project-specific constitution yet, so there are no additional constitutional MUST rules to evaluate. The following binding gates come from the feature specification and target `AGENTS.md`:

- **PASS — Source fidelity**: The supplied mock and design tokens remain the visual source of truth.
- **PASS — Integration readiness**: Pages depend on gateway interfaces and normalized domain models, never fixture arrays or transport DTOs.
- **PASS — Reuse**: Shared visual/interaction patterns are implemented once and consumed across feature modules.
- **PASS — Accessibility**: Primary controls are named, keyboard reachable, stateful, and visibly focusable; dialogs and drawers manage focus.
- **PASS — Runtime preservation**: Sites worker, hosting preparation, and worker tests remain intact.
- **PASS — Bounded prototype scope**: Real trading, backend mutation, authentication, and speculative API routes stay out of scope.

Post-design re-check: **PASS**. The data model, gateway contract, and tasks preserve all six gates. No complexity exception is required.

## Architecture Decisions

1. **Feature-sliced React SPA**: a thin app layer composes route, service, and workspace providers; feature folders own page-specific reducers and orchestration.
2. **Injected gateway ports**: mock adapters implement the same UI-facing contracts that future HTTP/WebSocket adapters will implement.
3. **Three state scopes**: route state lives in URLs, durable workspace selections live in a workspace provider/storage adapter, and page workflow state lives in feature reducers/hooks.
4. **Declarative domain configuration**: navigation, method schemas, parameter constraints, status metadata, table columns, layout presets, metrics, and landing content are data-driven.
5. **Normalized async resources**: shared resource states represent loading, success, empty, error, live, stale, reconnecting, partial, and degraded states consistently.
6. **Presentational chart boundary**: charts accept candles, overlays, markers, dimensions, and interval as inputs; data generation, normalization, and indicators remain outside the chart.

## Project Structure

### Documentation (this feature)

```text
specs/001-frontend-prototype-system/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── frontend-services.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
├── app/
│   ├── App.tsx
│   ├── routes.tsx
│   └── providers/
├── components/
│   ├── data-display/
│   ├── feedback/
│   ├── layout/
│   └── ui/
├── config/
├── domain/
├── features/
│   ├── backtests/
│   ├── landing/
│   ├── leaderboard/
│   ├── market/
│   ├── news/
│   ├── operations/
│   └── strategy-builder/
├── services/
│   ├── mock/
│   │   ├── fixtures/
│   │   └── generators/
│   ├── ports.ts
│   └── registry.tsx
├── shared/
│   ├── backtests/
│   ├── charts/
│   ├── hooks/
│   ├── market/
│   ├── provenance/
│   └── utils/
├── test/
│   ├── contracts/
│   ├── integration/
│   └── unit/
├── theme/
│   ├── globals.css
│   └── tokens.css
└── main.tsx

tests/
└── sites-worker.test.mjs
```

**Structure Decision**: A single frontend project is used because the requested change is confined to `CryptoStrategy`. Domain contracts and service ports isolate future backend transport concerns, while feature folders keep each of the seven workflows cohesive. The existing repository-level backend is not copied or coupled into this project.

## Delivery Phases

### Phase 0 — Research

- Confirm architecture, state ownership, service boundaries, source design tokens, and validation strategy.
- Record current backend capability versus contract-only and missing integrations.

### Phase 1 — Design and Contracts

- Define normalized frontend entities and lifecycle states.
- Define gateway contracts, adapter responsibilities, and mock behavior.
- Define the end-to-end validation quickstart.

### Phase 2 — Foundation

- Align the bootstrapped project with TypeScript, Tailwind, fonts, icons, routing, tests, and design tokens.
- Implement app providers, service registry, reusable UI primitives, shell, and shared feedback states.

### Phase 3 — Primary Journeys

- Implement Market and Strategy Builder with independent chart panes, catalog-driven strategy configuration, validation, review, and backtest handoff.

### Phase 4 — Evaluation Journeys

- Implement Single Backtest, Strategy Search, Runs, and Leaderboard with shared tables, metrics, provenance, and detail drawers.

### Phase 5 — Supporting Journeys and Polish

- Implement Landing, News & Sentiment, and Operations; complete compact-width behavior, accessibility, deterministic tests, and design QA.

## Complexity Tracking

No constitution or specification violations require complexity justification.
