# Generated Strategy Security and Source Policy

**Status:** Approved  
**Effective date:** 2026-08-23  
**Owner:** Crypto Strategy Lab Security and Product Review  
**Applies to:** Feature 003 LLM-assisted strategy generation, validation, activation, and reuse  
**Architecture decision:** [ADR-006](ADR/ADR-006-llm-generated-strategy-isolation.md)

## 1. Policy Objectives

This policy permits analysts to derive reusable analytical strategies from names, user-supplied text,
and public webpages without treating external content or generated Python as trusted. It protects the
host, credentials, private networks, source rights, reproducibility, and the analysis-only boundary.

The feature MUST fail closed. Missing policy evidence, uncertain source access, failed validation, or
stale confirmation prevents activation. No generated strategy may place, modify, or cancel a real
exchange order.

## 2. Approved Source Classes

| Source | Allowed baseline | Required evidence |
|--------|------------------|-------------------|
| Existing strategy name | Yes | Submitted name, normalized interpretation, assumptions, request fingerprint |
| User-supplied plain text | Yes | Exact content fingerprint and explicit user submission |
| Public webpage | Yes, subject to every control below | Submitted/canonical URL, title/attribution when available, retrieval time, content fingerprint, policy version |
| Authenticated/private webpage | No | Not fetched; user may provide permitted text directly |
| Local file, `file:` URL, private network, metadata endpoint | No | Denial reason only |
| Binary, archive, executable, audio/video, or script-rendered application | No in the baseline | User may provide permitted plain text |

## 3. Web Retrieval Controls

The source adapter MUST:

- accept only `https` on port 443; reject embedded credentials, IP-literal hosts, fragments used as
  commands, and non-public destinations;
- resolve DNS before connection and after every redirect; reject loopback, private, link-local,
  carrier-grade NAT, multicast, reserved, documentation, and cloud-metadata address ranges;
- permit at most three redirects and never forward cookies, authorization headers, client
  certificates, or user-controlled proxy settings;
- use no browser session, JavaScript execution, extension, logged-in state, or ambient system proxy;
- allow only `text/plain`, `text/html`, and equivalent UTF-8 textual responses;
- enforce 10-second connection, 30-second total, 1 MiB decoded-content, and 5 MiB transfer limits;
- reject retrieval when published robots/terms or explicit access signals prohibit automated use;
- remove active markup, forms, scripts, style, hidden executable content, and tracking parameters
  before LLM processing;
- treat retrieved text solely as quoted data. Embedded instructions cannot modify prompts, policy,
  tool permissions, validation, or activation.

DNS rebinding, redirect-to-private-address, decompression-bomb, mixed-content, malformed encoding, and
oversized-response fixtures are mandatory contract tests.

## 4. Rights, Attribution, and Retention

- The system records source title, publisher/author when available, submitted and canonical URLs,
  retrieval time, content fingerprint, and short evidence excerpts supporting extracted rules.
- Evidence excerpts are limited to the minimum needed for review and SHOULD be no longer than 200
  characters each. The UI links to the source instead of reproducing an article.
- Public webpage bodies and user-supplied draft text are encrypted at rest and retained for at most
  30 days unless a shorter environment policy applies. They are then deleted.
- Activated versions permanently retain only the source fingerprint, attribution, URL, minimal rule
  evidence, artifact, structured rules, model/prompt metadata, validation report, and confirmation
  event needed for audit and reproducibility.
- A source with missing required attribution, an explicit no-derivatives/no-automation restriction,
  uncertain permitted use, or a valid deletion/legal hold conflict cannot be activated.
- Deletion removes retained raw source where legally and technically allowed. Immutable experiment
  provenance retains only the minimal non-secret identity/fingerprint necessary to explain historical
  results.

This policy records an engineering baseline, not a legal determination. A deployment subject to
additional jurisdictional or contractual obligations must tighten the policy before use.

## 5. LLM Data Handling

- LLM access is through a provider-neutral application port. Provider credentials remain only in the
  infrastructure adapter and never enter prompts, source snapshots, artifacts, responses, or logs.
- A configured provider MUST contractually/API-configure submitted content as excluded from model
  training and use the minimum available retention. If that guarantee is unavailable, live generation
  is disabled.
- Prompts contain only the minimum source text needed for extraction. Cookies, headers, internal URLs,
  private files, environment values, secrets, and unrelated user data are prohibited.
- Model/provider ID, model version, prompt-template version, generation parameters, and request ID are
  recorded. Hidden system prompts and credentials are not exposed through product APIs.
- Tests use deterministic recorded outputs. Live-provider availability never determines core test
  results.
- Provider timeout, refusal, malformed output, or rate limit leaves a categorized retryable/terminal
  request state and no partial registry publication.

## 6. Generated Artifact Controls

- Model output is data, never directly executable. It first becomes an immutable draft and
  content-addressed artifact.
- Static policy rejects disallowed AST nodes, imports, builtins, reflection, dynamic loading,
  filesystem/network/process/environment/clock/random access, native extensions, serialization
  gadgets, and exchange/order operations.
- Dynamic validation and every later analysis invocation run only in the ADR-006 sandbox with no
  ambient host capability.
- Validation Reports bind exact draft, artifact, Strategy contract, sandbox image, and policy
  fingerprints. A report for different content or an expired/superseded policy cannot activate a
  draft.
- Artifact digest is verified before every load. Mismatch quarantines the version and returns a
  categorized unavailable/integrity failure.
- Logs contain identifiers, fingerprints, policy versions, duration, and result category only; they
  never contain full source, generated code, parameters containing sensitive text, or secrets.

## 7. Review, Activation, and Catalog Scope

- The trusted single-workspace MVP uses a global catalog and does not invent authentication or
  ownership semantics.
- The requester must review the normalized rules, parameters, evidence, explicit assumptions,
  artifact fingerprint, and passing Validation Report, then confirm the exact draft fingerprint.
- A second reviewer is not required for the MVP. Shared/public marketplace publication is outside
  scope and requires an access-control and moderation amendment.
- Activation is atomic and idempotent. Equivalent canonical content resolves the existing executable
  version while retaining request provenance.
- Pending, failed, rejected, archived, quarantined, deprecated-for-execution, or unavailable artifacts
  are not offered to new workflows.

## 8. Incident and Policy Change Handling

- Suspected escape, secret access, integrity mismatch, malicious source, or unsafe artifact immediately
  disables generated-strategy execution while preserving audit records.
- A policy tightening may require revalidation before new execution. Revalidation creates a new report
  and never modifies artifact bytes or historical results.
- Security events record request ID, strategy/version, artifact/report fingerprints, sandbox image,
  policy version, result, and sanitized finding codes.
- Emergency disablement must not affect built-in strategy execution unless the common Strategy
  contract itself is compromised.

## 9. Required Verification

- Source-policy contract suite covering SSRF, redirect, rebinding, encoding, size, content type,
  prompt injection, attribution, and retention.
- Sandbox suite covering every prohibited capability and resource limit in ADR-006.
- Atomic activation and duplicate-content tests using real persistence.
- Restart/reuse test with LLM and source adapters disabled.
- Log and API redaction tests.
- Architecture fitness test proving generated Python is never executed in API/domain/normal worker
  processes.

