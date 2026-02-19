# Project Roadmap 🚀

This roadmap outlines the evolution of **AI Guardian Lab** from a security prototype to a production-ready middleware.

## Phase 1: Core Functionality & Integrity ✅
*Goal: Ensure the system actually executes commands and validates them correctly.*
- [x] **Command Execution**: Secure subprocess executor in the Agent.
- [x] **Dual-Path Validation**: Matches patterns against *raw* and *normalized* commands.
- [x] **Functional Audit**: Fixed `/report` and enabled SQLite **WAL Mode**.
- [x] **Agnostic Engine**: Implemented case-insensitive regex matching.

## Phase 2: Operational Robustness ✅
*Goal: Eliminate common failure points like crashes, race conditions, and lack of scale.*
- [x] **Unprivileged Execution**: Services run as non-root users (`agent`/`guardian`).
- [x] **Production Stack**: Gunicorn integration with multi-worker support.
- [x] **Pre-filtering**: Enforced `MAX_COMMAND_LENGTH` (1024 chars).
- [x] **Hardened Rate Limiting**: Standardized on `Flask-Limiter` for both services.
- [x] **Security Test Suite**: `Pytest` suite for logic verification.

## Phase 3: Advanced Sandboxing & Governance ✅
*Goal: Secure the execution environment further and implement dynamic governance.*
- [x] **Resource Guarding**: CPU/Memory limits enforced via Docker.
- [x] **Policy Integration**: Mandatory binary allowlisting from `policy.yaml`.
- [x] **Dynamic Feedback Loop**: Authenticated `/learn` endpoint implemented and verified.
- [x] **Sandboxing**: All containers (Agent, Guardian, UI) run as unprivileged users.

## Phase 4: Maturity & Release 🚀 (Final Polish)
- [ ] **GitHub Release v1.1.1**: Official tag and release documentation.
- [ ] **Repo Cleanup**: Removing legacy `.working` and `.pre-test` files.
- [ ] **Threat Model Verification**: Final confirmation of "Defense in Depth" strategy.

---
*Note: This is a living document. We prioritize security and stability over feature bloat.*
