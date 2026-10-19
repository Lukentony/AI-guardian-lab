# Changelog

Entries below record earlier releases. Their original layer numbering and security
claims are historical, not verification of the current branch. The hardening work
uses L3 for deterministic intent mapping and L4 for semantic review. See
[Verification](VERIFICATION.md) for current results.

## Unreleased hardening branch

- Added restricted shell parsing and complete command-effect checks.
- Replaced worker-thread regex timeouts with engine-enforced timeouts that deny
  on failure. Required semantic responses now use strict validation.
- Unified audit storage and signing, repaired forensic argument handling, and
  made pattern promotion an operator action.
- Repaired installation and UI access. Added a shadow-only System One client.
- Quarantined the CPU model candidate after latency and dependency-security
  checks failed. Container verification remains pending.

## [1.2.0] - 2026-03-06

Added deterministic task/command mapping and semantic review for ambiguous cases,
then labelled L4 and L5. Added `intent_source` values `mapping`, `llm` and `skip`.
Removed a hardcoded private Ollama address and fixed Gunicorn-relative imports.
Added pytest and tests to the Guardian build at that time; the current branch
keeps pytest in development requirements instead.

## [1.1.4] - 2026-03-05

Fixed invalid `.*??` quantifiers produced by `safe_compile()` when a pattern
already contained `.*?`. The release recorded five patterns restored at startup.
The current engine does not rewrite regex semantics this way.

## [1.1.3] - 2026-02-19

Addressed dynamic-learning validation crashes (BUG-01), learned-pattern persistence
(BUG-02) and malformed Agent JSON (BUG-03). Introduced shlex-based chained-binary
checks (BUG-04), worker/concurrency changes (BUG-05) and reduced health-endpoint
information (BUG-06). Later inspection found further gaps; these entries do not
establish that those mechanisms were complete.

## [1.1.2] - 2026-02-19

Added subprocess execution markers, changed normalization and pattern-check order,
updated report handling and configured fail-closed policy defaults.

## [1.1.1] - 2026-02-14

Corrected version naming and removed development artifacts. Added zonal binary
allowlisting, Compose resource limits of 0.5-0.75 CPU and 256 MB-1 GB at that
revision, and JSON security logs.

## [1.1.0] - 2026-02-18

Added Flask-Limiter with a recorded 60 requests/minute limit, API authentication
and LiteLLM provider integration. The release used a one-second worker-thread
regex timeout. That wrapper did not establish cancellable regex execution;
the hardening branch replaces it with an engine timeout.
