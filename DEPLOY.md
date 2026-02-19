# Deployment Guide

## Prerequisites
- **Ubuntu 24.04** or any modern Linux/Windows/macOS with Docker.
- **Docker + Docker Compose (V2)**
- **Python 3.11+**
- **Accessible Ollama Server** (Local or Remote)

## Installation

```bash
# 1. Clone the project
git clone https://github.com/Lukentony/ai-guardian-lab.git
cd ai-guardian-lab

# 2. Build and Start the stack
docker compose up -d

# 3. Verify deployment
docker compose ps
curl http://localhost:5001/health
```

## Operational Guidelines
The laboratory is designed to be **Fail-Closed**. 
- Ensure your `API_KEY` is set in `.env`.
- Review `guardian/config/policy.yaml` to allow necessary binaries.

## Troubleshooting

### Network Issues
Ensure `agent-net` is created by Docker Compose. If not:
```bash
docker network create agent-net
```

### Unprivileged Permissions
If the containers fail to write to the `database/` folder, ensure the host directory has write permissions for the container users (UID 1000/1001).

---
*"Security and stability over feature bloat."*
