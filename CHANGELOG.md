# Changelog

## [1.1.0] - 2026-02-18

### Added
- **SEC-02 (Rate Limiting)**: Standardized rate limiting using `Flask-Limiter` in the Guardian service (60 req/min).
- **SEC-03 (ReDoS Protection)**: Real-time regex timeouts (1.0s) implemented using `ThreadPoolExecutor` to prevent Denial of Service attacks.
- **SEC-01 (Hardened Auth)**: Fail-closed authentication in both Agent and Guardian — requests are rejected with 401 if `API_KEY` is not set.
- **SEC-03 (Better Normalization)**: Expanded `normalize_command()` to handle hex encoding (`xxd`), subshell expansions (`$()`, `` ` ``), and `$IFS` variants.

### Fixed
- **SEC-03 (Regex Patterns)**: Replaced greedy `.*` quantifiers with non-greedy `.*?` in `patterns.yaml` to prevent catastrophic backtracking.
- **SEC-04 (Secrets Masking)**: Added `mask_secrets()` to `audit_logger.py` to prevent sensitive data from being stored in the database.
- **SEC-05 (Sudo Bypass)**: Removed `^` anchor from sudo patterns, allowing detection of privilege escalation even when used mid-command.
- **SEC-05 (Hardened Audit)**: Logged reasons now use pattern categories instead of raw regex strings to prevent logging injection.
- Removed debug `print` statements in the Agent that leaked API key prefixes.
- Aligned dependency versions across all services (Flask 3.0.3, litellm 1.44.6).

### Security
- Comprehensive security hardening across the entire stack, mitigating identified CVSS 9.8 (Critical) and HIGH severity vulnerabilities.
