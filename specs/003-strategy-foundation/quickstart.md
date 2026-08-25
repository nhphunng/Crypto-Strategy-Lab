# Quickstart: Validate Strategy Foundation

This guide validates the seven independently demonstrable Strategy Foundation stories after implementation. It uses deterministic model/source fixtures, never executes an unvalidated generated artifact, and does not place trades or calculate backtest results.

## Prerequisites

- Docker Desktop with Compose
- Backend dependencies locked for Python 3.12
- PostgreSQL 16 available through the project Compose environment
- Normalized-market-data contract from Feature 001, or its deterministic contract fixture
- TV3 fixture pack containing:
  - MA normal, cross-above, cross-below, equality, warm-up, empty, invalid-period, and insufficient-history cases;
  - RSI normal, threshold exit, equality, constant-price, gains-only, losses-only, warm-up, invalid-period/threshold, and insufficient-history cases;
  - unsorted, duplicate, incomplete, invalid-OHLCV, open, future, and misaligned Strategy Context cases;
  - compatible, duplicate, invalid-metadata, deprecated, unavailable, and incompatible registry/version cases;
  - one generic compliant test strategy used only for extensibility.
  - strategy-name fixtures covering known, unknown, misspelled, ambiguous, and canonically equivalent concepts;
  - direct-text and webpage snapshots containing zero, one, and multiple strategies, contradictory rules, missing evidence, prompt injection, and unsupported content;
  - generated artifacts covering prohibited imports/calls, syntax errors, contract failures, nondeterminism, look-ahead, timeout, memory/output bounds, and a fully valid reusable strategy;
  - deterministic recorded LLM responses; live model output is not part of acceptance assertions.

Contracts: [REST OpenAPI](contracts/openapi.yaml) and [TV4 domain contract](contracts/strategy-domain-contract.md).

## 1. Start the Required Environment

```bash
docker compose -f docker-compose.yml up -d postgres
```

Install the locked backend dependencies, apply migrations, and load deterministic normalized Candle fixtures using the repository commands established during implementation. Provider/network data must not be used for acceptance assertions.

### Secure generated-strategy deployment

Live generation uses the additive `docker-compose.generated.yml` profile. It requires file-backed
Docker secrets for the provider credential and 256-bit source/artifact wrapping key, an explicit
provider data-policy acknowledgement, a persistent encrypted-artifact volume, and the dedicated
credentialless sandbox Docker Engine. The API MUST NOT mount the host Docker socket.

The deterministic US5–US7 E2E profile adds `docker-compose.e2e.yml`, whose LLM fixture implements the
same provider-neutral structured-output boundary without a live provider. Start all three Compose
files, then run the opt-in E2E test:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.generated.yml \
  -f docker-compose.e2e.yml \
  up --build -d

CSL_RUN_GENERATED_E2E=1 pytest -q \
  backend/tests/e2e/test_generated_strategy_user_stories.py -s
```

Expected: name generation yields one passing reviewable draft; natural-language content yields two
independent drafts; exact confirmation activates the strategy; catalog discovery returns it before
and after API restart; protected request bytes and stored artifact files contain no plaintext source
or Python artifact.

## 2. Run Automated Quality Gates

```bash
cd backend
ruff check src tests
mypy src
pytest \
  tests/unit/strategy \
  tests/contract/test_strategy_contract.py \
  tests/contract/test_strategy_api.py \
  tests/contract/test_strategy_extensibility.py \
  tests/integration/test_strategy_definition_repository.py \
  tests/integration/test_strategy_analysis_api.py
```

After generated-strategy implementation is included, also run:

```bash
pytest \
  tests/contract/test_generated_strategy_sandbox.py \
  tests/contract/test_strategy_source_access.py \
  tests/integration/test_strategy_source_retention.py \
  tests/contract/test_generated_strategy_activation.py
