# ADR-006: Isolated Validation and Execution for LLM-Generated Strategies

**Status:** Accepted  
**Date:** 2026-08-23  
**Owners:** Architecture and Security Team  
**Extends:** [ADR-002](ADR-002-layered-boundaries.md), [ADR-004](ADR-004-strategy-plugin-and-versioning.md)  
**Policy:** [Generated Strategy Security and Source Policy](../GENERATED_STRATEGY_SECURITY_POLICY.md)

## Context

Feature 003 allows an Analyst to provide a known strategy name, natural-language content, or a
webpage URL. An LLM extracts zero or more structured strategies and generates executable Python logic
that can later be registered and reused. ADR-004 deliberately excluded dynamic or untrusted code and
listed sandboxed loading as a revisit condition.

LLM output and retrieved webpages are untrusted. Running generated Python in the API, worker, or
domain process would expose application memory, credentials, network, filesystem, database, queue,
and process-control capabilities. Static checks alone cannot prove runtime determinism, resource
bounds, or absence of look-ahead behavior.

## Decision

### 1. Separate trusted orchestration from untrusted execution

The modular monolith owns generation requests, source policy, LLM orchestration, structured drafts,
validation reports, confirmation, persistence, and registry publication. Generated Python never runs
inside the API, normal background worker, or domain process.

All generated artifact validation and later execution occur in a dedicated ephemeral
`strategy-sandbox` container/process through a versioned `GeneratedStrategyRuntime` port. The
infrastructure adapter is the only component allowed to start the sandbox runtime.

### 2. Deny capabilities by default

Each sandbox invocation MUST use:

- a non-root user, read-only root filesystem, no host or Docker-socket mounts;
- no network namespace access and no inherited application environment or secrets;
- all Linux capabilities dropped, `no-new-privileges`, a restrictive seccomp profile, and an
  AppArmor/SELinux profile where the host supports it;
- at most 1 CPU, 256 MiB memory, 32 processes/threads, 16 MiB temporary storage, 1 MiB combined
  output, and a 5-second wall-clock timeout per validation or analysis invocation;
- input artifact/context passed through a bounded one-shot channel and output limited to the
  versioned Strategy result/error contract.

The runtime image contains only the Strategy SDK and explicitly approved pure-calculation modules.
It contains no provider SDK, database/queue client, shell, compiler toolchain, package installer, or
application credential.

### 3. Validate before confirmation and activation

An artifact remains non-executable through the Strategy Registry until all checks pass under the
current validation-policy version:

1. structured draft and parameter-schema completeness;
2. Python syntax and AST policy;
3. allowlisted imports/calls and prohibited capability scan;
4. Strategy contract compatibility;
5. generated normal/boundary/invalid/warm-up fixtures;
6. repeated determinism and stable canonical output;
7. no-look-ahead fixtures;
8. sandbox CPU, memory, process, timeout, and output bounds.

The initial import allowlist is `math`, `decimal`, `statistics`, and the read-only Strategy SDK.
Dynamic import, reflection, bytecode loading, native extension loading, file/network/process APIs,
environment access, clocks, implicit randomness, serialization gadgets, and arbitrary builtins are
rejected. Allowlist expansion requires a security-policy version change and review.

### 4. Preserve immutable provenance and exact artifacts

Every artifact is content-addressed with SHA-256 over canonical source plus contract metadata.
Activation atomically stores the exact artifact, structured rules, source fingerprint/attribution,
model and prompt-template versions, validation-policy version/report, and confirmation record before
publishing the generated Strategy Version.

Later analysis resolves the stored exact artifact and verifies its digest. It never calls the LLM or
re-fetches the source implicitly. Changes to source, rules, artifact, model/prompt meaning, or
parameter schema create a new draft and immutable Strategy Version.

### 5. Keep the common Strategy contract

After activation, built-in and generated strategies expose the same Strategy Definition, parameter,
Signal, error, lifecycle, and provenance contracts. Downstream Backtester, Evaluator, Search,
Composite, and Leaderboard code MUST NOT branch on concrete strategy names or generated origin.

Origin remains visible for audit. A stricter future security policy MAY suspend new execution until
the unchanged artifact is revalidated; it MUST NOT rewrite or delete historical provenance.

### 6. Require explicit confirmation

For the trusted single-workspace MVP, the requester is the only required confirmer. There is no
invented RBAC model. A draft can activate only when its exact draft/artifact fingerprints match the
reviewed values and its current Validation Report is `PASSED`. Shared or multi-user catalogs require
a future access-control amendment before adding reviewer roles.

## Alternatives Considered

- **In-process `exec` or dynamic import:** rejected because Python language restrictions are not a
  security boundary and resource failure would affect the API/worker.
- **Static analysis only:** rejected because it cannot prove contract behavior, determinism,
  look-ahead safety, or resource bounds.
- **WebAssembly-only strategy language:** stronger isolation but conflicts with the approved Python
  strategy requirement and adds a second strategy SDK/runtime.
- **Human code review without sandboxing:** useful as an additional control but neither deterministic
  nor sufficient for runtime containment.
- **Permanent sandbox service with broad connectivity:** operationally convenient but increases
  lateral-movement and cross-request state risk.

## Consequences

### Positive

- Generated artifacts cannot directly access application secrets or infrastructure.
- Built-in and generated strategies remain substitutable after activation.
- Exact artifact and provenance make later workflows reproducible without LLM availability.
- Failed validation and sandbox termination cannot partially publish a registry entry.

### Negative

- Container startup and validation add latency and operational complexity.
- The restricted Python subset cannot represent every named trading concept.
- OS-specific hardening must be verified in CI and deployment, not assumed from local Docker alone.
- Validation reduces risk but does not prove trading correctness or profitability.

## Validation

- Contract tests submit artifacts attempting network, filesystem, environment, process, reflection,
  dynamic import, secret access, infinite loop, memory growth, output flood, nondeterminism, and
  look-ahead; none becomes available in the registry.
- Runtime tests assert the documented CPU, memory, PID, timeout, output, filesystem, privilege, and
  network limits.
- Restart tests disable source and LLM adapters and reproduce an activated generated strategy from
  its stored artifact and provenance.
- Architecture tests fail if API/domain code executes generated source directly or if sandbox code
  imports application infrastructure.
- Downstream fitness tests consume built-in and generated strategies through one contract without an
  origin-specific branch.

## Revisit When

- The contract needs multi-asset, stateful, GPU, native-extension, or model-inference strategies.
- Measured sandbox startup cost violates approved generation/backtest targets.
- The project introduces authenticated multi-user ownership or a shared public strategy marketplace.
- A stronger portable isolation technology can replace containers without weakening the controls.

