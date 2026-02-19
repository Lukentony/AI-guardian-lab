# AI Guardian Lab - Configuration Guide

## Overview

AI Guardian Lab is a security-first middleware designed to intercept and analyze AI-generated commands. It uses **LiteLLM** to support a wide range of LLM providers (Ollama, OpenAI, Groq, etc.).

## 🚀 Quick Setup

### 1. Environment Variables (.env)
Create a `.env` file in the root directory:

```env
API_KEY=your_secure_random_key_here
LLM_PROVIDER=ollama
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL_CODER=qwen2.5-coder:7b
OLLAMA_MODEL_EXPLAIN=llama3.2:3b-instruct
```

### 2. Start the Lab
```bash
docker compose up -d
```

---

## 🛡️ Security Governance

### Binary Allowlisting (Zonal Enforcement)
File: `guardian/config/policy.yaml`

The Guardian uses three safety zones to classify binaries:
- **Green**: Safe, common utilities (ls, pwd, echo).
- **Yellow**: Potentially risky, always logged (curl, git, wget).
- **Red**: Critically dangerous, blocked by default (rm, sudo, mkfs).

Set `mode: enforced` in `policy.yaml` to activate strict blocking.

### Content Analysis (Regex Patterns)
File: `guardian/config/patterns.yaml`

Commands are scanned for dangerous patterns (e.g., base64 bypasses, subshells, ReDoS attacks). Every regex evaluation is capped at 1.0 second to prevent Denial of Service.

---

## 🛠️ Advanced Configuration

### Resource Constraints
Defined in `docker-compose.yml`, each service is capped to:
- **CPU**: 0.5 - 0.75
- **Memory**: 256MB - 1GB
This prevents a compromised agent from exhausting the host's resources.

### Custom LLM Providers
Since we use LiteLLM, you can easily switch to Claude, Gemini, or DeepSeek by adding the respective API keys to your `.env` and updating `LLM_PROVIDER`.

---

## ❓ Troubleshooting

### Check Service Health
```bash
docker compose ps
curl http://localhost:5001/health
```

### Log Inspection
```bash
docker compose logs -f guardian
```

---
*"Security and stability over feature bloat."*
