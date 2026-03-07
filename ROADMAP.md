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

## Future Research (v2.0)
- **Advanced Parameter Matching**: Evaluate moving `nc` from Red Zone to Yellow with flag-aware regex (distinguish `nc -zv` from `nc -e`).
- **Contextual Learning**: Automated allowlist expansion based on audited "Safe" historical commands.

---
*"Security first. Because you can't control the randomness of an LLM with another random LLM."*
