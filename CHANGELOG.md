# Changelog

## [1.1.3] - 2026-02-19
### Fixed
- **Critical**: Resolved `ValueError` crash in `/validate` triggered by dynamic pattern learning (BUG-01).
- **Critical**: Fixed `/learn` persistence by moving learned patterns to a writable volume (BUG-02).
- **Critical**: Hardened Agent against DoS via malformed JSON (BUG-03).
- **Critical**: Re-engineered allowlist logic with `shlex` to detect chained binaries in pipes/concatenations (BUG-04).
- **Performance**: Optimized `ThreadPoolExecutor` with core-scaling and concurrency semaphores (BUG-05).
- **Security**: Hardened `/health` endpoint against information disclosure (BUG-06).

## [1.1.2] - 2026-02-19
### Fixed
- **Critical**: Added explicit execution markers to Agent container logs for subprocess validation.
- **Critical**: Re-architected normalization vs. pattern matching sequence in Guardian to prevent "Normalization Stripping" bypasses.
- **Critical**: Verified and hardened `/report` endpoint for external audit logging.
- **Security**: Reinforced Fail-Closed defaults in `policy.yaml`.

## [1.1.1] - 2026-02-14
### Fixed
- Corrected release version naming (v1.1.1 patch).
- Cleaned up legacy development artifacts from GitHub repository.

### Added
- **Zonal Enforcement (SEC-03b)**: Strict binary allowlisting via `policy.yaml`. Blocks any command not explicitly permitted.
- **Resource Sandboxing**: CPU (0.5-0.75) and Memory (256MB-1GB) limits enforced per container in `docker-compose.yml`.
- **Advanced Audit**: JSON-formatted structured logging for all security decisions.

## [1.1.0] - 2026-02-18

### Added
- **SEC-02 (Rate Limiting)**: Standardized rate limiting using `Flask-Limiter` in the Guardian service (60 req/min).
- **SEC-03 (ReDoS Protection)**: Real-time regex timeouts (1.0s) implemented using `ThreadPoolExecutor` to prevent Denial of Service attacks.
- **SEC-01 (Hardened Auth)**: Fail-closed authentication in both Agent and Guardian — requests are rejected with 401 if `API_KEY` is not set.
- **Universal Provider Support**: Full integration with LiteLLM for Ollama, OpenAI, Groq, and DeepSeek.

---
*"Security and stability over feature bloat."*
