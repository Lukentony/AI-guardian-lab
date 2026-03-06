# System Architecture

## Design Philosophy

> **"Security first. Because you can't control the randomness of an LLM with another random LLM."**

I built this project to prove that security in AI Agents should be deterministic, not just another layer of probabilistic matching. By enforcing strict boundaries, I ensure that no matter how much an LLM hallucinations or deviates, the system remains protected.

## Security Stack (Defense-in-Depth)

1. **L1 — Sandbox Isolation**: Containers run as non-privileged users with strict resource limits (cgroups). If a command breaks through the software layers, it's still trapped in a restricted environment.
2. **L2 — Zonal Enforcement**: A fail-closed binary allowlist governed by `policy.yaml`. I define `green`, `yellow`, and `red` zones to prevent unauthorized tool execution.
3. **L3 — Content Analysis**: A dual-path regex engine that analyzes both raw and normalized commands to catch obfuscation (hex, base64, etc.) with ReDoS-safe timeouts.
4. **L4 — Intent Coherence Mapping**: A deterministic layer that classifies the task and the command into intent families (e.g., `read`, `write`, `network`). It blocks conflicting intents without any LLM intervention.
5. **L5 — LLM Semantic Check**: I only call the LLM for ambiguous cases that L4 can't resolve, providing a final semantic safety net.
6. **L6 — Audit & Redaction**: All decisions are logged using WAL-enabled SQLite, with real-time masking to redact secrets before they hit the disk.

## Data Flow

1. **User → Agent**: Request execution of a task.
2. **Agent → LLM**: Prompt engineering for command generation.
3. **Agent → Guardian**: Validation request for the generated command and task description.
4. **Guardian Pipeline**: 
    - **Allowlist Check**: Verify the binary is permitted.
    - **Regex Check**: Normalize and scan for dangerous patterns.
    - **Intent Check**: Classify the task and command into intent families.
    - **Conflict Resolution**: If families conflict, block immediately.
    - **LLM Fallback**: If classification is ambiguous, call L5 for a semantic check.
5. **Agent Execution**: Execute in an unprivileged sandbox if (and only if) approved.
6. **Audit**: Log the full decision path, including the `intent_source` ("mapping", "llm", or "skip").

## Endpoints

### Guardian (Port 5000)
- `GET /health` - Liveness check.
- `POST /validate` - The core security pipeline. I inspect `command` and `task`.
- `POST /report` - Structured audit logging for external reports.

### Agent (Port 5001)
- `POST /execute` - The main task entrypoint.
- `GET /health` - Liveness check.

---

*"Security and stability over feature bloat."*
