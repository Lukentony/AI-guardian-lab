# AI Guardian Lab

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Docker](https://img.shields.io/badge/docker--compose-blue.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)

> [!IMPORTANT]
> **"Security first. Because you can't control the randomness of an LLM with another random LLM."**

---

# AI Guardian Lab

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Docker](https://img.shields.io/badge/docker--compose-blue.svg)
![Status](https://img.shields.io/badge/status-stable-success.svg)

> [!IMPORTANT]
> **"Security first. Because you can't control the randomness of an LLM with another random LLM."**

---

## The Problem

I wanted to use an AI agent on my machine, but I didn't trust giving it shell access without control. Current frameworks lack native enforcement on tools and rely almost exclusively on model compliance or fragile prompt engineering. I built Guardian as a deterministic intermediate layer to take the final decision-making power away from the LLM when it comes to executing commands on the system.

## How it works

The Guardian operates a 4-layer validation pipeline. It is "Fail-Closed" by design: if a layer has a doubt, the command is blocked.

1.  **L1: Binary Allowlist**: Immediate filter based on risk zones (green, yellow, red). If a binary is not explicitly permitted in the current context, the execution dies here.
2.  **L2: Regex Pattern Matching**: A dual-path ReDoS-safe engine that checks both the raw and normalized command against patterns of obfuscation, exfiltration, and destruction.
3.  **L3: Intent Coherence Mapping**: This is the differentiator. It verifies that the command is coherent with the assigned task by classifying them into intent families (read, write, delete).
    - *Example: task="analyze disk usage" + command="rm -rf /tmp" -> **BLOCKED** (conflict between 'read' intent and 'delete' action).*
4.  **L4: LLM Semantic Check**: The LLM is the last resort. It is consulted only for ambiguous cases that deterministic layers cannot resolve, adding a final level of semantic understanding.

## Why determinism first

I prioritized deterministic checks over LLM-based validation for three reasons:
- **Transparency**: You can audit the regex and the mappings. You know exactly why a command was blocked.
- **Speed**: Deterministic checks take milliseconds and require zero tokens.
- **Reliability**: Logic does not "hallucinate". It offers a rigid boundary that no prompt injection can jump.

## The integration wall

Agent frameworks block calls to private IPs by design for SSRF protection. This is an intentional and correct choice, but it has a heavy side effect: Guardian's enforcement today depends on model compliance (which must be instructed to call the middleware) rather than a native hard hook in the framework. This is an open problem for the entire ecosystem: true, unbreakable automatic enforcement will only arrive when frameworks implement native pre-tool hooks.

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

## Use cases

- **Local Testing**: Developers testing AI agents locally who want to understand what they are trying to do before giving total access.
- **Audit & Compliance**: Those who need immutable logs of every single command attempted by an agent, including rejections.
- **Hard Chokepoint**: Those who want a real filter between the LLM and the shell without hoping the model "behaves well" by following system instructions.

## Threat Model & Limits

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
