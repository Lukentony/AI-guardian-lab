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

## Phase 4: Intent Governance & Benchmarking ✅
*Goal: Ensure task/command coherence and measure validation performance.*
- [x] **Intent Coherence Layer**: Deterministic mapping (L3) and LLM fallback (L4).
- [x] **Benchmarking Suite**: Real-world dataset for Precision/Recall measurement (100% score).
- [x] **Automatic DB Init**: Container-native `entrypoint.sh` for zero-setup deployment.

## Phase 5: Forensics & Behavior Analysis (v2.0 — in design)

*Goal: Evolve Guardian from a runtime enforcement layer into a behavior analysis platform for AI agents.*

The next evolution of Guardian addresses a structural limitation of runtime enforcement: agent frameworks block calls to private IPs by design (SSRF protection), making automatic pre-execution interception unreliable across all frameworks.

The forensics approach sidesteps this constraint entirely by operating post-mortem on session logs rather than intercepting live calls.

### Planned capabilities

- **Session Parser**: Ingest agent session logs from any framework (OpenClaw, LangChain, AutoGPT, custom) and extract structured `AgentStep` sequences
- **Intent Drift Detection**: Identify when an agent's actions deviate from its declared task over the course of a session
- **Tool Escalation Analysis**: Flag sequences where tool usage escalates from read → write → execute without explicit user authorization
- **Prompt Injection Signals**: Detect linguistic patterns in tool inputs that suggest injection attempts
- **Structured Reports**: Generate per-session audit reports with risk scores, flagged steps, and evidence

### Design principles

- Framework-agnostic: analyzes logs, does not require SDK integration
- Offline-capable: no external API calls required for deterministic analysis layers
- Composable: each analysis module is independent and can be used standalone

### Attack corpus

The [`attack-corpus/`](attack-corpus/) directory contains categorized real-world attack scenarios used for regression testing and to document Guardian's detection surface. It will serve as the foundation for the forensics module's training and validation dataset.

---

*"Security first. Because you can't control the randomness of an LLM with another random LLM."*

