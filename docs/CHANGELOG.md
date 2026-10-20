# Changelog

Entries below record earlier releases. Their original layer numbering and security
claims are historical, not verification of release 1.4.0. The hardening work
uses L3 for deterministic intent mapping and L4 for semantic review. See
[Verification](VERIFICATION.md) for current results.

## [1.4.0] - 2026-10-20

Adds a first-run path that a new user can follow without a model.

- Added `guardian-lab` with `setup`, `doctor` and a deterministic `demo`.
- Added a release workflow for GHCR images, a Compose file with prebuilt images
  and a checksummed onboarding archive.
- The demo validates five fixed cases, checks the audit delta and the chain, and
  never executes a command.
- Forensic reports now mark unavailable model checks as incomplete instead of
  returning a clean summary.
- Added onboarding and configuration validation tests.

## [1.3.1] - 2026-10-19

Security fixes from an adversarial review:

- Parser denies comment-only input and globs in redirection targets.
- Agent requires HTTP 200 and does not follow redirects with the API key.
- UI returns 503 for malformed nested audit rows instead of a rendered error.
- Forensic annotation keeps unsupported shell commands at high risk.
- Added 172 adversarial regression cases.

## [1.3.0] - 2026-10-19

Introduces the shadow-only System One observer, which records a local model's
assessment of coherence, unauthorized transfer, untrusted instructions and
missing context. The observer cannot change an authorization decision. Its
bundled CPU candidate is quarantined after failing the latency budget on every
calibration case and after a PyTorch advisory and compatibility conflict.

- Added restricted shell parsing and complete command-effect checks.
- Replaced worker-thread regex timeouts with engine-enforced timeouts that deny
  on failure. Required semantic responses now use strict validation.
- Unified audit storage and signing, repaired forensic argument handling, and
  made pattern promotion an operator action.
- Repaired installation and UI access.
- Quarantined the CPU model candidate. Container build and startup were verified
  in a disposable VM and by CI.

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