cd ../frontend
npm test -- --run src/test/unit/generated-strategy-review.test.tsx
```

Expected: all tests pass, repeated fixtures are identical, and no test accesses a live provider.

Before running generated-strategy suites, verify the binding baselines exist: SRS 0.2 (`SP-US-04..06`, `SP-FR-06..20`), Accepted ADR-006, updated Architecture and Approved `docs/GENERATED_STRATEGY_SECURITY_POLICY.md`. A missing or weakened control is a test failure, never a bypass.

## 3. Validate `SE-US-01`: Run MA and RSI

1. Analyze the MA fixture with omitted `period`; confirm effective period 20 and one Signal per Candle.
2. Analyze explicit periods 2 and 500; confirm both boundaries are accepted.
3. Analyze period 1, 501, a non-integer, and an unknown parameter; confirm `INVALID_PARAMETERS` and zero Signals.
4. Inspect cross-above, cross-below, and equality fixtures; confirm BUY, SELL, and HOLD follow the specified strict boundaries.
5. Repeat steps 1–4 for RSI defaults 14/30/70 and valid period boundaries 2/200.
6. Confirm invalid thresholds, equal/reversed thresholds, constant prices, gains-only, and losses-only match the fixture outcomes.
7. Run empty and insufficient-history inputs; confirm `EMPTY` with zero Signals and `INSUFFICIENT` with one warm-up HOLD per supplied Candle.
8. Run the same complete fixtures at least 10 times; compare canonical results including Signal IDs, ordering, actions, phase, and reasons.

Expected: 100% identical repeated results, explicit warm-up, and no future Candle dependency.

## 4. Validate `SE-US-02`: Inspect Signals

1. Inspect any MA and RSI result and confirm exact Strategy Definition, parameters, dataset ID/version, context fingerprint, pair, timeframe, range, and decision timestamp.
2. Confirm each Signal timestamp equals its source Candle timestamp and sequence positions are contiguous.
3. Confirm action is only BUY, SELL, or HOLD and phase is WARMUP or EVALUATED.
4. Combine two result sequences that share timestamps and apply the documented cross-result ordering key.
5. Submit unsorted, duplicate, incomplete, invalid-OHLCV, open, future, and misaligned contexts.

Expected: valid Signals are fully traceable; invalid contexts return `INVALID_CONTEXT`, all issues are readable, and zero partial Signals are returned.

## 5. Validate `SP-US-01` and `SP-US-03`: Register and Discover

1. Start the application with built-in registration and request `GET /api/v1/strategies`.
2. Confirm MA and RSI use the same metadata shape and deterministic order.
3. Resolve each exact version and inspect its parameter definition, defaults, ranges, contract version, status, and capabilities.
4. In contract tests, attempt duplicate, invalid-metadata, invalid-parameter-schema, and incompatible registrations.
5. Register the generic compliant test strategy and repeat discovery/analysis without changing Backtester, Evaluator, or Leaderboard files.

Expected: invalid registration leaves all prior strategies usable; the generic strategy works through the common contract with no strategy-name branch downstream.

## 6. Validate `SP-US-02`: Immutable Versions

1. Create or resolve a Strategy Definition, record its ID and content fingerprint, and reference it from a historical fixture.
2. Repeat with identical canonical content; confirm the same definition resolves idempotently.
3. Change parameters; confirm a distinct immutable definition ID while the original remains unchanged.
4. Register a new behavior version; confirm the historical definition still resolves the original strategy version.
5. Request unknown, unavailable, deprecated, and incompatible versions for new analysis.

Expected: distinct categorized errors, no latest-version fallback, deprecated metadata remains historically resolvable, and all old definition content is unchanged.

## 7. Validate TV4 Contract

1. Give TV4's contract test an exact Strategy Definition and immutable Strategy Context rather than a concrete MA/RSI object.
2. Consume the resulting ordered Signals through the shared domain contract.
3. Repeat with MA, RSI, and the generic compliant strategy.
4. Search TV4 Backtester, Evaluator, and Leaderboard code for concrete strategy names.

Expected: all three strategies are consumed through one contract and no MA-, RSI-, or generic-strategy-specific branch exists downstream.

## 8. Benchmark and Architecture Fitness

Run the 10,000-Candle MA and RSI benchmark fixture on the documented reference environment. Record Python version, CPU, memory, fixture fingerprint, repetitions, and p95 duration.

Expected: each strategy completes in linear time with p95 below 1 second, repeated output remains identical, and calculation performs no database, HTTP, queue, provider, clock, or random access.

## 9. Validate `SP-US-04`: Generate from a Strategy Name

1. Submit a fixture name with one supported interpretation and confirm one structured non-executable draft is produced.
2. Inspect rules, parameters, assumptions, source/generation provenance, artifact fingerprint, and validation findings.
3. Submit ambiguous and misspelled names; confirm selection or `STRATEGY_INTENT_UNRESOLVED` occurs before activation.
4. Run the valid artifact through all required isolated validators, confirm it, and verify atomic registry publication.
5. In the Strategies UI, inspect exact rules, evidence, assumptions, draft/artifact fingerprints and Validation Report; confirm that failed or stale drafts cannot be submitted.
6. Submit an equivalent name/rule fixture and confirm the existing content-addressed version is resolved without duplicating executable behavior.

Expected: only the confirmed passing artifact becomes available; ambiguous, failed, and duplicate cases have explicit outcomes and leave the prior registry unchanged.

## 10. Validate `SP-US-05`: Extract from Text or Web Content

1. Submit direct text containing one strategy and verify every rule has source evidence or an explicit assumption.
2. Submit a snapshot containing multiple strategies; confirm separate draft identities and independent validation/rejection/activation.
3. Submit irrelevant, contradictory, and materially incomplete content; confirm zero executable output and readable review blockers.
4. Exercise URL policy fixtures for private destinations, prohibited redirects, unsupported schemes/media, oversized content, timeout, and missing attribution.
5. Include prompt-injection text instructing the system to bypass policy; confirm policy, tool access, validation, and activation behavior remain unchanged.
6. Persist a permitted raw-source fixture, verify only encrypted payload/ciphertext is stored, advance the retention clock to the 30-day boundary, run the purge use case, and confirm raw content/key reference is cleared while attribution, URL, fingerprint and minimal activated evidence remain.

Expected: extraction is evidence-backed and failure-isolated; source access and prompt injection cannot create or activate unsafe behavior.

## 11. Validate `SP-US-06`: Persist and Reuse Generated Strategies

1. Activate one passing generated draft and record its definition, artifact, validation-report, and provenance identities.
2. Restart the application with model/source adapters disabled; discover and analyze the exact version.
3. Pass it through the TV4 fixture and one later-workflow contract without origin-specific logic.
4. Revise a rule or artifact; confirm a new immutable version and unchanged historical resolution.
5. Change model/prompt/validation fixture versions and confirm the old activated behavior does not regenerate or drift.

Expected: the exact generated version survives restart and environmental evolution, remains reusable through the common Strategy contract, and retains complete immutable provenance.

## 12. Validate Generated-Code Isolation

Build the `strategy-sandbox` service from `infra/compose.yaml`, verify its effective user, mounts,
network, capabilities, no-new-privileges, seccomp/AppArmor and resource limits, then run hostile
artifacts individually: forbidden network/filesystem/process/environment access, secret reads,
dynamic imports, infinite loop, memory growth, output flood, nondeterminism, future-data access, and
process escape attempts.

Expected: every hostile fixture is rejected or terminated within approved limits, produces a structured Validation Report, exposes no secret or host capability, and never changes the active registry. Exact commands and limits must come from the Accepted isolation ADR rather than this guide inventing them.

```bash
docker compose -f infra/compose.yaml --profile strategy-sandbox-build-only build strategy-sandbox
```

On an AppArmor-enabled Linux host, install the reviewed profile with
`sudo infra/security/install-strategy-sandbox-apparmor.sh` and set
`CSL_STRATEGY_SANDBOX_APPARMOR_PROFILE=crypto-lab-strategy-sandbox`. On hosts without AppArmor,
leave that setting unset; seccomp, network, filesystem, user, capability, process, CPU, memory, and
timeout controls remain mandatory.

## Acceptance Summary

| Story | Pass signal |
|-------|-------------|
| `SE-US-01` | MA/RSI normal, boundary, warm-up, invalid, and repeated fixtures all match exact outcomes. |
| `SE-US-02` | Every Signal is ordered, aligned, categorized, and traceable; bad contexts yield no partial output. |
| `SP-US-01` / `SP-US-03` | MA, RSI, and a generic strategy register/discover uniformly; failure is atomic. |
| `SP-US-02` | Historical definitions remain immutable/resolvable and version-state errors never fall back. |
| TV4 contract | TV4 consumes every compliant strategy without concrete-strategy behavior. |
| `SP-US-04` | Specific names yield validated reviewable drafts; ambiguity and failures never activate silently. |
| `SP-US-05` | Text/URL sources yield zero-to-many evidence-backed independent drafts under source-access policy. |
| `SP-US-06` | Confirmed generated versions persist, remain immutable, and work in later workflows without regeneration. |
| Isolation | Hostile generated artifacts remain contained and unavailable to the active registry. |
