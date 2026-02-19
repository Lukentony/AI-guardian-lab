# AI Guardian Lab - Roadmap

## Phase 1: Core Content Safety ✅
*Goal: Protect against basic injection and malicious payloads.*
- [x] **Regex-based filtering**: Blocking known dangerous commands.
- [x] **LiteLLM Integration**: Support for 100+ LLM providers.
- [x] **Dual-Language Support**: Documentation in English and Italian.
- [x] **Audit Database**: Logging every command and task to SQLite.
- [x] **Secret Masking**: Redacting API keys and tokens from logs.

## Phase 2: Operational Robustness ✅
*Goal: Eliminate common failure points like crashes, race conditions, and lack of scale.*
- [x] **Unprivileged Execution**: Services run as non-root users (`agent`/`guardian`).
- [x] **Production Stack**: Gunicorn integration with multi-worker support.
- [x] **Pre-filtering**: Enforced `MAX_COMMAND_LENGTH` (1024 chars).
- [x] **Hardened Rate Limiting**: Standardized on `Flask-Limiter` for both services.
- [x] **Security Test Suite**: `Pytest` suite for logic verification.

## Phase 3: Advanced Sandboxing & Governance ✅
*Goal: Establish strict boundaries and adaptive security.*
- [x] **Zonal Allowlisting**: Strict binary zones (Green/Yellow/Red) in `policy.yaml`.
- [x] **Resource Quotas**: Hard CPU and Memory limits via Docker Compose.
- [x] **Fail-Closed State**: Default reject policy for unknown binaries.
- [x] **V1.1.2 Hardening**: Resolved normalization bypasses and and proof of execution.

## Phase 4: Enterprise Readiness 🚀
*Goal: Monitoring, scaling, and team collaboration.*
- [ ] **Real-time Monitoring**: Dashboard for security events and performance.
- [ ] **SIEM Integration**: Export logs to external platforms (ELK, Splunk).
- [ ] **Capability Whitelisting**: Move beyond binary matching to flag-level control.
- [ ] **Multi-tenant Auth**: JWT-based separation for teams.

---
*"Security and stability over feature bloat."*
