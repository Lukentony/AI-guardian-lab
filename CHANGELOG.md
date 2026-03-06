# Changelog

## [1.2.0] - 2026-03-06
### Added
- **Security**: Added Layer 3: Intent Family Mapping deterministico — classifica task e command in famiglie di intento, blocca i conflitti senza chiamare LLM.
- **Security**: Aggiunto Layer 4: LLM check con deepseek-coder-v2:16b via Ollama per i casi ambigui non classificabili dal mapping.
- **Pipeline fail-fast**: i nuovi layer entrano solo se regex e policy approvano.
- **intent_source nella risposta API**: "mapping", "llm", o "skip" per audit e debug.
- Aggiunto `CLEANUP_NOTES.md` per refactoring futuro.

### Fixed
- Fix: import `intent` invece di `from . import intent` in `main.py`
- Fix: `COPY guardian/intent.py` aggiunto al Dockerfile.

## [1.1.4] - 2026-03-05
### Fixed
- **Critical**: Fixed `safe_compile()` producing invalid `.*??` double quantifiers when patterns already contained non-greedy `.*?`. Replaced naive `str.replace` with `re.sub` using negative lookahead, plus a sanitization pass. Restores 5 previously broken security patterns at startup.

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
