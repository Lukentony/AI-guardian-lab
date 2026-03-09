# AI Guardian Lab

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Docker](https://img.shields.io/badge/docker--compose-blue.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)

> [!IMPORTANT]
> **"Security first. Because you can't control the randomness of an LLM with another random LLM."**

---

## 🛡️ Introduction

### ❓ What is it?
I built **AI Guardian Lab** because I realized a fundamental flaw in current AI Agent architectures: we are trusting non-deterministic models to execute deterministic code on our systems. 

An LLM can hallucinate, be manipulated via prompt injection, or simply make a mistake. Trying to "police" one LLM with another LLM just shifts the randomness—it doesn't eliminate it. I designed this project to be a hardened, deterministic proxy that intercepts and validates AI-generated commands **before** they touch your terminal.

### 🏗️ How it works
The Guardian operates a multi-layer validation pipeline. It is intentionally "Fail-Closed"—if any layer is unsure, the command is blocked.

1.  **L1: Binary Allowlist**: I use a zonal policy (`green`, `yellow`, `red`). If a binary isn't explicitly permitted for the current context, it's dead on arrival.
2.  **L2: Regex Pattern Matching**: A dual-path engine checks both raw and normalized commands against known dangerous patterns (obfuscation, exfiltration, ReDoS-safe checks).
3.  **L3: Intent Coherence Mapping**: This is the core differentiator of Guardian Lab. The problem it solves: an LLM can receive a task like *"read the config file"* and, due to hallucination or prompt injection, generate `rm -rf /etc/`. The task says "read". The command says "delete". No regex catches this, because `rm` in isolation might be legitimate in another context.

    Instead of asking another LLM *"does this look right?"* (which reintroduces randomness), L3 maps both the task description and the command to a discrete intent family: `read`, `write`, `delete`, `network`, `execute`, `admin`. The mapping is a deterministic lookup: no model call, no probability, no temperature. If the intents conflict, the command is blocked immediately.
```
    Task:    "check which files are in /tmp"   → intent: read
    Command: "rm -rf /tmp/*"                   → intent: delete

    Result:  BLOCKED — intent mismatch (read ≠ delete)
```

4.  **L4: LLM Semantic Check**: The LLM is my last resort. It's only called when L3 returns `ambiguous`, covering cases where the same binary can legitimately serve multiple intents depending on context. This keeps LLM usage minimal and auditable.

### 🏗️ Architecture
```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent (Python/Gunicorn)
    participant L as LLM (Ollama/Cloud)
    participant G as Guardian (Det. Pipeline)
    participant S as System (Unprivileged Shell)

    U->>A: "Analyze disk usage"
    A->>L: Prompt: "Generate bash command..."
    L-->>A: "rm -rf /"
    A->>G: POST /validate {"command": "rm -rf /", "task": "analyze disk"}
    
    rect rgb(255, 200, 200)
        Note over G: ✅ L1: Binary Allowlist: PASS (rm is in red, but let's say it passed)
        Note over G: ❌ L2: Regex Pattern: BLOCKED (filesystem destruction)
        Note over G: ❌ L3: Intent Mapping: BLOCKED (intent conflict: read vs delete)
    end
    
    G-->>A: Rejected
    A-->>U: Blocked by Security Policy
```

### 🧠 Why determinism first?
I chose to prioritize deterministic checks over LLM-based validation for three reasons:
- **Transparency**: You can audit the regex and the mapping. You know exactly why a command was blocked.
- **Speed**: Deterministic checks take milliseconds and require zero tokens.
- **Reliability**: Logic doesn't "hallucinate." It provides a rigid boundary that the LLM cannot cross.

### 🚀 Quick Start

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

### ⚠️ Threat Model & Limits
I designed AI Guardian Lab as a robust shield, but users must understand its boundaries:
1.  **Regex limitations**: Highly sophisticated obfuscation or polyglots could theoretically bypass patterns.
2.  **Normalization**: While I normalize commands to catch hex/base64 encoding, edge cases in shell syntax are a constant battle.
3.  **Sandbox Environment**: I enforce non-privileged users and resource limits, but the underlying host must be secure.

### 📚 Documentation
- [Architecture & Layers](ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY_POLICY.md)

---

## 📄 License
MIT License. See [LICENSE](LICENSE) for details.
